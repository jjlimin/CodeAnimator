#!/bin/bash
# Build a deployment ZIP for CodeAnimator-ScriptGenerator Lambda.
# Run this script from the lambda directory:
#   cd backend/lambdas/CodeAnimator-ScriptGenerator
#   bash build.sh

set -e

LAMBDA_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="$LAMBDA_DIR/package"
OUTPUT_ZIP="$LAMBDA_DIR/deployment.zip"

echo "==> Cleaning previous build..."
rm -rf "$PACKAGE_DIR" "$OUTPUT_ZIP"

echo "==> Installing dependencies into ./package/ ..."
pip install \
  --platform manylinux2014_x86_64 \
  --target "$PACKAGE_DIR" \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade \
  -r "$LAMBDA_DIR/requirements.txt"

echo "==> Zipping dependencies..."
cd "$PACKAGE_DIR"
zip -r "$OUTPUT_ZIP" . -x "*.pyc" -x "*/__pycache__/*"

echo "==> Adding lambda_function.py..."
cd "$LAMBDA_DIR"
zip "$OUTPUT_ZIP" lambda_function.py

echo ""
echo "Done! Upload $OUTPUT_ZIP to your Lambda function."
echo "Handler: lambda_function.lambda_handler"
