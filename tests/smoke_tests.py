"""
Smoke tests for EnergyGrid.AI Compliance Copilot deployment validation.
These tests verify that the deployed application is functioning correctly.
"""

import os
import pytest
import requests
import boto3
from botocore.exceptions import ClientError
import json
import time


class TestDeploymentSmoke:
    """Smoke tests to validate deployment health."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.stack_name = f"energygrid-compliance-copilot-{self.environment}"
        
        # Initialize AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.dynamodb = boto3.client('dynamodb', region_name=self.region)
        
        # Get stack outputs
        self.stack_outputs = self._get_stack_outputs()
        
    def _get_stack_outputs(self):
        """Get CloudFormation stack outputs."""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            outputs = {}
            for output in response['Stacks'][0].get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            return outputs
        except ClientError as e:
            pytest.fail(f"Failed to get stack outputs: {e}")
    
    def test_stack_exists_and_complete(self):
        """Test that the CloudFormation stack exists and is in a complete state."""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            stack_status = response['Stacks'][0]['StackStatus']
            
            assert stack_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE'], \
                f"Stack is not in a complete state: {stack_status}"
                
        except ClientError as e:
            pytest.fail(f"Stack does not exist or is not accessible: {e}")
    
    def test_lambda_functions_exist(self):
        """Test that all Lambda functions exist and are active."""
        expected_functions = [
            f"{self.environment}-energygrid-upload",
            f"{self.environment}-energygrid-analyzer",
            f"{self.environment}-energygrid-planner",
            f"{self.environment}-energygrid-reporter",
            f"{self.environment}-energygrid-status"
        ]
        
        for function_name in expected_functions:
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                assert response['Configuration']['State'] == 'Active', \
                    f"Function {function_name} is not active"
            except ClientError as e:
                pytest.fail(f"Function {function_name} does not exist: {e}")
    
    def test_s3_buckets_exist(self):
        """Test that S3 buckets exist and are accessible."""
        expected_buckets = [
            f"{self.environment}-energygrid-documents-{self._get_account_id()}",
            f"{self.environment}-energygrid-reports-{self._get_account_id()}"
        ]
        
        for bucket_name in expected_buckets:
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                pytest.fail(f"Bucket {bucket_name} does not exist or is not accessible: {e}")
    
    def test_dynamodb_tables_exist(self):
        """Test that DynamoDB tables exist and are active."""
        expected_tables = [
            f"{self.environment}-energygrid-documents",
            f"{self.environment}-energygrid-obligations",
            f"{self.environment}-energygrid-tasks",
            f"{self.environment}-energygrid-reports",
            f"{self.environment}-energygrid-processing-status"
        ]
        
        for table_name in expected_tables:
            try:
                response = self.dynamodb.describe_table(TableName=table_name)
                assert response['Table']['TableStatus'] == 'ACTIVE', \
                    f"Table {table_name} is not active"
            except ClientError as e:
                pytest.fail(f"Table {table_name} does not exist: {e}")
    
    def test_api_gateway_health(self):
        """Test that API Gateway is responding."""
        if 'ApiGatewayUrl' not in self.stack_outputs:
            pytest.skip("API Gateway URL not found in stack outputs")
        
        api_url = self.stack_outputs['ApiGatewayUrl']
        
        # Test basic connectivity (OPTIONS request should work without auth)
        try:
            response = requests.options(f"{api_url}/documents/upload", timeout=10)
            assert response.status_code in [200, 204], \
                f"API Gateway not responding correctly: {response.status_code}"
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API Gateway is not accessible: {e}")
    
    def test_cognito_user_pool_exists(self):
        """Test that Cognito User Pool exists."""
        if 'UserPoolId' not in self.stack_outputs:
            pytest.skip("User Pool ID not found in stack outputs")
        
        cognito = boto3.client('cognito-idp', region_name=self.region)
        user_pool_id = self.stack_outputs['UserPoolId']
        
        try:
            response = cognito.describe_user_pool(UserPoolId=user_pool_id)
            assert response['UserPool']['Status'] == 'Enabled', \
                "User Pool is not enabled"
        except ClientError as e:
            pytest.fail(f"User Pool does not exist or is not accessible: {e}")
    
    def test_lambda_function_invocation(self):
        """Test that Lambda functions can be invoked (basic connectivity)."""
        # Test status function with a simple invocation
        status_function_name = f"{self.environment}-energygrid-status"
        
        try:
            # Create a test event
            test_event = {
                "httpMethod": "GET",
                "path": "/documents/test-id/status",
                "pathParameters": {"id": "test-id"},
                "headers": {},
                "queryStringParameters": None,
                "body": None
            }
            
            response = self.lambda_client.invoke(
                FunctionName=status_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            # Should not crash, even if it returns an error due to missing document
            assert response['StatusCode'] == 200, \
                "Lambda function invocation failed"
                
        except ClientError as e:
            pytest.fail(f"Failed to invoke Lambda function: {e}")
    
    def test_cloudwatch_alarms_exist(self):
        """Test that CloudWatch alarms are configured."""
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        
        expected_alarms = [
            f"{self.environment}-energygrid-analyzer-errors",
            f"{self.environment}-energygrid-planner-errors",
            f"{self.environment}-energygrid-reporter-errors",
            f"{self.environment}-energygrid-upload-errors"
        ]
        
        try:
            response = cloudwatch.describe_alarms()
            alarm_names = [alarm['AlarmName'] for alarm in response['MetricAlarms']]
            
            for expected_alarm in expected_alarms:
                assert expected_alarm in alarm_names, \
                    f"Alarm {expected_alarm} not found"
                    
        except ClientError as e:
            pytest.fail(f"Failed to describe CloudWatch alarms: {e}")
    
    def test_sqs_queues_exist(self):
        """Test that SQS queues exist."""
        sqs = boto3.client('sqs', region_name=self.region)
        
        expected_queues = [
            f"{self.environment}-energygrid-upload-queue",
            f"{self.environment}-energygrid-analysis-queue",
            f"{self.environment}-energygrid-planning-queue",
            f"{self.environment}-energygrid-reporting-queue"
        ]
        
        try:
            response = sqs.list_queues()
            queue_urls = response.get('QueueUrls', [])
            
            for expected_queue in expected_queues:
                queue_found = any(expected_queue in url for url in queue_urls)
                assert queue_found, f"Queue {expected_queue} not found"
                
        except ClientError as e:
            pytest.fail(f"Failed to list SQS queues: {e}")
    
    def test_sns_topic_exists(self):
        """Test that SNS notification topic exists."""
        sns = boto3.client('sns', region_name=self.region)
        
        expected_topic = f"{self.environment}-energygrid-notifications"
        
        try:
            response = sns.list_topics()
            topic_arns = [topic['TopicArn'] for topic in response['Topics']]
            
            topic_found = any(expected_topic in arn for arn in topic_arns)
            assert topic_found, f"SNS topic {expected_topic} not found"
            
        except ClientError as e:
            pytest.fail(f"Failed to list SNS topics: {e}")
    
    def _get_account_id(self):
        """Get AWS account ID."""
        sts = boto3.client('sts', region_name=self.region)
        return sts.get_caller_identity()['Account']


class TestPerformanceBaseline:
    """Basic performance tests to establish baseline metrics."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.lambda_client = boto3.client('lambda', region_name=self.region)
    
    def test_lambda_cold_start_time(self):
        """Test Lambda function cold start performance."""
        function_name = f"{self.environment}-energygrid-status"
        
        # Measure cold start time
        start_time = time.time()
        
        try:
            test_event = {
                "httpMethod": "GET",
                "path": "/documents/test-id/status",
                "pathParameters": {"id": "test-id"},
                "headers": {},
                "queryStringParameters": None,
                "body": None
            }
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Cold start should be under 5 seconds for this function
            assert duration < 5000, f"Cold start took too long: {duration}ms"
            
            print(f"Cold start duration: {duration:.2f}ms")
            
        except ClientError as e:
            pytest.fail(f"Failed to test cold start performance: {e}")


if __name__ == "__main__":
    # Run smoke tests
    pytest.main([__file__, "-v"])