import json
import boto3
import uuid
import os
from datetime import datetime, timezone

dynamodb = boto3.client('dynamodb')
stepfunctions = boto3.client('stepfunctions')

TABLE_NAME = 'CodeAnimatorJobs'
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')

def lambda_handler(event, context):
    try:
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        user_code = body.get('user_code')
        
        if not user_code:
             return {"statusCode": 400, "body": json.dumps({"error": "Missing user_code"})}
             
        job_id = str(uuid.uuid4())
        
        # כתיבת סטטוס התחלתי
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                'job_id': {'S': job_id},
                'status': {'S': 'PENDING'},
                'created_at': {'S': datetime.now(timezone.utc).isoformat()}
            }
        )
        
        # הזנקת מכונת המצבים
        if STATE_MACHINE_ARN:
            stepfunctions.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=job_id,
                input=json.dumps({"job_id": job_id, "user_code": user_code})
            )
            
        return {
            "statusCode": 200,
            "body": json.dumps({"job_id": job_id, "message": "Job started"})
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}