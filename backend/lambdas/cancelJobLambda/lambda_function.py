"""DELETE /job?job_id=... — cancel an in-progress job.

Stops the Step Functions execution (its name is the job_id) so the render
actually halts, and DELETES the job so its row disappears from the user's
history (a cancelled job has no video, so there is nothing to keep).
Ownership is enforced via the Cognito sub.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
stepfunctions = boto3.client('stepfunctions')

TABLE_NAME = 'CodeAnimatorJobs'
EXECUTION_ARN_PREFIX = 'arn:aws:states:us-east-1:719246278807:execution:ai-code-animator-state-machine:'


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

        # Never delete a finished video.
        if item.get('status', {}).get('S', '') == 'COMPLETED':
            return {"statusCode": 200, "body": json.dumps({"job_id": job_id, "status": "COMPLETED"})}

        # Stop the state machine execution (halts the Fargate render too).
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
