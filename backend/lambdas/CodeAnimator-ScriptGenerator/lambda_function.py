import json
import random
import boto3
import os
from datetime import datetime
from openai import OpenAI

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CodeAnimatorTable')
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# ---------------------------------------------------------------------------
# Algorithm detection
# ---------------------------------------------------------------------------

_ALGO_NAME_HINTS = {
    'bubble_sort':     ['bubble', 'bubblesort', 'bubble_sort'],
    'quick_sort':      ['quicksort', 'quick_sort', 'qsort'],
    'merge_sort':      ['mergesort', 'merge_sort'],
    'insertion_sort':  ['insertion_sort', 'insertionsort', 'insertionsort'],
    'selection_sort':  ['selection_sort', 'selectionsort'],
    'binary_search':   ['binary_search', 'binarysearch'],
    'linear_search':   ['linear_search', 'linearsearch'],
    'bfs':             ['breadth_first', 'bfs'],
    'dfs':             ['depth_first', 'dfs', 'inorder', 'preorder', 'postorder'],
    'fibonacci':       ['fibonacci', 'fib'],
    'factorial':       ['factorial'],
}


def _has_print_statements(ast_content: dict) -> bool:
    """Return True if the AST contains any print() calls."""
    ast_str = json.dumps(ast_content)
    # Look for Call nodes where the function is 'print'
    return '"print"' in ast_str or "'print'" in ast_str


def _detect_algorithm(ast_content: dict) -> str:
    """Detect algorithm type from AST structure and function names."""
    ast_str = json.dumps(ast_content).lower()

    # Name-based match (fastest signal)
    for algo, hints in _ALGO_NAME_HINTS.items():
        if any(h in ast_str for h in hints):
            return algo

    # Structural heuristics
    for_count   = ast_str.count('"for"')
    has_swap    = 'swap' in ast_str or ('arr[' in ast_str and 'temp' in ast_str)
    has_recurse = ast_str.count('"functiondef"') > 0 and '"return"' in ast_str
    has_pivot   = 'pivot' in ast_str
    has_mid     = 'mid' in ast_str and ('left' in ast_str or 'right' in ast_str)

    if for_count >= 2 and has_swap:
        return 'bubble_sort'
    if has_recurse and has_pivot:
        return 'quick_sort'
    if has_recurse and has_mid:
        return 'binary_search'
    if for_count >= 1 and has_swap:
        return 'selection_sort'

    return 'generic'


def _generate_test_data(algorithm_type: str):
    """Return a concrete dataset appropriate for the detected algorithm."""
    if algorithm_type in ('bubble_sort', 'quick_sort', 'merge_sort',
                          'insertion_sort', 'selection_sort'):
        return random.sample(range(11, 99), 6)
    if algorithm_type in ('binary_search', 'linear_search'):
        data = sorted(random.sample(range(1, 50), 8))
        return {'array': data, 'target': random.choice(data)}
    if algorithm_type == 'fibonacci':
        return {'n': random.randint(6, 9)}
    if algorithm_type == 'factorial':
        return {'n': random.randint(4, 7)}
    return None


# ---------------------------------------------------------------------------
# Per-algorithm prompt guidance
# ---------------------------------------------------------------------------

_ALGO_GUIDANCE = {
    'bubble_sort': """
ALGORITHM CONTEXT — Bubble Sort:
- Nested loops: outer pass i (0 to n-1), inner comparison j (0 to n-i-2)
- Each pass bubbles the largest unsorted element to the right
- After pass k, elements at indices n-k to n-1 are in final sorted position

ANIMATION RULES:
1. CREATE_COLLECTION for the array (center); CREATE_VARIABLE for i, j counters (left).
2. For every comparison in the inner loop: set fast_forward: true, iteration_group: "pass_{i_value}"
   - MARK_ELEMENT both compared cells (role: "compare")
   - COMPARE_VALUES with concrete numbers
   - If swap needed: SWAP, then re-mark if still relevant
3. After each full pass: MARK_ELEMENT the newly-sorted rightmost element (role: "sorted") + CELEBRATE it (style: "circumscribe")
4. Final step (all sorted): CELEBRATE the whole array with style "indicate" on each sorted cell
Unroll minimum 5-6 concrete compare/swap steps.
""",

    'quick_sort': """
ALGORITHM CONTEXT — Quick Sort:
- Divide-and-conquer: choose pivot, partition array, recurse on sub-arrays
- After partition, pivot lands in its exact final sorted position

ANIMATION RULES:
1. CREATE_COLLECTION for the full array (center).
2. Mark the pivot cell: MARK_ELEMENT (role: "pivot") at start of each partition call.
3. Show pointer movement (i, j) with MOVE_POINTER; fast_forward: true for each pointer step.
4. After partition: MARK_ELEMENT pivot in its final position (role: "sorted") + CELEBRATE (style: "circumscribe")
5. Recurse visually on sub-arrays. Unroll at least 3-4 concrete partition steps.
""",

    'binary_search': """
ALGORITHM CONTEXT — Binary Search:
- Sorted array; compare mid to target; eliminate half each iteration
- Key variables: left, right, mid pointers

ANIMATION RULES:
1. CREATE_COLLECTION for sorted array (center); CREATE_VARIABLE for left, right, mid, target.
2. Each iteration: fast_forward: true
   - MARK_ELEMENT mid cell (role: "current"), left/right range cells (role: "compare")
   - COMPARE_VALUES target vs arr[mid]
   - Update left or right pointer
3. On match: MARK_ELEMENT found cell (role: "sorted") + CELEBRATE (style: "flash")
4. Unroll at least 3-4 bisection steps.
""",

    'linear_search': """
ALGORITHM CONTEXT — Linear Search:
- Scan each element; compare to target; return index on match

ANIMATION RULES:
1. CREATE_COLLECTION for array (center); CREATE_VARIABLE for i, target.
2. Each check step: fast_forward: true, MARK_ELEMENT current cell (role: "current")
3. COMPARE_VALUES arr[i] vs target
4. On mismatch: MARK_ELEMENT back to "default"
5. On match: MARK_ELEMENT (role: "sorted") + CELEBRATE (style: "flash")
""",

    'merge_sort': """
ALGORITHM CONTEXT — Merge Sort:
- Recursively split array in half, merge sorted halves

ANIMATION RULES:
1. Show split phases with multiple CREATE_COLLECTION objects.
2. Use fast_forward: true for merge comparison steps.
3. MARK_ELEMENT elements being merged (role: "compare"), merged result (role: "sorted").
4. CELEBRATE when a sub-array is fully merged.
""",

    'generic': """
ANIMATION RULES:
- For loops: mark the loop variable in the Variables Zone (top-left).
- Use fast_forward: true for inner loop body steps to maintain visual momentum.
- HIGHLIGHT array elements being accessed.
- If there is an obvious "success" condition (value found, sorted, etc.), end with CELEBRATE.
""",
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(algorithm_type: str, synthetic_data, has_console: bool) -> str:
    algo_guidance = _ALGO_GUIDANCE.get(algorithm_type, _ALGO_GUIDANCE['generic'])
    console_flag  = "true" if has_console else "false"

    synthetic_section = ""
    if synthetic_data is not None:
        synthetic_section = f"""
=== 7. SYNTHETIC TEST DATA ===
No concrete test data was found in the submitted code.
Use the following generated dataset in your animation steps:
  {json.dumps(synthetic_data)}
Create the collection / variables from this data at the start of the script.
"""

    return f"""
Role: You are the "Code Animator" Storyboard Architect. Transform Python code (as AST structure) into a detailed JSON storyboard for a Manim-based rendering engine.

=== 1. TOP-LEVEL JSON STRUCTURE ===
{{
  "metadata": {{
    "project_name": "<string>",
    "algorithm_type": "{algorithm_type}",
    "has_console_output": {console_flag}
  }},
  "script": [ <step>, <step>, ... ]
}}

Each step object MUST have these keys:
  "step_id"        : integer, starting at 1
  "line_number"    : integer, 1-based source line
  "code_snippet"   : string, exact code for this step
  "narration"      : string, beginner-friendly explanation (1-2 full sentences)
  "visual_commands": array of command objects

Optional step keys:
  "fast_forward"    : boolean — true for repetitive inner-loop / iteration steps.
                      The renderer skips the narration caption and uses 0.15 s/command.
                      Use for every comparison or swap step inside a loop body.
  "iteration_group" : string — groups related loop iterations, e.g. "pass_0", "pass_1".

=== 2. COMMAND API ===

--- MEMORY COMMANDS ---

CREATE_VARIABLE  Required: command, id, type, label, initial_value  Optional: position
  type values: "ValueBox" | "StringBox" | "BooleanBox" | "ScopeFrame"
  position: "LEFT" (variables zone) | "CENTER" | "RIGHT"
  Example: {{ "command": "CREATE_VARIABLE", "id": "var_i", "type": "ValueBox", "label": "i", "initial_value": 0, "position": "LEFT" }}

CREATE_COLLECTION  Required: command, id, type, label, initial_value  Optional: position
  type values: "BoxSeries" (list) | "NodeGraph" (dict)
  initial_value MUST be a JSON array or object — NOT a string.
  Example: {{ "command": "CREATE_COLLECTION", "id": "arr", "type": "BoxSeries", "label": "arr", "initial_value": [64, 34, 25, 12], "position": "CENTER" }}

DESTROY_OBJECT  Required: command, target_id
LINK_TARGET  Required: command, source_id, target_id  Optional: id

--- STATE COMMANDS ---

UPDATE_VALUE  Required: command, target_id, value  (NOT "new_value")
ANIMATE_MATH  Required: command, expression  Optional: result, target_id, id
TYPE_CAST  Required: command, target_id, new_type

--- COLLECTION COMMANDS ---

SWAP  Required: command, target_id, index_a, index_b  (concrete integers only)
APPEND_ELEMENT  Required: command, target_id, element
INSERT_AT  Required: command, target_id, index, element
POP_ELEMENT  Required: command, target_id  Optional: index

--- FLOW / EMPHASIS COMMANDS ---

MOVE_POINTER  Required: command, pointer_id, target_id  Optional: index
COMPARE_VALUES  Required: command, left, right, operator  Optional: result_id
HIGHLIGHT  Required: command, target_id, color
  color: "GREEN" | "RED" | "YELLOW" | "BLUE" | "WHITE" | "ORANGE"
PRINT_TO_CONSOLE  Required: command, value

--- ALGORITHM VISUALIZATION COMMANDS ---

MARK_ELEMENT — color-code a specific BoxSeries cell by its algorithmic role
  Required: command, target_id, index, role
  role values: "current" (blue) | "sorted" (teal) | "pivot" (orange) |
               "compare" (yellow) | "accent" (magenta) | "default" (reset/white)
  Example: {{ "command": "MARK_ELEMENT", "target_id": "arr", "index": 2, "role": "current" }}

CELEBRATE — play a joyful visual effect when an element reaches a milestone
  Required: command, target_id
  Optional: index (integer — specific BoxSeries cell), style ("flash" | "indicate" | "circumscribe")
  Example: {{ "command": "CELEBRATE", "target_id": "arr", "index": 5, "style": "circumscribe" }}

=== 3. CRITICAL RULES ===

A. CONCRETE VALUES ONLY — Never use variable names as indices or values.
   WRONG: {{ "command": "SWAP", "target_id": "arr", "index_a": "j", "index_b": "j+1" }}
   RIGHT: {{ "command": "SWAP", "target_id": "arr", "index_a": 2, "index_b": 3 }}

B. OBJECT PERSISTENCE — Every object needs a unique id. Reference the same id in all subsequent commands.

C. POINTER SETUP — Create pointer with CREATE_VARIABLE before using MOVE_POINTER.

D. NARRATION LENGTH drives duration for non-fast-forward steps. Write 1-2 full sentences.

E. LAYOUT ZONES — Variables (scalars like i, j, n) go in position "LEFT" (top-left zone).
   Collections go in position "CENTER" (visual stage).

F. OUTPUT — Return ONLY the raw JSON object. No markdown fences, no explanation text.

=== 4. NARRATION RULES (STRICTLY ENFORCED) ===

NARRATION MUST: Explain the CODE LOGIC — what the algorithm is doing and WHY.
  GOOD: "We compare 64 and 34. Since 64 is greater, it must move right."
  GOOD: "The outer loop starts a new pass, resetting j back to index zero."

NARRATION MUST NOT: Describe the visual animation or mention animation effects.
  FORBIDDEN (never write anything like these):
    - "A comparison display appears showing..."
    - "The element is highlighted..."
    - "A celebration animation plays..."
    - "Watch as the swap animation moves..."
    - "The pointer glides to..."
    - "The color changes to indicate..."
  The viewer can already SEE the animation.
  Narrate the algorithm LOGIC only — the WHY and HOW of the code.

=== 5. ALGORITHM-SPECIFIC GUIDANCE ===
{algo_guidance}

=== 6. EXAMPLE (bubble sort — 2-element pass excerpt) ===

{{
  "metadata": {{ "project_name": "Bubble Sort", "algorithm_type": "bubble_sort" }},
  "script": [
    {{
      "step_id": 1, "line_number": 1,
      "code_snippet": "arr = [64, 34, 25]",
      "narration": "We initialize the array with three unsorted integers. Each element lives in its own labeled cell.",
      "visual_commands": [
        {{ "command": "CREATE_COLLECTION", "id": "arr", "type": "BoxSeries", "label": "arr", "initial_value": [64, 34, 25], "position": "CENTER" }}
      ]
    }},
    {{
      "step_id": 2, "line_number": 3, "fast_forward": true, "iteration_group": "pass_0",
      "code_snippet": "if arr[0] > arr[1]:",
      "narration": "Compare index 0 and index 1.",
      "visual_commands": [
        {{ "command": "MARK_ELEMENT", "target_id": "arr", "index": 0, "role": "compare" }},
        {{ "command": "MARK_ELEMENT", "target_id": "arr", "index": 1, "role": "compare" }},
        {{ "command": "COMPARE_VALUES", "left": 64, "right": 34, "operator": ">" }}
      ]
    }},
    {{
      "step_id": 3, "line_number": 4, "fast_forward": true, "iteration_group": "pass_0",
      "code_snippet": "arr[0], arr[1] = arr[1], arr[0]",
      "narration": "64 > 34, so we swap them.",
      "visual_commands": [
        {{ "command": "SWAP", "target_id": "arr", "index_a": 0, "index_b": 1 }},
        {{ "command": "MARK_ELEMENT", "target_id": "arr", "index": 0, "role": "default" }},
        {{ "command": "MARK_ELEMENT", "target_id": "arr", "index": 1, "role": "default" }}
      ]
    }},
    {{
      "step_id": 4, "line_number": 7,
      "code_snippet": "# pass 0 complete — 64 in final position",
      "narration": "After the first pass, 64 has bubbled to its final sorted position at the end of the array. We mark it and celebrate!",
      "visual_commands": [
        {{ "command": "MARK_ELEMENT", "target_id": "arr", "index": 2, "role": "sorted" }},
        {{ "command": "CELEBRATE", "target_id": "arr", "index": 2, "style": "circumscribe" }}
      ]
    }}
  ]
}}
{synthetic_section}
"""


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    user_id    = event.get('user_id') or event.get('UserID')
    job_id     = event.get('job_id') or event.get('ProjectID')
    bucket_name = 'code-animator-assets'

    if not user_id or not job_id:
        return {'statusCode': 400, 'body': 'Missing UserID or ProjectID'}

    ast_s3_key = f'projects/{job_id}/ast_structure.json'

    try:
        table.update_item(
            Key={'UserID': user_id, 'ProjectID': f'PROJ#{job_id}'},
            UpdateExpression="set #s = :status_val",
            ExpressionAttributeNames={'#s': 'Status'},
            ExpressionAttributeValues={':status_val': 'GeneratingContent'}
        )

        if 'ast_data' in event:
            print("Using AST data directly from event.")
            ast_content = event['ast_data']
        else:
            print(f"Fetching AST from S3: {ast_s3_key}")
            response = s3.get_object(Bucket=bucket_name, Key=ast_s3_key)
            full_json = json.loads(response['Body'].read().decode('utf-8'))
            ast_content = full_json.get('ast_data', full_json)

        # Detect algorithm, console usage, and check for test data
        algorithm_type = _detect_algorithm(ast_content)
        has_console    = _has_print_statements(ast_content)
        print(f"Detected algorithm: {algorithm_type} | has_console: {has_console}")

        ast_str_lower = json.dumps(ast_content).lower()
        has_concrete_data = any(c in ast_str_lower for c in ['[', 'initial_value', 'num', 'data', 'arr'])
        synthetic_data = None if has_concrete_data else _generate_test_data(algorithm_type)
        if synthetic_data:
            print(f"Injecting synthetic test data: {synthetic_data}")

        base_instructions = _build_prompt(algorithm_type, synthetic_data, has_console)
        user_content = f"{base_instructions}\n\nINPUT AST STRUCTURE:\n{json.dumps(ast_content)}"

        completion = openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are an expert programming teacher who outputs valid JSON only."},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2
        )

        script_text = completion.choices[0].message.content

        script_s3_key = f'projects/{job_id}/script.json'

        try:
            final_script_json = json.loads(script_text)
            # Ensure algorithm_type / flags are in metadata even if LLM omitted them
            if isinstance(final_script_json, dict):
                meta = final_script_json.setdefault("metadata", {})
                meta.setdefault("algorithm_type", algorithm_type)
                meta.setdefault("color_theme", "joyful")
                meta["has_console_output"] = has_console  # always authoritative
        except Exception:
            final_script_json = script_text

        s3.put_object(
            Bucket=bucket_name,
            Key=script_s3_key,
            Body=json.dumps({
                "job_id": job_id,
                "user_id": user_id,
                "script": final_script_json,
                "algorithm_type": algorithm_type,
                "generated_at": datetime.now().isoformat()
            }),
            ContentType='application/json'
        )

        return {
            'statusCode': 200,
            'UserID': user_id,
            'ProjectID': job_id,
            'script_s3_key': script_s3_key,
            'algorithm_type': algorithm_type,
            'status': 'ScriptGenerated'
        }

    except Exception as e:
        print(f"Error in Script Generator: {str(e)}")
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
