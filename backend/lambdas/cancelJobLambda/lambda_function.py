"""DELETE /job?job_id=... — cancel an in-progress job, or delete a finished
one.

If the job is still PENDING/RUNNING: stops the Step Functions execution (its
name is the job_id) so the render actually halts, then deletes the row.
If the job is COMPLETED: deletes every S3 object under its prefix (all scene
renders + the final video), then the row — the user asked to remove the
video entirely, not just hide it from the list.
Ownership is enforced via the Cognito sub.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
stepfunctions = boto3.client('stepfunctions')
s3 = boto3.client('s3')

TABLE_NAME = 'CodeAnimatorJobs'
BUCKET_NAME = 'code-animator-media-bucket-2026'
EXECUTION_ARN_PREFIX = 'arn:aws:states:us-east-1:719246278807:execution:ai-code-animator-state-machine:'


def delete_job_media(job_id):
    """Delete every S3 object under this job's prefix — scene renders and
    the concatenated final video all live under the same jobs/{job_id}/ key."""
    prefix = f'jobs/{job_id}/'
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        keys = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        if keys:
            s3.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': keys})


def get_user_id(event):
    try:
        return event['requestContext']['authorizer']['jwt']['claims']['sub']
    except (KeyError, TypeError):
        return None


def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)
        if not user_id:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        params = event.get('queryStringParameters') or {}
        job_id = params.get('job_id')
        if not job_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing job_id"})}

        existing = dynamodb.get_item(TableName=TABLE_NAME, Key={'job_id': {'S': job_id}})
        item = existing.get('Item')
        if not item:
            return {"statusCode": 200, "body": json.dumps({"job_id": job_id, "status": "DELETED"})}
        if item.get('user_id', {}).get('S') != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        if item.get('status', {}).get('S', '') == 'COMPLETED':
            # A finished video: the user wants it gone, media included.
            delete_job_media(job_id)
        else:
            # Still in progress: stop the state machine execution (halts the
            # Fargate render too). No media exists yet for these jobs.
            try:
                stepfunctions.stop_execution(
                    executionArn=EXECUTION_ARN_PREFIX + job_id,
                    cause='Cancelled by user',
                )
            except stepfunctions.exceptions.ExecutionDoesNotExist:
                pass

        # Remove the job entirely so its row disappears from history.
        dynamodb.delete_item(TableName=TABLE_NAME, Key={'job_id': {'S': job_id}})

        return {"statusCode": 200, "body": json.dumps({"job_id": job_id, "status": "DELETED"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
