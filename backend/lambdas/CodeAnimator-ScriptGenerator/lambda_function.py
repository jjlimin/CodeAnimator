import json
import boto3
import os
from datetime import datetime
from openai import OpenAI

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CodeAnimatorTable')
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def lambda_handler(event, context):
    # 1. Configuration and Input
    user_id = event.get('user_id') or event.get('UserID')
    job_id = event.get('job_id') or event.get('ProjectID')
    bucket_name = 'code-animator-assets'

    if not user_id or not job_id:
        return {'statusCode': 400, 'body': 'Missing UserID or ProjectID'}

    # Dynamically build the S3 key
    ast_s3_key = f'projects/{job_id}/ast_structure.json'

    try:
        # 2. Update status in DynamoDB
        table.update_item(
            Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
            UpdateExpression="set #s = :status_val",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={':status_val': 'GeneratingContent'}
        )

        # 3. Read the AST JSON from S3 (Fallback/Safety)
        # However, we prioritize the AST data coming directly from the event if available
        if 'ast_data' in event:
            print("Using AST data directly from event.")
            ast_content = event['ast_data']
        else:
            print(f"Fetching AST from S3: {ast_s3_key}")
            response = s3.get_object(Bucket=bucket_name, Key=ast_s3_key)
            full_json = json.loads(response['Body'].read().decode('utf-8'))
            ast_content = full_json.get('ast_data', full_json)

        # 4. Prepare the prompt for OpenAI
        base_instructions = """
Role: You are the "Code Animator" Storyboard Architect. Your task is to transform Python code (provided as an AST structure) into a highly detailed JSON storyboard for a Manim-based rendering engine.
Goal: Generate a JSON object that maps specific lines of Python code to visual animations and mascot narration.

1. JSON Structure Requirements:
- Metadata: Include only project_name.
- Script (Array of Steps): Each object in the script must contain:
    * step_id: Incremental integer.
    * line_number: The 1-based index of the line in the original code.
    * code_snippet: The exact string of Python code being executed in this step.
    * narration: A clear, beginner-friendly explanation spoken by the mascot. Crucial: The length of this text determines the duration of the entire step.
    * visual_commands: An array of API calls to animate the scene.

2. API Reference (Use ONLY these entities)
Visual Objects (The Registry):
- ValueBox (int/float), StringBox (quoted strings), BooleanBox (True/False).
- BoxSeries (lists/tuples), NodeGraph (dicts/sets).
- Pointer (arrows for iterators/indices), ScopeFrame (function boundaries), ConsoleOutput (terminal text).
Action Commands:
- Memory: CREATE_VARIABLE, CREATE_COLLECTION, LINK_TARGET, DESTROY_OBJECT.
- State: UPDATE_VALUE (morphing text), ANIMATE_MATH (equations), TYPE_CAST.
- Collection: SWAP (arc motion), APPEND_ELEMENT, INSERT_AT, POP_ELEMENT.
- Flow: MOVE_POINTER (glide), COMPARE_VALUES (flash green/red), EVALUATE_CONDITION.
- Emphasis: HIGHLIGHT (color change), PRINT_TO_CONSOLE.

3. Logic Rules:
- Narration-Driven Timing: The engine calculates command duration as run_time = audio_duration / number_of_commands. Ensure you provide enough narration to allow animations to be seen clearly.
- Object Persistence: You must maintain a virtual "Object Registry." If you create a variable with id: "var_x", use that same ID for all future actions on that variable.
- Line Mapping: Every step must map to a specific line_number and code_snippet from the input code to ensure the UI can sync the code highlighter with the video.

4. Output Format:
Return ONLY the JSON object. No conversational text.

Example Input/Output for the LLM
User Input Code:

val = 5
print(val)

Desired JSON Output:
{
  "metadata": {
    "project_name": "Simple Print Execution"
  },
  "script": [
    {
      "step_id": 1,
      "line_number": 1,
      "code_snippet": "val = 5",
      "narration": "We start by creating a variable named 'val' and storing the integer five inside it.",
      "visual_commands": [
        {
          "command": "CREATE_VARIABLE",
          "id": "v1",
          "type": "ValueBox",
          "label": "val",
          "initial_value": "5",
          "position": "CENTER"
        }
      ]
    },
    {
      "step_id": 2,
      "line_number": 2,
      "code_snippet": "print(val)",
      "narration": "Next, the print function takes the value from our box and sends it to the console output.",
      "visual_commands": [
        {
          "command": "HIGHLIGHT",
          "target_id": "v1",
          "color": "GREEN"
        },
        {
          "command": "PRINT_TO_CONSOLE",
          "target_id": "v1",
          "value": "5"
        }
      ]
    }
  ]
}
"""
        user_content = f"{base_instructions}\n\nINPUT AST STRUCTURE:\n{json.dumps(ast_content)}"

        # 5. Call OpenAI API via SDK
        completion = openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are an expert programming teacher who outputs valid JSON only."},
                {"role": "user", "content": user_content}
            ],
            temperature=1
        )

        script_text = completion.choices[0].message.content

        # 6. Save the generated script back to S3
        script_s3_key = f'projects/{job_id}/script.json'

        try:
            final_script_json = json.loads(script_text)
        except Exception:
            final_script_json = script_text

        s3.put_object(
            Bucket=bucket_name,
            Key=script_s3_key,
            Body=json.dumps({
                "job_id": job_id,
                "user_id": user_id,
                "script": final_script_json,
                "generated_at": datetime.now().isoformat()
            }),
            ContentType='application/json'
        )

        # 7. Final Return
        return {
            'statusCode': 200,
            'UserID': user_id,
            'ProjectID': job_id,
            'script_s3_key': script_s3_key,
            'status': 'ScriptGenerated'
        }

    except Exception as e:
        print(f"Error in Content Generator: {str(e)}")
        try:
            table.update_item(
                Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
                UpdateExpression="set #s = :status_val, errorMessage = :err",
                ExpressionAttributeNames={'#s': 'Status'},
                ExpressionAttributeValues={':status_val': 'Error', ':err': str(e)}
            )
        except Exception:
            pass
        raise e
