"""GET /jobs — returns the authenticated user's jobs, newest first.

Powers the sidebar history AND the refresh-restore behaviour: the frontend
calls this on load, shows past videos, and resumes polling any job still
PENDING/RUNNING.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = 'CodeAnimatorJobs'
INDEX_NAME = 'user_id-created_at-index'
BUCKET_NAME = 'code-animator-media-bucket-2026'
PRESIGN_EXPIRY_SECONDS = 3600


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
            status = item.get('status', {}).get('S', 'UNKNOWN')
            video_url = item.get('video_url', {}).get('S', '')
            jobs.append({
                'job_id': item['job_id']['S'],
                'title': item.get('title', {}).get('S', ''),
                'status': status,
                'created_at': item.get('created_at', {}).get('S', ''),
                'video_url': presign(video_url) if status == 'COMPLETED' else '',
            })

        return {"statusCode": 200, "body": json.dumps({"jobs": jobs})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
