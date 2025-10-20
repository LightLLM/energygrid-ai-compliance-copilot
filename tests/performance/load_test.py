"""
Load testing for EnergyGrid.AI Compliance Copilot.
This module provides load testing capabilities using locust.
"""

import os
import json
import time
import random
import tempfile
from typing import Dict, Any
from locust import HttpUser, task, between
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class ComplianceAPIUser(HttpUser):
    """Simulated user for load testing the Compliance API."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Setup user session."""
        self.jwt_token = os.getenv('JWT_TOKEN', '')
        if not self.jwt_token:
            raise ValueError("JWT_TOKEN environment variable must be set")
        
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}'
        }
        
        # Store uploaded document IDs for later use
        self.document_ids = []
        self.obligation_ids = []
        self.task_ids = []
        self.report_ids = []
    
    def create_test_pdf(self, content_type: str = "basic") -> str:
        """Create a test PDF with different content types."""
        content_templates = {
            "basic": """
            BASIC REGULATORY DOCUMENT
            
            Section 1: Compliance Requirements
            All operators must comply with the following requirements:
            - Submit monthly reports by the 15th of each month
            - Maintain operational logs for 5 years
            - Conduct annual safety inspections
            """,
            "complex": """
            COMPREHENSIVE ENERGY REGULATION
            
            Section 1: Transmission Requirements
            1.1 All transmission operators must maintain system reliability
            1.2 Real-time monitoring is required for all critical equipment
            1.3 Backup systems must be tested quarterly
            
            Section 2: Reporting Obligations
            2.1 Monthly operational reports due by 15th of following month
            2.2 Annual compliance certification required
            2.3 Incident reports must be filed within 24 hours
            
            Section 3: Safety Standards
            3.1 Personnel must complete annual safety training
            3.2 Equipment inspections required every 6 months
            3.3 Emergency response procedures must be updated annually
            """,
            "minimal": """
            SIMPLE REGULATION
            
            Operators must submit annual reports.
            """
        }
        
        content = content_templates.get(content_type, content_templates["basic"])
        
        # Create temporary PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        width, height = letter
        
        lines = content.strip().split('\n')
        y_position = height - 50
        
        for line in lines:
            if y_position < 50:
                c.showPage()
                y_position = height - 50
            
            c.drawString(50, y_position, line.strip())
            y_position -= 20
        
        c.save()
        return temp_file.name
    
    @task(1)
    def upload_document(self):
        """Upload a document (low frequency task)."""
        content_type = random.choice(["basic", "complex", "minimal"])
        pdf_path = self.create_test_pdf(content_type)
        
        try:
            metadata = {
                "title": f"Load Test Document {random.randint(1000, 9999)}",
                "source": "Load Test Authority",
                "effective_date": "2024-01-01",
                "document_type": "regulation"
            }
            
            with open(pdf_path, 'rb') as file:
                files = {'file': file}
                data = {'metadata': json.dumps(metadata)}
                
                with self.client.post(
                    "/documents/upload",
                    files=files,
                    data=data,
                    headers={'Authorization': self.headers['Authorization']},
                    catch_response=True
                ) as response:
                    if response.status_code == 201:
                        result = response.json()
                        self.document_ids.append(result['document_id'])
                        response.success()
                    else:
                        response.failure(f"Upload failed: {response.status_code}")
        
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    @task(5)
    def get_obligations(self):
        """Get obligations list (high frequency task)."""
        params = {
            'limit': random.randint(10, 50),
            'offset': random.randint(0, 100)
        }
        
        # Randomly add filters
        if random.random() < 0.3:
            params['category'] = random.choice(['reporting', 'monitoring', 'operational', 'financial'])
        
        if random.random() < 0.3:
            params['severity'] = random.choice(['critical', 'high', 'medium', 'low'])
        
        with self.client.get(
            "/obligations",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                # Store some obligation IDs for later use
                if result['obligations']:
                    self.obligation_ids.extend([
                        obl['obligation_id'] for obl in result['obligations'][:5]
                    ])
                response.success()
            else:
                response.failure(f"Get obligations failed: {response.status_code}")
    
    @task(4)
    def get_tasks(self):
        """Get tasks list (high frequency task)."""
        params = {
            'limit': random.randint(10, 30),
            'offset': random.randint(0, 50)
        }
        
        # Randomly add filters
        if random.random() < 0.3:
            params['status'] = random.choice(['pending', 'in_progress', 'completed'])
        
        if random.random() < 0.3:
            params['priority'] = random.choice(['high', 'medium', 'low'])
        
        with self.client.get(
            "/tasks",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                # Store some task IDs for later use
                if result['tasks']:
                    self.task_ids.extend([
                        task['task_id'] for task in result['tasks'][:3]
                    ])
                response.success()
            else:
                response.failure(f"Get tasks failed: {response.status_code}")
    
    @task(3)
    def get_document_status(self):
        """Check document processing status (medium frequency task)."""
        if not self.document_ids:
            return
        
        document_id = random.choice(self.document_ids)
        
        with self.client.get(
            f"/documents/{document_id}/status",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Document might have been cleaned up
                if document_id in self.document_ids:
                    self.document_ids.remove(document_id)
                response.success()
            else:
                response.failure(f"Get status failed: {response.status_code}")
    
    @task(2)
    def get_reports(self):
        """Get reports list (medium frequency task)."""
        params = {
            'limit': random.randint(5, 20),
            'offset': random.randint(0, 20)
        }
        
        with self.client.get(
            "/reports",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                # Store some report IDs for later use
                if result['reports']:
                    self.report_ids.extend([
                        report['report_id'] for report in result['reports'][:2]
                    ])
                response.success()
            else:
                response.failure(f"Get reports failed: {response.status_code}")
    
    @task(1)
    def generate_report(self):
        """Generate a report (low frequency task)."""
        report_config = {
            "report_type": random.choice([
                "compliance_summary",
                "audit_readiness", 
                "obligation_status",
                "task_progress"
            ]),
            "title": f"Load Test Report {random.randint(1000, 9999)}",
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }
        
        # Randomly add filters
        if random.random() < 0.5:
            report_config["filters"] = {
                "categories": random.sample(
                    ["reporting", "monitoring", "operational", "financial"],
                    random.randint(1, 2)
                )
            }
        
        with self.client.post(
            "/reports/generate",
            json=report_config,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 202:
                result = response.json()
                self.report_ids.append(result['report_id'])
                response.success()
            else:
                response.failure(f"Generate report failed: {response.status_code}")
    
    @task(2)
    def get_obligation_details(self):
        """Get specific obligation details (medium frequency task)."""
        if not self.obligation_ids:
            return
        
        obligation_id = random.choice(self.obligation_ids)
        
        with self.client.get(
            f"/obligations/{obligation_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Obligation might have been cleaned up
                if obligation_id in self.obligation_ids:
                    self.obligation_ids.remove(obligation_id)
                response.success()
            else:
                response.failure(f"Get obligation details failed: {response.status_code}")
    
    @task(1)
    def update_task(self):
        """Update a task (low frequency task)."""
        if not self.task_ids:
            return
        
        task_id = random.choice(self.task_ids)
        
        update_data = {
            "status": random.choice(["pending", "in_progress", "completed"]),
            "notes": f"Updated by load test at {time.time()}"
        }
        
        with self.client.put(
            f"/tasks/{task_id}",
            json=update_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Task might have been cleaned up
                if task_id in self.task_ids:
                    self.task_ids.remove(task_id)
                response.success()
            else:
                response.failure(f"Update task failed: {response.status_code}")


class HeavyUser(HttpUser):
    """Heavy user that performs more intensive operations."""
    
    wait_time = between(2, 8)
    weight = 1  # Lower weight means fewer of these users
    
    def on_start(self):
        """Setup heavy user session."""
        self.jwt_token = os.getenv('JWT_TOKEN', '')
        if not self.jwt_token:
            raise ValueError("JWT_TOKEN environment variable must be set")
        
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}'
        }
    
    @task(1)
    def upload_large_document(self):
        """Upload a larger, more complex document."""
        # Create a more complex PDF with multiple pages
        content = """
        COMPREHENSIVE ENERGY SECTOR REGULATION
        
        CHAPTER 1: GENERAL PROVISIONS
        
        Section 1.1: Purpose and Scope
        This regulation establishes comprehensive requirements for energy sector
        compliance, including transmission, distribution, and generation operations.
        
        Section 1.2: Definitions
        For the purposes of this regulation:
        - "Operator" means any entity engaged in energy operations
        - "Authority" means the regulatory authority
        - "Compliance" means adherence to all applicable requirements
        
        CHAPTER 2: OPERATIONAL REQUIREMENTS
        
        Section 2.1: System Reliability
        All operators must maintain system reliability through:
        - Continuous monitoring of critical parameters
        - Implementation of redundant systems
        - Regular testing of backup equipment
        - Maintenance of emergency response capabilities
        
        Section 2.2: Performance Standards
        Operators must meet the following performance standards:
        - System availability: 99.9% minimum
        - Response time to emergencies: 15 minutes maximum
        - Equipment maintenance: As per manufacturer specifications
        
        CHAPTER 3: REPORTING REQUIREMENTS
        
        Section 3.1: Regular Reports
        Operators must submit the following reports:
        - Daily operational summaries
        - Weekly performance metrics
        - Monthly compliance certifications
        - Quarterly financial reports
        - Annual comprehensive assessments
        
        Section 3.2: Incident Reporting
        All incidents must be reported within specified timeframes:
        - Critical incidents: Immediate notification
        - Major incidents: Within 2 hours
        - Minor incidents: Within 24 hours
        
        CHAPTER 4: SAFETY REQUIREMENTS
        
        Section 4.1: Personnel Safety
        All personnel must:
        - Complete initial safety training
        - Undergo annual recertification
        - Follow established safety procedures
        - Report safety concerns immediately
        
        Section 4.2: Equipment Safety
        All equipment must:
        - Meet applicable safety standards
        - Undergo regular safety inspections
        - Be maintained according to safety protocols
        - Include appropriate safety devices
        
        CHAPTER 5: ENVIRONMENTAL COMPLIANCE
        
        Section 5.1: Environmental Monitoring
        Operators must monitor environmental impacts including:
        - Air quality measurements
        - Water quality assessments
        - Noise level monitoring
        - Wildlife impact studies
        
        Section 5.2: Environmental Reporting
        Environmental reports must include:
        - Monitoring data and analysis
        - Compliance status assessments
        - Corrective action plans
        - Future impact projections
        
        CHAPTER 6: ENFORCEMENT
        
        Section 6.1: Inspections
        The Authority may conduct inspections:
        - With or without prior notice
        - At any reasonable time
        - Of any relevant facilities or records
        
        Section 6.2: Penalties
        Violations may result in:
        - Warning notices
        - Monetary penalties
        - Operational restrictions
        - License suspension or revocation
        """
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        width, height = letter
        
        lines = content.strip().split('\n')
        y_position = height - 50
        
        for line in lines:
            if y_position < 50:
                c.showPage()
                y_position = height - 50
            
            c.drawString(50, y_position, line.strip())
            y_position -= 15
        
        c.save()
        
        try:
            metadata = {
                "title": f"Complex Regulation {random.randint(10000, 99999)}",
                "source": "Heavy Load Test Authority",
                "effective_date": "2024-01-01",
                "document_type": "comprehensive_regulation"
            }
            
            with open(temp_file.name, 'rb') as file:
                files = {'file': file}
                data = {'metadata': json.dumps(metadata)}
                
                with self.client.post(
                    "/documents/upload",
                    files=files,
                    data=data,
                    headers={'Authorization': self.headers['Authorization']},
                    catch_response=True,
                    timeout=60  # Longer timeout for large uploads
                ) as response:
                    if response.status_code == 201:
                        response.success()
                    else:
                        response.failure(f"Large upload failed: {response.status_code}")
        
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    @task(1)
    def generate_comprehensive_report(self):
        """Generate a comprehensive report with all data."""
        report_config = {
            "report_type": "compliance_summary",
            "title": f"Comprehensive Load Test Report {random.randint(10000, 99999)}",
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            "filters": {
                "categories": ["reporting", "monitoring", "operational", "financial"],
                "severities": ["critical", "high", "medium", "low"]
            },
            "include_charts": True,
            "include_recommendations": True
        }
        
        with self.client.post(
            "/reports/generate",
            json=report_config,
            headers=self.headers,
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 202:
                response.success()
            else:
                response.failure(f"Comprehensive report failed: {response.status_code}")


class ReadOnlyUser(HttpUser):
    """Read-only user that only performs GET operations."""
    
    wait_time = between(0.5, 2)
    weight = 3  # Higher weight means more of these users
    
    def on_start(self):
        """Setup read-only user session."""
        self.jwt_token = os.getenv('JWT_TOKEN', '')
        if not self.jwt_token:
            raise ValueError("JWT_TOKEN environment variable must be set")
        
        self.headers = {
            'Authorization': f'Bearer {self.jwt_token}'
        }
    
    @task(10)
    def browse_obligations(self):
        """Browse obligations with various filters."""
        params = {
            'limit': random.randint(20, 100),
            'offset': random.randint(0, 200)
        }
        
        # Add random filters
        filters = {}
        if random.random() < 0.4:
            filters['category'] = random.choice(['reporting', 'monitoring', 'operational'])
        if random.random() < 0.4:
            filters['severity'] = random.choice(['critical', 'high', 'medium'])
        
        params.update(filters)
        
        with self.client.get(
            "/obligations",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Browse obligations failed: {response.status_code}")
    
    @task(8)
    def browse_tasks(self):
        """Browse tasks with various filters."""
        params = {
            'limit': random.randint(10, 50),
            'offset': random.randint(0, 100)
        }
        
        # Add random filters
        if random.random() < 0.3:
            params['status'] = random.choice(['pending', 'in_progress', 'completed'])
        if random.random() < 0.3:
            params['priority'] = random.choice(['high', 'medium', 'low'])
        
        with self.client.get(
            "/tasks",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Browse tasks failed: {response.status_code}")
    
    @task(5)
    def browse_reports(self):
        """Browse available reports."""
        params = {
            'limit': random.randint(5, 25),
            'offset': random.randint(0, 50)
        }
        
        with self.client.get(
            "/reports",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Browse reports failed: {response.status_code}")


if __name__ == "__main__":
    # Run load test with locust
    import subprocess
    import sys
    
    # Check if locust is installed
    try:
        import locust
    except ImportError:
        print("Installing locust...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "locust"])
    
    # Run basic load test
    api_url = os.getenv('API_BASE_URL', 'http://localhost:3000')
    
    print(f"Starting load test against: {api_url}")
    print("Make sure JWT_TOKEN environment variable is set")
    
    # Run locust programmatically for basic test
    from locust.env import Environment
    from locust.stats import stats_printer, stats_history
    from locust.log import setup_logging
    import gevent
    
    setup_logging("INFO", None)
    
    # Setup environment
    env = Environment(user_classes=[ComplianceAPIUser, ReadOnlyUser])
    env.create_local_runner()
    
    # Start statistics printer
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    
    # Start load test
    env.runner.start(10, spawn_rate=2)  # 10 users, spawn 2 per second
    
    # Run for 60 seconds
    gevent.spawn_later(60, lambda: env.runner.quit())
    
    # Wait for test to complete
    env.runner.greenlet.join()
    
    # Print final stats
    print("\nFinal Statistics:")
    print(f"Total requests: {env.stats.total.num_requests}")
    print(f"Failed requests: {env.stats.total.num_failures}")
    print(f"Average response time: {env.stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {env.stats.total.max_response_time:.2f}ms")