"""Local test harness — simulates an AWS Lambda invocation while AWS is down.

Usage:
  python local_test.py                    # run the full agent on the built-in sample code
  python local_test.py --file my_code.py  # run it on your own Python file
  python local_test.py --self-test        # validator-only smoke test, no OpenAI call

Requires OPENAI_API_KEY in the environment (or in a .env file next to this
script) for the full run; --self-test needs no key.
"""

import argparse
import json
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_dotenv_if_present():
    """Minimal .env loader so no extra dependency is needed."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


class FakeLambdaContext:
    """Mimics the AWS Lambda context object the handler actually uses."""

    function_name = "code-animator-scene-generator"
    memory_limit_in_mb = 1024
    invoked_function_arn = (
        "arn:aws:lambda:us-east-1:000000000000:function:code-animator-scene-generator"
    )
    aws_request_id = "local-test-request-id"

    def __init__(self, timeout_seconds: int = 900):
        self._deadline = time.monotonic() + timeout_seconds

    def get_remaining_time_in_millis(self) -> int:
        return max(0, int((self._deadline - time.monotonic()) * 1000))


SAMPLE_USER_CODE = '''\
def fibonacci(n):
    """Return the first n Fibonacci numbers using memoization."""
    memo = {0: 0, 1: 1}

    def fib(k):
        if k not in memo:
            memo[k] = fib(k - 1) + fib(k - 2)
        return memo[k]

    return [fib(i) for i in range(n)]
'''


def run_self_test() -> int:
    """Exercise the validator tiers without calling OpenAI."""
    from validator import MANIM_AVAILABLE, validate_scene

    print(f"manim available locally: {MANIM_AVAILABLE}")

    cases = [
        (
            "valid scene (should PASS)",
            "from manim import *\n\n"
            "class DemoScene(Scene):\n"
            "    def construct(self):\n"
            "        title = Text('Hello')\n"
            "        self.play(Write(title))\n"
            "        self.wait(1)\n",
            True,
        ),
        (
            "syntax error (should FAIL at syntax tier)",
            "from manim import *\n\nclass Broken(Scene)\n    def construct(self):\n        pass\n",
            False,
        ),
        (
            "removed API ShowCreation (should FAIL at lint tier)",
            "from manim import *\n\n"
            "class OldApi(Scene):\n"
            "    def construct(self):\n"
            "        c = Circle()\n"
            "        self.play(ShowCreation(c))\n",
            False,
        ),
        (
            "runtime error (should FAIL at dry_run tier if manim installed)",
            "from manim import *\n\n"
            "class RuntimeBoom(Scene):\n"
            "    def construct(self):\n"
            "        c = Circle(radius='not a number')\n"
            "        self.play(Create(c))\n",
            not MANIM_AVAILABLE,  # passes lint; only dry-run can catch it
        ),
    ]

    failures = 0
    for name, code, expect_pass in cases:
        result = validate_scene(code, timeout=60)
        ok = result.passed == expect_pass
        failures += 0 if ok else 1
        print(f"\n[{'OK' if ok else 'UNEXPECTED'}] {name}")
        print(f"  passed={result.passed} tier={result.tier}")
        if result.error:
            first_lines = "\n    ".join(result.error.splitlines()[:6])
            print(f"  error:\n    {first_lines}")

    print(f"\nSelf-test: {len(cases) - failures}/{len(cases)} cases behaved as expected")
    return 1 if failures else 0


def run_lambda(user_code: str, timeout_seconds: int) -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set (env var or .env file).", file=sys.stderr)
        return 1

    from lambda_function import SceneValidationError, lambda_handler

    event = {"job_id": "local-test-job-001", "user_code": user_code}
    context = FakeLambdaContext(timeout_seconds=timeout_seconds)

    print(f"Invoking lambda_handler (simulated timeout: {timeout_seconds}s)...\n")
    started = time.monotonic()
    try:
        result = lambda_handler(event, context)
    except SceneValidationError as e:
        print("\n=== JOB FAILED: scenes exhausted all correction attempts ===")
        print(e)
        return 1
    elapsed = time.monotonic() - started

    print(f"\n=== SUCCESS in {elapsed:.1f}s — {len(result['scenes'])} scenes ===\n")
    for scene in result["scenes"]:
        words = len(scene["narration"].split())
        print(f"--- Scene {scene['scene_id']} (~{words / 2.5:.0f}s narration, {words} words)")
        print(f"    {scene['narration']}\n")

    total_words = sum(len(s["narration"].split()) for s in result["scenes"])
    print(f"Total narration: {total_words} words (~{total_words / 2.5:.0f}s at 150 wpm)")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_test_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Full result (including manim_code) written to {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Lambda test harness")
    parser.add_argument("--file", help="Python file to use as user_code (default: built-in sample)")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Simulated Lambda timeout in seconds (default 900)")
    parser.add_argument("--self-test", action="store_true",
                        help="Run validator smoke tests only (no OpenAI call)")
    args = parser.parse_args()

    load_dotenv_if_present()

    if args.self_test:
        return run_self_test()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            user_code = f.read()
    else:
        user_code = SAMPLE_USER_CODE

    return run_lambda(user_code, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
