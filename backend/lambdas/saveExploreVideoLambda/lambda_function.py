"""POST /explore/save — copy a shared video (+ its code) into the caller's
own history. Body: { "job_id": "<explore job id>" }.

The video is never duplicated in S3 — the new row just points at the same
video_url; presigning happens fresh on read, same as every other job
(CheckStatusLambda / listJobsLambda). Rejects anything that isn't currently
shared and completed, even if the job_id is known/guessed, so this can't be
used to pull a private or in-progress job into someone else's history.
"""
import json
import uuid
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
        source_job_id = (body.get('job_id') or '').strip()
        if not source_job_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing job_id"})}

        existing = dynamodb.get_item(TableName=TABLE_NAME, Key={'job_id': {'S': source_job_id}})
        source = existing.get('Item')
        if not source:
            return {"statusCode": 404, "body": json.dumps({"error": "Video not found"})}
        if (source.get('is_shared', {}).get('S') != 'true'
                or source.get('status', {}).get('S') != 'COMPLETED'):
            return {"statusCode": 403, "body": json.dumps({"error": "This video isn't available to save"})}

        new_job_id = str(uuid.uuid4())
        item = {
            'job_id': {'S': new_job_id},
            'status': {'S': 'COMPLETED'},
            'created_at': {'S': datetime.now(timezone.utc).isoformat()},
            'title': source.get('title', {'S': 'Untitled'}),
            'user_code': source.get('user_code', {'S': ''}),
            'video_url': source.get('video_url', {'S': ''}),
            'user_id': {'S': user_id},
        }
        dynamodb.put_item(TableName=TABLE_NAME, Item=item)

        return {"statusCode": 200, "body": json.dumps({"job_id": new_job_id})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
