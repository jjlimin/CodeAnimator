import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CodeAnimatorTable')


def lambda_handler(event, context):
    # Get parameters from query string or direct event
    params = event.get('queryStringParameters') or {}
    user_id = params.get('userId') or event.get('userId')
    project_id = params.get('projectId') or event.get('projectId')

    print(f"Received request for User: {user_id}, Project: {project_id}")

    if not user_id or not project_id:
        return _response(400, {'error': 'Missing userId or projectId'})

    try:
        result = table.get_item(
            Key={
                'UserID': user_id,
                'ProjectID': f'PROJ#{project_id}'
            }
        )
        print(f"LOG LOG LOG LOG LOG FOR TEST LOG LOG LOG {result}")
        item = result.get('Item')
        if not item:
            return _response(404, {'error': 'Project not found'})

        status = item.get('Status', 'Unknown')

        if status == 'Done':
            return _response(200, {
                'Status': status,
                'S3_VideoUrl': item.get('VideoURL')
            })

        return _response(200, {'Status': status})

    except Exception as e:
        print(f"Error: {str(e)}")
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