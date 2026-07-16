import json
import boto3

dynamodb = boto3.client('dynamodb')
TABLE_NAME = 'CodeAnimatorJobs'

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
        return {
            "statusCode": 200,
            "body": json.dumps({
                "job_id": item['job_id']['S'],
                "status": item.get('status', {}).get('S', 'UNKNOWN'),
                "video_url": item.get('video_url', {}).get('S', '')
            })
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}