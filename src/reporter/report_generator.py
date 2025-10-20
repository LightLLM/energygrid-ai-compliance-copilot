"""
Report Generation Logic for EnergyGrid.AI Compliance Copilot
Compiles data from obligations and tasks to generate formatted compliance reports
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

try:
    from ..shared.models import (
        Report, Obligation, Task, Document, ReportType, ProcessingStatus,
        ObligationCategory, ObligationSeverity, TaskStatus, TaskPriority
    )
    from ..shared.dynamodb_helper import get_db_helper
    from ..analyzer.bedrock_client import BedrockClient
except ImportError:
    from src.shared.models import (
        Report, Obligation, Task, Document, ReportType, ProcessingStatus,
        ObligationCategory, ObligationSeverity, TaskStatus, TaskPriority
    )
    from src.shared.dynamodb_helper import get_db_helper
    from src.analyzer.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


@dataclass
class ReportData:
    """Container for compiled report data"""
    obligations: List[Obligation]
    tasks: List[Task]
    documents: List[Document]
    summary_stats: Dict[str, Any]
    date_range: Dict[str, datetime]


@dataclass
class ReportTemplate:
    """Report template configuration"""
    title: str
    sections: List[str]
    include_charts: bool
    include_tables: bool
    format_type: str = "pdf"


class ReportGenerationError(Exception):
    """Custom exception for report generation errors"""
    pass


class ReportGenerator:
    """
    Report generation logic for compliance reports
    Compiles data from obligations and tasks and generates formatted reports
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize report generator
        
        Args:
            region_name: AWS region for services
        """
        self.region_name = region_name
        self.db_helper = get_db_helper()
        self.bedrock_client = BedrockClient(region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        
        # Report templates
        self.templates = {
            ReportType.COMPLIANCE_SUMMARY: ReportTemplate(
                title="Compliance Summary Report",
                sections=["executive_summary", "obligation_overview", "compliance_status", "recommendations"],
                include_charts=True,
                include_tables=True
            ),
            ReportType.AUDIT_READINESS: ReportTemplate(
                title="Audit Readiness Report",
                sections=["audit_scope", "compliance_gaps", "task_status", "evidence_summary", "action_plan"],
                include_charts=True,
                include_tables=True
            ),
            ReportType.OBLIGATION_STATUS: ReportTemplate(
                title="Obligation Status Report",
                sections=["obligation_summary", "status_breakdown", "upcoming_deadlines", "risk_assessment"],
                include_charts=False,
                include_tables=True
            )
        }
    
    def compile_report_data(
        self,
        report_type: ReportType,
        date_range: Dict[str, datetime],
        filters: Optional[Dict[str, Any]] = None
    ) -> ReportData:
        """
        Compile data from obligations and tasks for report generation
        
        Args:
            report_type: Type of report to generate
            date_range: Date range for the report (start_date, end_date)
            filters: Optional filters for data selection
            
        Returns:
            Compiled report data
            
        Raises:
            ReportGenerationError: If data compilation fails
        """
        logger.info(f"Compiling data for {report_type.value} report")
        
        try:
            # Initialize filters
            filters = filters or {}
            
            # Compile obligations data
            obligations = self._get_filtered_obligations(date_range, filters)
            logger.info(f"Found {len(obligations)} obligations in date range")
            
            # Compile tasks data
            tasks = self._get_filtered_tasks(obligations, date_range, filters)
            logger.info(f"Found {len(tasks)} tasks for obligations")
            
            # Get related documents
            document_ids = list(set(obl.document_id for obl in obligations))
            documents = self._get_documents(document_ids)
            logger.info(f"Found {len(documents)} related documents")
            
            # Generate summary statistics
            summary_stats = self._generate_summary_stats(obligations, tasks, documents)
            
            report_data = ReportData(
                obligations=obligations,
                tasks=tasks,
                documents=documents,
                summary_stats=summary_stats,
                date_range=date_range
            )
            
            logger.info("Successfully compiled report data")
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to compile report data: {e}")
            raise ReportGenerationError(f"Data compilation failed: {e}")
    
    def _get_filtered_obligations(
        self,
        date_range: Dict[str, datetime],
        filters: Dict[str, Any]
    ) -> List[Obligation]:
        """Get obligations filtered by date range and criteria"""
        try:
            # For now, get all obligations and filter in memory
            # In production, this should use DynamoDB queries with date filters
            all_obligations = []
            
            # Get obligations by category if specified
            if 'category' in filters:
                category = ObligationCategory(filters['category'])
                severity = filters.get('severity')
                if severity:
                    severity = ObligationSeverity(severity)
                obligations = self.db_helper.list_obligations_by_category(category, severity)
                all_obligations.extend(obligations)
            else:
                # Get all obligations (this is a simplified approach)
                # In production, implement pagination and date-based queries
                logger.warning("Getting all obligations - implement pagination for production")
                # For now, return empty list as we don't have a scan_all method
                all_obligations = []
            
            # Filter by date range
            filtered_obligations = []
            start_date = date_range['start_date']
            end_date = date_range['end_date']
            
            for obligation in all_obligations:
                if start_date <= obligation.created_timestamp <= end_date:
                    filtered_obligations.append(obligation)
            
            return filtered_obligations
            
        except Exception as e:
            logger.error(f"Failed to get filtered obligations: {e}")
            return []
    
    def _get_filtered_tasks(
        self,
        obligations: List[Obligation],
        date_range: Dict[str, datetime],
        filters: Dict[str, Any]
    ) -> List[Task]:
        """Get tasks related to obligations and filtered by criteria"""
        try:
            all_tasks = []
            
            # Get tasks for each obligation
            for obligation in obligations:
                tasks = self.db_helper.list_tasks_by_obligation(obligation.obligation_id)
                all_tasks.extend(tasks)
            
            # Filter by date range and other criteria
            filtered_tasks = []
            start_date = date_range['start_date']
            end_date = date_range['end_date']
            
            for task in all_tasks:
                # Filter by creation date
                if not (start_date <= task.created_timestamp <= end_date):
                    continue
                
                # Filter by status if specified
                if 'task_status' in filters:
                    if task.status.value != filters['task_status']:
                        continue
                
                # Filter by priority if specified
                if 'task_priority' in filters:
                    if task.priority.value != filters['task_priority']:
                        continue
                
                filtered_tasks.append(task)
            
            return filtered_tasks
            
        except Exception as e:
            logger.error(f"Failed to get filtered tasks: {e}")
            return []
    
    def _get_documents(self, document_ids: List[str]) -> List[Document]:
        """Get documents by IDs"""
        try:
            documents = []
            for doc_id in document_ids:
                document = self.db_helper.get_document(doc_id)
                if document:
                    documents.append(document)
            return documents
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []
    
    def _generate_summary_stats(
        self,
        obligations: List[Obligation],
        tasks: List[Task],
        documents: List[Document]
    ) -> Dict[str, Any]:
        """Generate summary statistics for the report"""
        try:
            # Obligation statistics
            obligation_stats = {
                'total_count': len(obligations),
                'by_category': {},
                'by_severity': {},
                'by_deadline_type': {}
            }
            
            for obligation in obligations:
                # Count by category
                category = obligation.category.value
                obligation_stats['by_category'][category] = obligation_stats['by_category'].get(category, 0) + 1
                
                # Count by severity
                severity = obligation.severity.value
                obligation_stats['by_severity'][severity] = obligation_stats['by_severity'].get(severity, 0) + 1
                
                # Count by deadline type
                deadline_type = obligation.deadline_type.value
                obligation_stats['by_deadline_type'][deadline_type] = obligation_stats['by_deadline_type'].get(deadline_type, 0) + 1
            
            # Task statistics
            task_stats = {
                'total_count': len(tasks),
                'by_status': {},
                'by_priority': {},
                'overdue_count': 0,
                'completed_count': 0
            }
            
            current_time = datetime.utcnow()
            for task in tasks:
                # Count by status
                status = task.status.value
                task_stats['by_status'][status] = task_stats['by_status'].get(status, 0) + 1
                
                # Count by priority
                priority = task.priority.value
                task_stats['by_priority'][priority] = task_stats['by_priority'].get(priority, 0) + 1
                
                # Count overdue tasks
                if task.due_date and task.due_date < current_time and task.status != TaskStatus.COMPLETED:
                    task_stats['overdue_count'] += 1
                
                # Count completed tasks
                if task.status == TaskStatus.COMPLETED:
                    task_stats['completed_count'] += 1
            
            # Document statistics
            document_stats = {
                'total_count': len(documents),
                'by_status': {},
                'total_size_mb': 0
            }
            
            for document in documents:
                # Count by processing status
                status = document.processing_status.value
                document_stats['by_status'][status] = document_stats['by_status'].get(status, 0) + 1
                
                # Sum file sizes
                document_stats['total_size_mb'] += document.file_size / (1024 * 1024)
            
            # Compliance metrics
            compliance_metrics = {
                'completion_rate': 0.0,
                'overdue_rate': 0.0,
                'critical_obligations': 0,
                'high_priority_tasks': 0
            }
            
            if len(tasks) > 0:
                compliance_metrics['completion_rate'] = task_stats['completed_count'] / len(tasks) * 100
                compliance_metrics['overdue_rate'] = task_stats['overdue_count'] / len(tasks) * 100
            
            compliance_metrics['critical_obligations'] = obligation_stats['by_severity'].get('critical', 0)
            compliance_metrics['high_priority_tasks'] = task_stats['by_priority'].get('high', 0)
            
            return {
                'obligations': obligation_stats,
                'tasks': task_stats,
                'documents': document_stats,
                'compliance_metrics': compliance_metrics,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary statistics: {e}")
            return {}
    
    def generate_report_content(
        self,
        report_data: ReportData,
        report_type: ReportType,
        title: str
    ) -> str:
        """
        Generate formatted report content using Claude Sonnet
        
        Args:
            report_data: Compiled report data
            report_type: Type of report to generate
            title: Report title
            
        Returns:
            Generated report content in markdown format
            
        Raises:
            ReportGenerationError: If content generation fails
        """
        logger.info(f"Generating content for {report_type.value} report")
        
        try:
            # Get report template
            template = self.templates.get(report_type)
            if not template:
                raise ReportGenerationError(f"No template found for report type: {report_type.value}")
            
            # Build prompt for Claude Sonnet
            prompt = self._build_report_prompt(report_data, template, title)
            
            # Generate content using Claude Sonnet
            content = self.bedrock_client._call_claude_with_retry(prompt)
            
            logger.info("Successfully generated report content")
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate report content: {e}")
            raise ReportGenerationError(f"Content generation failed: {e}")
    
    def _build_report_prompt(
        self,
        report_data: ReportData,
        template: ReportTemplate,
        title: str
    ) -> str:
        """Build prompt for Claude Sonnet report generation"""
        
        # Prepare data summaries for the prompt
        obligations_summary = self._summarize_obligations(report_data.obligations)
        tasks_summary = self._summarize_tasks(report_data.tasks)
        stats_summary = json.dumps(report_data.summary_stats, indent=2)
        
        date_range_str = f"{report_data.date_range['start_date'].strftime('%Y-%m-%d')} to {report_data.date_range['end_date'].strftime('%Y-%m-%d')}"
        
        prompt = f"""You are an expert compliance analyst generating a professional regulatory compliance report. Create a comprehensive {template.title.lower()} based on the provided data.

REPORT REQUIREMENTS:
- Title: {title}
- Report Type: {template.title}
- Date Range: {date_range_str}
- Format: Professional markdown document
- Sections Required: {', '.join(template.sections)}

DATA SUMMARY:
Total Obligations: {len(report_data.obligations)}
Total Tasks: {len(report_data.tasks)}
Total Documents: {len(report_data.documents)}

OBLIGATIONS DATA:
{obligations_summary}

TASKS DATA:
{tasks_summary}

STATISTICAL SUMMARY:
{stats_summary}

REPORT STRUCTURE:
Please generate a professional compliance report with the following sections:

1. **Executive Summary**: High-level overview of compliance status and key findings
2. **Data Overview**: Summary of analyzed documents, obligations, and tasks
3. **Compliance Status Analysis**: Detailed analysis of compliance obligations and their status
4. **Task Management Summary**: Overview of audit tasks, completion rates, and priorities
5. **Risk Assessment**: Identification of compliance gaps and risk areas
6. **Recommendations**: Actionable recommendations for improving compliance
7. **Appendix**: Detailed data tables and supporting information

FORMATTING REQUIREMENTS:
- Use professional markdown formatting
- Include tables for data presentation where appropriate
- Use bullet points for lists and recommendations
- Include percentage calculations and metrics
- Maintain a formal, professional tone
- Ensure all data is accurately represented

ANALYSIS FOCUS:
- Highlight critical and high-severity obligations
- Identify overdue or at-risk tasks
- Calculate compliance completion rates
- Assess regulatory coverage and gaps
- Provide actionable insights and recommendations

Please generate the complete report content in markdown format."""

        return prompt
    
    def _summarize_obligations(self, obligations: List[Obligation]) -> str:
        """Create a text summary of obligations for the prompt"""
        if not obligations:
            return "No obligations found in the specified date range."
        
        summary_lines = []
        summary_lines.append(f"Total Obligations: {len(obligations)}")
        
        # Group by category
        by_category = {}
        by_severity = {}
        
        for obl in obligations:
            category = obl.category.value
            severity = obl.severity.value
            
            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        summary_lines.append("\nBy Category:")
        for category, count in by_category.items():
            summary_lines.append(f"  - {category.title()}: {count}")
        
        summary_lines.append("\nBy Severity:")
        for severity, count in by_severity.items():
            summary_lines.append(f"  - {severity.title()}: {count}")
        
        # Add sample obligations
        summary_lines.append("\nSample Obligations:")
        for i, obl in enumerate(obligations[:3]):  # Show first 3
            summary_lines.append(f"  {i+1}. [{obl.severity.value.upper()}] {obl.description[:100]}...")
        
        return "\n".join(summary_lines)
    
    def _summarize_tasks(self, tasks: List[Task]) -> str:
        """Create a text summary of tasks for the prompt"""
        if not tasks:
            return "No tasks found for the analyzed obligations."
        
        summary_lines = []
        summary_lines.append(f"Total Tasks: {len(tasks)}")
        
        # Group by status and priority
        by_status = {}
        by_priority = {}
        overdue_count = 0
        
        current_time = datetime.utcnow()
        
        for task in tasks:
            status = task.status.value
            priority = task.priority.value
            
            by_status[status] = by_status.get(status, 0) + 1
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            if task.due_date and task.due_date < current_time and task.status != TaskStatus.COMPLETED:
                overdue_count += 1
        
        summary_lines.append("\nBy Status:")
        for status, count in by_status.items():
            summary_lines.append(f"  - {status.replace('_', ' ').title()}: {count}")
        
        summary_lines.append("\nBy Priority:")
        for priority, count in by_priority.items():
            summary_lines.append(f"  - {priority.title()}: {count}")
        
        if overdue_count > 0:
            summary_lines.append(f"\nOverdue Tasks: {overdue_count}")
        
        # Add sample tasks
        summary_lines.append("\nSample Tasks:")
        for i, task in enumerate(tasks[:3]):  # Show first 3
            due_str = task.due_date.strftime('%Y-%m-%d') if task.due_date else "No due date"
            summary_lines.append(f"  {i+1}. [{task.priority.value.upper()}] {task.title} (Due: {due_str})")
        
        return "\n".join(summary_lines)
    
    def create_pdf_report(
        self,
        content: str,
        report_id: str,
        bucket_name: str,
        charts: Optional[List] = None,
        tables: Optional[List] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create PDF report from markdown content and upload to S3
        
        Args:
            content: Report content in markdown format
            report_id: Unique report identifier
            bucket_name: S3 bucket name for storage
            charts: Optional list of charts to include
            tables: Optional list of tables to include
            metadata: Optional metadata for the report
            
        Returns:
            S3 key for the uploaded PDF
            
        Raises:
            ReportGenerationError: If PDF creation fails
        """
        logger.info(f"Creating PDF report for {report_id}")
        
        try:
            # Import PDF generator
            try:
                from .pdf_generator import create_compliance_report_pdf
                
                # Extract title from content
                title = self._extract_title_from_content(content)
                
                # Create PDF using ReportLab
                pdf_content = create_compliance_report_pdf(
                    title=title,
                    report_content=content,
                    charts=charts,
                    tables=tables,
                    metadata=metadata
                )
                
            except ImportError:
                logger.warning("ReportLab not available, using simple PDF generation")
                # Fallback to simple PDF
                pdf_content = self._create_simple_pdf(content, report_id)
            
            # Upload to S3
            s3_key = f"reports/{report_id}.pdf"
            
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=pdf_content,
                ContentType='application/pdf',
                Metadata={
                    'report_id': report_id,
                    'generated_at': datetime.utcnow().isoformat(),
                    'content_type': 'compliance_report'
                }
            )
            
            logger.info(f"Successfully uploaded PDF report to S3: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to create PDF report: {e}")
            raise ReportGenerationError(f"PDF creation failed: {e}")
    
    def _extract_title_from_content(self, content: str) -> str:
        """Extract title from markdown content"""
        try:
            lines = content.split('\n')
            for line in lines:
                if line.startswith('# '):
                    return line[2:].strip()
            return "Compliance Report"
        except:
            return "Compliance Report"
    
    def _create_simple_pdf(self, content: str, report_id: str) -> bytes:
        """Create a simple PDF fallback when ReportLab is not available"""
        try:
            from .pdf_generator import create_simple_pdf
            return create_simple_pdf(content, f"Report {report_id}")
        except ImportError:
            # Ultimate fallback - return content as text with PDF header
            pdf_header = b"%PDF-1.4\n"
            pdf_content = content.encode('utf-8')
            return pdf_header + pdf_content
    
    def validate_report_request(
        self,
        report_type: str,
        date_range: Dict[str, Any],
        user_id: str
    ) -> Tuple[bool, str]:
        """
        Validate report generation request
        
        Args:
            report_type: Requested report type
            date_range: Date range for the report
            user_id: User requesting the report
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate report type
            try:
                ReportType(report_type)
            except ValueError:
                return False, f"Invalid report type: {report_type}"
            
            # Validate date range
            if not isinstance(date_range, dict):
                return False, "Date range must be a dictionary"
            
            if 'start_date' not in date_range or 'end_date' not in date_range:
                return False, "Date range must contain start_date and end_date"
            
            start_date = date_range['start_date']
            end_date = date_range['end_date']
            
            if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
                return False, "start_date and end_date must be datetime objects"
            
            if start_date >= end_date:
                return False, "start_date must be before end_date"
            
            # Check if date range is reasonable (not too large)
            max_range = timedelta(days=365)  # 1 year max
            if end_date - start_date > max_range:
                return False, "Date range cannot exceed 365 days"
            
            # Validate user ID
            if not user_id or not user_id.strip():
                return False, "User ID is required"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating report request: {e}")
            return False, f"Validation error: {e}"


# Convenience functions
def generate_compliance_summary_report(
    date_range: Dict[str, datetime],
    user_id: str,
    filters: Optional[Dict[str, Any]] = None
) -> Tuple[str, ReportData]:
    """
    Generate a compliance summary report
    
    Args:
        date_range: Date range for the report
        user_id: User generating the report
        filters: Optional filters for data selection
        
    Returns:
        Tuple of (report_content, report_data)
    """
    generator = ReportGenerator()
    
    # Compile data
    report_data = generator.compile_report_data(
        ReportType.COMPLIANCE_SUMMARY,
        date_range,
        filters
    )
    
    # Generate content
    title = f"Compliance Summary Report - {date_range['start_date'].strftime('%Y-%m-%d')} to {date_range['end_date'].strftime('%Y-%m-%d')}"
    content = generator.generate_report_content(
        report_data,
        ReportType.COMPLIANCE_SUMMARY,
        title
    )
    
    return content, report_data


def generate_audit_readiness_report(
    date_range: Dict[str, datetime],
    user_id: str,
    filters: Optional[Dict[str, Any]] = None
) -> Tuple[str, ReportData]:
    """
    Generate an audit readiness report
    
    Args:
        date_range: Date range for the report
        user_id: User generating the report
        filters: Optional filters for data selection
        
    Returns:
        Tuple of (report_content, report_data)
    """
    generator = ReportGenerator()
    
    # Compile data
    report_data = generator.compile_report_data(
        ReportType.AUDIT_READINESS,
        date_range,
        filters
    )
    
    # Generate content
    title = f"Audit Readiness Report - {date_range['start_date'].strftime('%Y-%m-%d')} to {date_range['end_date'].strftime('%Y-%m-%d')}"
    content = generator.generate_report_content(
        report_data,
        ReportType.AUDIT_READINESS,
        title
    )
    
    return content, report_data