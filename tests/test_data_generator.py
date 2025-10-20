"""
Test data generator for EnergyGrid.AI Compliance Copilot tests.
"""

import os
import json
import tempfile
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pathlib import Path


class TestDataGenerator:
    """Generate test data for various test scenarios."""
    
    def __init__(self):
        self.test_data_dir = Path(__file__).parent / 'data'
        self.test_data_dir.mkdir(exist_ok=True)
    
    def generate_sample_pdf(self, content_type: str = 'basic', 
                          pages: int = 1) -> str:
        """Generate a sample PDF with regulatory content."""
        content_templates = {
            'basic': self._get_basic_regulation_content(),
            'complex': self._get_complex_regulation_content(),
            'minimal': self._get_minimal_regulation_content(),
            'large': self._get_large_regulation_content(),
            'multilingual': self._get_multilingual_regulation_content(),
            'technical': self._get_technical_regulation_content()
        }
        
        content = content_templates.get(content_type, content_templates['basic'])
        
        # Create temporary PDF file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        width, height = letter
        
        lines = content.strip().split('\n')
        y_position = height - 50
        page_count = 0
        
        for line in lines:
            if y_position < 50 or (pages > 1 and page_count < pages - 1 and random.random() < 0.1):
                c.showPage()
                y_position = height - 50
                page_count += 1
            
            c.drawString(50, y_position, line.strip()[:80])  # Limit line length
            y_position -= 15
        
        c.save()
        return temp_file.name
    
    def _get_basic_regulation_content(self) -> str:
        """Get basic regulation content."""
        return """
        ENERGY SECTOR COMPLIANCE REGULATION
        
        Section 1: Reporting Requirements
        
        1.1 Monthly Reports
        All transmission operators must submit monthly operational reports
        to the regulatory authority by the 15th of the following month.
        
        Reports must include:
        - System availability metrics
        - Incident summaries
        - Maintenance activities
        - Compliance status updates
        
        1.2 Annual Certification
        Each operator must obtain annual compliance certification
        from an approved third-party auditor.
        
        Section 2: Safety Standards
        
        2.1 Personnel Training
        All personnel working on electrical systems must complete
        annual safety training and maintain current certifications.
        
        2.2 Equipment Maintenance
        Critical equipment must be inspected quarterly and maintained
        according to manufacturer specifications.
        
        Section 3: Environmental Compliance
        
        3.1 Emissions Monitoring
        Operators must monitor and report emissions data monthly.
        
        3.2 Environmental Impact Assessments
        Annual environmental impact assessments are required
        for all major facilities.
        """
    
    def _get_complex_regulation_content(self) -> str:
        """Get complex regulation content with multiple obligations."""
        return """
        COMPREHENSIVE ENERGY REGULATORY FRAMEWORK
        
        CHAPTER 1: GENERAL PROVISIONS
        
        Article 1: Scope and Application
        This regulation applies to all energy sector participants including:
        - Transmission system operators
        - Distribution system operators
        - Generation companies
        - Energy service providers
        - Market operators
        
        Article 2: Definitions
        For the purposes of this regulation:
        - "Critical infrastructure" means facilities essential for system reliability
        - "Compliance officer" means designated personnel responsible for regulatory adherence
        - "Incident" means any event affecting system operations or safety
        
        CHAPTER 2: OPERATIONAL REQUIREMENTS
        
        Article 3: System Reliability Standards
        3.1 Operators must maintain system availability of 99.95% annually
        3.2 Maximum allowable outage duration: 4 hours per incident
        3.3 Backup systems must be tested monthly
        3.4 Emergency response procedures must be updated quarterly
        
        Article 4: Performance Monitoring
        4.1 Real-time monitoring required for all critical parameters
        4.2 Data retention period: 7 years minimum
        4.3 Automated alerting systems mandatory for critical thresholds
        4.4 Performance reports due within 48 hours of month end
        
        CHAPTER 3: REPORTING OBLIGATIONS
        
        Article 5: Regular Reporting
        5.1 Daily operational summaries due by 10:00 AM following day
        5.2 Weekly performance metrics due every Monday
        5.3 Monthly compliance reports due by 15th of following month
        5.4 Quarterly financial reports due within 45 days of quarter end
        5.5 Annual comprehensive assessments due by March 31st
        
        Article 6: Incident Reporting
        6.1 Critical incidents: Immediate notification (within 1 hour)
        6.2 Major incidents: Notification within 4 hours
        6.3 Minor incidents: Notification within 24 hours
        6.4 Follow-up reports due within 72 hours of initial notification
        
        CHAPTER 4: SAFETY AND SECURITY
        
        Article 7: Personnel Requirements
        7.1 All personnel must undergo background checks
        7.2 Safety training required every 12 months
        7.3 Specialized certifications required for high-voltage work
        7.4 Fitness for duty assessments required annually
        
        Article 8: Cybersecurity Standards
        8.1 Implementation of cybersecurity framework mandatory
        8.2 Vulnerability assessments required quarterly
        8.3 Incident response plan must be tested semi-annually
        8.4 Security awareness training required for all personnel
        
        CHAPTER 5: ENVIRONMENTAL COMPLIANCE
        
        Article 9: Environmental Monitoring
        9.1 Continuous emissions monitoring required
        9.2 Water quality testing monthly
        9.3 Noise level assessments quarterly
        9.4 Wildlife impact studies annually
        
        Article 10: Sustainability Reporting
        10.1 Carbon footprint reporting required annually
        10.2 Renewable energy integration targets must be met
        10.3 Energy efficiency improvements must be documented
        10.4 Waste management plans must be updated annually
        
        CHAPTER 6: FINANCIAL REQUIREMENTS
        
        Article 11: Financial Reporting
        11.1 Audited financial statements due within 90 days of year end
        11.2 Quarterly financial reports required
        11.3 Capital expenditure plans must be submitted annually
        11.4 Rate case filings must include detailed cost justifications
        
        Article 12: Insurance Requirements
        12.1 Minimum liability coverage: $100 million
        12.2 Property insurance required for all critical assets
        12.3 Cyber liability insurance mandatory
        12.4 Insurance certificates must be filed annually
        
        CHAPTER 7: ENFORCEMENT
        
        Article 13: Inspections and Audits
        13.1 Regulatory inspections may occur without prior notice
        13.2 Annual compliance audits required
        13.3 Records must be made available within 24 hours of request
        13.4 Corrective action plans due within 30 days of findings
        
        Article 14: Penalties and Sanctions
        14.1 Monetary penalties up to $1 million per violation
        14.2 Operational restrictions may be imposed
        14.3 License suspension possible for repeated violations
        14.4 Criminal referral for willful violations
        """
    
    def _get_minimal_regulation_content(self) -> str:
        """Get minimal regulation content."""
        return """
        BASIC ENERGY REGULATION
        
        Section 1: Requirements
        All energy operators must submit annual compliance reports.
        
        Section 2: Deadlines
        Reports are due by December 31st each year.
        
        Section 3: Penalties
        Late submissions incur a $1,000 daily penalty.
        """
    
    def _get_large_regulation_content(self) -> str:
        """Get large regulation content for performance testing."""
        base_content = self._get_complex_regulation_content()
        
        # Repeat and expand content to create a larger document
        expanded_content = base_content
        
        for i in range(5):  # Repeat content 5 times with variations
            section_content = f"""
            
            APPENDIX {i+1}: ADDITIONAL REQUIREMENTS
            
            A{i+1}.1 Supplementary Obligations
            Additional compliance requirements specific to {['transmission', 'distribution', 'generation', 'retail', 'market'][i]} operations.
            
            A{i+1}.2 Technical Standards
            Detailed technical specifications and performance criteria.
            
            A{i+1}.3 Reporting Templates
            Standardized forms and templates for regulatory submissions.
            
            A{i+1}.4 Implementation Timeline
            Phased implementation schedule for new requirements.
            """
            expanded_content += section_content
        
        return expanded_content
    
    def _get_multilingual_regulation_content(self) -> str:
        """Get regulation content with multiple languages (for testing edge cases)."""
        return """
        ENERGY REGULATION / RÉGLEMENTATION ÉNERGÉTIQUE
        
        Section 1: Requirements / Exigences
        All operators must comply / Tous les opérateurs doivent se conformer
        
        Sección 1: Requisitos
        Todos los operadores deben cumplir con los siguientes requisitos
        
        第1章：要求事項
        すべての事業者は以下の要件を満たす必要があります
        
        Section 2: Reporting / Rapports
        Monthly reports required / Rapports mensuels requis
        
        Section 3: Compliance / Conformité
        Annual audits mandatory / Audits annuels obligatoires
        """
    
    def _get_technical_regulation_content(self) -> str:
        """Get technical regulation content with specific parameters."""
        return """
        TECHNICAL STANDARDS FOR ELECTRICAL SYSTEMS
        
        Section 1: Voltage Requirements
        1.1 Transmission voltage: 115kV, 138kV, 230kV, 345kV, 500kV, 765kV
        1.2 Voltage regulation: ±5% of nominal voltage
        1.3 Power factor: 0.95 lagging to 0.95 leading
        1.4 Frequency: 60 Hz ±0.1 Hz
        
        Section 2: Protection Systems
        2.1 Primary protection clearing time: <100ms
        2.2 Backup protection clearing time: <500ms
        2.3 Reclosing sequences: 1 fast, 2 slow
        2.4 Coordination time intervals: 300-400ms
        
        Section 3: Communication Requirements
        3.1 SCADA system availability: 99.9%
        3.2 Communication latency: <200ms
        3.3 Data update rate: 2-4 seconds
        3.4 Cybersecurity: NERC CIP compliance
        
        Section 4: Performance Standards
        4.1 System Average Interruption Duration Index (SAIDI): <240 minutes
        4.2 System Average Interruption Frequency Index (SAIFI): <2.0
        4.3 Customer Average Interruption Duration Index (CAIDI): <120 minutes
        4.4 Momentary Average Interruption Frequency Index (MAIFI): <10.0
        """
    
    def generate_document_metadata(self, document_type: str = 'regulation') -> Dict[str, Any]:
        """Generate sample document metadata."""
        base_metadata = {
            'title': f'Test {document_type.title()} Document',
            'source': 'Test Regulatory Authority',
            'effective_date': '2024-01-01',
            'document_type': document_type,
            'version': '1.0',
            'language': 'en',
            'jurisdiction': 'US',
            'sector': 'energy'
        }
        
        # Add random variations
        variations = {
            'regulation': {
                'title': f'Energy Regulation {random.randint(100, 999)}',
                'source': random.choice([
                    'Federal Energy Regulatory Commission',
                    'Public Utilities Commission',
                    'State Energy Board',
                    'Regional Transmission Organization'
                ])
            },
            'standard': {
                'title': f'Technical Standard {random.randint(1000, 9999)}',
                'source': random.choice([
                    'IEEE Standards Association',
                    'ANSI Standards',
                    'IEC International Standards',
                    'NERC Reliability Standards'
                ])
            },
            'guideline': {
                'title': f'Compliance Guideline {random.randint(10, 99)}',
                'source': random.choice([
                    'Industry Best Practices Committee',
                    'Regulatory Guidance Board',
                    'Technical Advisory Group'
                ])
            }
        }
        
        if document_type in variations:
            base_metadata.update(variations[document_type])
        
        return base_metadata
    
    def generate_obligation_data(self, document_id: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generate sample obligation data."""
        categories = ['reporting', 'monitoring', 'operational', 'financial', 'safety']
        severities = ['critical', 'high', 'medium', 'low']
        deadline_types = ['recurring', 'one-time', 'ongoing']
        entities = ['transmission_operators', 'distribution_operators', 'generators', 'all_operators']
        
        obligations = []
        
        for i in range(count):
            obligation = {
                'obligation_id': f'obl-{document_id}-{i+1:03d}',
                'document_id': document_id,
                'description': self._generate_obligation_description(),
                'category': random.choice(categories),
                'severity': random.choice(severities),
                'deadline_type': random.choice(deadline_types),
                'applicable_entities': random.sample(entities, random.randint(1, 2)),
                'extracted_text': f'Original text from document section {i+1}...',
                'confidence_score': round(random.uniform(0.7, 1.0), 2),
                'created_timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            obligations.append(obligation)
        
        return obligations
    
    def _generate_obligation_description(self) -> str:
        """Generate a realistic obligation description."""
        templates = [
            "Submit {report_type} reports {frequency} by the {day} of each {period}",
            "Maintain {system_type} availability of {percentage}% {timeframe}",
            "Conduct {activity_type} inspections {frequency}",
            "Complete {training_type} training for all personnel {frequency}",
            "File {document_type} with regulatory authority within {timeframe}",
            "Implement {standard_type} standards by {deadline}",
            "Monitor {parameter_type} continuously and report {frequency}",
            "Update {plan_type} plans {frequency}"
        ]
        
        replacements = {
            'report_type': ['operational', 'financial', 'compliance', 'safety', 'environmental'],
            'frequency': ['monthly', 'quarterly', 'annually', 'semi-annually'],
            'day': ['15th', '30th', 'last day', '1st'],
            'period': ['month', 'quarter', 'year'],
            'system_type': ['transmission', 'distribution', 'generation', 'communication'],
            'percentage': ['99.9', '99.5', '95.0', '98.0'],
            'timeframe': ['annually', 'monthly', 'continuously'],
            'activity_type': ['safety', 'maintenance', 'compliance', 'security'],
            'training_type': ['safety', 'cybersecurity', 'technical', 'compliance'],
            'document_type': ['incident reports', 'compliance certificates', 'audit results'],
            'standard_type': ['cybersecurity', 'safety', 'environmental', 'technical'],
            'deadline': ['December 31, 2024', 'within 90 days', 'by end of quarter'],
            'parameter_type': ['emissions', 'voltage', 'frequency', 'temperature'],
            'plan_type': ['emergency response', 'maintenance', 'cybersecurity', 'training']
        }
        
        template = random.choice(templates)
        
        for key, values in replacements.items():
            if f'{{{key}}}' in template:
                template = template.replace(f'{{{key}}}', random.choice(values))
        
        return template
    
    def generate_task_data(self, obligation_id: str, count: int = 3) -> List[Dict[str, Any]]:
        """Generate sample task data."""
        priorities = ['high', 'medium', 'low']
        statuses = ['pending', 'in_progress', 'completed', 'overdue']
        
        tasks = []
        
        for i in range(count):
            due_date = datetime.utcnow() + timedelta(days=random.randint(1, 90))
            
            task = {
                'task_id': f'task-{obligation_id}-{i+1:03d}',
                'obligation_id': obligation_id,
                'title': self._generate_task_title(),
                'description': self._generate_task_description(),
                'priority': random.choice(priorities),
                'status': random.choice(statuses),
                'assigned_to': f'user-{random.randint(100, 999)}',
                'due_date': due_date.isoformat() + 'Z',
                'created_timestamp': datetime.utcnow().isoformat() + 'Z',
                'updated_timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            tasks.append(task)
        
        return tasks
    
    def _generate_task_title(self) -> str:
        """Generate a realistic task title."""
        templates = [
            "Prepare {report_type} Report",
            "Complete {activity_type} Assessment",
            "Update {document_type} Documentation",
            "Conduct {inspection_type} Inspection",
            "Review {standard_type} Compliance",
            "Submit {filing_type} Filing",
            "Implement {system_type} Improvements",
            "Schedule {maintenance_type} Maintenance"
        ]
        
        replacements = {
            'report_type': ['Monthly Compliance', 'Quarterly Financial', 'Annual Safety', 'Environmental Impact'],
            'activity_type': ['Risk', 'Performance', 'Security', 'Environmental'],
            'document_type': ['Policy', 'Procedure', 'Emergency Response', 'Training'],
            'inspection_type': ['Safety', 'Equipment', 'Facility', 'Compliance'],
            'standard_type': ['Cybersecurity', 'Safety', 'Environmental', 'Technical'],
            'filing_type': ['Regulatory', 'Compliance', 'Financial', 'Incident'],
            'system_type': ['Safety', 'Security', 'Monitoring', 'Communication'],
            'maintenance_type': ['Preventive', 'Corrective', 'Emergency', 'Scheduled']
        }
        
        template = random.choice(templates)
        
        for key, values in replacements.items():
            if f'{{{key}}}' in template:
                template = template.replace(f'{{{key}}}', random.choice(values))
        
        return template
    
    def _generate_task_description(self) -> str:
        """Generate a realistic task description."""
        descriptions = [
            "Compile and analyze data for regulatory submission",
            "Review current procedures and identify improvement opportunities",
            "Coordinate with relevant stakeholders to ensure compliance",
            "Gather documentation and prepare comprehensive report",
            "Conduct thorough assessment of current status and requirements",
            "Update documentation to reflect current practices and regulations",
            "Schedule and coordinate necessary activities with operations team",
            "Verify compliance with all applicable standards and requirements"
        ]
        
        return random.choice(descriptions)
    
    def generate_report_data(self, report_type: str = 'compliance_summary') -> Dict[str, Any]:
        """Generate sample report data."""
        report_types = {
            'compliance_summary': 'Comprehensive Compliance Summary Report',
            'audit_readiness': 'Audit Readiness Assessment Report',
            'obligation_status': 'Obligation Status Tracking Report',
            'task_progress': 'Task Progress Monitoring Report',
            'performance_metrics': 'Performance Metrics Analysis Report'
        }
        
        return {
            'report_id': f'rpt-{random.randint(100000, 999999)}',
            'title': report_types.get(report_type, 'Test Report'),
            'report_type': report_type,
            'generated_by': f'user-{random.randint(100, 999)}',
            's3_key': f'reports/rpt-{random.randint(100000, 999999)}.pdf',
            'status': random.choice(['generating', 'completed', 'failed']),
            'created_timestamp': datetime.utcnow().isoformat() + 'Z',
            'date_range': {
                'start_date': '2024-01-01',
                'end_date': '2024-12-31'
            },
            'filters': {
                'categories': random.sample(['reporting', 'monitoring', 'operational'], 2),
                'severities': random.sample(['critical', 'high', 'medium'], 2)
            }
        }
    
    def save_test_data(self, data: Dict[str, Any], filename: str) -> str:
        """Save test data to a JSON file."""
        filepath = self.test_data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return str(filepath)
    
    def load_test_data(self, filename: str) -> Dict[str, Any]:
        """Load test data from a JSON file."""
        filepath = self.test_data_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Test data file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary files created during testing."""
        temp_dir = Path(tempfile.gettempdir())
        
        # Clean up PDF files created by tests
        for pdf_file in temp_dir.glob('tmp*.pdf'):
            try:
                pdf_file.unlink()
            except OSError:
                pass  # File might be in use or already deleted


# Global test data generator instance
test_data_generator = TestDataGenerator()


def get_test_data_generator() -> TestDataGenerator:
    """Get the global test data generator."""
    return test_data_generator