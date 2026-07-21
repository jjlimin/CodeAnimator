"""PATCH /job — rename a job's title. Body: { "job_id": "...", "title": "..." }

Only the owner (matching Cognito sub) may rename; the ownership check prevents
one user from editing another user's video.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
TABLE_NAME = 'CodeAnimatorJobs'


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

        body_str = event.get('body', '{}')
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        job_id = body.get('job_id')
        title = (body.get('title') or '').strip()

        if not job_id or not title:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing job_id or title"})}

        existing = dynamodb.get_item(TableName=TABLE_NAME, Key={'job_id': {'S': job_id}})
        item = existing.get('Item')
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Job not found"})}
        if item.get('user_id', {}).get('S') != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET title = :t',
            ExpressionAttributeValues={':t': {'S': title}},
        )

        return {"statusCode": 200, "body": json.dumps({"job_id": job_id, "title": title})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
