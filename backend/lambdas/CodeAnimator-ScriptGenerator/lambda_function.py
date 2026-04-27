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
Goal: Generate a JSON object that maps specific lines of Python code to visual animations and narration.

=== 1. TOP-LEVEL JSON STRUCTURE ===
{
  "metadata": { "project_name": "<string>" },
  "script": [ <step>, <step>, ... ]
}

Each step object MUST have exactly these five keys:
  "step_id"        : integer, starting at 1, incrementing by 1
  "line_number"    : integer, 1-based line number in the original source
  "code_snippet"   : string, exact code being executed in this step
  "narration"      : string, beginner-friendly explanation (longer = more animation time)
  "visual_commands": array of command objects (see Section 2)

=== 2. COMMAND API — EXACT FIELD NAMES ===

Every command object must have a "command" key. Use ONLY the field names listed below.
Do NOT invent new field names. Field names are case-sensitive.

--- MEMORY COMMANDS ---

CREATE_VARIABLE — create a single variable box
  Required: "command", "id", "type", "label", "initial_value"
  Optional: "position"  ("LEFT" | "CENTER" | "RIGHT")
  "type" values: "ValueBox" (int/float), "StringBox" (str), "BooleanBox" (bool), "ScopeFrame" (function scope)
  Example:
    { "command": "CREATE_VARIABLE", "id": "var_n", "type": "ValueBox", "label": "n", "initial_value": 7, "position": "CENTER" }

CREATE_COLLECTION — create a list/array or dict
  Required: "command", "id", "type", "label", "initial_value"
  Optional: "position"
  "type" values: "BoxSeries" (list/array), "NodeGraph" (dict)
  "initial_value" MUST be a JSON array (for BoxSeries) or JSON object (for NodeGraph) — NOT a string.
  Example:
    { "command": "CREATE_COLLECTION", "id": "arr", "type": "BoxSeries", "label": "elements", "initial_value": [64, 34, 25, 12], "position": "LEFT" }

DESTROY_OBJECT — remove an object from the scene
  Required: "command", "target_id"
  Example:
    { "command": "DESTROY_OBJECT", "target_id": "var_n" }

LINK_TARGET — draw an arrow between two objects
  Required: "command", "source_id", "target_id"
  Optional: "id"
  Example:
    { "command": "LINK_TARGET", "source_id": "ptr_i", "target_id": "arr" }

--- STATE COMMANDS ---

UPDATE_VALUE — animate a variable changing its value
  Required: "command", "target_id", "value"
  ("value" is the NEW value to display — do NOT use "new_value")
  Example:
    { "command": "UPDATE_VALUE", "target_id": "var_n", "value": 5 }

ANIMATE_MATH — show a math expression animating to its result
  Required: "command", "expression"
  Optional: "result", "target_id", "id"
  Example:
    { "command": "ANIMATE_MATH", "expression": "n - 1", "result": 6, "target_id": "var_n" }

--- COLLECTION COMMANDS ---

SWAP — swap two elements inside a BoxSeries
  Required: "command", "target_id", "index_a", "index_b"
  ("target_id" is the id of the BoxSeries — do NOT use "collection_id")
  "index_a" and "index_b" MUST be concrete integers (0-based). Never use variable names or expressions.
  Example:
    { "command": "SWAP", "target_id": "arr", "index_a": 2, "index_b": 3 }

APPEND_ELEMENT — add a value to the end of a BoxSeries
  Required: "command", "target_id", "element"
  Example:
    { "command": "APPEND_ELEMENT", "target_id": "arr", "element": 99 }

INSERT_AT — insert a value at a specific index
  Required: "command", "target_id", "index", "element"
  "index" MUST be a concrete integer.
  Example:
    { "command": "INSERT_AT", "target_id": "arr", "index": 1, "element": 42 }

POP_ELEMENT — remove an element from a BoxSeries
  Required: "command", "target_id"
  Optional: "index" (integer, defaults to last element)
  Example:
    { "command": "POP_ELEMENT", "target_id": "arr", "index": 0 }

--- FLOW / EMPHASIS COMMANDS ---

MOVE_POINTER — glide a pointer arrow to point at an object or a specific cell
  Required: "command", "pointer_id", "target_id"
  ("pointer_id" is the id of the Pointer object — you MUST provide it; create the pointer with CREATE_VARIABLE first if it doesn't exist yet)
  Optional: "index" (integer — which cell of a BoxSeries to point at)
  Example:
    { "command": "MOVE_POINTER", "pointer_id": "ptr_j", "target_id": "arr", "index": 2 }

COMPARE_VALUES — display a comparison expression and flash the result
  Required: "command", "left", "right", "operator"
  Optional: "result_id" (id to store the display object under)
  "operator" values: "==" | "!=" | ">" | "<" | ">=" | "<="
  "left" and "right" must be concrete scalar values (not variable names).
  Example:
    { "command": "COMPARE_VALUES", "left": 34, "right": 25, "operator": ">", "result_id": "cmp1" }

HIGHLIGHT — flash a color border on any registered object
  Required: "command", "target_id", "color"
  "color" values: "GREEN" | "RED" | "YELLOW" | "BLUE" | "WHITE" | "ORANGE"
  Example:
    { "command": "HIGHLIGHT", "target_id": "arr", "color": "YELLOW" }

PRINT_TO_CONSOLE — append a line to the on-screen console panel
  Required: "command", "value"
  "value" is the string to print (use the concrete resolved value, not a variable name).
  Example:
    { "command": "PRINT_TO_CONSOLE", "value": "Sorted: [11, 12, 22, 25]" }

=== 3. CRITICAL RULES ===

A. CONCRETE VALUES ONLY — No variable expressions as indices or values.
   For loops and algorithms, UNROLL each iteration into its own step.
   WRONG: { "command": "SWAP", "target_id": "arr", "index_a": "j", "index_b": "j+1" }
   RIGHT: { "command": "SWAP", "target_id": "arr", "index_a": 2, "index_b": 3 }

B. OBJECT PERSISTENCE — Every object you CREATE must use a unique "id".
   Use that exact same id in all subsequent commands that reference the object.
   Never reference an id that hasn't been created yet.

C. POINTER SETUP — Before using MOVE_POINTER, create the pointer with CREATE_VARIABLE:
   { "command": "CREATE_VARIABLE", "id": "ptr_i", "type": "ValueBox", "label": "i", "initial_value": 0 }
   Then glide it: { "command": "MOVE_POINTER", "pointer_id": "ptr_i", "target_id": "arr", "index": 0 }

D. NARRATION LENGTH drives step duration. Write at least 1–2 full sentences per step
   so the animations are visible. Short narration = rushed animation.

E. OUTPUT — Return ONLY the raw JSON object. No markdown fences, no explanation text.

=== 4. EXAMPLE (list swap algorithm) ===

Input code:
arr = [5, 3, 1]
arr[0], arr[1] = arr[1], arr[0]
print(arr)

Output:
{
  "metadata": { "project_name": "List Swap Example" },
  "script": [
    {
      "step_id": 1,
      "line_number": 1,
      "code_snippet": "arr = [5, 3, 1]",
      "narration": "We create a list called arr containing three integers: five, three, and one. Each element lives in its own cell and is labelled with its zero-based index below.",
      "visual_commands": [
        { "command": "CREATE_COLLECTION", "id": "arr", "type": "BoxSeries", "label": "arr", "initial_value": [5, 3, 1], "position": "CENTER" }
      ]
    },
    {
      "step_id": 2,
      "line_number": 2,
      "code_snippet": "arr[0], arr[1] = arr[1], arr[0]",
      "narration": "We swap the elements at index zero and index one. Watch the five and the three trade places in an arc swap animation.",
      "visual_commands": [
        { "command": "HIGHLIGHT", "target_id": "arr", "color": "YELLOW" },
        { "command": "SWAP", "target_id": "arr", "index_a": 0, "index_b": 1 }
      ]
    },
    {
      "step_id": 3,
      "line_number": 3,
      "code_snippet": "print(arr)",
      "narration": "Finally we print the modified list. The console shows the new order: three, five, one.",
      "visual_commands": [
        { "command": "PRINT_TO_CONSOLE", "value": "[3, 5, 1]" }
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
            temperature=0.2
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
