# EnergyGrid.AI Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the EnergyGrid.AI Compliance Copilot system.

## Table of Contents

1. [Deployment Issues](#deployment-issues)
2. [Authentication Problems](#authentication-problems)
3. [Document Processing Failures](#document-processing-failures)
4. [Performance Issues](#performance-issues)
5. [API Errors](#api-errors)
6. [Database Issues](#database-issues)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Network and Connectivity](#network-and-connectivity)
9. [Resource Limits](#resource-limits)
10. [Data Issues](#data-issues)

## Deployment Issues

### Issue: CloudFormation Stack Creation Fails

**Symptoms:**
- Stack creation fails with `CREATE_FAILED` status
- Resources are not created or partially created
- Error messages in CloudFormation events

**Diagnosis:**
```bash
# Check stack events for detailed error messages
aws cloudformation describe-stack-events --stack-name energygrid-compliance-copilot-dev

# Check stack resources status
aws cloudformation list-stack-resources --stack-name energygrid-compliance-copilot-dev
```

**Common Causes and Solutions:**

1. **Insufficient IAM Permissions**
   ```bash
   # Check current user permissions
   aws sts get-caller-identity
   aws iam get-user
   
   # Solution: Ensure user has required permissions
   # - CloudFormationFullAccess
   # - IAMFullAccess
   # - AWSLambda_FullAccess
   # - AmazonS3FullAccess
   # - AmazonDynamoDBFullAccess
   ```

2. **S3 Bucket Name Conflicts**
   ```
   Error: Bucket name already exists
   
   # Solution: S3 bucket names must be globally unique
   # Update template.yaml with unique bucket names or use account ID suffix
   ```

3. **Resource Limits Exceeded**
   ```bash
   # Check service limits
   aws service-quotas get-service-quota --service-code lambda --quota-code L-B99A9384
   
   # Solution: Request limit increases or clean up unused resources
   ```

4. **Bedrock Access Not Enabled**
   ```
   Error: Access denied to Bedrock model
   
   # Solution: Enable Bedrock access in AWS console
   # Go to Bedrock console -> Model access -> Enable Claude 3 Sonnet
   ```

### Issue: SAM Build Failures

**Symptoms:**
- `sam build` command fails
- Missing dependencies errors
- Python import errors

**Diagnosis:**
```bash
# Run build with verbose output
sam build --debug

# Check Python version
python --version

# Check requirements files
find . -name "requirements.txt" -exec echo {} \; -exec cat {} \;
```

**Solutions:**

1. **Python Version Mismatch**
   ```bash
   # Ensure Python 3.11 is installed
   python3.11 --version
   
   # Use specific Python version
   sam build --use-container
   ```

2. **Missing Dependencies**
   ```bash
   # Install all requirements
   pip install -r requirements.txt
   pip install -r src/upload/requirements.txt
   # ... for all modules
   ```

3. **Docker Issues (when using containers)**
   ```bash
   # Check Docker status
   docker --version
   docker ps
   
   # Clean Docker cache
   docker system prune -f
   ```

### Issue: Deployment Timeout

**Symptoms:**
- Deployment takes longer than expected
- CloudFormation operations timeout
- Stack gets stuck in `UPDATE_IN_PROGRESS`

**Solutions:**

1. **Increase Timeout Values**
   ```yaml
   # In template.yaml, increase Lambda timeouts
   Globals:
     Function:
       Timeout: 900  # 15 minutes
   ```

2. **Cancel and Retry**
   ```bash
   # Cancel stuck deployment
   aws cloudformation cancel-update-stack --stack-name energygrid-compliance-copilot-dev
   
   # Continue rollback if needed
   aws cloudformation continue-update-rollback --stack-name energygrid-compliance-copilot-dev
   ```

## Authentication Problems

### Issue: Cognito Authentication Failures

**Symptoms:**
- Users cannot log in
- JWT token validation fails
- 401 Unauthorized errors

**Diagnosis:**
```bash
# Check Cognito User Pool status
aws cognito-idp describe-user-pool --user-pool-id <pool-id>

# List users
aws cognito-idp list-users --user-pool-id <pool-id>

# Check user status
aws cognito-idp admin-get-user --user-pool-id <pool-id> --username <username>
```

**Solutions:**

1. **User Not Confirmed**
   ```bash
   # Confirm user manually
   aws cognito-idp admin-confirm-sign-up --user-pool-id <pool-id> --username <username>
   
   # Set permanent password
   aws cognito-idp admin-set-user-password --user-pool-id <pool-id> --username <username> --password <password> --permanent
   ```

2. **User Not in Correct Group**
   ```bash
   # List user groups
   aws cognito-idp admin-list-groups-for-user --user-pool-id <pool-id> --username <username>
   
   # Add user to group
   aws cognito-idp admin-add-user-to-group --user-pool-id <pool-id> --username <username> --group-name ComplianceOfficers
   ```

3. **JWT Token Expired**
   ```bash
   # Decode JWT token to check expiration
   echo "<jwt-token>" | cut -d. -f2 | base64 -d | jq .exp
   
   # Compare with current timestamp
   date +%s
   ```

### Issue: API Gateway Authorization Failures

**Symptoms:**
- 403 Forbidden errors
- Authorizer function failures
- CORS errors

**Diagnosis:**
```bash
# Check API Gateway logs
aws logs tail /aws/apigateway/energygrid-compliance-copilot-dev --follow

# Check authorizer function logs
aws logs tail /aws/lambda/dev-energygrid-authorizer --follow
```

**Solutions:**

1. **CORS Configuration**
   ```yaml
   # Ensure CORS is properly configured in template.yaml
   Cors:
     AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
     AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
     AllowOrigin: "'*'"
   ```

2. **Authorizer Function Issues**
   ```python
   # Check authorizer function code for proper JWT validation
   # Ensure it returns proper IAM policy
   ```

## Document Processing Failures

### Issue: PDF Upload Failures

**Symptoms:**
- Upload requests fail with 400/500 errors
- Files are not stored in S3
- Processing pipeline doesn't start

**Diagnosis:**
```bash
# Check upload function logs
aws logs tail /aws/lambda/dev-energygrid-upload --follow

# Check S3 bucket permissions
aws s3api get-bucket-policy --bucket dev-energygrid-documents-<account-id>

# List recent uploads
aws s3 ls s3://dev-energygrid-documents-<account-id>/ --recursive --human-readable
```

**Solutions:**

1. **File Size Limits**
   ```python
   # Check file size before upload
   MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
   if file_size > MAX_FILE_SIZE:
       raise ValueError("File too large")
   ```

2. **Invalid PDF Format**
   ```python
   # Validate PDF format
   import PyPDF2
   try:
       with open(file_path, 'rb') as file:
           PyPDF2.PdfReader(file)
   except Exception as e:
       print(f"Invalid PDF: {e}")
   ```

3. **S3 Permissions**
   ```bash
   # Check Lambda execution role permissions
   aws iam get-role-policy --role-name <lambda-role> --policy-name <policy-name>
   ```

### Issue: Analyzer Agent Failures

**Symptoms:**
- Documents stuck in "processing" status
- Bedrock API errors
- Text extraction failures

**Diagnosis:**
```bash
# Check analyzer function logs
aws logs tail /aws/lambda/dev-energygrid-analyzer --follow

# Check SQS queue status
aws sqs get-queue-attributes --queue-url <analysis-queue-url> --attribute-names All

# Check dead letter queue
aws sqs get-queue-attributes --queue-url <analysis-dlq-url> --attribute-names All
```

**Solutions:**

1. **Bedrock API Throttling**
   ```python
   # Implement exponential backoff
   import time
   import random
   
   def retry_with_backoff(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except ThrottlingException:
               wait_time = (2 ** attempt) + random.uniform(0, 1)
               time.sleep(wait_time)
       raise Exception("Max retries exceeded")
   ```

2. **Memory Issues**
   ```yaml
   # Increase Lambda memory in template.yaml
   AnalyzerFunction:
     Properties:
       MemorySize: 3008  # Maximum for Lambda
   ```

3. **Timeout Issues**
   ```yaml
   # Increase timeout
   AnalyzerFunction:
     Properties:
       Timeout: 900  # 15 minutes
   ```

### Issue: Text Extraction Problems

**Symptoms:**
- Empty or garbled text extraction
- OCR failures
- Encoding issues

**Solutions:**

1. **PDF Corruption**
   ```python
   # Try multiple extraction methods
   import PyPDF2
   import pdfplumber
   
   def extract_text_fallback(pdf_path):
       try:
           # Try PyPDF2 first
           return extract_with_pypdf2(pdf_path)
       except:
           try:
               # Fallback to pdfplumber
               return extract_with_pdfplumber(pdf_path)
           except:
               # Last resort: OCR
               return extract_with_ocr(pdf_path)
   ```

2. **Encoding Issues**
   ```python
   # Handle different encodings
   import chardet
   
   def detect_encoding(text_bytes):
       result = chardet.detect(text_bytes)
       return result['encoding']
   ```

## Performance Issues

### Issue: Slow Response Times

**Symptoms:**
- API requests take longer than expected
- Lambda cold starts
- Database query timeouts

**Diagnosis:**
```bash
# Check X-Ray traces
aws xray get-trace-summaries --time-range-type TimeRangeByStartTime --start-time <start> --end-time <end>

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration --dimensions Name=FunctionName,Value=dev-energygrid-analyzer --start-time <start> --end-time <end> --period 300 --statistics Average,Maximum
```

**Solutions:**

1. **Lambda Cold Starts**
   ```yaml
   # Use provisioned concurrency for critical functions
   ProvisionedConcurrencyConfig:
     ProvisionedConcurrencyUnits: 5
   ```

2. **Database Performance**
   ```python
   # Optimize DynamoDB queries
   # Use GSI for efficient filtering
   # Implement pagination for large result sets
   ```

3. **Memory Optimization**
   ```bash
   # Monitor memory usage
   aws logs filter-log-events --log-group-name /aws/lambda/dev-energygrid-analyzer --filter-pattern "REPORT"
   ```

### Issue: High Costs

**Symptoms:**
- Unexpected AWS bills
- High Bedrock API usage
- Excessive Lambda invocations

**Diagnosis:**
```bash
# Check AWS Cost Explorer
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE

# Check Bedrock usage
aws bedrock get-model-invocation-logging-configuration
```

**Solutions:**

1. **Optimize Bedrock Usage**
   ```python
   # Cache results to avoid duplicate API calls
   # Use smaller prompts when possible
   # Implement request deduplication
   ```

2. **Lambda Optimization**
   ```yaml
   # Right-size Lambda functions
   # Use appropriate memory settings
   # Implement efficient error handling
   ```

## API Errors

### Issue: 500 Internal Server Errors

**Symptoms:**
- Intermittent 500 errors
- Lambda function failures
- Unhandled exceptions

**Diagnosis:**
```bash
# Check API Gateway logs
aws logs tail /aws/apigateway/energygrid-compliance-copilot-dev --follow

# Check specific Lambda function logs
aws logs tail /aws/lambda/dev-energygrid-<function-name> --follow
```

**Solutions:**

1. **Add Comprehensive Error Handling**
   ```python
   import logging
   import traceback
   
   def lambda_handler(event, context):
       try:
           # Your code here
           return success_response(result)
       except Exception as e:
           logging.error(f"Unhandled exception: {str(e)}")
           logging.error(traceback.format_exc())
           return error_response(500, "Internal server error")
   ```

2. **Validate Input Data**
   ```python
   from pydantic import BaseModel, ValidationError
   
   def validate_request(data, model_class):
       try:
           return model_class(**data)
       except ValidationError as e:
           raise ValueError(f"Invalid request data: {e}")
   ```

### Issue: Rate Limiting Errors

**Symptoms:**
- 429 Too Many Requests errors
- API Gateway throttling
- Bedrock rate limits

**Solutions:**

1. **Implement Client-Side Retry Logic**
   ```python
   import time
   import random
   
   def api_call_with_retry(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except RateLimitError:
               if attempt == max_retries - 1:
                   raise
               wait_time = (2 ** attempt) + random.uniform(0, 1)
               time.sleep(wait_time)
   ```

2. **Increase API Gateway Limits**
   ```yaml
   # In template.yaml
   ThrottleSettings:
     RateLimit: 1000
     BurstLimit: 2000
   ```

## Database Issues

### Issue: DynamoDB Throttling

**Symptoms:**
- ProvisionedThroughputExceededException
- High read/write latency
- Failed database operations

**Diagnosis:**
```bash
# Check DynamoDB metrics
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB --metric-name ConsumedReadCapacityUnits --dimensions Name=TableName,Value=dev-energygrid-documents --start-time <start> --end-time <end> --period 300 --statistics Sum

# Check table status
aws dynamodb describe-table --table-name dev-energygrid-documents
```

**Solutions:**

1. **Enable Auto Scaling**
   ```yaml
   # In template.yaml
   BillingMode: PAY_PER_REQUEST  # Or configure auto-scaling
   ```

2. **Optimize Query Patterns**
   ```python
   # Use batch operations
   dynamodb.batch_write_item(RequestItems={...})
   
   # Use pagination for large queries
   paginator = dynamodb.get_paginator('scan')
   ```

### Issue: Data Consistency Problems

**Symptoms:**
- Stale data in queries
- Missing records
- Duplicate entries

**Solutions:**

1. **Use Consistent Reads**
   ```python
   # For critical operations
   response = table.get_item(
       Key={'id': item_id},
       ConsistentRead=True
   )
   ```

2. **Implement Proper Error Handling**
   ```python
   try:
       table.put_item(Item=item, ConditionExpression='attribute_not_exists(id)')
   except ClientError as e:
       if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
           # Handle duplicate
           pass
   ```

## Monitoring and Logging

### Issue: Missing Logs

**Symptoms:**
- No logs appearing in CloudWatch
- Incomplete log entries
- Log retention issues

**Solutions:**

1. **Check Log Group Configuration**
   ```bash
   # List log groups
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/dev-energygrid

   # Check retention settings
   aws logs put-retention-policy --log-group-name /aws/lambda/dev-energygrid-analyzer --retention-in-days 30
   ```

2. **Ensure Proper Logging in Code**
   ```python
   import logging
   
   # Configure logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   def lambda_handler(event, context):
       logger.info(f"Processing event: {event}")
       # Your code here
   ```

### Issue: Alarm Not Triggering

**Symptoms:**
- CloudWatch alarms not firing
- Missing notifications
- Incorrect alarm configuration

**Diagnosis:**
```bash
# Check alarm status
aws cloudwatch describe-alarms --alarm-names dev-energygrid-analyzer-errors

# Check alarm history
aws cloudwatch describe-alarm-history --alarm-name dev-energygrid-analyzer-errors
```

**Solutions:**

1. **Verify Alarm Configuration**
   ```yaml
   # Ensure correct metric and threshold
   MetricName: Errors
   Threshold: 5
   ComparisonOperator: GreaterThanThreshold
   EvaluationPeriods: 2
   ```

2. **Check SNS Topic Subscriptions**
   ```bash
   # List subscriptions
   aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
   
   # Add email subscription
   aws sns subscribe --topic-arn <topic-arn> --protocol email --notification-endpoint your-email@example.com
   ```

## Network and Connectivity

### Issue: VPC Configuration Problems

**Symptoms:**
- Lambda functions cannot access external services
- Database connection failures
- Internet connectivity issues

**Solutions:**

1. **Check VPC Configuration**
   ```bash
   # Check Lambda VPC configuration
   aws lambda get-function-configuration --function-name dev-energygrid-analyzer
   ```

2. **Ensure NAT Gateway for Internet Access**
   ```yaml
   # Lambda functions in VPC need NAT Gateway for internet access
   # Or use VPC endpoints for AWS services
   ```

### Issue: DNS Resolution Problems

**Symptoms:**
- Cannot resolve external hostnames
- Service discovery failures
- Intermittent connectivity

**Solutions:**

1. **Check DNS Configuration**
   ```python
   import socket
   
   try:
       socket.gethostbyname('bedrock.us-east-1.amazonaws.com')
   except socket.gaierror as e:
       print(f"DNS resolution failed: {e}")
   ```

2. **Use VPC Endpoints**
   ```yaml
   # Create VPC endpoints for AWS services
   BedrockVPCEndpoint:
     Type: AWS::EC2::VPCEndpoint
     Properties:
       ServiceName: com.amazonaws.us-east-1.bedrock
   ```

## Resource Limits

### Issue: Lambda Concurrent Execution Limits

**Symptoms:**
- TooManyRequestsException
- Functions not executing
- Throttling errors

**Diagnosis:**
```bash
# Check current concurrency
aws lambda get-account-settings

# Check function-specific limits
aws lambda get-function-concurrency --function-name dev-energygrid-analyzer
```

**Solutions:**

1. **Request Limit Increase**
   ```bash
   # Request service limit increase through AWS Support
   # Or use reserved concurrency for critical functions
   aws lambda put-function-concurrency --function-name dev-energygrid-analyzer --reserved-concurrent-executions 100
   ```

2. **Optimize Function Performance**
   ```python
   # Reduce execution time to handle more concurrent requests
   # Use connection pooling
   # Implement efficient algorithms
   ```

### Issue: Storage Limits

**Symptoms:**
- S3 upload failures
- DynamoDB item size errors
- Lambda deployment package too large

**Solutions:**

1. **S3 Storage Optimization**
   ```bash
   # Implement lifecycle policies
   aws s3api put-bucket-lifecycle-configuration --bucket <bucket-name> --lifecycle-configuration file://lifecycle.json
   ```

2. **DynamoDB Item Size**
   ```python
   # Split large items across multiple records
   # Use S3 for large data, store reference in DynamoDB
   ```

## Data Issues

### Issue: Data Corruption

**Symptoms:**
- Invalid data in database
- Encoding issues
- Malformed JSON

**Solutions:**

1. **Implement Data Validation**
   ```python
   from pydantic import BaseModel, validator
   
   class DocumentModel(BaseModel):
       document_id: str
       filename: str
       
       @validator('document_id')
       def validate_document_id(cls, v):
           if not v.startswith('doc-'):
               raise ValueError('Invalid document ID format')
           return v
   ```

2. **Add Data Integrity Checks**
   ```python
   import hashlib
   
   def calculate_checksum(data):
       return hashlib.sha256(data.encode()).hexdigest()
   
   def verify_data_integrity(data, expected_checksum):
       return calculate_checksum(data) == expected_checksum
   ```

### Issue: Missing Data

**Symptoms:**
- Records not found
- Incomplete processing results
- Data synchronization issues

**Solutions:**

1. **Implement Retry Logic**
   ```python
   def process_with_retry(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except Exception as e:
               if attempt == max_retries - 1:
                   raise
               time.sleep(2 ** attempt)
   ```

2. **Add Data Recovery Mechanisms**
   ```python
   def recover_missing_data(document_id):
       # Check if data exists in backup
       # Reprocess if necessary
       # Update status accordingly
       pass
   ```

## Getting Help

### Diagnostic Commands

```bash
# System health check
make smoke-test ENV=dev

# Check all stack resources
make resources ENV=dev

# View recent events
make events ENV=dev

# Check function logs
aws logs tail /aws/lambda/dev-energygrid-analyzer --follow

# Monitor metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=dev-energygrid-analyzer --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum
```

### Support Channels

- **GitHub Issues**: [Report bugs and issues](https://github.com/your-org/energygrid-ai-compliance-copilot/issues)
- **Documentation**: [Complete documentation](https://docs.energygrid.ai)
- **Email Support**: support@energygrid.ai
- **Community Forum**: [Discussions](https://github.com/your-org/energygrid-ai-compliance-copilot/discussions)

### When Reporting Issues

Please include:
1. **Environment**: dev/staging/prod
2. **AWS Region**: us-east-1, etc.
3. **Error Messages**: Complete error logs
4. **Steps to Reproduce**: Detailed reproduction steps
5. **Expected vs Actual**: What you expected vs what happened
6. **System Information**: AWS CLI version, SAM CLI version, Python version
7. **Recent Changes**: Any recent deployments or configuration changes