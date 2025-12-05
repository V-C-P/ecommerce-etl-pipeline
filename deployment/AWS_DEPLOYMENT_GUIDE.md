# AWS Lambda Deployment Guide

This guide walks you through deploying the E-commerce ETL pipeline to AWS Lambda with EventBridge scheduling.

## Prerequisites

- AWS Account (Free Tier eligible)
- AWS CLI installed and configured (optional but recommended)
- Python 3.9, 3.10, or 3.11 installed locally
- Supabase database set up with schema deployed
- Shopify and Amazon API credentials

## Deployment Steps

### Step 1: Build the Deployment Package

#### On Windows:
```bash
cd deployment
build_lambda_package.bat
```

#### On Mac/Linux:
```bash
cd deployment
chmod +x build_lambda_package.sh
./build_lambda_package.sh
```

This will create `ecommerce-etl-lambda.zip` in the deployment directory.

### Step 2: Create IAM Role for Lambda

1. Go to AWS Console → IAM → Roles
2. Click "Create role"
3. Select "Lambda" as the trusted entity
4. Attach the following policies:
   - `AWSLambdaBasicExecutionRole` (for CloudWatch Logs)
5. Click "Next" and name the role: `ecommerce-etl-lambda-role`
6. Click "Create role"

### Step 3: Create Lambda Function

#### Option A: Using AWS Console

1. Go to AWS Console → Lambda → Functions
2. Click "Create function"
3. Choose "Author from scratch"
4. Configure:
   - **Function name**: `ecommerce-etl-pipeline`
   - **Runtime**: Python 3.11 (or your chosen version)
   - **Architecture**: x86_64
   - **Execution role**: Use existing role → `ecommerce-etl-lambda-role`
5. Click "Create function"

#### Option B: Using AWS CLI

```bash
aws lambda create-function \
  --function-name ecommerce-etl-pipeline \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ecommerce-etl-lambda-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://ecommerce-etl-lambda.zip \
  --timeout 900 \
  --memory-size 512
```

Replace `YOUR_ACCOUNT_ID` with your AWS account ID.

### Step 4: Upload Deployment Package

#### Using AWS Console:

1. In your Lambda function, go to "Code" tab
2. Click "Upload from" → ".zip file"
3. Select `ecommerce-etl-lambda.zip`
4. Click "Save"

#### Using AWS CLI:

```bash
aws lambda update-function-code \
  --function-name ecommerce-etl-pipeline \
  --zip-file fileb://ecommerce-etl-lambda.zip
```

### Step 5: Configure Lambda Settings

1. Go to "Configuration" tab → "General configuration"
2. Click "Edit"
3. Set:
   - **Memory**: 512 MB (adjust based on data volume)
   - **Timeout**: 15 minutes (900 seconds)
4. Click "Save"

### Step 6: Set Environment Variables

1. Go to "Configuration" tab → "Environment variables"
2. Click "Edit"
3. Add the following variables:

```
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
SHOPIFY_API_VERSION=2024-01

AMAZON_REFRESH_TOKEN=Atzr|xxxxx
AMAZON_CLIENT_ID=amzn1.application-oa2-client.xxxxx
AMAZON_CLIENT_SECRET=xxxxx
AMAZON_REGION=US
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER

SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx
SUPABASE_DB_URL=postgresql://postgres:xxxxx@db.xxxxx.supabase.co:5432/postgres

DAYS_TO_SYNC=7
BATCH_SIZE=100
```

4. Click "Save"

### Step 7: Test the Lambda Function

1. Go to "Test" tab
2. Click "Create new test event"
3. Event name: `test-connections`
4. Use this JSON:

```json
{
  "sync_type": "test"
}
```

5. Click "Test"
6. Check the execution results - all connections should show `true`

### Step 8: Create EventBridge Schedule

#### Option A: Using AWS Console

1. Go to AWS Console → EventBridge → Rules
2. Click "Create rule"
3. Configure:
   - **Name**: `ecommerce-etl-daily-sync`
   - **Description**: Daily sync of e-commerce data
   - **Rule type**: Schedule
4. Click "Next"
5. Schedule pattern:
   - Choose "Cron expression"
   - Enter: `0 2 * * ? *` (runs daily at 2 AM UTC)
   - Or use "Rate expression": `rate(1 day)`
6. Click "Next"
7. Select target:
   - **Target type**: AWS service
   - **Target**: Lambda function
   - **Function**: ecommerce-etl-pipeline
8. Configure input (optional):
   - Choose "Constant (JSON text)"
   - Enter: `{"sync_type": "all"}`
9. Click "Next" → "Next" → "Create rule"

#### Option B: Using AWS CLI

```bash
# Create the rule
aws events put-rule \
  --name ecommerce-etl-daily-sync \
  --description "Daily sync of e-commerce data" \
  --schedule-expression "cron(0 2 * * ? *)"

# Add Lambda permission
aws lambda add-permission \
  --function-name ecommerce-etl-pipeline \
  --statement-id ecommerce-etl-daily-sync \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:REGION:ACCOUNT_ID:rule/ecommerce-etl-daily-sync

# Add the target
aws events put-targets \
  --rule ecommerce-etl-daily-sync \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT_ID:function:ecommerce-etl-pipeline","Input"='{"sync_type":"all"}'
```

Replace `REGION` and `ACCOUNT_ID` with your values.

### Step 9: Monitor Execution

1. Go to Lambda → Functions → ecommerce-etl-pipeline
2. Click "Monitor" tab
3. View CloudWatch Logs to see execution details
4. Check Supabase database `sync_logs` table for sync statistics

## Common Schedule Expressions

- Every hour: `rate(1 hour)` or `cron(0 * * * ? *)`
- Every 6 hours: `rate(6 hours)` or `cron(0 */6 * * ? *)`
- Daily at 2 AM UTC: `cron(0 2 * * ? *)`
- Daily at midnight UTC: `cron(0 0 * * ? *)`
- Weekdays at 9 AM UTC: `cron(0 9 ? * MON-FRI *)`

## Cost Optimization (Free Tier)

AWS Lambda Free Tier includes:
- 1 million requests per month
- 400,000 GB-seconds of compute time per month

With a 512 MB function running for ~5 minutes daily:
- Monthly requests: ~30
- Monthly compute: ~75 GB-seconds
- **Cost: FREE** (well within free tier)

## Troubleshooting

### Package Size Too Large

If deployment package exceeds 50 MB:

1. Use Lambda Layers for dependencies:
```bash
# Create layer
mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python

# Upload layer in AWS Console
aws lambda publish-layer-version \
  --layer-name ecommerce-etl-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

2. Attach layer to function in Lambda console

### Timeout Errors

If function times out:
- Increase timeout in Lambda configuration (max 15 minutes)
- Reduce `DAYS_TO_SYNC` to sync less data per run
- Consider splitting into separate functions per platform

### Memory Errors

If function runs out of memory:
- Increase memory allocation in Lambda configuration
- Reduce `BATCH_SIZE` in environment variables
- Process data in smaller chunks

### Connection Errors

For Supabase connection issues:
- Ensure database URL is correct
- Check Supabase firewall/IP allowlist (should allow AWS Lambda)
- Verify credentials are correct

## Manual Invocation

To manually trigger the ETL:

### Using AWS Console:
1. Go to Lambda function → Test tab
2. Use event: `{"sync_type": "all"}`
3. Click "Test"

### Using AWS CLI:
```bash
# Sync all platforms
aws lambda invoke \
  --function-name ecommerce-etl-pipeline \
  --payload '{"sync_type":"all"}' \
  response.json

# Sync only Shopify
aws lambda invoke \
  --function-name ecommerce-etl-pipeline \
  --payload '{"sync_type":"shopify"}' \
  response.json

# Sync only Amazon
aws lambda invoke \
  --function-name ecommerce-etl-pipeline \
  --payload '{"sync_type":"amazon"}' \
  response.json

# Test connections
aws lambda invoke \
  --function-name ecommerce-etl-pipeline \
  --payload '{"sync_type":"test"}' \
  response.json
```

## Security Best Practices

1. **Environment Variables**: Consider using AWS Secrets Manager for sensitive credentials
2. **IAM Role**: Apply principle of least privilege
3. **VPC**: If using Supabase in a VPC, configure Lambda VPC settings
4. **Encryption**: Enable encryption at rest for environment variables

## Next Steps

After deployment:
1. Monitor the first few scheduled runs
2. Check sync_logs table in Supabase for statistics
3. Set up CloudWatch alarms for failures
4. Create a dashboard in Supabase to visualize synced data
