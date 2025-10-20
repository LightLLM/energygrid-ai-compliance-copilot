#!/usr/bin/env python3
"""
Comprehensive system validation tests for EnergyGrid.AI Compliance Copilot.
These tests validate the complete system functionality including all agent interactions,
data flow consistency, error handling, and recovery mechanisms.
"""

import pytest
import boto3
import requests
import json
import time
import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemValidationTest:
    """Comprehensive system validation test suite."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment and clients."""
        self.environment = os.getenv('ENVIRONMENT', 'test')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.api_base_url = os.getenv('API_BASE_URL', '')
        self.jwt_token = os.getenv('JWT_TOKEN', '')
        
        if not self.api_base_url:
            pytest.skip("API_BASE_URL environment variable not set")
        
        if not self.jwt_token:
            pytest.skip("JWT_TOKEN environment variable not set")
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.dynamodb = boto3.client('dynamodb', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.sqs_client = boto3.client('sqs', region_name=self.region)
        
        # API headers
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        }
        
        # Test data storage
        self.test_documents = []
        self.test_obligations = []
        self.test_tasks = []
        self.test_reports = []
    
    def create_regulatory_test_pdf(self, content_type: str = "comprehensive") -> str:
        """Create test PDF with specific regulatory content types."""
        if content_type == "comprehensive":
            content = """
            COMPREHENSIVE ENERGY REGULATORY FRAMEWORK
            Document ID: SYS-VAL-001
            Effective Date: January 1, 2024
            
            SECTION 1: CRITICAL REPORTING OBLIGATIONS
            
            1.1 Quarterly Financial Reports
            All transmission system operators must submit quarterly financial reports
            to the regulatory authority within 45 days of quarter end.
            SEVERITY: CRITICAL
            DEADLINE: Quarterly (45 days after quarter end)
            
            1.2 Annual Safety Performance Reports
            Each utility must file annual safety performance reports by March 31st.
            SEVERITY: HIGH
            DEADLINE: Annual (March 31st)
            
            SECTION 2: OPERATIONAL MONITORING REQUIREMENTS
            
            2.1 Real-time System Monitoring
            Grid operators must maintain continuous monitoring of system parameters.
            SEVERITY: CRITICAL
            DEADLINE: Continuous
            
            2.2 Outage Reporting
            All unplanned outages affecting more than 1000 customers must be reported
            within 1 hour of occurrence.
            SEVERITY: HIGH
            DEADLINE: 1 hour from occurrence
            
            SECTION 3: ENVIRONMENTAL COMPLIANCE
            
            3.1 Emissions Monitoring
            All generating facilities must monitor and report emissions monthly.
            SEVERITY: MEDIUM
            DEADLINE: Monthly
            
            3.2 Renewable Energy Certificates
            Utilities must maintain renewable energy certificate compliance.
            SEVERITY: HIGH
            DEADLINE: Annual verification
            """
        elif content_type == "simple":
            content = """
            SIMPLE REGULATORY DOCUMENT
            
            Section 1: Basic Requirements
            All operators must submit annual reports by December 31st.
            SEVERITY: MEDIUM
            DEADLINE: Annual
            """
        elif content_type == "complex":
            content = """
            COMPLEX MULTI-JURISDICTIONAL REGULATORY FRAMEWORK
            """ + "Complex regulatory text with multiple obligations. " * 200
        else:
            content = content_type  # Use as literal content
        
        # Create temporary PDF file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        
        # Create PDF with content
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        width, height = letter
        
        # Add content to PDF
        lines = content.strip().split('\n')
        y_position = height - 50
        
        for line in lines:
            if y_position < 50:  # Start new page
                c.showPage()
                y_position = height - 50
            
            c.drawString(50, y_position, line.strip()[:80])  # Limit line length
            y_position -= 15
        
        c.save()
        return temp_file.name
    
    def upload_document(self, pdf_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a document and return the response."""
        with open(pdf_path, 'rb') as file:
            files = {'file': file}
            data = {'metadata': json.dumps(metadata)}
            
            response = requests.post(
                f"{self.api_base_url}/documents/upload",
                files=files,
                data=data,
                headers={'Authorization': self.headers['Authorization']},
                timeout=60
            )
        
        assert response.status_code == 201, f"Upload failed: {response.text}"
        return response.json()
    
    def wait_for_processing_completion(self, document_id: str, timeout: int = 900) -> Dict[str, Any]:
        """Wait for document processing to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.api_base_url}/documents/{document_id}/status",
                headers=self.headers,
                timeout=10
            )
            
            assert response.status_code == 200, f"Status check failed: {response.text}"
            status_data = response.json()
            
            if status_data['status'] == 'completed':
                return status_data
            elif status_data['status'] == 'failed':
                pytest.fail(f"Document processing failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(15)  # Wait 15 seconds between checks
        
        pytest.fail(f"Document processing timed out after {timeout} seconds")
    
    def get_obligations(self, document_id: str = None) -> List[Dict]:
        """Get obligations, optionally filtered by document."""
        params = {'limit': 100}
        if document_id:
            params['document_id'] = document_id
        
        response = requests.get(
            f"{self.api_base_url}/obligations",
            params=params,
            headers=self.headers,
            timeout=30
        )
        
        assert response.status_code == 200, f"Get obligations failed: {response.text}"
        return response.json()['obligations']
    
    def get_tasks(self, obligation_id: str = None) -> List[Dict]:
        """Get tasks, optionally filtered by obligation."""
        params = {'limit': 100}
        if obligation_id:
            params['obligation_id'] = obligation_id
        
        response = requests.get(
            f"{self.api_base_url}/tasks",
            params=params,
            headers=self.headers,
            timeout=30
        )
        
        assert response.status_code == 200, f"Get tasks failed: {response.text}"
        return response.json()['tasks']
    
    def test_complete_system_workflow_validation(self):
        """Validate the complete system workflow from upload to report generation."""
        logger.info("Starting complete system workflow validation...")
        
        # Step 1: Upload comprehensive test document
        pdf_path = self.create_regulatory_test_pdf("comprehensive")
        
        try:
            upload_response = self.upload_document(pdf_path, {
                "title": "System Validation Comprehensive Document",
                "source": "System Validation Authority",
                "effective_date": "2024-01-01",
                "document_type": "regulation"
            })
            
            document_id = upload_response['document_id']
            self.test_documents.append(document_id)
            
            # Step 2: Wait for complete processing
            final_status = self.wait_for_processing_completion(document_id)
            assert final_status['status'] == 'completed'
            
            # Step 3: Validate Analyzer Agent output
            obligations = self.get_obligations(document_id)
            self.test_obligations.extend(obligations)
            
            # Validate obligation extraction quality
            assert len(obligations) >= 6, f"Expected at least 6 obligations, got {len(obligations)}"
            
            # Validate obligation structure
            required_fields = ['obligation_id', 'description', 'category', 'severity', 'confidence_score']
            for obligation in obligations:
                for field in required_fields:
                    assert field in obligation, f"Missing field {field} in obligation"
                
                # Validate confidence score
                assert 0.0 <= obligation['confidence_score'] <= 1.0, \
                    f"Invalid confidence score: {obligation['confidence_score']}"
            
            # Validate categorization
            categories = {obl['category'] for obl in obligations}
            expected_categories = {'reporting', 'monitoring', 'operational', 'environmental'}
            found_categories = categories.intersection(expected_categories)
            assert len(found_categories) >= 3, f"Expected multiple categories, found: {found_categories}"
            
            # Validate severity distribution
            severities = {obl['severity'] for obl in obligations}
            expected_severities = {'critical', 'high', 'medium'}
            found_severities = severities.intersection(expected_severities)
            assert len(found_severities) >= 2, f"Expected multiple severities, found: {found_severities}"
            
            # Step 4: Validate Planner Agent output
            all_tasks = self.get_tasks()
            obligation_ids = {obl['obligation_id'] for obl in obligations}
            document_tasks = [task for task in all_tasks if task.get('obligation_id') in obligation_ids]
            self.test_tasks.extend(document_tasks)
            
            # Validate task generation
            assert len(document_tasks) >= 3, f"Expected at least 3 tasks, got {len(document_tasks)}"
            
            # Validate task structure
            required_task_fields = ['task_id', 'title', 'description', 'priority', 'status', 'due_date']
            for task in document_tasks:
                for field in required_task_fields:
                    assert field in task, f"Missing field {field} in task"
            
            # Validate priority assignment logic
            critical_obligations = [obl for obl in obligations if obl['severity'] == 'critical']
            if critical_obligations:
                critical_tasks = [
                    task for task in document_tasks 
                    if task.get('obligation_id') in {obl['obligation_id'] for obl in critical_obligations}
                ]
                high_priority_critical = [task for task in critical_tasks if task['priority'] == 'high']
                assert len(high_priority_critical) >= len(critical_tasks) * 0.5, \
                    "Critical obligations should generate high-priority tasks"
            
            # Step 5: Validate data consistency across agents
            # All tasks should reference valid obligations
            for task in document_tasks:
                if 'obligation_id' in task:
                    assert task['obligation_id'] in obligation_ids, \
                        f"Task references invalid obligation: {task['obligation_id']}"
            
            # Step 6: Validate Reporter Agent functionality
            report_config = {
                "report_type": "compliance_summary",
                "title": "System Validation Report",
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                "filters": {
                    "document_ids": [document_id]
                }
            }
            
            report_response = requests.post(
                f"{self.api_base_url}/reports/generate",
                json=report_config,
                headers=self.headers,
                timeout=60
            )
            
            assert report_response.status_code == 202, f"Report generation failed: {report_response.text}"
            report_id = report_response.json()['report_id']
            self.test_reports.append(report_id)
            
            # Wait for report completion
            max_wait = 300
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                report_status_response = requests.get(
                    f"{self.api_base_url}/reports/{report_id}/status",
                    headers=self.headers,
                    timeout=10
                )
                
                assert report_status_response.status_code == 200
                report_status = report_status_response.json()
                
                if report_status['status'] == 'completed':
                    break
                elif report_status['status'] == 'failed':
                    pytest.fail(f"Report generation failed: {report_status.get('error')}")
                
                time.sleep(10)
            
            # Validate report download
            download_response = requests.get(
                f"{self.api_base_url}/reports/{report_id}",
                headers=self.headers,
                timeout=60
            )
            
            assert download_response.status_code == 200
            assert download_response.headers['content-type'] == 'application/pdf'
            assert len(download_response.content) > 1000, "Report seems too small"
            
            logger.info("✓ Complete system workflow validation passed")
            
        finally:
            os.unlink(pdf_path)
    
    def test_agent_interaction_validation(self):
        """Validate interactions between all agents."""
        logger.info("Starting agent interaction validation...")
        
        # Use data from previous test if available
        if not self.test_obligations:
            pytest.skip("No test obligations available for agent interaction testing")
        
        # Test 1: Analyzer → Planner data flow
        analyzer_output = self.test_obligations
        planner_input_obligations = {obl['obligation_id'] for obl in analyzer_output}
        
        # Verify Planner Agent received and processed Analyzer output
        planner_output = self.test_tasks
        task_obligation_refs = {task.get('obligation_id') for task in planner_output if task.get('obligation_id')}
        
        # Check data flow consistency
        valid_references = task_obligation_refs.intersection(planner_input_obligations)
        assert len(valid_references) > 0, "No valid obligation references found in tasks"
        
        # Test 2: Verify intelligent task planning
        # High-severity obligations should generate more tasks
        high_severity_obligations = [obl for obl in analyzer_output if obl['severity'] in ['critical', 'high']]
        low_severity_obligations = [obl for obl in analyzer_output if obl['severity'] in ['medium', 'low']]
        
        if high_severity_obligations and low_severity_obligations:
            high_severity_ids = {obl['obligation_id'] for obl in high_severity_obligations}
            low_severity_ids = {obl['obligation_id'] for obl in low_severity_obligations}
            
            high_severity_tasks = [task for task in planner_output if task.get('obligation_id') in high_severity_ids]
            low_severity_tasks = [task for task in planner_output if task.get('obligation_id') in low_severity_ids]
            
            # High severity obligations should generate more tasks on average
            if len(high_severity_obligations) > 0 and len(low_severity_obligations) > 0:
                high_task_ratio = len(high_severity_tasks) / len(high_severity_obligations)
                low_task_ratio = len(low_severity_tasks) / len(low_severity_obligations)
                
                assert high_task_ratio >= low_task_ratio, \
                    "High severity obligations should generate more tasks per obligation"
        
        # Test 3: Verify Reporter Agent can access all data
        # The successful report generation in the previous test validates this
        assert len(self.test_reports) > 0, "No reports generated for validation"
        
        logger.info("✓ Agent interaction validation passed")
    
    def test_error_handling_and_recovery(self):
        """Test comprehensive error handling and recovery mechanisms."""
        logger.info("Starting error handling and recovery validation...")
        
        # Test 1: Invalid file handling
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"This is not a PDF file")
            temp_file.flush()
            
            try:
                with open(temp_file.name, 'rb') as file:
                    files = {'file': file}
                    data = {'metadata': json.dumps({"title": "Invalid File Test"})}
                    
                    response = requests.post(
                        f"{self.api_base_url}/documents/upload",
                        files=files,
                        data=data,
                        headers={'Authorization': self.headers['Authorization']},
                        timeout=30
                    )
                
                assert response.status_code == 400, "Invalid file should be rejected"
                error_data = response.json()
                assert 'error' in error_data, "Error response should contain error message"
                
            finally:
                os.unlink(temp_file.name)
        
        # Test 2: Authentication error handling
        # Test without token
        response = requests.get(f"{self.api_base_url}/obligations", timeout=10)
        assert response.status_code == 401, "Should require authentication"
        
        # Test with invalid token
        invalid_headers = {'Authorization': 'Bearer invalid-token-12345'}
        response = requests.get(
            f"{self.api_base_url}/obligations",
            headers=invalid_headers,
            timeout=10
        )
        assert response.status_code == 401, "Should reject invalid token"
        
        # Test 3: Malformed request handling
        response = requests.post(
            f"{self.api_base_url}/reports/generate",
            json={"invalid": "request"},
            headers=self.headers,
            timeout=30
        )
        assert response.status_code == 400, "Should reject malformed requests"
        
        # Test 4: Rate limiting (if implemented)
        responses = []
        for i in range(20):
            response = requests.get(
                f"{self.api_base_url}/obligations",
                headers=self.headers,
                timeout=10
            )
            responses.append(response.status_code)
            
            if response.status_code == 429:
                break  # Rate limit hit
        
        # Should have at least some successful requests
        assert 200 in responses, "No successful requests made"
        
        logger.info("✓ Error handling and recovery validation passed")
    
    def test_system_performance_validation(self):
        """Validate system performance under normal load."""
        logger.info("Starting system performance validation...")
        
        # Test 1: API response times
        endpoints = [
            ('/obligations', 'GET'),
            ('/tasks', 'GET')
        ]
        
        for endpoint, method in endpoints:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(
                    f"{self.api_base_url}{endpoint}",
                    headers=self.headers,
                    timeout=10
                )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            assert response.status_code == 200, f"{endpoint} request failed"
            assert response_time < 5000, f"{endpoint} response time too slow: {response_time:.2f}ms"
        
        # Test 2: Document processing performance
        pdf_path = self.create_regulatory_test_pdf("simple")
        
        try:
            # Measure upload time
            upload_start = time.time()
            upload_response = self.upload_document(pdf_path, {
                "title": "Performance Test Document",
                "source": "Performance Test Authority",
                "document_type": "regulation"
            })
            upload_time = time.time() - upload_start
            
            document_id = upload_response['document_id']
            
            # Measure processing time
            processing_start = time.time()
            final_status = self.wait_for_processing_completion(document_id, timeout=300)
            processing_time = time.time() - processing_start
            
            # Validate performance
            assert upload_time < 30, f"Upload too slow: {upload_time:.2f}s"
            assert processing_time < 180, f"Processing too slow: {processing_time:.2f}s"
            assert final_status['status'] == 'completed', "Processing should complete successfully"
            
        finally:
            os.unlink(pdf_path)
        
        logger.info("✓ System performance validation passed")
    
    def test_data_consistency_validation(self):
        """Validate data consistency across the entire system."""
        logger.info("Starting data consistency validation...")
        
        if not self.test_documents:
            pytest.skip("No test documents available for consistency validation")
        
        # Test 1: Cross-reference validation
        for document_id in self.test_documents:
            # Get all related data
            obligations = self.get_obligations(document_id)
            all_tasks = self.get_tasks()
            
            obligation_ids = {obl['obligation_id'] for obl in obligations}
            document_tasks = [task for task in all_tasks if task.get('obligation_id') in obligation_ids]
            
            # Validate referential integrity
            for task in document_tasks:
                if 'obligation_id' in task:
                    assert task['obligation_id'] in obligation_ids, \
                        f"Task {task['task_id']} references non-existent obligation {task['obligation_id']}"
        
        # Test 2: Data format consistency
        all_obligations = self.test_obligations
        all_tasks = self.test_tasks
        
        # Validate obligation format consistency
        if all_obligations:
            first_obligation = all_obligations[0]
            required_fields = set(first_obligation.keys())
            
            for obligation in all_obligations:
                current_fields = set(obligation.keys())
                assert current_fields == required_fields, \
                    f"Inconsistent obligation fields: {current_fields} vs {required_fields}"
        
        # Validate task format consistency
        if all_tasks:
            first_task = all_tasks[0]
            required_fields = set(first_task.keys())
            
            for task in all_tasks:
                current_fields = set(task.keys())
                # Allow for optional fields, but core fields should be consistent
                core_fields = {'task_id', 'title', 'description', 'priority', 'status'}
                task_core_fields = current_fields.intersection(core_fields)
                expected_core_fields = required_fields.intersection(core_fields)
                
                assert task_core_fields == expected_core_fields, \
                    f"Inconsistent core task fields: {task_core_fields} vs {expected_core_fields}"
        
        logger.info("✓ Data consistency validation passed")
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Log test completion
        logger.info("System validation test completed")
        
        # In a real environment, you might want to clean up test data
        # For now, we'll leave the data for inspection


if __name__ == "__main__":
    # Run the validation tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])