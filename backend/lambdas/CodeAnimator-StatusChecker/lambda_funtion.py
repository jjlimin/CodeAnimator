import json
import boto3
import logging
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CodeAnimatorTable')

def lambda_handler(event, context):
    # Get parameters from query string or direct event
    request_id = context.aws_request_id
    params = event.get('queryStringParameters') or {}
    user_id = params.get('userId') or event.get('userId')
    project_id = params.get('projectId') or event.get('projectId')

    logger.info(f"[request_id:{request_id}]: Received status request for User: {user_id}, Project: {project_id}")

    if not user_id or not project_id:
        logger.warning(f"[request_id:{request_id}]: Missing userId or projectId in request")
        return _response(400, {'error': 'Missing userId or projectId'})

    try:
        logger.info(f"[request_id:{request_id}]: Querying DynamoDB for status of User: {user_id}, Project: {project_id}")
        result = table.get_item(
            Key={
                'UserID': user_id,
                'ProjectID': f'PROJ#{project_id}'
            }
        )
        logger.info(f"[request_id:{request_id}]: DynamoDB query result (for User: {user_id}, Project: {project_id}) is {result}")

        item = result.get('Item')
        if not item:
            logger.warning(f"[request_id:{request_id}]: No item found in DynamoDB for User: {user_id}, Project: {project_id}")
            return _response(404, {'error': 'Project not found'})

        status = item.get('Status', 'Unknown')

        if status == 'Done':
            return _response(200, {
                'Status': status,
                'S3_VideoUrl': item.get('VideoURL')
            })

        return _response(200, {'Status': status})

    except Exception as e:
        logger.error(f"[request_id:{request_id}]: Error accessing DynamoDB for User: {user_id}, Project: {project_id}: {str(e)}")
        return _response(500, {'error': 'Internal server error accessing database'})


def _response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }