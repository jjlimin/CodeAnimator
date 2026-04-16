import json
import boto3
import ast
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CodeAnimatorTable')
BUCKET_NAME = 'code-animator-assets'

def ast_to_dict(node):
    """
    Recursive helper to convert AST nodes into a dictionary format.
    """
    result = {'node_type': node.__class__.__name__}
    
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            result[field] = [ast_to_dict(item) if isinstance(item, ast.AST) else item for item in value]
        elif isinstance(value, ast.AST):
            result[field] = ast_to_dict(value)
        else:
            result[field] = value
            
    if hasattr(node, 'lineno'):
        result['lineno'] = node.lineno
        
    return result

def lambda_handler(event, context):
    user_id = event.get('UserID')
    job_id = event.get('ProjectID')
    raw_code = event.get('code', '')

    if not user_id or not job_id:
        return {'statusCode': 400, 'body': 'Missing UserID or ProjectID'}

    try:
        # Update status in DynamoDB
        table.update_item(
            Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
            UpdateExpression="set #s = :status_val, startTime = :time_val",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={
                ':status_val': 'Parsing',
                ':time_val': datetime.now().isoformat()
            }
        )

        # Convert raw code to AST JSON
        parsed_tree = ast.parse(raw_code)
        ast_json = ast_to_dict(parsed_tree)

        # Upload AST JSON to S3
        s3_key = f'projects/{job_id}/ast_structure.json'
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps({
                "job_id": job_id,
                "user_id": user_id,
                "ast_data": ast_json
            }),
            ContentType='application/json'
        )

        return {
            'statusCode': 200,
            'UserID': user_id,
            'ProjectID': job_id,
            'ast_s3_key': s3_key,
            'status': 'Parsed'
        }

    except SyntaxError as se:
        table.update_item(
            Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
            UpdateExpression="set #s = :status_val, errorMessage = :err_val",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={':status_val': 'SyntaxError', ':err_val': str(se)}
        )
        return {'statusCode': 400, 'body': f'Invalid Python code: {str(se)}'}
        
    except Exception as e:
        table.update_item(
            Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
            UpdateExpression="set #s = :status_val, errorMessage = :err_val",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={':status_val': 'Error', ':err_val': str(e)}
        )
        raise e