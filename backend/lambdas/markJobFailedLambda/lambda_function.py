"""Invoked by the state machine's Catch handler when any generation/render step
errors out. Marks the job FAILED so it stops looking 'in progress' — the
frontend poll then shows a failure screen, and listJobs drops it from history.
"""
import json
import boto3

dynamodb = boto3.client('dynamodb')
TABLE_NAME = 'CodeAnimatorJobs'


def lambda_handler(event, context):
    job_id = event.get('job_id')
    if job_id:
        try:
            dynamodb.update_item(
                TableName=TABLE_NAME,
                Key={'job_id': {'S': job_id}},
                UpdateExpression='SET #st = :s',
                ExpressionAttributeNames={'#st': 'status'},
                ExpressionAttributeValues={':s': {'S': 'FAILED'}},
            )
        except Exception as e:
            print(f"markJobFailed error for {job_id}: {e}")
    return {"job_id": job_id, "status": "FAILED"}
