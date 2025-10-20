#!/usr/bin/env python3
"""
Comprehensive system integration test for EnergyGrid.AI Compliance Copilot.
This test validates the complete system functionality including all agent interactions,
data flow, error handling, and recovery mechanisms.
"""

import os
import sys
import json
import time
import boto3
import pytest
import requests
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SystemTestResult:
    """System test result data structure."""
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error: Optional[str] = None


class SystemIntegrationTest:
    """Comprehensive system integration test suite."""
    
    def __init__(self):
        """Initialize system test environment."""
        self.environment = os.getenv('ENVIRONMENT', 'test')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.api_base_url = os.getenv('API_BASE_URL', '')
        self.jwt_token = os.getenv('JWT_TOKEN', '')
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.dynamodb = boto3.client('dynamodb', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.sqs_client = boto3.client('sqs', region_name=self.region)
        self.sns_client = boto3.client('sns', region_name=self.region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.region)
        
        # Test configuration
        self.test_results: List[SystemTestResult] = []
        self.test_data = {}
        
        # API headers
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        } if self.jwt_token else {}
    
    def create_comprehensive_test_pdf(self) -> str:
        """Create a comprehensive test PDF with various regulatory content types."""
        content = """
        COMPREHENSIVE ENERGY REGULATORY FRAMEWORK
        Document ID: REG-2024-001
        Effective Date: January 1, 2024
        
        SECTION 1: CRITICAL REPORTING OBLIGATIONS
        
        1.1 Quarterly Financial Reports
        All transmission system operators must submit quarterly financial reports
        to the regulatory authority within 45 days of quarter end. Reports must include:
        - Revenue and expense statements
        - Capital expenditure details
        - Rate base calculations
        - Customer impact assessments
        
        COMPLIANCE DEADLINE: Quarterly (45 days after quarter end)
        SEVERITY: CRITICAL
        PENALTY: $50,000 per day for late submission
        
        1.2 Annual Safety Performance Reports
        Each utility must file annual safety performance reports by March 31st
        covering the previous calendar year. Reports must contain:
        - Incident statistics and root cause analysis
        - Safety training completion rates
        - Equipment failure analysis
        - Public safety metrics
        
        COMPLIANCE DEADLINE: Annual (March 31st)
        SEVERITY: HIGH
        PENALTY: $25,000 per violation
        
        SECTION 2: OPERATIONAL MONITORING REQUIREMENTS
        
        2.1 Real-time System Monitoring
        Grid operators must maintain continuous monitoring of:
        - System frequency (±0.1 Hz tolerance)
        - Voltage levels at all substations
        - Power flow measurements every 5 minutes
        - Weather conditions affecting operations
        
        Data must be archived for minimum 10 years and available for regulatory
        inspection within 24 hours of request.
        
        COMPLIANCE DEADLINE: Continuous
        SEVERITY: CRITICAL
        AUDIT FREQUENCY: Monthly
        
        2.2 Outage Reporting
        All unplanned outages affecting more than 1000 customers must be reported
        within 1 hour of occurrence. Reports must include:
        - Affected customer count
        - Estimated restoration time
        - Root cause (if known)
        - Mitigation actions taken
        
        COMPLIANCE DEADLINE: 1 hour from occurrence
        SEVERITY: HIGH
        PENALTY: $10,000 per hour delay
        
        SECTION 3: ENVIRONMENTAL COMPLIANCE
        
        3.1 Emissions Monitoring
        All generating facilities must monitor and report:
        - CO2 emissions (monthly)
        - NOx and SOx levels (weekly)
        - Particulate matter (daily)
        - Water discharge quality (daily)
        
        COMPLIANCE DEADLINE: Various (see above)
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Quarterly
        
        3.2 Renewable Energy Certificates
        Utilities must maintain renewable energy certificate (REC) compliance
        at minimum 25% of total generation by 2025, increasing to 50% by 2030.
        
        COMPLIANCE DEADLINE: Annual verification
        SEVERITY: HIGH
        PENALTY: $100 per MWh shortfall
        
        SECTION 4: CYBERSECURITY REQUIREMENTS
        
        4.1 Critical Infrastructure Protection
        All critical cyber assets must implement:
        - Multi-factor authentication
        - Network segmentation
        - Continuous monitoring
        - Incident response procedures
        
        COMPLIANCE DEADLINE: Immediate implementation
        SEVERITY: CRITICAL
        AUDIT FREQUENCY: Semi-annual
        
        4.2 Vulnerability Management
        Organizations must conduct quarterly vulnerability assessments
        and remediate critical vulnerabilities within 30 days.
        
        COMPLIANCE DEADLINE: Quarterly assessments, 30-day remediation
        SEVERITY: HIGH
        PENALTY: $5,000 per unpatched critical vulnerability
        
        SECTION 5: CUSTOMER PROTECTION
        
        5.1 Service Quality Standards
        Utilities must maintain:
        - Average outage duration < 2 hours annually
        - Customer satisfaction rating > 85%
        - Response time to service calls < 4 hours
        - Billing accuracy > 99.5%
        
        COMPLIANCE DEADLINE: Continuous monitoring
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Annual
        
        5.2 Rate Change Notifications
        All rate changes must be communicated to customers:
        - 60 days advance notice for increases > 5%
        - 30 days notice for increases < 5%
        - Public hearings for increases > 10%
        
        COMPLIANCE DEADLINE: As specified above
        SEVERITY: MEDIUM
        PENALTY: Rate change reversal + $50,000 fine
        
        SECTION 6: EMERGENCY PREPAREDNESS
        
        6.1 Emergency Response Plans
        All utilities must maintain current emergency response plans including:
        - Natural disaster response procedures
        - Cyber incident response protocols
        - Communication plans with authorities
        - Resource allocation strategies
        
        Plans must be updated annually and tested quarterly.
        
        COMPLIANCE DEADLINE: Annual updates, quarterly testing
        SEVERITY: HIGH
        AUDIT FREQUENCY: Annual
        
        6.2 Mutual Aid Agreements
        Utilities must maintain mutual aid agreements with neighboring utilities
        for emergency response and resource sharing.
        
        COMPLIANCE DEADLINE: Agreements must be current
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Bi-annual
        
        APPENDIX A: DEFINITIONS AND INTERPRETATIONS
        
        Critical Cyber Asset: Any cyber asset that, if compromised, could
        adversely impact the reliable operation of the bulk electric system.
        
        Transmission System Operator: An entity responsible for the reliable
        operation of the transmission system within its area.
        
        Renewable Energy Certificate: A tradable certificate representing
        the environmental attributes of one megawatt-hour of renewable energy.
        
        APPENDIX B: ENFORCEMENT AND PENALTIES
        
        Violation categories and associated penalties:
        - Critical violations: $10,000 - $1,000,000 per day
        - High violations: $5,000 - $100,000 per occurrence
        - Medium violations: $1,000 - $25,000 per occurrence
        - Low violations: Warning to $5,000 per occurrence
        
        Repeat violations may result in enhanced penalties up to 200% of base amount.
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
            
            c.drawString(50, y_position, line.strip()[:80])  # Limit line length
            y_position -= 15
        
        c.save()
        return temp_file.name
    
    def test_complete_document_workflow(self) -> SystemTestResult:
        """Test the complete document processing workflow from upload to report generation."""
        start_time = time.time()
        test_details = {}
        
        try:
            logger.info("Starting complete document workflow test...")
            
            # Step 1: Create and upload test document
            pdf_path = self.create_comprehensive_test_pdf()
            test_details['pdf_created'] = True
            
            # Upload document
            with open(pdf_path, 'rb') as file:
                files = {'file': file}
                metadata = {
                    "title": "Comprehensive Energy Regulatory Framework",
                    "source": "Test Regulatory Authority",
                    "effective_date": "2024-01-01",
                    "document_type": "regulation"
                }
                data = {'metadata': json.dumps(metadata)}
                
                upload_response = requests.post(
                    f"{self.api_base_url}/documents/upload",
                    files=files,
                    data=data,
                    headers={'Authorization': self.headers['Authorization']},
                    timeout=60
                )
            
            assert upload_response.status_code == 201, f"Upload failed: {upload_response.text}"
            upload_data = upload_response.json()
            document_id = upload_data['document_id']
            test_details['document_uploaded'] = True
            test_details['document_id'] = document_id
            
            # Step 2: Monitor processing status
            processing_complete = False
            max_wait_time = 900  # 15 minutes
            check_interval = 15   # 15 seconds
            start_wait = time.time()
            
            while not processing_complete and (time.time() - start_wait) < max_wait_time:
                status_response = requests.get(
                    f"{self.api_base_url}/documents/{document_id}/status",
                    headers=self.headers,
                    timeout=10
                )
                
                assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
                status_data = status_response.json()
                
                if status_data['status'] == 'completed':
                    processing_complete = True
                    test_details['processing_completed'] = True
                elif status_data['status'] == 'failed':
                    raise AssertionError(f"Document processing failed: {status_data.get('error', 'Unknown error')}")
                
                time.sleep(check_interval)
            
            assert processing_complete, f"Document processing timed out after {max_wait_time} seconds"
            
            # Step 3: Verify obligations were extracted
            obligations_response = requests.get(
                f"{self.api_base_url}/obligations",
                params={'document_id': document_id, 'limit': 100},
                headers=self.headers,
                timeout=30
            )
            
            assert obligations_response.status_code == 200, f"Get obligations failed: {obligations_response.text}"
            obligations_data = obligations_response.json()
            obligations = obligations_data['obligations']
            
            assert len(obligations) >= 10, f"Expected at least 10 obligations, got {len(obligations)}"
            test_details['obligations_extracted'] = len(obligations)
            
            # Verify obligation structure and content
            categories_found = set()
            severities_found = set()
            
            for obligation in obligations:
                assert 'obligation_id' in obligation
                assert 'description' in obligation
                assert 'category' in obligation
                assert 'severity' in obligation
                assert 'confidence_score' in obligation
                
                categories_found.add(obligation['category'])
                severities_found.add(obligation['severity'])
                
                # Verify confidence score is reasonable
                assert 0.0 <= obligation['confidence_score'] <= 1.0
            
            test_details['categories_found'] = list(categories_found)
            test_details['severities_found'] = list(severities_found)
            
            # Step 4: Verify tasks were generated
            tasks_response = requests.get(
                f"{self.api_base_url}/tasks",
                params={'limit': 100},
                headers=self.headers,
                timeout=30
            )
            
            assert tasks_response.status_code == 200, f"Get tasks failed: {tasks_response.text}"
            tasks_data = tasks_response.json()
            all_tasks = tasks_data['tasks']
            
            # Filter tasks related to our document
            document_tasks = []
            obligation_ids = {obl['obligation_id'] for obl in obligations}
            
            for task in all_tasks:
                if task.get('obligation_id') in obligation_ids:
                    document_tasks.append(task)
            
            assert len(document_tasks) >= 5, f"Expected at least 5 tasks, got {len(document_tasks)}"
            test_details['tasks_generated'] = len(document_tasks)
            
            # Verify task structure
            priorities_found = set()
            for task in document_tasks:
                assert 'task_id' in task
                assert 'title' in task
                assert 'description' in task
                assert 'priority' in task
                assert 'status' in task
                assert 'due_date' in task
                
                priorities_found.add(task['priority'])
            
            test_details['priorities_found'] = list(priorities_found)
            
            # Step 5: Generate compliance report
            report_config = {
                "report_type": "compliance_summary",
                "title": "System Test Compliance Report",
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
            report_data = report_response.json()
            report_id = report_data['report_id']
            test_details['report_requested'] = True
            test_details['report_id'] = report_id
            
            # Wait for report completion
            report_complete = False
            max_report_wait = 300  # 5 minutes
            start_report_wait = time.time()
            
            while not report_complete and (time.time() - start_report_wait) < max_report_wait:
                report_status_response = requests.get(
                    f"{self.api_base_url}/reports/{report_id}/status",
                    headers=self.headers,
                    timeout=10
                )
                
                assert report_status_response.status_code == 200, f"Report status check failed: {report_status_response.text}"
                report_status_data = report_status_response.json()
                
                if report_status_data['status'] == 'completed':
                    report_complete = True
                    test_details['report_completed'] = True
                elif report_status_data['status'] == 'failed':
                    raise AssertionError(f"Report generation failed: {report_status_data.get('error', 'Unknown error')}")
                
                time.sleep(5)
            
            assert report_complete, f"Report generation timed out after {max_report_wait} seconds"
            
            # Step 6: Download and verify report
            download_response = requests.get(
                f"{self.api_base_url}/reports/{report_id}",
                headers=self.headers,
                timeout=60
            )
            
            assert download_response.status_code == 200, f"Report download failed: {download_response.text}"
            assert download_response.headers['content-type'] == 'application/pdf'
            assert len(download_response.content) > 1000, "Report PDF seems too small"
            
            test_details['report_downloaded'] = True
            test_details['report_size_bytes'] = len(download_response.content)
            
            # Store test data for other tests
            self.test_data['document_id'] = document_id
            self.test_data['obligations'] = obligations
            self.test_data['tasks'] = document_tasks
            self.test_data['report_id'] = report_id
            
            # Cleanup
            os.unlink(pdf_path)
            
            duration = time.time() - start_time
            return SystemTestResult(
                test_name="complete_document_workflow",
                success=True,
                duration=duration,
                details=test_details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Complete document workflow test failed: {str(e)}")
            return SystemTestResult(
                test_name="complete_document_workflow",
                success=False,
                duration=duration,
                details=test_details,
                error=str(e)
            )
    
    def test_agent_interactions(self) -> SystemTestResult:
        """Test all agent interactions and data flow between agents."""
        start_time = time.time()
        test_details = {}
        
        try:
            logger.info("Testing agent interactions and data flow...")
            
            # Verify we have test data from previous test
            if not self.test_data.get('document_id'):
                raise AssertionError("No test document available for agent interaction testing")
            
            document_id = self.test_data['document_id']
            obligations = self.test_data['obligations']
            tasks = self.test_data['tasks']
            
            # Test 1: Verify Analyzer Agent output quality
            test_details['analyzer_agent_test'] = {}
            
            # Check that obligations have proper categorization
            categories = [obl['category'] for obl in obligations]
            expected_categories = ['reporting', 'monitoring', 'operational', 'environmental']
            found_categories = [cat for cat in expected_categories if cat in categories]
            
            test_details['analyzer_agent_test']['categories_found'] = found_categories
            test_details['analyzer_agent_test']['total_obligations'] = len(obligations)
            
            # Verify high-confidence obligations
            high_confidence_obligations = [
                obl for obl in obligations 
                if obl['confidence_score'] >= 0.8
            ]
            test_details['analyzer_agent_test']['high_confidence_count'] = len(high_confidence_obligations)
            
            assert len(high_confidence_obligations) >= 5, "Not enough high-confidence obligations extracted"
            
            # Test 2: Verify Planner Agent output quality
            test_details['planner_agent_test'] = {}
            
            # Check task prioritization
            priorities = [task['priority'] for task in tasks]
            priority_distribution = {
                'high': priorities.count('high'),
                'medium': priorities.count('medium'),
                'low': priorities.count('low')
            }
            test_details['planner_agent_test']['priority_distribution'] = priority_distribution
            
            # Verify critical obligations have high-priority tasks
            critical_obligations = [obl for obl in obligations if obl['severity'] == 'critical']
            critical_obligation_ids = {obl['obligation_id'] for obl in critical_obligations}
            
            high_priority_tasks_for_critical = [
                task for task in tasks 
                if task.get('obligation_id') in critical_obligation_ids and task['priority'] == 'high'
            ]
            
            test_details['planner_agent_test']['critical_obligations'] = len(critical_obligations)
            test_details['planner_agent_test']['high_priority_tasks_for_critical'] = len(high_priority_tasks_for_critical)
            
            # Test 3: Verify data consistency between agents
            test_details['data_consistency_test'] = {}
            
            # Check that all tasks reference valid obligations
            task_obligation_ids = {task.get('obligation_id') for task in tasks if task.get('obligation_id')}
            obligation_ids = {obl['obligation_id'] for obl in obligations}
            
            orphaned_tasks = task_obligation_ids - obligation_ids
            test_details['data_consistency_test']['orphaned_tasks'] = len(orphaned_tasks)
            
            assert len(orphaned_tasks) == 0, f"Found {len(orphaned_tasks)} tasks referencing non-existent obligations"
            
            # Test 4: Verify Reporter Agent can access all data
            test_details['reporter_agent_test'] = {}
            
            # The fact that we successfully generated a report in the previous test
            # indicates the Reporter Agent can access and compile data from both
            # Analyzer and Planner agents
            test_details['reporter_agent_test']['report_generated'] = True
            test_details['reporter_agent_test']['report_id'] = self.test_data.get('report_id')
            
            duration = time.time() - start_time
            return SystemTestResult(
                test_name="agent_interactions",
                success=True,
                duration=duration,
                details=test_details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Agent interactions test failed: {str(e)}")
            return SystemTestResult(
                test_name="agent_interactions",
                success=False,
                duration=duration,
                details=test_details,
                error=str(e)
            )
    
    def test_error_scenarios_and_recovery(self) -> SystemTestResult:
        """Test error scenarios and recovery mechanisms."""
        start_time = time.time()
        test_details = {}
        
        try:
            logger.info("Testing error scenarios and recovery mechanisms...")
            
            # Test 1: Invalid file upload
            test_details['invalid_file_test'] = {}
            
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
                    
                    test_details['invalid_file_test']['response_code'] = response.status_code
                    test_details['invalid_file_test']['error_handled'] = response.status_code == 400
                    
                    assert response.status_code == 400, "Invalid file should be rejected"
                    
                finally:
                    os.unlink(temp_file.name)
            
            # Test 2: Corrupted PDF handling
            test_details['corrupted_pdf_test'] = {}
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(b"Not a real PDF content but has PDF extension")
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
                    
                    test_details['corrupted_pdf_test']['upload_response_code'] = response.status_code
                    
                    if response.status_code == 201:
                        # Upload succeeded, check if processing fails gracefully
                        document_id = response.json()['document_id']
                        
                        # Wait and check status
                        time.sleep(60)  # Give it time to process
                        
                        status_response = requests.get(
                            f"{self.api_base_url}/documents/{document_id}/status",
                            headers=self.headers,
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            test_details['corrupted_pdf_test']['processing_status'] = status_data['status']
                            test_details['corrupted_pdf_test']['error_handled'] = status_data['status'] == 'failed'
                        
                finally:
                    os.unlink(temp_file.name)
            
            # Test 3: Authentication error handling
            test_details['auth_error_test'] = {}
            
            # Test without token
            response = requests.get(f"{self.api_base_url}/obligations", timeout=10)
            test_details['auth_error_test']['no_token_response'] = response.status_code
            assert response.status_code == 401, "Should require authentication"
            
            # Test with invalid token
            invalid_headers = {'Authorization': 'Bearer invalid-token-12345'}
            response = requests.get(
                f"{self.api_base_url}/obligations",
                headers=invalid_headers,
                timeout=10
            )
            test_details['auth_error_test']['invalid_token_response'] = response.status_code
            assert response.status_code == 401, "Should reject invalid token"
            
            # Test 4: Rate limiting behavior
            test_details['rate_limiting_test'] = {}
            
            # Make rapid requests to test rate limiting
            responses = []
            for i in range(15):
                response = requests.get(
                    f"{self.api_base_url}/obligations",
                    headers=self.headers,
                    timeout=10
                )
                responses.append(response.status_code)
                
                if response.status_code == 429:
                    test_details['rate_limiting_test']['rate_limit_triggered'] = True
                    break
                
                time.sleep(0.1)  # Small delay between requests
            
            test_details['rate_limiting_test']['responses'] = responses
            test_details['rate_limiting_test']['successful_requests'] = responses.count(200)
            
            # Test 5: Large document handling
            test_details['large_document_test'] = {}
            
            # Create a larger PDF (but still within limits)
            large_content = "LARGE REGULATORY DOCUMENT\n\n" + ("This is a test line for a large document.\n" * 1000)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            c = canvas.Canvas(temp_file.name, pagesize=letter)
            width, height = letter
            
            lines = large_content.split('\n')
            y_position = height - 50
            
            for line in lines[:500]:  # Limit to avoid timeout
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                
                c.drawString(50, y_position, line[:80])
                y_position -= 15
            
            c.save()
            
            try:
                with open(temp_file.name, 'rb') as file:
                    files = {'file': file}
                    data = {'metadata': json.dumps({"title": "Large Test Document"})}
                    
                    response = requests.post(
                        f"{self.api_base_url}/documents/upload",
                        files=files,
                        data=data,
                        headers={'Authorization': self.headers['Authorization']},
                        timeout=120
                    )
                
                test_details['large_document_test']['upload_response'] = response.status_code
                test_details['large_document_test']['handled_successfully'] = response.status_code in [201, 413]
                
                if response.status_code == 201:
                    # Monitor processing
                    document_id = response.json()['document_id']
                    
                    # Check status after some time
                    time.sleep(120)
                    status_response = requests.get(
                        f"{self.api_base_url}/documents/{document_id}/status",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        test_details['large_document_test']['processing_status'] = status_data['status']
                
            finally:
                os.unlink(temp_file.name)
            
            duration = time.time() - start_time
            return SystemTestResult(
                test_name="error_scenarios_and_recovery",
                success=True,
                duration=duration,
                details=test_details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error scenarios test failed: {str(e)}")
            return SystemTestResult(
                test_name="error_scenarios_and_recovery",
                success=False,
                duration=duration,
                details=test_details,
                error=str(e)
            )
    
    def test_concurrent_processing(self) -> SystemTestResult:
        """Test system behavior under concurrent load."""
        start_time = time.time()
        test_details = {}
        
        try:
            logger.info("Testing concurrent processing capabilities...")
            
            # Create multiple test PDFs
            pdf_files = []
            for i in range(3):  # Create 3 test documents
                content = f"""
                TEST REGULATION DOCUMENT {i+1}
                
                Section 1: Test Obligations for Document {i+1}
                
                1.1 Test Reporting Requirement {i+1}
                All entities must submit test report {i+1} within 30 days.
                This is a test obligation with medium severity.
                
                1.2 Test Monitoring Requirement {i+1}
                Continuous monitoring of test parameter {i+1} is required.
                This is a test obligation with high severity.
                """
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                c = canvas.Canvas(temp_file.name, pagesize=letter)
                
                lines = content.strip().split('\n')
                y_position = 750
                
                for line in lines:
                    c.drawString(50, y_position, line.strip())
                    y_position -= 20
                
                c.save()
                pdf_files.append(temp_file.name)
            
            # Upload documents concurrently
            def upload_document(pdf_path, doc_index):
                try:
                    with open(pdf_path, 'rb') as file:
                        files = {'file': file}
                        metadata = {
                            "title": f"Concurrent Test Document {doc_index}",
                            "source": "Test Authority",
                            "document_type": "regulation"
                        }
                        data = {'metadata': json.dumps(metadata)}
                        
                        response = requests.post(
                            f"{self.api_base_url}/documents/upload",
                            files=files,
                            data=data,
                            headers={'Authorization': self.headers['Authorization']},
                            timeout=60
                        )
                    
                    return {
                        'doc_index': doc_index,
                        'success': response.status_code == 201,
                        'response_code': response.status_code,
                        'document_id': response.json().get('document_id') if response.status_code == 201 else None
                    }
                    
                except Exception as e:
                    return {
                        'doc_index': doc_index,
                        'success': False,
                        'error': str(e)
                    }
            
            # Execute concurrent uploads
            with ThreadPoolExecutor(max_workers=3) as executor:
                upload_futures = [
                    executor.submit(upload_document, pdf_path, i)
                    for i, pdf_path in enumerate(pdf_files)
                ]
                
                upload_results = [future.result() for future in as_completed(upload_futures)]
            
            test_details['concurrent_uploads'] = upload_results
            successful_uploads = [r for r in upload_results if r['success']]
            test_details['successful_uploads'] = len(successful_uploads)
            
            assert len(successful_uploads) >= 2, "At least 2 concurrent uploads should succeed"
            
            # Monitor processing of all documents
            document_ids = [r['document_id'] for r in successful_uploads if r.get('document_id')]
            
            def check_processing_status(document_id):
                max_wait = 300  # 5 minutes per document
                start_wait = time.time()
                
                while (time.time() - start_wait) < max_wait:
                    try:
                        response = requests.get(
                            f"{self.api_base_url}/documents/{document_id}/status",
                            headers=self.headers,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            status_data = response.json()
                            if status_data['status'] in ['completed', 'failed']:
                                return {
                                    'document_id': document_id,
                                    'final_status': status_data['status'],
                                    'processing_time': time.time() - start_wait
                                }
                        
                        time.sleep(10)
                        
                    except Exception as e:
                        return {
                            'document_id': document_id,
                            'final_status': 'error',
                            'error': str(e)
                        }
                
                return {
                    'document_id': document_id,
                    'final_status': 'timeout',
                    'processing_time': max_wait
                }
            
            # Check processing status for all documents
            with ThreadPoolExecutor(max_workers=3) as executor:
                status_futures = [
                    executor.submit(check_processing_status, doc_id)
                    for doc_id in document_ids
                ]
                
                processing_results = [future.result() for future in as_completed(status_futures)]
            
            test_details['processing_results'] = processing_results
            completed_processing = [r for r in processing_results if r['final_status'] == 'completed']
            test_details['completed_processing'] = len(completed_processing)
            
            # Test concurrent API requests
            def make_api_request(endpoint):
                try:
                    response = requests.get(
                        f"{self.api_base_url}{endpoint}",
                        headers=self.headers,
                        timeout=10
                    )
                    return {
                        'endpoint': endpoint,
                        'success': response.status_code == 200,
                        'response_code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                except Exception as e:
                    return {
                        'endpoint': endpoint,
                        'success': False,
                        'error': str(e)
                    }
            
            # Make concurrent API requests
            endpoints = ['/obligations', '/tasks', '/reports']
            with ThreadPoolExecutor(max_workers=6) as executor:
                api_futures = [
                    executor.submit(make_api_request, endpoint)
                    for endpoint in endpoints
                    for _ in range(2)  # 2 requests per endpoint
                ]
                
                api_results = [future.result() for future in as_completed(api_futures)]
            
            test_details['concurrent_api_requests'] = api_results
            successful_api_requests = [r for r in api_results if r['success']]
            test_details['successful_api_requests'] = len(successful_api_requests)
            
            # Cleanup
            for pdf_path in pdf_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
            
            duration = time.time() - start_time
            return SystemTestResult(
                test_name="concurrent_processing",
                success=True,
                duration=duration,
                details=test_details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Concurrent processing test failed: {str(e)}")
            
            # Cleanup on error
            for pdf_path in pdf_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
            
            return SystemTestResult(
                test_name="concurrent_processing",
                success=False,
                duration=duration,
                details=test_details,
                error=str(e)
            )
    
    def run_all_system_tests(self) -> List[SystemTestResult]:
        """Run all system integration tests."""
        logger.info("Starting comprehensive system integration tests...")
        
        if not self.api_base_url:
            logger.error("API_BASE_URL not configured, skipping system tests")
            return []
        
        if not self.jwt_token:
            logger.error("JWT_TOKEN not configured, skipping system tests")
            return []
        
        # Test sequence
        tests = [
            self.test_complete_document_workflow,
            self.test_agent_interactions,
            self.test_error_scenarios_and_recovery,
            self.test_concurrent_processing
        ]
        
        results = []
        for test_func in tests:
            logger.info(f"Running {test_func.__name__}...")
            result = test_func()
            results.append(result)
            
            if result.success:
                logger.info(f"✅ {result.test_name} passed ({result.duration:.1f}s)")
            else:
                logger.error(f"❌ {result.test_name} failed ({result.duration:.1f}s): {result.error}")
        
        self.test_results = results
        return results
    
    def generate_system_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive system test report."""
        if not self.test_results:
            return {"error": "No test results available"}
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        total_duration = sum(r.duration for r in self.test_results)
        
        report = {
            "timestamp": time.time(),
            "environment": self.environment,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                "total_duration": total_duration
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "details": r.details,
                    "error": r.error
                }
                for r in self.test_results
            ]
        }
        
        return report


def main():
    """Main entry point for system integration tests."""
    test_runner = SystemIntegrationTest()
    results = test_runner.run_all_system_tests()
    
    if not results:
        print("⚠️  System tests skipped due to configuration issues")
        return 0
    
    # Generate and save report
    report = test_runner.generate_system_test_report()
    
    report_file = Path(__file__).parent.parent / 'system-test-report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "="*60)
    print("🚀 SYSTEM INTEGRATION TEST SUMMARY")
    print("="*60)
    
    for result in results:
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"{result.test_name:35} {status:8} {result.duration:>8.1f}s")
    
    print("="*60)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed:      {report['summary']['passed_tests']}")
    print(f"Failed:      {report['summary']['failed_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Duration:    {report['summary']['total_duration']:.1f}s")
    print("="*60)
    
    # Return appropriate exit code
    return 0 if report['summary']['failed_tests'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())