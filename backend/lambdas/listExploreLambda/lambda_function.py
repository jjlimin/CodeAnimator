"""GET /explore — public feed of shared videos, newest first.

Queries the explore-index GSI (partition key is_shared="true", sort key
shared_at) so only videos their owner opted into sharing ever show up here.
No auth required to browse (mirrors CheckStatusLambda's existing
no-auth-enforced pattern) — this is a public gallery, not a private job.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = 'CodeAnimatorJobs'
INDEX_NAME = 'explore-index'
BUCKET_NAME = 'code-animator-media-bucket-2026'
PRESIGN_EXPIRY_SECONDS = 3600


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
        resp = dynamodb.query(
            TableName=TABLE_NAME,
            IndexName=INDEX_NAME,
            KeyConditionExpression='is_shared = :s',
            ExpressionAttributeValues={':s': {'S': 'true'}},
            ScanIndexForward=False,  # newest shared first
            Limit=50,
        )

        videos = [
            {
                'job_id': item['job_id']['S'],
                'title': item.get('title', {}).get('S', ''),
                'owner_name': item.get('owner_name', {}).get('S', ''),
                'shared_at': item.get('shared_at', {}).get('S', ''),
                'video_url': presign(item.get('video_url', {}).get('S', '')),
            }
            for item in resp.get('Items', [])
        ]

        return {"statusCode": 200, "body": json.dumps({"videos": videos})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
