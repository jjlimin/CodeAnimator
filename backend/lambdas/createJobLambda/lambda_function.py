import json
import boto3
import uuid
import os
from datetime import datetime, timezone

dynamodb = boto3.client('dynamodb')
stepfunctions = boto3.client('stepfunctions')

TABLE_NAME = 'CodeAnimatorJobs'
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')


def get_user_id(event):
    """Cognito user id (sub) from the API Gateway JWT authorizer claims.
    Returns None if the request is not authenticated (keeps the endpoint
    working before the authorizer cutover)."""
    try:
        return event['requestContext']['authorizer']['jwt']['claims']['sub']
    except (KeyError, TypeError):
        return None


def default_title():
    # Default title = human-readable creation time; the user can rename it later.
    return datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')


def lambda_handler(event, context):
    try:
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        user_code = body.get('user_code')

        if not user_code:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_code"})}

        job_id = str(uuid.uuid4())
        user_id = get_user_id(event)
        title = (body.get('title') or '').strip() or default_title()
        created_at = datetime.now(timezone.utc).isoformat()

        item = {
            'job_id': {'S': job_id},
            'status': {'S': 'PENDING'},
            'created_at': {'S': created_at},
            'title': {'S': title},
        }
        # Only set user_id when authenticated, so it lands in the GSI.
        if user_id:
            item['user_id'] = {'S': user_id}

        dynamodb.put_item(TableName=TABLE_NAME, Item=item)

        if STATE_MACHINE_ARN:
            stepfunctions.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=job_id,
                input=json.dumps({"job_id": job_id, "user_code": user_code})
            )

        return {
            "statusCode": 200,
            "body": json.dumps({"job_id": job_id, "title": title, "message": "Job started"})
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
