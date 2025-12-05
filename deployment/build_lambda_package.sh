#!/bin/bash

# Build Lambda Deployment Package Script
# This script creates a deployment package for AWS Lambda

set -e

echo "========================================="
echo "Building Lambda Deployment Package"
echo "========================================="

# Configuration
PACKAGE_DIR="lambda_package"
ZIP_FILE="ecommerce-etl-lambda.zip"
PYTHON_VERSION="python3.11"  # Change to python3.9 or python3.10 if needed

# Clean up previous builds
echo "Cleaning up previous builds..."
rm -rf $PACKAGE_DIR
rm -f $ZIP_FILE

# Create package directory
echo "Creating package directory..."
mkdir -p $PACKAGE_DIR

# Install dependencies
echo "Installing Python dependencies..."
pip install -r ../requirements.txt -t $PACKAGE_DIR/

# Copy source code
echo "Copying source code..."
cp -r ../src $PACKAGE_DIR/
cp ../lambda_handler.py $PACKAGE_DIR/

# Remove unnecessary files to reduce package size
echo "Removing unnecessary files..."
cd $PACKAGE_DIR
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create ZIP file
echo "Creating deployment package..."
zip -r ../$ZIP_FILE . -x "*.git*" "*.DS_Store"

cd ..

# Display package info
PACKAGE_SIZE=$(du -h $ZIP_FILE | cut -f1)
echo "========================================="
echo "Deployment package created successfully!"
echo "File: $ZIP_FILE"
echo "Size: $PACKAGE_SIZE"
echo "========================================="

# Check if package exceeds Lambda limits
SIZE_BYTES=$(wc -c < $ZIP_FILE)
MAX_SIZE=$((50 * 1024 * 1024))  # 50 MB

if [ $SIZE_BYTES -gt $MAX_SIZE ]; then
    echo "WARNING: Package size exceeds 50MB. Consider using Lambda Layers for dependencies."
fi

echo ""
echo "Next steps:"
echo "1. Upload $ZIP_FILE to AWS Lambda"
echo "2. Set environment variables in Lambda configuration"
echo "3. Configure EventBridge schedule"
echo ""
