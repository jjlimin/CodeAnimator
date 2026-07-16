import json
import boto3

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = 'CodeAnimatorJobs'
BUCKET_NAME = 'code-animator-media-bucket-2026'
PRESIGN_EXPIRY_SECONDS = 3600


def lambda_handler(event, context):
    try:
        job_id = event.get('queryStringParameters', {}).get('job_id')

        if not job_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing job_id"})}

        response = dynamodb.get_item(
            TableName=TABLE_NAME,
            Key={'job_id': {'S': job_id}}
        )

        if 'Item' not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Job not found"})}

        item = response['Item']
        video_url = item.get('video_url', {}).get('S', '')

        # הבאקט פרטי — ממירים את ה-URL הקבוע שנשמר ב-DynamoDB
        # ל-Presigned URL זמני שהדפדפן יכול לנגן ולהוריד ממנו
        if video_url:
            s3_key = video_url.split('.amazonaws.com/', 1)[-1]
            video_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=PRESIGN_EXPIRY_SECONDS
            )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "job_id": item['job_id']['S'],
                "status": item.get('status', {}).get('S', 'UNKNOWN'),
                "video_url": video_url
            })
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
