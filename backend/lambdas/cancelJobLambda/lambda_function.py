"""DELETE /job?job_id=... — cancel an in-progress job.

Stops the Step Functions execution (its name is the job_id) so the render
actually halts, and marks the job CANCELLED. Ownership is enforced via the
Cognito sub.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
stepfunctions = boto3.client('stepfunctions')

TABLE_NAME = 'CodeAnimatorJobs'
STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:719246278807:stateMachine:ai-code-animator-state-machine'
# Execution name == job_id (see createJobLambda), so the execution ARN is derived.
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
            return {"statusCode": 404, "body": json.dumps({"error": "Job not found"})}
        if item.get('user_id', {}).get('S') != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        status = item.get('status', {}).get('S', '')
        if status in ('COMPLETED', 'CANCELLED', 'FAILED'):
            return {"statusCode": 200, "body": json.dumps({"job_id": job_id, "status": status})}

        # Stop the state machine execution (halts the Fargate render too).
        try:
            stepfunctions.stop_execution(
                executionArn=EXECUTION_ARN_PREFIX + job_id,
                cause='Cancelled by user',
            )
        except stepfunctions.exceptions.ExecutionDoesNotExist:
            pass  # already finished / never started — still mark cancelled

        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #st = :s',
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={':s': {'S': 'CANCELLED'}},
        )

        return {"statusCode": 200, "body": json.dumps({"job_id": job_id, "status": "CANCELLED"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
