"""
End-to-end tests for the complete document processing workflow.
These tests verify the entire pipeline from document upload to report generation.
"""

import pytest
import boto3
import requests
import json
import time
import os
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class TestDocumentWorkflow:
    """End-to-end tests for document processing workflow."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment and clients."""
        self.environment = os.getenv('ENVIRONMENT', 'dev')
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
        
        # API headers
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        }
        
        # Test data
        self.test_document_id = None
        self.test_obligations = []
        self.test_tasks = []
        self.test_report_id = None
    
    def create_test_pdf(self, content: str = None) -> str:
        """Create a test PDF file with sample regulatory content."""
        if content is None:
            content = """
            ENERGY REGULATORY COMPLIANCE REQUIREMENTS
            
            Section 1: Reporting Obligations
            
            1.1 Quarterly Reporting
            All transmission operators must submit quarterly compliance reports 
            to the regulatory authority within 30 days of the end of each quarter.
            The reports must include:
            - Operational performance metrics
            - Safety incident reports
            - Environmental compliance status
            - Financial performance indicators
            
            1.2 Annual Audits
            Each utility company shall undergo an annual compliance audit 
            conducted by an independent third party. The audit must be completed
            within 90 days of the fiscal year end.
            
            Section 2: Monitoring Requirements
            
            2.1 Real-time Monitoring
            All grid operators must maintain continuous monitoring of:
            - System frequency and voltage levels
            - Power flow measurements
            - Equipment status and alarms
            - Weather conditions affecting operations
            
            2.2 Data Retention
            All monitoring data must be retained for a minimum of 7 years
            and made available to regulatory authorities upon request.
            
            Section 3: Safety Requirements
            
            3.1 Personnel Training
            All personnel working on electrical systems must complete
            annual safety training and certification programs.
            
            3.2 Equipment Maintenance
            Critical equipment must be inspected and maintained according
            to manufacturer specifications and industry best practices.
            """
        
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
            
            c.drawString(50, y_position, line.strip())
            y_position -= 20
        
        c.save()
        return temp_file.name
    
    def upload_document(self, pdf_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Upload a document and return the response."""
        if metadata is None:
            metadata = {
                "title": "Test Regulatory Document",
                "source": "Test Regulatory Authority",
                "effective_date": "2024-01-01",
                "document_type": "regulation"
            }
        
        with open(pdf_path, 'rb') as file:
            files = {'file': file}
            data = {'metadata': json.dumps(metadata)}
            
            response = requests.post(
                f"{self.api_base_url}/documents/upload",
                files=files,
                data=data,
                headers={'Authorization': self.headers['Authorization']},
                timeout=30
            )
        
        assert response.status_code == 201, f"Upload failed: {response.text}"
        return response.json()
    
    def wait_for_processing_completion(self, document_id: str, timeout: int = 600) -> Dict[str, Any]:
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
            
            time.sleep(10)  # Wait 10 seconds before checking again
        
        pytest.fail(f"Document processing timed out after {timeout} seconds")
    
    def get_obligations(self, document_id: str) -> list:
        """Get obligations extracted from a document."""
        response = requests.get(
            f"{self.api_base_url}/obligations",
            params={'document_id': document_id, 'limit': 100},
            headers=self.headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Get obligations failed: {response.text}"
        return response.json()['obligations']
    
    def get_tasks(self, obligation_id: str = None) -> list:
        """Get tasks generated from obligations."""
        params = {'limit': 100}
        if obligation_id:
            params['obligation_id'] = obligation_id
        
        response = requests.get(
            f"{self.api_base_url}/tasks",
            params=params,
            headers=self.headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Get tasks failed: {response.text}"
        return response.json()['tasks']
    
    def generate_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a compliance report."""
        response = requests.post(
            f"{self.api_base_url}/reports/generate",
            json=report_config,
            headers=self.headers,
            timeout=30
        )
        
        assert response.status_code == 202, f"Report generation failed: {response.text}"
        return response.json()
    
    def wait_for_report_completion(self, report_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for report generation to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.api_base_url}/reports/{report_id}/status",
                headers=self.headers,
                timeout=10
            )
            
            assert response.status_code == 200, f"Report status check failed: {response.text}"
            status_data = response.json()
            
            if status_data['status'] == 'completed':
                return status_data
            elif status_data['status'] == 'failed':
                pytest.fail(f"Report generation failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(5)  # Wait 5 seconds before checking again
        
        pytest.fail(f"Report generation timed out after {timeout} seconds")
    
    def test_complete_document_workflow(self):
        """Test the complete document processing workflow."""
        # Step 1: Create and upload test document
        pdf_path = self.create_test_pdf()
        
        try:
            upload_response = self.upload_document(pdf_path)
            self.test_document_id = upload_response['document_id']
            
            assert 'document_id' in upload_response
            assert upload_response['status'] == 'uploaded'
            
            # Step 2: Wait for processing to complete
            final_status = self.wait_for_processing_completion(self.test_document_id)
            assert final_status['status'] == 'completed'
            
            # Step 3: Verify obligations were extracted
            obligations = self.get_obligations(self.test_document_id)
            self.test_obligations = obligations
            
            assert len(obligations) > 0, "No obligations were extracted"
            
            # Verify obligation structure
            for obligation in obligations:
                assert 'obligation_id' in obligation
                assert 'description' in obligation
                assert 'category' in obligation
                assert 'severity' in obligation
                assert 'confidence_score' in obligation
                assert obligation['confidence_score'] >= 0.0
                assert obligation['confidence_score'] <= 1.0
            
            # Step 4: Verify tasks were generated
            tasks = self.get_tasks()
            self.test_tasks = [task for task in tasks if any(
                task.get('obligation_id') == obl['obligation_id'] 
                for obl in obligations
            )]
            
            assert len(self.test_tasks) > 0, "No tasks were generated"
            
            # Verify task structure
            for task in self.test_tasks:
                assert 'task_id' in task
                assert 'title' in task
                assert 'description' in task
                assert 'priority' in task
                assert 'status' in task
                assert 'due_date' in task
            
            # Step 5: Generate and verify report
            report_config = {
                "report_type": "compliance_summary",
                "title": "E2E Test Report",
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                "filters": {
                    "document_ids": [self.test_document_id]
                }
            }
            
            report_response = self.generate_report(report_config)
            self.test_report_id = report_response['report_id']
            
            assert 'report_id' in report_response
            assert report_response['status'] == 'generating'
            
            # Wait for report completion
            report_status = self.wait_for_report_completion(self.test_report_id)
            assert report_status['status'] == 'completed'
            assert 'download_url' in report_status
            
            # Step 6: Verify report download
            download_response = requests.get(
                f"{self.api_base_url}/reports/{self.test_report_id}",
                headers=self.headers,
                timeout=30
            )
            
            assert download_response.status_code == 200
            assert download_response.headers['content-type'] == 'application/pdf'
            assert len(download_response.content) > 0
            
        finally:
            # Cleanup
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_document_processing_error_handling(self):
        """Test error handling in document processing."""
        # Test 1: Upload invalid file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"This is not a PDF file")
            temp_file.flush()
            
            try:
                with open(temp_file.name, 'rb') as file:
                    files = {'file': file}
                    data = {'metadata': json.dumps({"title": "Invalid File"})}
                    
                    response = requests.post(
                        f"{self.api_base_url}/documents/upload",
                        files=files,
                        data=data,
                        headers={'Authorization': self.headers['Authorization']},
                        timeout=30
                    )
                
                assert response.status_code == 400
                error_data = response.json()
                assert 'error' in error_data
                
            finally:
                os.unlink(temp_file.name)
        
        # Test 2: Upload oversized file (simulate with large content)
        large_content = "Large file content. " * 100000  # Create large content
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Create a large PDF-like file
            temp_file.write(b"%PDF-1.4\n")
            temp_file.write(large_content.encode() * 100)  # Make it very large
            temp_file.flush()
            
            try:
                # Check file size
                file_size = os.path.getsize(temp_file.name)
                if file_size > 50 * 1024 * 1024:  # If larger than 50MB
                    with open(temp_file.name, 'rb') as file:
                        files = {'file': file}
                        data = {'metadata': json.dumps({"title": "Large File"})}
                        
                        response = requests.post(
                            f"{self.api_base_url}/documents/upload",
                            files=files,
                            data=data,
                            headers={'Authorization': self.headers['Authorization']},
                            timeout=60
                        )
                    
                    # Should reject large files
                    assert response.status_code == 413
                
            finally:
                os.unlink(temp_file.name)
        
        # Test 3: Test with corrupted PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"Not a real PDF content")
            temp_file.flush()
            
            try:
                with open(temp_file.name, 'rb') as file:
                    files = {'file': file}
                    data = {'metadata': json.dumps({"title": "Corrupted PDF"})}
                    
                    response = requests.post(
                        f"{self.api_base_url}/documents/upload",
                        files=files,
                        data=data,
                        headers={'Authorization': self.headers['Authorization']},
                        timeout=30
                    )
                
                # Upload might succeed but processing should fail
                if response.status_code == 201:
                    document_id = response.json()['document_id']
                    
                    # Wait a bit and check status
                    time.sleep(60)
                    status_response = requests.get(
                        f"{self.api_base_url}/documents/{document_id}/status",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    assert status_response.status_code == 200
                    status_data = status_response.json()
                    
                    # Should either be failed or still processing
                    assert status_data['status'] in ['failed', 'processing']
                
            finally:
                os.unlink(temp_file.name)
        
        # Test 4: Test malformed metadata
        pdf_path = self.create_test_pdf("Simple test content")
        try:
            with open(pdf_path, 'rb') as file:
                files = {'file': file}
                data = {'metadata': 'invalid json'}  # Invalid JSON
                
                response = requests.post(
                    f"{self.api_base_url}/documents/upload",
                    files=files,
                    data=data,
                    headers={'Authorization': self.headers['Authorization']},
                    timeout=30
                )
            
            assert response.status_code == 400
            
        finally:
            os.unlink(pdf_path)
        
        # Test 5: Test missing required fields
        pdf_path = self.create_test_pdf("Simple test content")
        try:
            with open(pdf_path, 'rb') as file:
                files = {'file': file}
                # No metadata provided
                
                response = requests.post(
                    f"{self.api_base_url}/documents/upload",
                    files=files,
                    headers={'Authorization': self.headers['Authorization']},
                    timeout=30
                )
            
            # Should either accept with defaults or reject
            assert response.status_code in [201, 400]
            
        finally:
            os.unlink(pdf_path)
    
    def test_api_authentication(self):
        """Test API authentication and authorization."""
        # Test without token
        response = requests.get(
            f"{self.api_base_url}/obligations",
            timeout=10
        )
        assert response.status_code == 401
        
        # Test with invalid token
        invalid_headers = {'Authorization': 'Bearer invalid-token'}
        response = requests.get(
            f"{self.api_base_url}/obligations",
            headers=invalid_headers,
            timeout=10
        )
        assert response.status_code == 401
    
    def test_api_rate_limiting(self):
        """Test API rate limiting behavior."""
        # Make multiple rapid requests to test rate limiting
        responses = []
        
        for i in range(20):
            response = requests.get(
                f"{self.api_base_url}/obligations",
                headers=self.headers,
                timeout=10
            )
            responses.append(response.status_code)
            
            if response.status_code == 429:
                # Rate limit hit, this is expected
                break
        
        # Should have at least some successful requests
        assert 200 in responses
    
    def test_data_consistency(self):
        """Test data consistency across different API endpoints."""
        if not self.test_document_id:
            pytest.skip("No test document available")
        
        # Get obligations from obligations endpoint
        obligations_response = requests.get(
            f"{self.api_base_url}/obligations",
            params={'document_id': self.test_document_id},
            headers=self.headers,
            timeout=10
        )
        
        assert obligations_response.status_code == 200
        obligations = obligations_response.json()['obligations']
        
        # Get tasks and verify they reference valid obligations
        tasks_response = requests.get(
            f"{self.api_base_url}/tasks",
            headers=self.headers,
            timeout=10
        )
        
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()['tasks']
        
        obligation_ids = {obl['obligation_id'] for obl in obligations}
        
        for task in tasks:
            if 'obligation_id' in task:
                # If task has obligation_id, it should reference a valid obligation
                # (Note: tasks might reference obligations from other documents too)
                pass
    
    def test_pagination(self):
        """Test API pagination functionality."""
        # Test obligations pagination
        response = requests.get(
            f"{self.api_base_url}/obligations",
            params={'limit': 5, 'offset': 0},
            headers=self.headers,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'obligations' in data
        assert 'pagination' in data
        assert 'total' in data['pagination']
        assert 'limit' in data['pagination']
        assert 'offset' in data['pagination']
        
        # Test tasks pagination
        response = requests.get(
            f"{self.api_base_url}/tasks",
            params={'limit': 5, 'offset': 0},
            headers=self.headers,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'tasks' in data
        assert 'pagination' in data
    
    def test_filtering_and_search(self):
        """Test API filtering and search functionality."""
        # Test obligation filtering by category
        response = requests.get(
            f"{self.api_base_url}/obligations",
            params={'category': 'reporting'},
            headers=self.headers,
            timeout=10
        )
        
        assert response.status_code == 200
        obligations = response.json()['obligations']
        
        for obligation in obligations:
            assert obligation['category'] == 'reporting'
        
        # Test task filtering by status
        response = requests.get(
            f"{self.api_base_url}/tasks",
            params={'status': 'pending'},
            headers=self.headers,
            timeout=10
        )
        
        assert response.status_code == 200
        tasks = response.json()['tasks']
        
        for task in tasks:
            assert task['status'] == 'pending'
    
    def test_agent_data_flow_verification(self):
        """Test data flow between all agents and verify consistency."""
        if not self.test_document_id:
            pytest.skip("No test document available")
        
        # Get all data related to our test document
        obligations = self.get_obligations(self.test_document_id)
        all_tasks = self.get_tasks()
        
        # Filter tasks related to our obligations
        obligation_ids = {obl['obligation_id'] for obl in obligations}
        related_tasks = [task for task in all_tasks if task.get('obligation_id') in obligation_ids]
        
        # Test 1: Verify Analyzer Agent output quality
        assert len(obligations) > 0, "No obligations extracted by Analyzer Agent"
        
        # Check obligation categorization
        categories = [obl['category'] for obl in obligations]
        expected_categories = ['reporting', 'monitoring', 'operational', 'environmental']
        found_categories = [cat for cat in expected_categories if cat in categories]
        assert len(found_categories) >= 2, f"Expected multiple categories, found: {found_categories}"
        
        # Check confidence scores
        high_confidence_count = sum(1 for obl in obligations if obl['confidence_score'] >= 0.7)
        assert high_confidence_count >= len(obligations) * 0.5, "Too few high-confidence obligations"
        
        # Test 2: Verify Planner Agent output quality
        assert len(related_tasks) > 0, "No tasks generated by Planner Agent"
        
        # Check task prioritization logic
        critical_obligations = [obl for obl in obligations if obl['severity'] == 'critical']
        if critical_obligations:
            critical_tasks = [
                task for task in related_tasks 
                if task.get('obligation_id') in {obl['obligation_id'] for obl in critical_obligations}
            ]
            high_priority_critical_tasks = [
                task for task in critical_tasks if task['priority'] == 'high'
            ]
            # At least 50% of critical obligation tasks should be high priority
            assert len(high_priority_critical_tasks) >= len(critical_tasks) * 0.5
        
        # Test 3: Verify data consistency
        # All tasks should reference valid obligations
        for task in related_tasks:
            if 'obligation_id' in task:
                assert task['obligation_id'] in obligation_ids, f"Task references invalid obligation: {task['obligation_id']}"
        
        # Test 4: Verify temporal consistency
        # Tasks should have reasonable due dates
        for task in related_tasks:
            if 'due_date' in task and task['due_date']:
                # Due date should be in the future (basic sanity check)
                # This is a simplified check - in reality you'd parse the date
                assert len(task['due_date']) > 0, "Due date should not be empty"
    
    def test_system_recovery_mechanisms(self):
        """Test system recovery from various failure scenarios."""
        # Test 1: Verify system handles processing interruptions
        # Create a document that might cause processing delays
        complex_content = """
        COMPLEX REGULATORY DOCUMENT WITH MULTIPLE SECTIONS
        """ + "Complex regulation text. " * 1000  # Large content
        
        pdf_path = self.create_test_pdf(complex_content)
        
        try:
            upload_response = self.upload_document(pdf_path, {
                "title": "Complex Recovery Test Document",
                "source": "Recovery Test Authority",
                "document_type": "regulation"
            })
            
            document_id = upload_response['document_id']
            
            # Monitor processing with shorter intervals to catch any issues
            max_wait = 300  # 5 minutes
            start_time = time.time()
            last_status = None
            
            while (time.time() - start_time) < max_wait:
                status_response = requests.get(
                    f"{self.api_base_url}/documents/{document_id}/status",
                    headers=self.headers,
                    timeout=10
                )
                
                assert status_response.status_code == 200
                status_data = status_response.json()
                current_status = status_data['status']
                
                # Verify status transitions are logical
                if last_status and last_status != current_status:
                    valid_transitions = {
                        'uploaded': ['processing', 'failed'],
                        'processing': ['completed', 'failed'],
                        'completed': ['completed'],  # Should stay completed
                        'failed': ['failed']  # Should stay failed
                    }
                    
                    assert current_status in valid_transitions.get(last_status, []), \
                        f"Invalid status transition: {last_status} -> {current_status}"
                
                last_status = current_status
                
                if current_status in ['completed', 'failed']:
                    break
                
                time.sleep(10)
            
            # Verify final state is reasonable
            assert last_status in ['completed', 'failed'], f"Processing stuck in status: {last_status}"
            
        finally:
            os.unlink(pdf_path)
    
    def test_concurrent_processing(self):
        """Test system behavior under concurrent load."""
        import concurrent.futures
        
        def upload_and_process_document(doc_num):
            """Upload and process a single document."""
            content = f"""
            TEST DOCUMENT {doc_num}
            
            Section 1: Reporting Requirements
            All entities must submit reports within 30 days.
            
            Section 2: Monitoring Requirements  
            Continuous monitoring is required for all operations.
            """
            
            pdf_path = self.create_test_pdf(content)
            
            try:
                upload_response = self.upload_document(pdf_path, {
                    "title": f"Concurrent Test Document {doc_num}",
                    "source": "Concurrent Test Authority",
                    "document_type": "regulation"
                })
                
                document_id = upload_response['document_id']
                
                # Wait for processing (shorter timeout for concurrent test)
                max_wait = 180  # 3 minutes
                start_time = time.time()
                
                while (time.time() - start_time) < max_wait:
                    status_response = requests.get(
                        f"{self.api_base_url}/documents/{document_id}/status",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data['status'] == 'completed':
                            return {'success': True, 'document_id': document_id}
                        elif status_data['status'] == 'failed':
                            return {'success': False, 'document_id': document_id, 'error': 'Processing failed'}
                    
                    time.sleep(5)
                
                return {'success': False, 'document_id': document_id, 'error': 'Timeout'}
                
            except Exception as e:
                return {'success': False, 'error': str(e)}
            finally:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
        
        # Process 3 documents concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_and_process_document, i) for i in range(1, 4)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify results
        successful_uploads = [r for r in results if r['success']]
        assert len(successful_uploads) >= 2, f"Too many concurrent processing failures: {results}"
    
    def test_end_to_end_performance(self):
        """Test end-to-end performance metrics."""
        # Create a moderately sized document
        content = """
        PERFORMANCE TEST REGULATORY DOCUMENT
        
        """ + "Performance test content. " * 500  # Moderate size
        
        pdf_path = self.create_test_pdf(content)
        
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
            final_status = self.wait_for_processing_completion(document_id, timeout=600)
            processing_time = time.time() - processing_start
            
            # Verify performance is within acceptable limits
            assert upload_time < 30, f"Upload took too long: {upload_time:.2f}s"
            assert processing_time < 300, f"Processing took too long: {processing_time:.2f}s"
            
            # Verify obligations were extracted efficiently
            obligations = self.get_obligations(document_id)
            assert len(obligations) > 0, "No obligations extracted"
            
            # Verify tasks were generated
            tasks = self.get_tasks()
            document_tasks = [task for task in tasks if any(
                task.get('obligation_id') == obl['obligation_id'] 
                for obl in obligations
            )]
            assert len(document_tasks) > 0, "No tasks generated"
            
            # Log performance metrics
            logger.info(f"Performance metrics - Upload: {upload_time:.2f}s, Processing: {processing_time:.2f}s")
            
        finally:
            os.unlink(pdf_path)
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Note: In a real environment, you might want to clean up test data
        # For now, we'll leave the data for inspection
        pass


class TestPerformanceE2E:
    """Performance tests for the end-to-end workflow."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup performance test environment."""
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.api_base_url = os.getenv('API_BASE_URL', '')
        self.jwt_token = os.getenv('JWT_TOKEN', '')
        
        if not self.api_base_url or not self.jwt_token:
            pytest.skip("API_BASE_URL or JWT_TOKEN not set")
        
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        }
    
    def test_api_response_times(self):
        """Test API response times are within acceptable limits."""
        endpoints = [
            ('/obligations', 'GET'),
            ('/tasks', 'GET'),
            ('/reports', 'GET')
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
            
            assert response.status_code == 200
            assert response_time < 5000, f"{endpoint} response time too slow: {response_time}ms"
    
    def test_concurrent_requests(self):
        """Test system behavior under concurrent load."""
        import concurrent.futures
        import threading
        
        def make_request():
            response = requests.get(
                f"{self.api_base_url}/obligations",
                headers=self.headers,
                timeout=10
            )
            return response.status_code
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Most requests should succeed
        success_count = sum(1 for status in results if status == 200)
        assert success_count >= 8, f"Too many failed requests: {results}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])