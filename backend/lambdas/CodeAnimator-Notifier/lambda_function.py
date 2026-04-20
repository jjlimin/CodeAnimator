import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CodeAnimatorTable')

BUCKET_NAME = 'code-animator-assets'
PRESIGNED_URL_EXPIRY = 60 * 60 * 24 * 7  # 7 days


def lambda_handler(event, context):
    user_id = event.get('UserID')
    job_id = event.get('ProjectID')

    if not user_id or not job_id:
        raise ValueError(f"Missing UserID or ProjectID in event: {event}")

    video_s3_key = f'projects/{job_id}/animation.mp4'

    # Generate a pre-signed URL so the frontend can stream/download the video
    video_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': video_s3_key},
        ExpiresIn=PRESIGNED_URL_EXPIRY
    )

    # Mark job as finished in DynamoDB and store the video URL
    table.update_item(
        Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
        UpdateExpression="set #s = :status_val, VideoS3Key = :s3key, VideoURL = :url, FinishedAt = :ts",
        ExpressionAttributeNames={'#s': 'Status'},
        ExpressionAttributeValues={
            ':status_val': 'Done',
            ':s3key': video_s3_key,
            ':url': video_url,
            ':ts': datetime.utcnow().isoformat()
        }
    )

    print(f"Job {job_id} finished. Video at s3://{BUCKET_NAME}/{video_s3_key}")

    return {
        'statusCode': 200,
        'UserID': user_id,
        'ProjectID': job_id,
        'video_s3_key': video_s3_key,
        'video_url': video_url,
        'status': 'Done'
    }
