"""GET /jobs — returns the authenticated user's jobs, newest first.

Only shows jobs that are meaningful to the user:
  - COMPLETED  -> a real video (with a presigned URL).
  - genuinely in-progress -> PENDING/RUNNING whose Step Functions execution is
    still alive.
Anything else (cancelled, failed, or a job whose render died leaving it stuck
in PENDING) is junk with no video, so it is DELETED and excluded here — this
self-cleans the history on every load.
"""
import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
sfn = boto3.client('stepfunctions')

TABLE_NAME = 'CodeAnimatorJobs'
INDEX_NAME = 'user_id-created_at-index'
BUCKET_NAME = 'code-animator-media-bucket-2026'
PRESIGN_EXPIRY_SECONDS = 3600
EXEC_ARN_PREFIX = 'arn:aws:states:us-east-1:719246278807:execution:ai-code-animator-state-machine:'
ACTIVE_STATUSES = ('PENDING', 'RUNNING')
# Never treat a very fresh job as junk — its execution may not be queryable the
# instant after it starts (avoids a race that would delete a real in-progress job).
GRACE_SECONDS = 120


def is_fresh(created_at):
    try:
        dt = datetime.fromisoformat(created_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() < GRACE_SECONDS
    except Exception:
        return False


def get_user_id(event):
    try:
        return event['requestContext']['authorizer']['jwt']['claims']['sub']
    except (KeyError, TypeError):
        return None


def presign(video_url):
    if not video_url:
        return ''
    s3_key = video_url.split('.amazonaws.com/', 1)[-1]
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=PRESIGN_EXPIRY_SECONDS,
    )


def execution_alive(job_id):
    """True if the job's execution is still running (or just succeeded and the
    video is on the way). False if it failed/aborted/timed out/gone."""
    try:
        status = sfn.describe_execution(executionArn=EXEC_ARN_PREFIX + job_id)['status']
    except Exception:
        return False
    return status in ('RUNNING', 'SUCCEEDED')


def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)
        if not user_id:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        resp = dynamodb.query(
            TableName=TABLE_NAME,
            IndexName=INDEX_NAME,
            KeyConditionExpression='user_id = :u',
            ExpressionAttributeValues={':u': {'S': user_id}},
            ScanIndexForward=False,  # newest first
            Limit=50,
        )

        jobs = []
        for item in resp.get('Items', []):
            job_id = item['job_id']['S']
            status = item.get('status', {}).get('S', 'UNKNOWN')
            video_url = item.get('video_url', {}).get('S', '')

            if status == 'COMPLETED':
                jobs.append({
                    'job_id': job_id,
                    'title': item.get('title', {}).get('S', ''),
                    'status': status,
                    'created_at': item.get('created_at', {}).get('S', ''),
                    'video_url': presign(video_url),
                })
                continue

            created_at = item.get('created_at', {}).get('S', '')
            # Keep genuinely in-progress jobs (live execution) AND brand-new jobs
            # whose execution may not be queryable yet.
            if status in ACTIVE_STATUSES and (is_fresh(created_at) or execution_alive(job_id)):
                jobs.append({
                    'job_id': job_id,
                    'title': item.get('title', {}).get('S', ''),
                    'status': status,
                    'created_at': created_at,
                    'video_url': '',
                })
                continue

            # Junk (cancelled / failed / stuck) -> delete and skip.
            try:
                dynamodb.delete_item(TableName=TABLE_NAME, Key={'job_id': {'S': job_id}})
            except Exception:
                pass

        return {"statusCode": 200, "body": json.dumps({"jobs": jobs})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
