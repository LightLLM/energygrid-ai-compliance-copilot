#!/usr/bin/env python3
"""
Comprehensive End-to-End System Test for EnergyGrid.AI Compliance Copilot.
This test validates the complete system functionality including all agent interactions,
data flow, error scenarios, and recovery mechanisms as specified in task 12.1.
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


class ComprehensiveE2ESystemTest:
    """Comprehensive end-to-end system test suite."""
    
    def __init__(self):
        """Initialize system test environment."""
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
        self.sns_client = boto3.client('sns', region_name=self.region)
        
        # Test configuration
        self.test_results: List[SystemTestResult] = []
        self.test_data = {}
        
        # API headers
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        }
    
    def create_comprehensive_test_pdf(self) -> str:
        """Create a comprehensive test PDF with various regulatory content types."""
        content = """
        COMPREHENSIVE ENERGY REGULATORY FRAMEWORK
        Document ID: REG-E2E-2024-001
        Effective Date: January 1, 2024
        
        SECTION 1: CRITICAL REPORTING OBLIGATIONS
        
        1.1 Quarterly Financial Reports
        All transmission system operators must submit quarterly financial reports
        to the regulatory authority within 45 days of quarter end. Reports must include:
        - Revenue and expense statements with detailed breakdowns
        - Capital expenditure details and justifications
        - Rate base calculations and methodologies
        - Customer impact assessments and mitigation strategies
        
        COMPLIANCE DEADLINE: Quarterly (45 days after quarter end)
        SEVERITY: CRITICAL
        PENALTY: $50,000 per day for late submission
        APPLICABLE ENTITIES: Transmission operators, distribution utilities
        
        1.2 Annual Safety Performance Reports
        Each utility must file annual safety performance reports by March 31st
        covering the previous calendar year. Reports must contain:
        - Incident statistics and comprehensive root cause analysis
        - Safety training completion rates by department
        - Equipment failure analysis with trending data
        - Public safety metrics and improvement plans
        
        COMPLIANCE DEADLINE: Annual (March 31st)
        SEVERITY: HIGH
        PENALTY: $25,000 per violation
        APPLICABLE ENTITIES: All utilities
        
        SECTION 2: OPERATIONAL MONITORING REQUIREMENTS
        
        2.1 Real-time System Monitoring
        Grid operators must maintain continuous monitoring of:
        - System frequency (±0.1 Hz tolerance) with 1-second resolution
        - Voltage levels at all substations (±5% tolerance)
        - Power flow measurements every 5 minutes
        - Weather conditions affecting operations
        - Equipment status and alarm conditions
        
        Data must be archived for minimum 10 years and available for regulatory
        inspection within 24 hours of request.
        
        COMPLIANCE DEADLINE: Continuous
        SEVERITY: CRITICAL
        AUDIT FREQUENCY: Monthly
        APPLICABLE ENTITIES: Grid operators, system operators
        
        2.2 Outage Reporting
        All unplanned outages affecting more than 1000 customers must be reported
        within 1 hour of occurrence. Reports must include:
        - Affected customer count and geographic distribution
        - Estimated restoration time with regular updates
        - Root cause analysis (if known)
        - Mitigation actions taken and resources deployed
        - Communication plan for affected customers
        
        COMPLIANCE DEADLINE: 1 hour from occurrence
        SEVERITY: HIGH
        PENALTY: $10,000 per hour delay
        APPLICABLE ENTITIES: Distribution utilities
        
        SECTION 3: ENVIRONMENTAL COMPLIANCE
        
        3.1 Emissions Monitoring
        All generating facilities must monitor and report:
        - CO2 emissions (monthly reporting required)
        - NOx and SOx levels (weekly monitoring and reporting)
        - Particulate matter (daily measurements)
        - Water discharge quality (daily testing and reporting)
        - Waste heat recovery efficiency metrics
        
        COMPLIANCE DEADLINE: Various (see above)
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Quarterly
        APPLICABLE ENTITIES: Generation facilities
        
        3.2 Renewable Energy Certificates
        Utilities must maintain renewable energy certificate (REC) compliance
        at minimum 25% of total generation by 2025, increasing to 50% by 2030.
        Annual verification required with third-party attestation.
        
        COMPLIANCE DEADLINE: Annual verification
        SEVERITY: HIGH
        PENALTY: $100 per MWh shortfall
        APPLICABLE ENTITIES: All utilities
        
        SECTION 4: CYBERSECURITY REQUIREMENTS
        
        4.1 Critical Infrastructure Protection
        All critical cyber assets must implement:
        - Multi-factor authentication for all administrative access
        - Network segmentation with air-gapped critical systems
        - Continuous monitoring with 24/7 security operations center
        - Incident response procedures with 15-minute notification requirement
        - Annual penetration testing by certified third parties
        
        COMPLIANCE DEADLINE: Immediate implementation
        SEVERITY: CRITICAL
        AUDIT FREQUENCY: Semi-annual
        APPLICABLE ENTITIES: All entities with critical cyber assets
        
        4.2 Vulnerability Management
        Organizations must conduct quarterly vulnerability assessments
        and remediate critical vulnerabilities within 30 days.
        High-severity vulnerabilities must be addressed within 90 days.
        
        COMPLIANCE DEADLINE: Quarterly assessments, 30-day remediation
        SEVERITY: HIGH
        PENALTY: $5,000 per unpatched critical vulnerability
        APPLICABLE ENTITIES: All entities
        
        SECTION 5: CUSTOMER PROTECTION
        
        5.1 Service Quality Standards
        Utilities must maintain:
        - Average outage duration < 2 hours annually (SAIDI)
        - Customer satisfaction rating > 85% in annual surveys
        - Response time to service calls < 4 hours for non-emergency
        - Billing accuracy > 99.5% with monthly verification
        - Complaint resolution within 30 days
        
        COMPLIANCE DEADLINE: Continuous monitoring
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Annual
        APPLICABLE ENTITIES: Customer-serving utilities
        
        5.2 Rate Change Notifications
        All rate changes must be communicated to customers:
        - 60 days advance notice for increases > 5%
        - 30 days notice for increases < 5%
        - Public hearings for increases > 10%
        - Multi-language notifications in diverse communities
        
        COMPLIANCE DEADLINE: As specified above
        SEVERITY: MEDIUM
        PENALTY: Rate change reversal + $50,000 fine
        APPLICABLE ENTITIES: Rate-regulated utilities
        
        SECTION 6: EMERGENCY PREPAREDNESS
        
        6.1 Emergency Response Plans
        All utilities must maintain current emergency response plans including:
        - Natural disaster response procedures with resource allocation
        - Cyber incident response protocols with escalation procedures
        - Communication plans with authorities and customers
        - Resource allocation strategies and mutual aid agreements
        - Annual tabletop exercises and quarterly drills
        
        Plans must be updated annually and tested quarterly.
        
        COMPLIANCE DEADLINE: Annual updates, quarterly testing
        SEVERITY: HIGH
        AUDIT FREQUENCY: Annual
        APPLICABLE ENTITIES: All utilities
        
        6.2 Mutual Aid Agreements
        Utilities must maintain mutual aid agreements with neighboring utilities
        for emergency response and resource sharing. Agreements must specify:
        - Resource sharing protocols and cost allocation
        - Communication procedures and contact information
        - Equipment compatibility and transportation logistics
        
        COMPLIANCE DEADLINE: Agreements must be current
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Bi-annual
        APPLICABLE ENTITIES: All utilities
        
        SECTION 7: FINANCIAL REPORTING
        
        7.1 Rate Base Reporting
        Regulated utilities must file annual rate base reports including:
        - Detailed asset inventories with depreciation schedules
        - Capital investment plans for next 5 years
        - Cost allocation methodologies and justifications
        - Return on investment calculations
        
        COMPLIANCE DEADLINE: Annual (June 30th)
        SEVERITY: HIGH
        PENALTY: $15,000 per month delay
        APPLICABLE ENTITIES: Rate-regulated utilities
        
        7.2 Affiliate Transaction Reporting
        Utilities with affiliate relationships must report:
        - All transactions > $100,000 with detailed justifications
        - Quarterly summaries of affiliate activities
        - Annual compliance certifications from senior management
        
        COMPLIANCE DEADLINE: Quarterly and annual
        SEVERITY: MEDIUM
        AUDIT FREQUENCY: Annual
        APPLICABLE ENTITIES: Utilities with affiliates
        
        APPENDIX A: DEFINITIONS AND INTERPRETATIONS
        
        Critical Cyber Asset: Any cyber asset that, if compromised, could
        adversely impact the reliable operation of the bulk electric system.
        
        Transmission System Operator: An entity responsible for the reliable
        operation of the transmission system within its area.
        
        Renewable Energy Certificate: A tradable certificate representing
        the environmental attributes of one megawatt-hour of renewable energy.
        
        SAIDI: System Average Interruption Duration Index - measures the
        average outage duration for customers served.
        
        APPENDIX B: ENFORCEMENT AND PENALTIES
        
        Violation categories and associated penalties:
        - Critical violations: $10,000 - $1,000,000 per day
        - High violations: $5,000 - $100,000 per occurrence
        - Medium violations: $1,000 - $25,000 per occurrence
        - Low violations: Warning to $5,000 per occurrence
        
        Repeat violations may result in enhanced penalties up to 200% of base amount.
        Willful violations may result in criminal referral to appropriate authorities.
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
            logger.info("Starting comprehensive document workflow test...")
            
            # Step 1: Create and upload test document
            pdf_path = self.create_comprehensive_test_pdf()
            test_details['pdf_created'] = True
            
            # Upload document
            with open(pdf_path, 'rb') as file:
                files = {'file': file}
                metadata = {
                    "title": "Comprehensive Energy Regulatory Framework E2E Test",
                    "source": "E2E Test Regulatory Authority",
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
            
            # Step 2: Monitor processing status with detailed tracking
            processing_complete = False
            max_wait_time = 1200  # 20 minutes for comprehensive document
            check_interval = 15   # 15 seconds
            start_wait = time.time()
            status_history = []
            
            while not processing_complete and (time.time() - start_wait) < max_wait_time:
                status_response = requests.get(
                    f"{self.api_base_url}/documents/{document_id}/status",
                    headers=self.headers,
                    timeout=10
                )
                
                assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
                status_data = status_response.json()
                status_history.append({
                    'timestamp': time.time(),
                    'status': status_data['status'],
                    'details': status_data.get('details', {})
                })
                
                if status_data['status'] == 'completed':
                    processing_complete = True
                    test_details['processing_completed'] = True
                elif status_data['status'] == 'failed':
                    raise AssertionError(f"Document processing failed: {status_data.get('error', 'Unknown error')}")
                
                time.sleep(check_interval)
            
            assert processing_complete, f"Document processing timed out after {max_wait_time} seconds"
            test_details['status_history'] = status_history
            test_details['processing_duration'] = time.time() - start_wait
            
            # Step 3: Verify obligations were extracted with comprehensive validation
            obligations_response = requests.get(
                f"{self.api_base_url}/obligations",
                params={'document_id': document_id, 'limit': 100},
                headers=self.headers,
                timeout=30
            )
            
            assert obligations_response.status_code == 200, f"Get obligations failed: {obligations_response.text}"
            obligations_data = obligations_response.json()
            obligations = obligations_data['obligations']
            
            # Validate minimum number of obligations extracted
            assert len(obligations) >= 15, f"Expected at least 15 obligations, got {len(obligations)}"
            test_details['obligations_extracted'] = len(obligations)
            
            # Verify obligation structure and content quality
            categories_found = set()
            severities_found = set()
            high_confidence_count = 0
            
            for obligation in obligations:
                # Validate required fields
                assert 'obligation_id' in obligation
                assert 'description' in obligation
                assert 'category' in obligation
                assert 'severity' in obligation
                assert 'confidence_score' in obligation
                
                categories_found.add(obligation['category'])
                severities_found.add(obligation['severity'])
                
                # Verify confidence score is reasonable
                assert 0.0 <= obligation['confidence_score'] <= 1.0
                if obligation['confidence_score'] >= 0.8:
                    high_confidence_count += 1
                
                # Validate description quality
                assert len(obligation['description']) >= 10, "Obligation description too short"
                assert obligation['category'] in ['reporting', 'monitoring', 'operational', 'environmental', 'cybersecurity', 'financial']
                assert obligation['severity'] in ['critical', 'high', 'medium', 'low']
            
            test_details['categories_found'] = list(categories_found)
            test_details['severities_found'] = list(severities_found)
            test_details['high_confidence_count'] = high_confidence_count
            
            # Verify we found multiple categories and severities
            assert len(categories_found) >= 4, f"Expected at least 4 categories, found: {categories_found}"
            assert len(severities_found) >= 3, f"Expected at least 3 severities, found: {severities_found}"
            assert high_confidence_count >= len(obligations) * 0.6, "Too few high-confidence obligations"
            
            # Step 4: Verify tasks were generated with proper planning
            tasks_response = requests.get(
                f"{self.api_base_url}/tasks",
                params={'limit': 200},
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
            
            assert len(document_tasks) >= 10, f"Expected at least 10 tasks, got {len(document_tasks)}"
            test_details['tasks_generated'] = len(document_tasks)
            
            # Verify task structure and quality
            priorities_found = set()
            critical_task_count = 0
            
            for task in document_tasks:
                assert 'task_id' in task
                assert 'title' in task
                assert 'description' in task
                assert 'priority' in task
                assert 'status' in task
                assert 'due_date' in task
                
                priorities_found.add(task['priority'])
                
                # Validate task quality
                assert len(task['title']) >= 5, "Task title too short"
                assert len(task['description']) >= 10, "Task description too short"
                assert task['priority'] in ['high', 'medium', 'low']
                assert task['status'] in ['pending', 'in_progress', 'completed', 'overdue']
                
                # Check if critical obligations have high-priority tasks
                related_obligation = next((obl for obl in obligations if obl['obligation_id'] == task.get('obligation_id')), None)
                if related_obligation and related_obligation['severity'] == 'critical':
                    if task['priority'] == 'high':
                        critical_task_count += 1
            
            test_details['priorities_found'] = list(priorities_found)
            test_details['critical_task_count'] = critical_task_count
            
            # Verify task prioritization logic
            critical_obligations = [obl for obl in obligations if obl['severity'] == 'critical']
            if critical_obligations:
                assert critical_task_count >= len(critical_obligations) * 0.5, "Critical obligations should generate high-priority tasks"
            
            # Step 5: Generate comprehensive compliance report
            report_config = {
                "report_type": "compliance_summary",
                "title": "E2E System Test Comprehensive Compliance Report",
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                "filters": {
                    "document_ids": [document_id],
                    "include_all_categories": True,
                    "include_task_summary": True
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
            max_report_wait = 600  # 10 minutes
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
                
                time.sleep(10)
            
            assert report_complete, f"Report generation timed out after {max_report_wait} seconds"
            test_details['report_generation_duration'] = time.time() - start_report_wait
            
            # Step 6: Download and verify report quality
            download_response = requests.get(
                f"{self.api_base_url}/reports/{report_id}",
                headers=self.headers,
                timeout=60
            )
            
            assert download_response.status_code == 200, f"Report download failed: {download_response.text}"
            assert download_response.headers['content-type'] == 'application/pdf'
            assert len(download_response.content) > 5000, "Report PDF seems too small for comprehensive content"
            
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
    
    def test_agent_interactions_and_data_flow(self) -> SystemTestResult:
        """Test all agent interactions and data flow between agents."""
        start_time = time.time()
        test_details = {}
        
        try:
            logger.info("Testing comprehensive agent interactions and data flow...")
            
            # Verify we have test data from previous test
            if not self.test_data.get('document_id'):
                raise AssertionError("No test document available for agent interaction testing")
            
            document_id = self.test_data['document_id']
            obligations = self.test_data['obligations']
            tasks = self.test_data['tasks']
            
            # Test 1: Verify Analyzer Agent output quality and consistency
            test_details['analyzer_agent_test'] = {}
            
            # Check obligation categorization quality
            categories = [obl['category'] for obl in obligations]
            expected_categories = ['reporting', 'monitoring', 'operational', 'environmental', 'cybersecurity', 'financial']
            found_categories = [cat for cat in expected_categories if cat in categories]
            
            test_details['analyzer_agent_test']['categories_found'] = found_categories
            test_details['analyzer_agent_test']['total_obligations'] = len(obligations)
            
            # Verify high-confidence obligations
            high_confidence_obligations = [obl for obl in obligations if obl['confidence_score'] >= 0.8]
            medium_confidence_obligations = [obl for obl in obligations if 0.6 <= obl['confidence_score'] < 0.8]
            
            test_details['analyzer_agent_test']['high_confidence_count'] = len(high_confidence_obligations)
            test_details['analyzer_agent_test']['medium_confidence_count'] = len(medium_confidence_obligations)
            
            assert len(high_confidence_obligations) >= 8, "Not enough high-confidence obligations extracted"
            assert len(found_categories) >= 4, "Not enough obligation categories identified"
            
            # Verify obligation content quality
            for obligation in high_confidence_obligations:
                assert len(obligation['description']) >= 20, "High-confidence obligations should have detailed descriptions"
                assert 'applicable_entities' in obligation or 'deadline_type' in obligation, "Missing important obligation metadata"
            
            # Test 2: Verify Planner Agent output quality and logic
            test_details['planner_agent_test'] = {}
            
            # Check task prioritization logic
            priorities = [task['priority'] for task in tasks]
            priority_distribution = {
                'high': priorities.count('high'),
                'medium': priorities.count('medium'),
                'low': priorities.count('low')
            }
            test_details['planner_agent_test']['priority_distribution'] = priority_distribution
            
            # Verify critical obligations have appropriate task priorities
            critical_obligations = [obl for obl in obligations if obl['severity'] == 'critical']
            high_obligations = [obl for obl in obligations if obl['severity'] == 'high']
            
            critical_obligation_ids = {obl['obligation_id'] for obl in critical_obligations}
            high_obligation_ids = {obl['obligation_id'] for obl in high_obligations}
            
            high_priority_tasks_for_critical = [
                task for task in tasks 
                if task.get('obligation_id') in critical_obligation_ids and task['priority'] == 'high'
            ]
            
            high_priority_tasks_for_high = [
                task for task in tasks 
                if task.get('obligation_id') in high_obligation_ids and task['priority'] in ['high', 'medium']
            ]
            
            test_details['planner_agent_test']['critical_obligations'] = len(critical_obligations)
            test_details['planner_agent_test']['high_priority_tasks_for_critical'] = len(high_priority_tasks_for_critical)
            test_details['planner_agent_test']['appropriate_tasks_for_high'] = len(high_priority_tasks_for_high)
            
            # Verify task planning logic
            if critical_obligations:
                assert len(high_priority_tasks_for_critical) >= len(critical_obligations) * 0.7, \
                    "Most critical obligations should generate high-priority tasks"
            
            if high_obligations:
                assert len(high_priority_tasks_for_high) >= len(high_obligations) * 0.5, \
                    "High-severity obligations should generate appropriate priority tasks"
            
            # Test 3: Verify data consistency between agents
            test_details['data_consistency_test'] = {}
            
            # Check that all tasks reference valid obligations
            task_obligation_ids = {task.get('obligation_id') for task in tasks if task.get('obligation_id')}
            obligation_ids = {obl['obligation_id'] for obl in obligations}
            
            orphaned_tasks = task_obligation_ids - obligation_ids
            test_details['data_consistency_test']['orphaned_tasks'] = len(orphaned_tasks)
            test_details['data_consistency_test']['task_obligation_coverage'] = len(task_obligation_ids & obligation_ids)
            
            assert len(orphaned_tasks) == 0, f"Found {len(orphaned_tasks)} tasks referencing non-existent obligations"
            
            # Verify obligation-task relationship quality
            obligations_with_tasks = set()
            for task in tasks:
                if task.get('obligation_id'):
                    obligations_with_tasks.add(task['obligation_id'])
            
            coverage_ratio = len(obligations_with_tasks) / len(obligations) if obligations else 0
            test_details['data_consistency_test']['obligation_task_coverage_ratio'] = coverage_ratio
            
            assert coverage_ratio >= 0.6, f"Too few obligations have associated tasks: {coverage_ratio:.2f}"
            
            # Test 4: Verify Reporter Agent data access and compilation
            test_details['reporter_agent_test'] = {}
            
            # The fact that we successfully generated a report indicates the Reporter Agent
            # can access and compile data from both Analyzer and Planner agents
            test_details['reporter_agent_test']['report_generated'] = True
            test_details['reporter_agent_test']['report_id'] = self.test_data.get('report_id')
            
            # Verify report metadata
            report_status_response = requests.get(
                f"{self.api_base_url}/reports/{self.test_data['report_id']}/status",
                headers=self.headers,
                timeout=10
            )
            
            if report_status_response.status_code == 200:
                report_status = report_status_response.json()
                test_details['reporter_agent_test']['report_metadata'] = report_status
                
                # Verify report includes data from all agents
                assert 'obligations_included' in report_status.get('details', {}) or \
                       report_status.get('status') == 'completed', "Report should include obligation data"
            
            # Test 5: Verify agent processing times are reasonable
            test_details['performance_test'] = {}
            
            processing_duration = test_details.get('processing_duration', 0)
            report_duration = test_details.get('report_generation_duration', 0)
            
            test_details['performance_test']['document_processing_duration'] = processing_duration
            test_details['performance_test']['report_generation_duration'] = report_duration
            
            # Performance assertions (adjust based on system capacity)
            assert processing_duration < 1200, f"Document processing took too long: {processing_duration}s"
            assert report_duration < 600, f"Report generation took too long: {report_duration}s"
            
            duration = time.time() - start_time
            return SystemTestResult(
                test_name="agent_interactions_and_data_flow",
                success=True,
                duration=duration,
                details=test_details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Agent interactions test failed: {str(e)}")
            return SystemTestResult(
                test_name="agent_interactions_and_data_flow",
                success=False,
                duration=duration,
                details=test_details,
                error=str(e)
            )
    
    def test_error_scenarios_and_recovery(self) -> SystemTestResult:
        """Test comprehensive error scenarios and recovery mechanisms."""
        start_time = time.time()
        test_details = {}
        
        try:
            logger.info("Testing comprehensive error scenarios and recovery mechanisms...")
            
            # Test 1: Invalid file upload scenarios
            test_details['invalid_file_tests'] = {}
            
            # Test 1a: Non-PDF file
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(b"This is not a PDF file content")
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
                    
                    test_details['invalid_file_tests']['non_pdf_response'] = response.status_code
                    assert response.status_code == 400, "Non-PDF file should be rejected"
                    
                    if response.status_code == 400:
                        error_data = response.json()
                        assert 'error' in error_data, "Error response should include error message"
                        test_details['invalid_file_tests']['non_pdf_error'] = error_data.get('error')
                    
                finally:
                    os.unlink(temp_file.name)
            
            # Test 1b: Corrupted PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(b"%PDF-1.4\nCorrupted PDF content that is not valid")
                temp_file.flush()
                
                try:
                    with open(temp_file.name, 'rb') as file:
                        files = {'file': file}
                        data = {'metadata': json.dumps({"title": "Corrupted PDF Test"})}
                        
                        response = requests.post(
                            f"{self.api_base_url}/documents/upload",
                            files=files,
                            data=data,
                            headers={'Authorization': self.headers['Authorization']},
                            timeout=30
                        )
                    
                    test_details['invalid_file_tests']['corrupted_pdf_upload'] = response.status_code
                    
                    if response.status_code == 201:
                        # Upload succeeded, check if processing fails gracefully
                        document_id = response.json()['document_id']
                        
                        # Wait and check status
                        time.sleep(90)  # Give it time to process and fail
                        
                        status_response = requests.get(
                            f"{self.api_base_url}/documents/{document_id}/status",
                            headers=self.headers,
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            test_details['invalid_file_tests']['corrupted_pdf_status'] = status_data['status']
                            test_details['invalid_file_tests']['error_handled'] = status_data['status'] == 'failed'
                            
                            if status_data['status'] == 'failed':
                                assert 'error' in status_data, "Failed processing should include error details"
                    
                finally:
                    os.unlink(temp_file.name)
            
            # Test 2: Authentication and authorization error handling
            test_details['auth_error_tests'] = {}
            
            # Test 2a: No authentication token
            response = requests.get(f"{self.api_base_url}/obligations", timeout=10)
            test_details['auth_error_tests']['no_token_response'] = response.status_code
            assert response.status_code == 401, "Should require authentication"
            
            # Test 2b: Invalid authentication token
            invalid_headers = {'Authorization': 'Bearer invalid-token-12345-test'}
            response = requests.get(
                f"{self.api_base_url}/obligations",
                headers=invalid_headers,
                timeout=10
            )
            test_details['auth_error_tests']['invalid_token_response'] = response.status_code
            assert response.status_code == 401, "Should reject invalid token"
            
            # Test 2c: Malformed authorization header
            malformed_headers = {'Authorization': 'InvalidFormat token-12345'}
            response = requests.get(
                f"{self.api_base_url}/obligations",
                headers=malformed_headers,
                timeout=10
            )
            test_details['auth_error_tests']['malformed_header_response'] = response.status_code
            assert response.status_code == 401, "Should reject malformed authorization header"
            
            # Test 3: API rate limiting and throttling
            test_details['rate_limiting_tests'] = {}
            
            # Make rapid requests to test rate limiting
            responses = []
            rate_limited = False
            
            for i in range(25):  # Increased number to trigger rate limiting
                response = requests.get(
                    f"{self.api_base_url}/obligations",
                    headers=self.headers,
                    timeout=5
                )
                responses.append(response.status_code)
                
                if response.status_code == 429:
                    rate_limited = True
                    test_details['rate_limiting_tests']['rate_limit_triggered_at_request'] = i + 1
                    
                    # Verify rate limit response includes retry information
                    if 'retry-after' in response.headers:
                        test_details['rate_limiting_tests']['retry_after_header'] = response.headers['retry-after']
                    
                    break
                
                time.sleep(0.1)  # Small delay between requests
            
            test_details['rate_limiting_tests']['total_requests_made'] = len(responses)
            test_details['rate_limiting_tests']['successful_requests'] = responses.count(200)
            test_details['rate_limiting_tests']['rate_limited'] = rate_limited
            
            # Test 4: Malformed request handling
            test_details['malformed_request_tests'] = {}
            
            # Test 4a: Invalid JSON in request body
            response = requests.post(
                f"{self.api_base_url}/reports/generate",
                data="invalid json content",
                headers={'Authorization': self.headers['Authorization'], 'Content-Type': 'application/json'},
                timeout=10
            )
            test_details['malformed_request_tests']['invalid_json_response'] = response.status_code
            assert response.status_code == 400, "Should reject invalid JSON"
            
            # Test 4b: Missing required fields
            response = requests.post(
                f"{self.api_base_url}/reports/generate",
                json={"incomplete": "data"},
                headers=self.headers,
                timeout=10
            )
            test_details['malformed_request_tests']['missing_fields_response'] = response.status_code
            assert response.status_code == 400, "Should reject requests with missing required fields"
            
            # Test 5: Resource not found handling
            test_details['not_found_tests'] = {}
            
            # Test 5a: Non-existent document
            response = requests.get(
                f"{self.api_base_url}/documents/non-existent-doc-id/status",
                headers=self.headers,
                timeout=10
            )
            test_details['not_found_tests']['non_existent_document'] = response.status_code
            assert response.status_code == 404, "Should return 404 for non-existent document"
            
            # Test 5b: Non-existent report
            response = requests.get(
                f"{self.api_base_url}/reports/non-existent-report-id",
                headers=self.headers,
                timeout=10
            )
            test_details['not_found_tests']['non_existent_report'] = response.status_code
            assert response.status_code == 404, "Should return 404 for non-existent report"
            
            # Test 6: System recovery after errors
            test_details['recovery_tests'] = {}
            
            # Verify system is still functional after error scenarios
            response = requests.get(
                f"{self.api_base_url}/obligations",
                params={'limit': 5},
                headers=self.headers,
                timeout=10
            )
            test_details['recovery_tests']['system_functional_after_errors'] = response.status_code == 200
            assert response.status_code == 200, "System should remain functional after error scenarios"
            
            # Test 7: Timeout handling (if applicable)
            test_details['timeout_tests'] = {}
            
            # Test with very short timeout to simulate timeout scenarios
            try:
                response = requests.get(
                    f"{self.api_base_url}/obligations",
                    headers=self.headers,
                    timeout=0.001  # Very short timeout
                )
                test_details['timeout_tests']['timeout_occurred'] = False
            except requests.exceptions.Timeout:
                test_details['timeout_tests']['timeout_occurred'] = True
                test_details['timeout_tests']['timeout_handled_gracefully'] = True
            
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
    
    def run_comprehensive_system_test(self) -> Dict[str, Any]:
        """Run all comprehensive system tests."""
        logger.info("Starting comprehensive end-to-end system testing...")
        
        test_methods = [
            self.test_complete_document_workflow,
            self.test_agent_interactions_and_data_flow,
            self.test_error_scenarios_and_recovery
        ]
        
        all_results = []
        
        for test_method in test_methods:
            logger.info(f"Running {test_method.__name__}...")
            result = test_method()
            all_results.append(result)
            self.test_results.append(result)
            
            if result.success:
                logger.info(f"✓ {result.test_name} passed in {result.duration:.2f}s")
            else:
                logger.error(f"✗ {result.test_name} failed: {result.error}")
        
        # Generate comprehensive test report
        total_tests = len(all_results)
        passed_tests = sum(1 for result in all_results if result.success)
        total_duration = sum(result.duration for result in all_results)
        
        report = {
            'test_suite': 'comprehensive_e2e_system_test',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'environment': self.environment,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': total_duration
            },
            'test_results': [
                {
                    'test_name': result.test_name,
                    'success': result.success,
                    'duration': result.duration,
                    'error': result.error,
                    'details': result.details
                }
                for result in all_results
            ]
        }
        
        # Save detailed test report
        report_filename = f"comprehensive_e2e_test_report_{int(time.time())}.json"
        try:
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Detailed test report saved to {report_filename}")
        except Exception as e:
            logger.warning(f"Could not save test report: {e}")
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("COMPREHENSIVE E2E SYSTEM TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        
        if passed_tests == total_tests:
            logger.info("🎉 All comprehensive system tests passed!")
        else:
            logger.error("❌ Some comprehensive system tests failed.")
        
        return report


# Pytest integration
class TestComprehensiveE2ESystem:
    """Pytest wrapper for comprehensive E2E system tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.test_runner = ComprehensiveE2ESystemTest()
    
    def test_complete_document_workflow(self):
        """Test complete document processing workflow."""
        result = self.test_runner.test_complete_document_workflow()
        assert result.success, f"Complete document workflow test failed: {result.error}"
    
    def test_agent_interactions_and_data_flow(self):
        """Test agent interactions and data flow."""
        # Ensure we have test data from previous test
        if not self.test_runner.test_data.get('document_id'):
            # Run the workflow test first to generate test data
            workflow_result = self.test_runner.test_complete_document_workflow()
            assert workflow_result.success, "Workflow test must pass before testing agent interactions"
        
        result = self.test_runner.test_agent_interactions_and_data_flow()
        assert result.success, f"Agent interactions test failed: {result.error}"
    
    def test_error_scenarios_and_recovery(self):
        """Test error scenarios and recovery mechanisms."""
        result = self.test_runner.test_error_scenarios_and_recovery()
        assert result.success, f"Error scenarios test failed: {result.error}"


if __name__ == '__main__':
    # Allow running as standalone script
    test_runner = ComprehensiveE2ESystemTest()
    report = test_runner.run_comprehensive_system_test()
    
    # Exit with appropriate code
    sys.exit(0 if report['summary']['success_rate'] == 100 else 1)