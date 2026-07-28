import ast
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
    try:
        return event['requestContext']['authorizer']['jwt']['claims']['sub']
    except (KeyError, TypeError):
        return None


def default_title():
    return datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')


def validate_python_code(code):
    """Return None if the code looks runnable, else a short human-readable error.

    Two static tiers (no code is executed):
      1. compile() -> syntax / parse errors (e.g. print(Hello World!)).
      2. pyflakes  -> undefined names (e.g. print(xsd), or gibberish that is a
         syntactically valid but undefined identifier)."""
    # Tier 1: syntax.
    try:
        tree = compile(code, '<user_code>', 'exec', ast.PyCF_ONLY_AST)
    except SyntaxError as e:
        loc = f" (line {e.lineno})" if e.lineno else ""
        return f"{e.msg}{loc}"
    except Exception as e:  # e.g. ValueError for null bytes
        return str(e)

    # Tier 2: undefined names via pyflakes (static, safe). Only undefined-name
    # findings block generation — other lints (unused import, etc.) are ignored.
    try:
        from pyflakes.checker import Checker
        from pyflakes.messages import UndefinedName, UndefinedLocal
        result = Checker(tree, filename='<user_code>')
        for m in result.messages:
            if isinstance(m, (UndefinedName, UndefinedLocal)):
                return f"{m.message % m.message_args} (line {m.lineno})"
    except Exception:
        pass  # if pyflakes is unavailable, fall back to syntax-only checking

    return None


def lambda_handler(event, context):
    try:
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if isinstance(body_str, str) else body_str
        user_code = body.get('user_code')

        if not user_code:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_code"})}

        # mode is set only when the user has chosen how to handle broken code.
        mode = body.get('mode')  # None | 'explain_bug'
        code_error = validate_python_code(user_code)

        # Broken code and the user hasn't chosen yet -> ask them what to do,
        # without starting a job.
        if code_error and mode != 'explain_bug':
            return {
                "statusCode": 200,
                "body": json.dumps({"needs_choice": True, "error": code_error}),
            }

        job_id = str(uuid.uuid4())
        user_id = get_user_id(event)
        title = (body.get('title') or '').strip() or default_title()
        # Requested explanation depth from the UI; AIAgent uses it in the prompt.
        complexity = body.get('complexity') or 'balanced'
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

        sf_input = {"job_id": job_id, "user_code": user_code, "complexity": complexity}
        # explain_bug mode: the video explains the broken code (never rewrites it).
        if mode == 'explain_bug' and code_error:
            sf_input['mode'] = 'explain_bug'
            sf_input['code_error'] = code_error

        if STATE_MACHINE_ARN:
            stepfunctions.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=job_id,
                input=json.dumps(sf_input),
            )

        return {
            "statusCode": 200,
            "body": json.dumps({"job_id": job_id, "title": title, "message": "Job started"}),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
