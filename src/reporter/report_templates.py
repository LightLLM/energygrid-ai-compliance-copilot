"""
Report Templates and Formatting Utilities for EnergyGrid.AI Compliance Copilot
Provides templates and utilities for creating formatted reports with charts and tables
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from ..shared.models import (
        Obligation, Task, Document, ReportType,
        ObligationCategory, ObligationSeverity, TaskStatus, TaskPriority
    )
except ImportError:
    from src.shared.models import (
        Obligation, Task, Document, ReportType,
        ObligationCategory, ObligationSeverity, TaskStatus, TaskPriority
    )

logger = logging.getLogger(__name__)


class ChartType(str, Enum):
    """Chart type enumeration"""
    PIE = "pie"
    BAR = "bar"
    LINE = "line"
    DONUT = "donut"


@dataclass
class ChartData:
    """Chart data structure"""
    title: str
    chart_type: ChartType
    labels: List[str]
    values: List[int]
    colors: Optional[List[str]] = None


@dataclass
class TableData:
    """Table data structure"""
    title: str
    headers: List[str]
    rows: List[List[str]]
    footer: Optional[List[str]] = None


class ReportTemplateEngine:
    """
    Report template engine for generating formatted reports with charts and tables
    """
    
    def __init__(self):
        """Initialize the template engine"""
        self.color_schemes = {
            'severity': {
                'critical': '#dc3545',  # Red
                'high': '#fd7e14',      # Orange
                'medium': '#ffc107',    # Yellow
                'low': '#28a745'        # Green
            },
            'status': {
                'completed': '#28a745',     # Green
                'in_progress': '#007bff',   # Blue
                'pending': '#6c757d',       # Gray
                'overdue': '#dc3545'        # Red
            },
            'category': {
                'reporting': '#007bff',     # Blue
                'monitoring': '#28a745',    # Green
                'operational': '#ffc107',   # Yellow
                'financial': '#dc3545'      # Red
            }
        }
    
    def create_obligation_charts(
        self,
        obligations: List[Obligation]
    ) -> List[ChartData]:
        """
        Create charts for obligation data
        
        Args:
            obligations: List of obligations
            
        Returns:
            List of chart data objects
        """
        charts = []
        
        if not obligations:
            return charts
        
        try:
            # Obligations by category chart
            category_chart = self._create_category_chart(obligations)
            if category_chart:
                charts.append(category_chart)
            
            # Obligations by severity chart
            severity_chart = self._create_severity_chart(obligations)
            if severity_chart:
                charts.append(severity_chart)
            
            # Obligations by deadline type chart
            deadline_chart = self._create_deadline_type_chart(obligations)
            if deadline_chart:
                charts.append(deadline_chart)
            
            logger.info(f"Created {len(charts)} obligation charts")
            return charts
            
        except Exception as e:
            logger.error(f"Failed to create obligation charts: {e}")
            return []
    
    def create_task_charts(
        self,
        tasks: List[Task]
    ) -> List[ChartData]:
        """
        Create charts for task data
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of chart data objects
        """
        charts = []
        
        if not tasks:
            return charts
        
        try:
            # Tasks by status chart
            status_chart = self._create_task_status_chart(tasks)
            if status_chart:
                charts.append(status_chart)
            
            # Tasks by priority chart
            priority_chart = self._create_task_priority_chart(tasks)
            if priority_chart:
                charts.append(priority_chart)
            
            # Task completion trend (if we have date data)
            completion_chart = self._create_task_completion_chart(tasks)
            if completion_chart:
                charts.append(completion_chart)
            
            logger.info(f"Created {len(charts)} task charts")
            return charts
            
        except Exception as e:
            logger.error(f"Failed to create task charts: {e}")
            return []
    
    def _create_category_chart(self, obligations: List[Obligation]) -> Optional[ChartData]:
        """Create chart for obligations by category"""
        try:
            category_counts = {}
            for obligation in obligations:
                category = obligation.category.value
                category_counts[category] = category_counts.get(category, 0) + 1
            
            if not category_counts:
                return None
            
            labels = list(category_counts.keys())
            values = list(category_counts.values())
            colors = [self.color_schemes['category'].get(label, '#6c757d') for label in labels]
            
            return ChartData(
                title="Obligations by Category",
                chart_type=ChartType.PIE,
                labels=[label.replace('_', ' ').title() for label in labels],
                values=values,
                colors=colors
            )
            
        except Exception as e:
            logger.error(f"Failed to create category chart: {e}")
            return None
    
    def _create_severity_chart(self, obligations: List[Obligation]) -> Optional[ChartData]:
        """Create chart for obligations by severity"""
        try:
            severity_counts = {}
            for obligation in obligations:
                severity = obligation.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if not severity_counts:
                return None
            
            # Order by severity level
            severity_order = ['critical', 'high', 'medium', 'low']
            labels = []
            values = []
            colors = []
            
            for severity in severity_order:
                if severity in severity_counts:
                    labels.append(severity.title())
                    values.append(severity_counts[severity])
                    colors.append(self.color_schemes['severity'][severity])
            
            return ChartData(
                title="Obligations by Severity",
                chart_type=ChartType.BAR,
                labels=labels,
                values=values,
                colors=colors
            )
            
        except Exception as e:
            logger.error(f"Failed to create severity chart: {e}")
            return None
    
    def _create_deadline_type_chart(self, obligations: List[Obligation]) -> Optional[ChartData]:
        """Create chart for obligations by deadline type"""
        try:
            deadline_counts = {}
            for obligation in obligations:
                deadline_type = obligation.deadline_type.value
                deadline_counts[deadline_type] = deadline_counts.get(deadline_type, 0) + 1
            
            if not deadline_counts:
                return None
            
            labels = list(deadline_counts.keys())
            values = list(deadline_counts.values())
            
            return ChartData(
                title="Obligations by Deadline Type",
                chart_type=ChartType.DONUT,
                labels=[label.replace('_', ' ').title() for label in labels],
                values=values
            )
            
        except Exception as e:
            logger.error(f"Failed to create deadline type chart: {e}")
            return None
    
    def _create_task_status_chart(self, tasks: List[Task]) -> Optional[ChartData]:
        """Create chart for tasks by status"""
        try:
            status_counts = {}
            for task in tasks:
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if not status_counts:
                return None
            
            labels = list(status_counts.keys())
            values = list(status_counts.values())
            colors = [self.color_schemes['status'].get(label, '#6c757d') for label in labels]
            
            return ChartData(
                title="Tasks by Status",
                chart_type=ChartType.PIE,
                labels=[label.replace('_', ' ').title() for label in labels],
                values=values,
                colors=colors
            )
            
        except Exception as e:
            logger.error(f"Failed to create task status chart: {e}")
            return None
    
    def _create_task_priority_chart(self, tasks: List[Task]) -> Optional[ChartData]:
        """Create chart for tasks by priority"""
        try:
            priority_counts = {}
            for task in tasks:
                priority = task.priority.value
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            if not priority_counts:
                return None
            
            # Order by priority level
            priority_order = ['high', 'medium', 'low']
            labels = []
            values = []
            
            for priority in priority_order:
                if priority in priority_counts:
                    labels.append(priority.title())
                    values.append(priority_counts[priority])
            
            return ChartData(
                title="Tasks by Priority",
                chart_type=ChartType.BAR,
                labels=labels,
                values=values
            )
            
        except Exception as e:
            logger.error(f"Failed to create task priority chart: {e}")
            return None
    
    def _create_task_completion_chart(self, tasks: List[Task]) -> Optional[ChartData]:
        """Create chart for task completion over time"""
        try:
            # This would require grouping tasks by completion date
            # For now, just show completion rate
            completed_count = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
            total_count = len(tasks)
            
            if total_count == 0:
                return None
            
            pending_count = total_count - completed_count
            
            return ChartData(
                title="Task Completion Status",
                chart_type=ChartType.DONUT,
                labels=["Completed", "Pending"],
                values=[completed_count, pending_count],
                colors=["#28a745", "#6c757d"]
            )
            
        except Exception as e:
            logger.error(f"Failed to create task completion chart: {e}")
            return None
    
    def create_obligation_table(
        self,
        obligations: List[Obligation],
        limit: int = 20
    ) -> TableData:
        """
        Create table for obligation data
        
        Args:
            obligations: List of obligations
            limit: Maximum number of rows to include
            
        Returns:
            Table data object
        """
        try:
            headers = [
                "ID",
                "Description",
                "Category",
                "Severity",
                "Deadline Type",
                "Confidence",
                "Created"
            ]
            
            rows = []
            for i, obligation in enumerate(obligations[:limit]):
                row = [
                    obligation.obligation_id[-8:],  # Last 8 chars of ID
                    obligation.description[:50] + "..." if len(obligation.description) > 50 else obligation.description,
                    obligation.category.value.title(),
                    obligation.severity.value.title(),
                    obligation.deadline_type.value.replace('_', ' ').title(),
                    f"{obligation.confidence_score:.2f}",
                    obligation.created_timestamp.strftime('%Y-%m-%d')
                ]
                rows.append(row)
            
            footer = None
            if len(obligations) > limit:
                footer = [f"Showing {limit} of {len(obligations)} obligations"]
            
            return TableData(
                title="Compliance Obligations",
                headers=headers,
                rows=rows,
                footer=footer
            )
            
        except Exception as e:
            logger.error(f"Failed to create obligation table: {e}")
            return TableData(
                title="Compliance Obligations",
                headers=["Error"],
                rows=[["Failed to load obligation data"]]
            )
    
    def create_task_table(
        self,
        tasks: List[Task],
        limit: int = 20
    ) -> TableData:
        """
        Create table for task data
        
        Args:
            tasks: List of tasks
            limit: Maximum number of rows to include
            
        Returns:
            Table data object
        """
        try:
            headers = [
                "ID",
                "Title",
                "Priority",
                "Status",
                "Assigned To",
                "Due Date",
                "Created"
            ]
            
            rows = []
            for task in tasks[:limit]:
                row = [
                    task.task_id[-8:],  # Last 8 chars of ID
                    task.title[:40] + "..." if len(task.title) > 40 else task.title,
                    task.priority.value.title(),
                    task.status.value.replace('_', ' ').title(),
                    task.assigned_to[-10:] if task.assigned_to else "Unassigned",
                    task.due_date.strftime('%Y-%m-%d') if task.due_date else "No due date",
                    task.created_timestamp.strftime('%Y-%m-%d')
                ]
                rows.append(row)
            
            footer = None
            if len(tasks) > limit:
                footer = [f"Showing {limit} of {len(tasks)} tasks"]
            
            return TableData(
                title="Audit Tasks",
                headers=headers,
                rows=rows,
                footer=footer
            )
            
        except Exception as e:
            logger.error(f"Failed to create task table: {e}")
            return TableData(
                title="Audit Tasks",
                headers=["Error"],
                rows=[["Failed to load task data"]]
            )
    
    def create_summary_table(
        self,
        summary_stats: Dict[str, Any]
    ) -> TableData:
        """
        Create summary statistics table
        
        Args:
            summary_stats: Summary statistics dictionary
            
        Returns:
            Table data object
        """
        try:
            headers = ["Metric", "Value"]
            rows = []
            
            # Add obligation metrics
            if 'obligations' in summary_stats:
                obl_stats = summary_stats['obligations']
                rows.append(["Total Obligations", str(obl_stats.get('total_count', 0))])
                
                # Add category breakdown
                if 'by_category' in obl_stats:
                    for category, count in obl_stats['by_category'].items():
                        rows.append([f"  {category.title()} Obligations", str(count)])
                
                # Add severity breakdown
                if 'by_severity' in obl_stats:
                    for severity, count in obl_stats['by_severity'].items():
                        rows.append([f"  {severity.title()} Severity", str(count)])
            
            # Add task metrics
            if 'tasks' in summary_stats:
                task_stats = summary_stats['tasks']
                rows.append(["Total Tasks", str(task_stats.get('total_count', 0))])
                rows.append(["Completed Tasks", str(task_stats.get('completed_count', 0))])
                rows.append(["Overdue Tasks", str(task_stats.get('overdue_count', 0))])
            
            # Add compliance metrics
            if 'compliance_metrics' in summary_stats:
                metrics = summary_stats['compliance_metrics']
                completion_rate = metrics.get('completion_rate', 0)
                overdue_rate = metrics.get('overdue_rate', 0)
                
                rows.append(["Completion Rate", f"{completion_rate:.1f}%"])
                rows.append(["Overdue Rate", f"{overdue_rate:.1f}%"])
                rows.append(["Critical Obligations", str(metrics.get('critical_obligations', 0))])
                rows.append(["High Priority Tasks", str(metrics.get('high_priority_tasks', 0))])
            
            # Add document metrics
            if 'documents' in summary_stats:
                doc_stats = summary_stats['documents']
                rows.append(["Total Documents", str(doc_stats.get('total_count', 0))])
                total_size = doc_stats.get('total_size_mb', 0)
                rows.append(["Total Size (MB)", f"{total_size:.1f}"])
            
            return TableData(
                title="Summary Statistics",
                headers=headers,
                rows=rows
            )
            
        except Exception as e:
            logger.error(f"Failed to create summary table: {e}")
            return TableData(
                title="Summary Statistics",
                headers=["Error"],
                rows=[["Failed to load summary data"]]
            )
    
    def format_chart_for_markdown(self, chart: ChartData) -> str:
        """
        Format chart data for markdown representation
        
        Args:
            chart: Chart data object
            
        Returns:
            Markdown formatted chart representation
        """
        try:
            lines = [f"### {chart.title}", ""]
            
            if chart.chart_type in [ChartType.PIE, ChartType.DONUT]:
                # Format as a simple list for pie/donut charts
                for label, value in zip(chart.labels, chart.values):
                    percentage = (value / sum(chart.values)) * 100 if sum(chart.values) > 0 else 0
                    lines.append(f"- **{label}**: {value} ({percentage:.1f}%)")
            
            elif chart.chart_type == ChartType.BAR:
                # Format as a simple bar representation
                max_value = max(chart.values) if chart.values else 1
                for label, value in zip(chart.labels, chart.values):
                    bar_length = int((value / max_value) * 20)  # Scale to 20 chars
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    lines.append(f"- **{label}**: {bar} {value}")
            
            lines.append("")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to format chart for markdown: {e}")
            return f"### {chart.title}\n\nError formatting chart data\n\n"
    
    def format_table_for_markdown(self, table: TableData) -> str:
        """
        Format table data for markdown representation
        
        Args:
            table: Table data object
            
        Returns:
            Markdown formatted table
        """
        try:
            lines = [f"### {table.title}", ""]
            
            # Create header row
            header_row = "| " + " | ".join(table.headers) + " |"
            lines.append(header_row)
            
            # Create separator row
            separator = "| " + " | ".join(["---"] * len(table.headers)) + " |"
            lines.append(separator)
            
            # Add data rows
            for row in table.rows:
                data_row = "| " + " | ".join(str(cell) for cell in row) + " |"
                lines.append(data_row)
            
            # Add footer if present
            if table.footer:
                lines.append("")
                for footer_line in table.footer:
                    lines.append(f"*{footer_line}*")
            
            lines.append("")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to format table for markdown: {e}")
            return f"### {table.title}\n\nError formatting table data\n\n"
    
    def generate_report_template(
        self,
        report_type: ReportType,
        obligations: List[Obligation],
        tasks: List[Task],
        summary_stats: Dict[str, Any],
        date_range: Dict[str, datetime]
    ) -> str:
        """
        Generate a complete report template with charts and tables
        
        Args:
            report_type: Type of report to generate
            obligations: List of obligations
            tasks: List of tasks
            summary_stats: Summary statistics
            date_range: Report date range
            
        Returns:
            Complete markdown report template
        """
        try:
            # Create charts and tables
            obligation_charts = self.create_obligation_charts(obligations)
            task_charts = self.create_task_charts(tasks)
            
            obligation_table = self.create_obligation_table(obligations)
            task_table = self.create_task_table(tasks)
            summary_table = self.create_summary_table(summary_stats)
            
            # Build report content
            lines = []
            
            # Header
            date_str = f"{date_range['start_date'].strftime('%Y-%m-%d')} to {date_range['end_date'].strftime('%Y-%m-%d')}"
            lines.extend([
                f"# {report_type.value.replace('_', ' ').title()} Report",
                f"**Report Period**: {date_str}",
                f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                "",
                "---",
                ""
            ])
            
            # Summary section
            lines.extend([
                "## Executive Summary",
                "",
                self.format_table_for_markdown(summary_table)
            ])
            
            # Charts section
            if obligation_charts or task_charts:
                lines.extend([
                    "## Data Visualization",
                    ""
                ])
                
                for chart in obligation_charts:
                    lines.append(self.format_chart_for_markdown(chart))
                
                for chart in task_charts:
                    lines.append(self.format_chart_for_markdown(chart))
            
            # Tables section
            lines.extend([
                "## Detailed Data",
                "",
                self.format_table_for_markdown(obligation_table),
                self.format_table_for_markdown(task_table)
            ])
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to generate report template: {e}")
            return f"# Report Generation Error\n\nFailed to generate report: {e}"


# Convenience functions
def create_compliance_summary_template(
    obligations: List[Obligation],
    tasks: List[Task],
    summary_stats: Dict[str, Any],
    date_range: Dict[str, datetime]
) -> str:
    """Create a compliance summary report template"""
    engine = ReportTemplateEngine()
    return engine.generate_report_template(
        ReportType.COMPLIANCE_SUMMARY,
        obligations,
        tasks,
        summary_stats,
        date_range
    )


def create_audit_readiness_template(
    obligations: List[Obligation],
    tasks: List[Task],
    summary_stats: Dict[str, Any],
    date_range: Dict[str, datetime]
) -> str:
    """Create an audit readiness report template"""
    engine = ReportTemplateEngine()
    return engine.generate_report_template(
        ReportType.AUDIT_READINESS,
        obligations,
        tasks,
        summary_stats,
        date_range
    )