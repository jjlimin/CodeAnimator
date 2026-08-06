"""PATCH /job — rename a job's title and/or toggle Explore sharing.
Body: { "job_id": "...", "title"?: "...", "is_shared"?: true|false, "owner_name"?: "..." }

Only the owner (matching Cognito sub) may update; the ownership check prevents
one user from editing another user's video. is_shared=true stamps shared_at
(sort key for the explore-index GSI) and, if given, owner_name — cached here
so listExploreLambda never needs a cross-user Cognito lookup. is_shared=false
removes both attributes, pulling the job out of Explore (sparse GSI).
"""
import json
import boto3
from datetime import datetime, timezone

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
        is_shared = body.get('is_shared')  # True | False | None (untouched)
        owner_name = (body.get('owner_name') or '').strip()

        if not job_id or (not title and is_shared is None):
            return {"statusCode": 400, "body": json.dumps({"error": "Missing job_id, or nothing to update"})}

        existing = dynamodb.get_item(TableName=TABLE_NAME, Key={'job_id': {'S': job_id}})
        item = existing.get('Item')
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Job not found"})}
        if item.get('user_id', {}).get('S') != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        set_clauses = []
        remove_clauses = []
        values = {}

        if title:
            set_clauses.append('title = :t')
            values[':t'] = {'S': title}

        if is_shared is True:
            set_clauses.append('is_shared = :s')
            values[':s'] = {'S': 'true'}
            set_clauses.append('shared_at = :sa')
            values[':sa'] = {'S': datetime.now(timezone.utc).isoformat()}
            if owner_name:
                set_clauses.append('owner_name = :on')
                values[':on'] = {'S': owner_name}
        elif is_shared is False:
            remove_clauses.extend(['is_shared', 'shared_at'])

        expr = ''
        if set_clauses:
            expr += 'SET ' + ', '.join(set_clauses)
        if remove_clauses:
            expr += (' ' if expr else '') + 'REMOVE ' + ', '.join(remove_clauses)

        update_kwargs = {
            'TableName': TABLE_NAME,
            'Key': {'job_id': {'S': job_id}},
            'UpdateExpression': expr,
        }
        if values:
            update_kwargs['ExpressionAttributeValues'] = values
        dynamodb.update_item(**update_kwargs)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "job_id": job_id,
                "title": title or item.get('title', {}).get('S', ''),
                "is_shared": bool(is_shared) if is_shared is not None else None,
            }),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
