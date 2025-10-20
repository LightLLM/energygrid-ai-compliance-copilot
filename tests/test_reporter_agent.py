"""
Unit Tests for Reporter Agent
Tests report compilation logic, PDF generation functionality, and various report types and formats
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
import os
from io import BytesIO

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import shared models first
from src.shared.models import (
    Report, Obligation, Task, Document, ReportType, ProcessingStatus,
    ObligationCategory, ObligationSeverity, TaskStatus, TaskPriority, DeadlineType
)

# Import reporter modules
from src.reporter.report_generator import (
    ReportGenerator, ReportData, ReportTemplate, ReportGenerationError,
    generate_compliance_summary_report, generate_audit_readiness_report
)
from src.reporter.handler import lambda_handler, generate_report, send_completion_notification, send_failure_notification
from src.reporter.pdf_generator import (
    PDFReportGenerator, PDFGenerationError, create_compliance_report_pdf, create_simple_pdf
)
from src.reporter.report_templates import (
    ReportTemplateEngine, ChartData, TableData, ChartType
)


class TestReportCompilationLogic:
    """Test report compilation logic and data aggregation"""
    
    @pytest.fixture
    def mock_report_generator(self):
        """Mock report generator fixture"""
        # Create a mock that simulates the ReportGenerator behavior
        mock_generator = Mock()
        mock_generator.db_helper = Mock()
        mock_generator.bedrock_client = Mock()
        mock_generator.s3_client = Mock()
        return mock_generator
    
    @pytest.fixture
    def report_generator(self):
        """Real report generator fixture with mocked dependencies"""
        with patch('src.reporter.report_generator.get_db_helper') as mock_db_helper, \
             patch('src.reporter.report_generator.BedrockClient') as mock_bedrock:
            generator = ReportGenerator()
            generator.db_helper = mock_db_helper.return_value
            generator.bedrock_client = mock_bedrock.return_value
            return generator
    
    @pytest.fixture
    def sample_obligations(self):
        """Sample obligations for testing"""
        return [
            Obligation(
                obligation_id="obl_001",
                document_id="doc_001",
                description="Submit quarterly compliance reports within 30 days",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                applicable_entities=["utility_companies"],
                extracted_text="All utility companies SHALL submit quarterly compliance reports",
                confidence_score=0.95,
                created_timestamp=datetime(2024, 1, 15)
            ),
            Obligation(
                obligation_id="obl_002",
                document_id="doc_001",
                description="Monitor grid stability parameters continuously",
                category=ObligationCategory.MONITORING,
                severity=ObligationSeverity.CRITICAL,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=["grid_operators"],
                extracted_text="Utilities MUST continuously monitor grid stability",
                confidence_score=0.92,
                created_timestamp=datetime(2024, 1, 16)
            ),
            Obligation(
                obligation_id="obl_003",
                document_id="doc_002",
                description="Maintain financial reserves of 10% operating costs",
                category=ObligationCategory.FINANCIAL,
                severity=ObligationSeverity.MEDIUM,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=["all_entities"],
                extracted_text="SHALL maintain financial reserves equal to at least 10%",
                confidence_score=0.88,
                created_timestamp=datetime(2024, 1, 17)
            )
        ]
    
    @pytest.fixture
    def sample_tasks(self):
        """Sample tasks for testing"""
        return [
            Task(
                task_id="task_001",
                obligation_id="obl_001",
                title="Prepare Q1 compliance report",
                description="Compile operational data and safety metrics for Q1 report",
                priority=TaskPriority.HIGH,
                assigned_to="compliance_officer",
                due_date=datetime(2024, 4, 30),
                status=TaskStatus.COMPLETED,
                created_timestamp=datetime(2024, 3, 1),
                updated_timestamp=datetime(2024, 4, 25)
            ),
            Task(
                task_id="task_002",
                obligation_id="obl_002",
                title="Set up grid monitoring alerts",
                description="Configure automated alerts for grid stability deviations",
                priority=TaskPriority.CRITICAL,
                assigned_to="grid_operator",
                due_date=datetime(2024, 2, 15),
                status=TaskStatus.IN_PROGRESS,
                created_timestamp=datetime(2024, 1, 20),
                updated_timestamp=datetime(2024, 2, 10)
            ),
            Task(
                task_id="task_003",
                obligation_id="obl_003",
                title="Review financial reserves calculation",
                description="Verify current reserves meet 10% requirement",
                priority=TaskPriority.MEDIUM,
                assigned_to="financial_analyst",
                due_date=datetime(2024, 1, 10),
                status=TaskStatus.OVERDUE,
                created_timestamp=datetime(2024, 1, 5),
                updated_timestamp=datetime(2024, 1, 5)
            )
        ]
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing"""
        return [
            Document(
                document_id="doc_001",
                filename="energy_compliance_reg.pdf",
                upload_timestamp=datetime(2024, 1, 10),
                file_size=2048000,
                s3_key="documents/doc_001.pdf",
                processing_status=ProcessingStatus.COMPLETED,
                user_id="user_001",
                metadata={"regulation_type": "compliance"}
            ),
            Document(
                document_id="doc_002",
                filename="financial_requirements.pdf",
                upload_timestamp=datetime(2024, 1, 12),
                file_size=1536000,
                s3_key="documents/doc_002.pdf",
                processing_status=ProcessingStatus.COMPLETED,
                user_id="user_001",
                metadata={"regulation_type": "financial"}
            )
        ]
    
    def test_compile_report_data_success(self, report_generator, sample_obligations, sample_tasks, sample_documents):
        """Test successful report data compilation"""
        # Mock database helper methods
        report_generator.db_helper.list_obligations_by_category = Mock(return_value=sample_obligations)
        report_generator.db_helper.list_tasks_by_obligation = Mock(return_value=sample_tasks)
        report_generator.db_helper.get_document = Mock(side_effect=lambda doc_id: 
            next((doc for doc in sample_documents if doc.document_id == doc_id), None))
        
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        # Test compilation
        result = report_generator.compile_report_data(
            ReportType.COMPLIANCE_SUMMARY,
            date_range,
            {'category': 'reporting'}
        )
        
        # Verify result structure
        assert isinstance(result, ReportData)
        assert len(result.obligations) >= 0  # May be filtered
        assert len(result.tasks) >= 0
        assert len(result.documents) >= 0
        assert 'obligations' in result.summary_stats
        assert 'tasks' in result.summary_stats
        assert 'compliance_metrics' in result.summary_stats
        assert result.date_range == date_range
    
    def test_compile_report_data_with_filters(self, report_generator, sample_obligations):
        """Test report data compilation with various filters"""
        report_generator.db_helper.list_obligations_by_category = Mock(return_value=sample_obligations)
        report_generator.db_helper.list_tasks_by_obligation = Mock(return_value=[])
        
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        # Test with category filter
        filters = {'category': 'reporting', 'severity': 'high'}
        result = report_generator.compile_report_data(
            ReportType.COMPLIANCE_SUMMARY,
            date_range,
            filters
        )
        
        assert isinstance(result, ReportData)
        # Verify database helper was called with correct parameters
        report_generator.db_helper.list_obligations_by_category.assert_called_with(
            ObligationCategory.REPORTING, ObligationSeverity.HIGH
        )
    
    def test_compile_report_data_empty_results(self, report_generator):
        """Test report data compilation with no data"""
        report_generator.db_helper.list_obligations_by_category = Mock(return_value=[])
        report_generator.db_helper.list_tasks_by_obligation = Mock(return_value=[])
        
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        result = report_generator.compile_report_data(
            ReportType.COMPLIANCE_SUMMARY,
            date_range
        )
        
        assert isinstance(result, ReportData)
        assert len(result.obligations) == 0
        assert len(result.tasks) == 0
        assert len(result.documents) == 0
        assert result.summary_stats['obligations']['total_count'] == 0
        assert result.summary_stats['tasks']['total_count'] == 0
    
    def test_generate_summary_stats(self, report_generator, sample_obligations, sample_tasks, sample_documents):
        """Test summary statistics generation"""
        stats = report_generator._generate_summary_stats(sample_obligations, sample_tasks, sample_documents)
        
        # Verify obligation stats
        assert stats['obligations']['total_count'] == 3
        assert 'reporting' in stats['obligations']['by_category']
        assert 'monitoring' in stats['obligations']['by_category']
        assert 'financial' in stats['obligations']['by_category']
        assert stats['obligations']['by_severity']['critical'] == 1
        assert stats['obligations']['by_severity']['high'] == 1
        assert stats['obligations']['by_severity']['medium'] == 1
        
        # Verify task stats
        assert stats['tasks']['total_count'] == 3
        assert stats['tasks']['completed_count'] == 1
        assert stats['tasks']['overdue_count'] == 1
        assert 'completed' in stats['tasks']['by_status']
        assert 'in_progress' in stats['tasks']['by_status']
        assert 'overdue' in stats['tasks']['by_status']
        
        # Verify compliance metrics
        assert stats['compliance_metrics']['completion_rate'] == pytest.approx(33.33, rel=1e-2)
        assert stats['compliance_metrics']['overdue_rate'] == pytest.approx(33.33, rel=1e-2)
        assert stats['compliance_metrics']['critical_obligations'] == 1
        
        # Verify document stats
        assert stats['documents']['total_count'] == 2
        assert stats['documents']['total_size_mb'] > 0
    
    def test_compilation_error_handling(self, report_generator):
        """Test error handling during data compilation"""
        # Mock database error
        report_generator.db_helper.list_obligations_by_category = Mock(
            side_effect=Exception("Database connection failed")
        )
        
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        with pytest.raises(ReportGenerationError) as exc_info:
            report_generator.compile_report_data(ReportType.COMPLIANCE_SUMMARY, date_range)
        
        assert "Data compilation failed" in str(exc_info.value)


class TestReportContentGeneration:
    """Test report content generation using Claude Sonnet"""
    
    @pytest.fixture
    def report_generator(self):
        """Report generator fixture with mocked Bedrock client"""
        with patch('src.reporter.report_generator.get_db_helper'), \
             patch('src.reporter.report_generator.BedrockClient') as mock_bedrock:
            generator = ReportGenerator()
            generator.bedrock_client = mock_bedrock.return_value
            return generator
    
    @pytest.fixture
    def sample_report_data(self):
        """Sample report data for testing"""
        obligations = [
            Obligation(
                obligation_id="obl_001",
                document_id="doc_001",
                description="Submit quarterly reports",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                applicable_entities=["utilities"],
                extracted_text="Submit reports quarterly",
                confidence_score=0.95,
                created_timestamp=datetime(2024, 1, 15)
            )
        ]
        
        tasks = [
            Task(
                task_id="task_001",
                obligation_id="obl_001",
                title="Prepare Q1 report",
                description="Compile Q1 data",
                priority=TaskPriority.HIGH,
                assigned_to="officer",
                due_date=datetime(2024, 4, 30),
                status=TaskStatus.COMPLETED,
                created_timestamp=datetime(2024, 3, 1),
                updated_timestamp=datetime(2024, 4, 25)
            )
        ]
        
        summary_stats = {
            'obligations': {'total_count': 1, 'by_category': {'reporting': 1}},
            'tasks': {'total_count': 1, 'completed_count': 1},
            'compliance_metrics': {'completion_rate': 100.0}
        }
        
        return ReportData(
            obligations=obligations,
            tasks=tasks,
            documents=[],
            summary_stats=summary_stats,
            date_range={
                'start_date': datetime(2024, 1, 1),
                'end_date': datetime(2024, 12, 31)
            }
        )
    
    def test_generate_report_content_success(self, report_generator, sample_report_data):
        """Test successful report content generation"""
        # Mock Claude Sonnet response
        mock_content = """# Compliance Summary Report

## Executive Summary
This report provides an overview of compliance status for the period January 1, 2024 to December 31, 2024.

## Data Overview
- Total Obligations: 1
- Total Tasks: 1
- Completion Rate: 100%

## Compliance Status Analysis
All reporting obligations are being tracked and managed effectively.

## Recommendations
Continue current compliance monitoring practices."""
        
        report_generator.bedrock_client._call_claude_with_retry = Mock(return_value=mock_content)
        
        # Test content generation
        result = report_generator.generate_report_content(
            sample_report_data,
            ReportType.COMPLIANCE_SUMMARY,
            "Test Compliance Summary Report"
        )
        
        assert isinstance(result, str)
        assert "Compliance Summary Report" in result
        assert "Executive Summary" in result
        assert "Compliance Status Analysis" in result
        
        # Verify Claude was called with proper prompt
        report_generator.bedrock_client._call_claude_with_retry.assert_called_once()
        call_args = report_generator.bedrock_client._call_claude_with_retry.call_args[0][0]
        assert "compliance analyst" in call_args.lower()
        assert "Test Compliance Summary Report" in call_args
    
    def test_generate_report_content_different_types(self, report_generator, sample_report_data):
        """Test content generation for different report types"""
        mock_content = "# Audit Readiness Report\n\nAudit readiness analysis..."
        report_generator.bedrock_client._call_claude_with_retry = Mock(return_value=mock_content)
        
        # Test audit readiness report
        result = report_generator.generate_report_content(
            sample_report_data,
            ReportType.AUDIT_READINESS,
            "Audit Readiness Report"
        )
        
        assert "Audit Readiness Report" in result
        
        # Verify template was used correctly
        call_args = report_generator.bedrock_client._call_claude_with_retry.call_args[0][0]
        assert "audit readiness" in call_args.lower()
    
    def test_generate_report_content_bedrock_error(self, report_generator, sample_report_data):
        """Test error handling when Bedrock fails"""
        # Mock Bedrock error
        report_generator.bedrock_client._call_claude_with_retry = Mock(
            side_effect=Exception("Bedrock API error")
        )
        
        with pytest.raises(ReportGenerationError) as exc_info:
            report_generator.generate_report_content(
                sample_report_data,
                ReportType.COMPLIANCE_SUMMARY,
                "Test Report"
            )
        
        assert "Content generation failed" in str(exc_info.value)
    
    def test_build_report_prompt(self, report_generator, sample_report_data):
        """Test report prompt building"""
        template = ReportTemplate(
            title="Test Report",
            sections=["summary", "analysis"],
            include_charts=True,
            include_tables=True
        )
        
        prompt = report_generator._build_report_prompt(
            sample_report_data,
            template,
            "Test Report Title"
        )
        
        assert "compliance analyst" in prompt
        assert "Test Report Title" in prompt
        assert "Total Obligations: 1" in prompt
        assert "Total Tasks: 1" in prompt
        assert "summary, analysis" in prompt
    
    def test_summarize_obligations_and_tasks(self, report_generator):
        """Test obligation and task summarization for prompts"""
        obligations = [
            Obligation(
                obligation_id="obl_001",
                document_id="doc_001",
                description="Test obligation description that is quite long and should be truncated",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.CRITICAL,
                deadline_type=DeadlineType.RECURRING,
                applicable_entities=["test"],
                extracted_text="test",
                confidence_score=0.95,
                created_timestamp=datetime(2024, 1, 15)
            )
        ]
        
        # Test obligation summarization
        summary = report_generator._summarize_obligations(obligations)
        assert "Total Obligations: 1" in summary
        assert "Reporting: 1" in summary
        assert "Critical: 1" in summary
        assert "Test obligation description" in summary
        
        # Test empty obligations
        empty_summary = report_generator._summarize_obligations([])
        assert "No obligations found" in empty_summary


class TestPDFGeneration:
    """Test PDF generation functionality"""
    
    @pytest.fixture
    def pdf_generator(self):
        """PDF generator fixture"""
        try:
            return PDFReportGenerator()
        except PDFGenerationError:
            pytest.skip("ReportLab not available")
    
    @pytest.fixture
    def sample_content_sections(self):
        """Sample content sections for PDF generation"""
        return [
            {
                'title': 'Executive Summary',
                'content': 'This report provides an overview of compliance status.\n\nKey findings include improved completion rates.'
            },
            {
                'title': 'Detailed Analysis',
                'content': 'Analysis of compliance obligations shows:\n\n• High completion rate\n• Few overdue tasks\n• Strong monitoring practices'
            }
        ]
    
    @pytest.fixture
    def sample_charts(self):
        """Sample charts for PDF generation"""
        return [
            ChartData(
                title="Obligations by Category",
                chart_type=ChartType.PIE,
                labels=["Reporting", "Monitoring", "Financial"],
                values=[5, 3, 2],
                colors=["#007bff", "#28a745", "#dc3545"]
            ),
            ChartData(
                title="Task Status",
                chart_type=ChartType.BAR,
                labels=["Completed", "In Progress", "Overdue"],
                values=[8, 3, 1]
            )
        ]
    
    @pytest.fixture
    def sample_tables(self):
        """Sample tables for PDF generation"""
        return [
            TableData(
                title="Summary Statistics",
                headers=["Metric", "Value"],
                rows=[
                    ["Total Obligations", "10"],
                    ["Completed Tasks", "8"],
                    ["Completion Rate", "80%"]
                ]
            )
        ]
    
    @patch('src.reporter.pdf_generator.REPORTLAB_AVAILABLE', True)
    def test_generate_pdf_report_success(self, pdf_generator, sample_content_sections, sample_charts, sample_tables):
        """Test successful PDF report generation"""
        metadata = {
            'date_range': '2024-01-01 to 2024-12-31',
            'generated_at': '2024-01-15 10:30:00',
            'generated_by': 'test_user'
        }
        
        # Mock ReportLab components
        with patch('src.reporter.pdf_generator.SimpleDocTemplate') as mock_doc, \
             patch('src.reporter.pdf_generator.Paragraph') as mock_paragraph, \
             patch('src.reporter.pdf_generator.Table') as mock_table:
            
            mock_doc_instance = Mock()
            mock_doc.return_value = mock_doc_instance
            
            result = pdf_generator.generate_pdf_report(
                title="Test Compliance Report",
                content_sections=sample_content_sections,
                charts=sample_charts,
                tables=sample_tables,
                metadata=metadata
            )
            
            assert isinstance(result, bytes)
            mock_doc_instance.build.assert_called_once()
    
    def test_create_title_page(self, pdf_generator):
        """Test title page creation"""
        metadata = {
            'date_range': '2024-01-01 to 2024-12-31',
            'generated_at': '2024-01-15 10:30:00',
            'generated_by': 'test_user'
        }
        
        with patch('src.reporter.pdf_generator.Paragraph') as mock_paragraph, \
             patch('src.reporter.pdf_generator.Spacer') as mock_spacer, \
             patch('src.reporter.pdf_generator.PageBreak') as mock_pagebreak:
            
            elements = pdf_generator._create_title_page("Test Report", metadata)
            
            assert len(elements) > 0
            # Verify title, spacers, and page break were created
            assert mock_paragraph.call_count >= 3  # Title + metadata elements
            assert mock_spacer.call_count >= 2
            assert mock_pagebreak.call_count == 1
    
    def test_create_chart_pie(self, pdf_generator):
        """Test pie chart creation"""
        chart_data = ChartData(
            title="Test Pie Chart",
            chart_type=ChartType.PIE,
            labels=["A", "B", "C"],
            values=[30, 40, 30],
            colors=["#ff0000", "#00ff00", "#0000ff"]
        )
        
        with patch('src.reporter.pdf_generator.Drawing') as mock_drawing, \
             patch('src.reporter.pdf_generator.Pie') as mock_pie, \
             patch('src.reporter.pdf_generator.Legend') as mock_legend:
            
            mock_drawing_instance = Mock()
            mock_drawing.return_value = mock_drawing_instance
            
            result = pdf_generator._create_pie_chart(chart_data)
            
            assert result == mock_drawing_instance
            mock_drawing_instance.add.assert_called()  # Should add pie and legend
    
    def test_create_table(self, pdf_generator):
        """Test table creation"""
        table_data = TableData(
            title="Test Table",
            headers=["Column 1", "Column 2"],
            rows=[["Row 1 Col 1", "Row 1 Col 2"], ["Row 2 Col 1", "Row 2 Col 2"]],
            footer=["Table footer note"]
        )
        
        with patch('src.reporter.pdf_generator.Paragraph') as mock_paragraph, \
             patch('src.reporter.pdf_generator.Table') as mock_table, \
             patch('src.reporter.pdf_generator.KeepTogether') as mock_keep:
            
            elements = pdf_generator._create_table(table_data)
            
            assert len(elements) > 0
            mock_paragraph.assert_called()  # Title and footer
            mock_table.assert_called_once()
            mock_keep.assert_called_once()
    
    def test_pdf_generation_error_handling(self, pdf_generator, sample_content_sections):
        """Test PDF generation error handling"""
        with patch('src.reporter.pdf_generator.SimpleDocTemplate', side_effect=Exception("PDF error")):
            with pytest.raises(PDFGenerationError) as exc_info:
                pdf_generator.generate_pdf_report(
                    title="Test Report",
                    content_sections=sample_content_sections
                )
            
            assert "PDF generation failed" in str(exc_info.value)
    
    def test_create_compliance_report_pdf(self, sample_charts, sample_tables):
        """Test high-level PDF creation function"""
        content = """# Test Compliance Report

## Executive Summary
This is a test report.

## Analysis
Key findings and analysis."""
        
        metadata = {'generated_at': '2024-01-15'}
        
        with patch('src.reporter.pdf_generator.PDFReportGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            mock_generator.generate_pdf_report.return_value = b"PDF content"
            
            result = create_compliance_report_pdf(
                title="Test Report",
                report_content=content,
                charts=sample_charts,
                tables=sample_tables,
                metadata=metadata
            )
            
            assert result == b"PDF content"
            mock_generator.generate_pdf_report.assert_called_once()
    
    def test_simple_pdf_fallback(self):
        """Test simple PDF fallback when ReportLab is not available"""
        content = "Test report content"
        title = "Test Report"
        
        result = create_simple_pdf(content, title)
        
        assert isinstance(result, bytes)
        assert b"%PDF" in result
        assert title.encode() in result


class TestReportTemplates:
    """Test report templates and formatting utilities"""
    
    @pytest.fixture
    def template_engine(self):
        """Template engine fixture"""
        return ReportTemplateEngine()
    
    @pytest.fixture
    def sample_obligations(self):
        """Sample obligations for template testing"""
        return [
            Obligation(
                obligation_id="obl_001",
                document_id="doc_001",
                description="Submit quarterly reports",
                category=ObligationCategory.REPORTING,
                severity=ObligationSeverity.HIGH,
                deadline_type=DeadlineType.RECURRING,
                applicable_entities=["utilities"],
                extracted_text="Submit reports",
                confidence_score=0.95,
                created_timestamp=datetime(2024, 1, 15)
            ),
            Obligation(
                obligation_id="obl_002",
                document_id="doc_001",
                description="Monitor grid stability",
                category=ObligationCategory.MONITORING,
                severity=ObligationSeverity.CRITICAL,
                deadline_type=DeadlineType.ONGOING,
                applicable_entities=["operators"],
                extracted_text="Monitor stability",
                confidence_score=0.92,
                created_timestamp=datetime(2024, 1, 16)
            )
        ]
    
    def test_create_obligation_charts(self, template_engine, sample_obligations):
        """Test obligation chart creation"""
        charts = template_engine.create_obligation_charts(sample_obligations)
        
        assert len(charts) >= 2  # Should have category and severity charts
        
        # Find category chart
        category_chart = next((c for c in charts if "Category" in c.title), None)
        assert category_chart is not None
        assert category_chart.chart_type == ChartType.PIE
        assert "Reporting" in category_chart.labels
        assert "Monitoring" in category_chart.labels
        
        # Find severity chart
        severity_chart = next((c for c in charts if "Severity" in c.title), None)
        assert severity_chart is not None
        assert severity_chart.chart_type == ChartType.BAR
        assert "High" in severity_chart.labels
        assert "Critical" in severity_chart.labels
    
    def test_create_task_charts(self, template_engine):
        """Test task chart creation"""
        tasks = [
            Task(
                task_id="task_001",
                obligation_id="obl_001",
                title="Test task 1",
                description="Description",
                priority=TaskPriority.HIGH,
                assigned_to="user1",
                due_date=datetime(2024, 4, 30),
                status=TaskStatus.COMPLETED,
                created_timestamp=datetime(2024, 3, 1),
                updated_timestamp=datetime(2024, 4, 25)
            ),
            Task(
                task_id="task_002",
                obligation_id="obl_002",
                title="Test task 2",
                description="Description",
                priority=TaskPriority.MEDIUM,
                assigned_to="user2",
                due_date=datetime(2024, 5, 15),
                status=TaskStatus.IN_PROGRESS,
                created_timestamp=datetime(2024, 3, 5),
                updated_timestamp=datetime(2024, 4, 20)
            )
        ]
        
        charts = template_engine.create_task_charts(tasks)
        
        assert len(charts) >= 2  # Should have status and priority charts
        
        # Find status chart
        status_chart = next((c for c in charts if "Status" in c.title), None)
        assert status_chart is not None
        assert "Completed" in status_chart.labels
        assert "In Progress" in status_chart.labels
    
    def test_create_obligation_table(self, template_engine, sample_obligations):
        """Test obligation table creation"""
        table = template_engine.create_obligation_table(sample_obligations, limit=10)
        
        assert table.title == "Compliance Obligations"
        assert len(table.headers) == 7  # ID, Description, Category, Severity, Deadline Type, Confidence, Created
        assert len(table.rows) == 2  # Two sample obligations
        
        # Verify data content
        first_row = table.rows[0]
        assert len(first_row[0]) == 8  # Last 8 chars of ID
        assert "Submit quarterly reports" in first_row[1]
        assert "Reporting" in first_row[2]
        assert "High" in first_row[3]
    
    def test_create_task_table(self, template_engine):
        """Test task table creation"""
        tasks = [
            Task(
                task_id="task_001",
                obligation_id="obl_001",
                title="Test task with a very long title that should be truncated",
                description="Description",
                priority=TaskPriority.HIGH,
                assigned_to="test_user_with_long_name",
                due_date=datetime(2024, 4, 30),
                status=TaskStatus.COMPLETED,
                created_timestamp=datetime(2024, 3, 1),
                updated_timestamp=datetime(2024, 4, 25)
            )
        ]
        
        table = template_engine.create_task_table(tasks, limit=10)
        
        assert table.title == "Audit Tasks"
        assert len(table.headers) == 7  # ID, Title, Priority, Status, Assigned To, Due Date, Created
        assert len(table.rows) == 1
        
        # Verify data truncation
        first_row = table.rows[0]
        assert len(first_row[1]) <= 43  # Title should be truncated (40 + "...")
        assert len(first_row[4]) <= 10  # Assigned to should be truncated
    
    def test_create_summary_table(self, template_engine):
        """Test summary statistics table creation"""
        summary_stats = {
            'obligations': {
                'total_count': 5,
                'by_category': {'reporting': 3, 'monitoring': 2},
                'by_severity': {'critical': 1, 'high': 2, 'medium': 2}
            },
            'tasks': {
                'total_count': 8,
                'completed_count': 6,
                'overdue_count': 1
            },
            'compliance_metrics': {
                'completion_rate': 75.0,
                'overdue_rate': 12.5,
                'critical_obligations': 1,
                'high_priority_tasks': 3
            },
            'documents': {
                'total_count': 3,
                'total_size_mb': 15.5
            }
        }
        
        table = template_engine.create_summary_table(summary_stats)
        
        assert table.title == "Summary Statistics"
        assert len(table.headers) == 2  # Metric, Value
        assert len(table.rows) > 10  # Should have multiple metrics
        
        # Verify specific metrics are present
        metric_names = [row[0] for row in table.rows]
        assert "Total Obligations" in metric_names
        assert "Completion Rate" in metric_names
        assert "Critical Obligations" in metric_names
    
    def test_format_chart_for_markdown(self, template_engine):
        """Test chart formatting for markdown"""
        chart = ChartData(
            title="Test Chart",
            chart_type=ChartType.PIE,
            labels=["A", "B", "C"],
            values=[30, 40, 30]
        )
        
        result = template_engine.format_chart_for_markdown(chart)
        
        assert "### Test Chart" in result
        assert "**A**: 30 (30.0%)" in result
        assert "**B**: 40 (40.0%)" in result
        assert "**C**: 30 (30.0%)" in result
    
    def test_format_table_for_markdown(self, template_engine):
        """Test table formatting for markdown"""
        table = TableData(
            title="Test Table",
            headers=["Column 1", "Column 2"],
            rows=[["Row 1 A", "Row 1 B"], ["Row 2 A", "Row 2 B"]],
            footer=["Table footer"]
        )
        
        result = template_engine.format_table_for_markdown(table)
        
        assert "### Test Table" in result
        assert "| Column 1 | Column 2 |" in result
        assert "| --- | --- |" in result
        assert "| Row 1 A | Row 1 B |" in result
        assert "| Row 2 A | Row 2 B |" in result
        assert "*Table footer*" in result
    
    def test_generate_report_template(self, template_engine, sample_obligations):
        """Test complete report template generation"""
        tasks = [
            Task(
                task_id="task_001",
                obligation_id="obl_001",
                title="Test task",
                description="Description",
                priority=TaskPriority.HIGH,
                assigned_to="user1",
                due_date=datetime(2024, 4, 30),
                status=TaskStatus.COMPLETED,
                created_timestamp=datetime(2024, 3, 1),
                updated_timestamp=datetime(2024, 4, 25)
            )
        ]
        
        summary_stats = {
            'obligations': {'total_count': 2},
            'tasks': {'total_count': 1, 'completed_count': 1},
            'compliance_metrics': {'completion_rate': 100.0}
        }
        
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        result = template_engine.generate_report_template(
            ReportType.COMPLIANCE_SUMMARY,
            sample_obligations,
            tasks,
            summary_stats,
            date_range
        )
        
        assert "# Compliance Summary Report" in result
        assert "## Executive Summary" in result
        assert "## Data Visualization" in result
        assert "## Detailed Data" in result
        assert "2024-01-01 to 2024-12-31" in result


class TestReporterAgentHandler:
    """Test Reporter Agent Lambda handler"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for handler testing"""
        with patch('src.reporter.handler.get_config') as mock_config, \
             patch('src.reporter.handler.get_db_helper') as mock_db, \
             patch('src.reporter.handler.ReportGenerator') as mock_generator, \
             patch('src.reporter.handler.sns_client') as mock_sns:
            
            # Configure mocks
            mock_config.return_value.aws_region = 'us-east-1'
            mock_config.return_value.s3_bucket_name = 'test-bucket'
            mock_config.return_value.sns_topic_arn = 'arn:aws:sns:us-east-1:123456789012:test-topic'
            
            yield {
                'config': mock_config,
                'db_helper': mock_db,
                'generator': mock_generator,
                'sns': mock_sns
            }
    
    def test_lambda_handler_sqs_event(self, mock_dependencies):
        """Test Lambda handler with SQS event"""
        sqs_event = {
            'Records': [
                {
                    'body': json.dumps({
                        'report_id': 'report_001',
                        'report_type': 'compliance_summary',
                        'date_range': {
                            'start_date': '2024-01-01T00:00:00',
                            'end_date': '2024-12-31T23:59:59'
                        },
                        'generated_by': 'test_user'
                    })
                }
            ]
        }
        
        # Mock successful report generation
        with patch('src.reporter.handler.generate_report', return_value=True):
            result = lambda_handler(sqs_event, Mock())
        
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['processed_count'] == 1
        assert response_body['failed_count'] == 0
    
    def test_lambda_handler_direct_event(self, mock_dependencies):
        """Test Lambda handler with direct invocation"""
        direct_event = {
            'report_type': 'compliance_summary',
            'date_range': {
                'start_date': '2024-01-01T00:00:00',
                'end_date': '2024-12-31T23:59:59'
            },
            'generated_by': 'test_user',
            'title': 'Test Report'
        }
        
        # Mock report generator validation and creation
        mock_generator = mock_dependencies['generator'].return_value
        mock_generator.validate_report_request.return_value = (True, "")
        
        mock_db = mock_dependencies['db_helper'].return_value
        mock_db.create_report.return_value = True
        
        with patch('src.reporter.handler.generate_report', return_value=True):
            result = lambda_handler(direct_event, Mock())
        
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert 'report_id' in response_body
        assert response_body['message'] == 'Report generated successfully'
    
    def test_lambda_handler_validation_error(self, mock_dependencies):
        """Test Lambda handler with validation error"""
        invalid_event = {
            'report_type': 'invalid_type',
            'date_range': {
                'start_date': '2024-01-01T00:00:00',
                'end_date': '2024-12-31T23:59:59'
            },
            'generated_by': 'test_user'
        }
        
        # Mock validation failure
        mock_generator = mock_dependencies['generator'].return_value
        mock_generator.validate_report_request.return_value = (False, "Invalid report type")
        
        result = lambda_handler(invalid_event, Mock())
        
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Invalid report request'
        assert response_body['message'] == 'Invalid report type'
    
    def test_lambda_handler_missing_parameters(self, mock_dependencies):
        """Test Lambda handler with missing required parameters"""
        incomplete_event = {
            'report_type': 'compliance_summary'
            # Missing date_range and generated_by
        }
        
        result = lambda_handler(incomplete_event, Mock())
        
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Missing required parameters'
        assert 'date_range' in response_body['required']
        assert 'generated_by' in response_body['required']
    
    def test_generate_report_success(self, mock_dependencies):
        """Test successful report generation"""
        mock_generator = Mock()
        mock_generator.compile_report_data.return_value = Mock()
        mock_generator.generate_report_content.return_value = "Report content"
        mock_generator.create_pdf_report.return_value = "reports/test.pdf"
        
        mock_db = Mock()
        mock_config = Mock()
        mock_config.s3_bucket_name = 'test-bucket'
        
        with patch('src.reporter.handler.send_completion_notification'):
            result = generate_report(
                report_id='test_report',
                report_type=ReportType.COMPLIANCE_SUMMARY,
                date_range={'start_date': datetime(2024, 1, 1), 'end_date': datetime(2024, 12, 31)},
                generated_by='test_user',
                filters={},
                report_generator=mock_generator,
                db_helper=mock_db,
                config=mock_config
            )
        
        assert result is True
        mock_db.update_report_status.assert_called()
        mock_generator.compile_report_data.assert_called_once()
        mock_generator.generate_report_content.assert_called_once()
        mock_generator.create_pdf_report.assert_called_once()
    
    def test_generate_report_failure(self, mock_dependencies):
        """Test report generation failure"""
        mock_generator = Mock()
        mock_generator.compile_report_data.side_effect = ReportGenerationError("Data compilation failed")
        
        mock_db = Mock()
        mock_config = Mock()
        
        with patch('src.reporter.handler.send_failure_notification'):
            result = generate_report(
                report_id='test_report',
                report_type=ReportType.COMPLIANCE_SUMMARY,
                date_range={'start_date': datetime(2024, 1, 1), 'end_date': datetime(2024, 12, 31)},
                generated_by='test_user',
                filters={},
                report_generator=mock_generator,
                db_helper=mock_db,
                config=mock_config
            )
        
        assert result is False
        mock_db.update_report_status.assert_called_with('test_report', ProcessingStatus.FAILED)
    
    def test_send_completion_notification(self, mock_dependencies):
        """Test completion notification sending"""
        mock_config = Mock()
        mock_config.sns_topic_arn = 'arn:aws:sns:us-east-1:123456789012:test-topic'
        
        send_completion_notification(
            report_id='test_report',
            report_type=ReportType.COMPLIANCE_SUMMARY,
            generated_by='test_user',
            s3_key='reports/test.pdf',
            config=mock_config
        )
        
        mock_dependencies['sns'].publish.assert_called_once()
        call_args = mock_dependencies['sns'].publish.call_args
        assert call_args[1]['TopicArn'] == mock_config.sns_topic_arn
        
        message = json.loads(call_args[1]['Message'])
        assert message['event_type'] == 'report_completed'
        assert message['report_id'] == 'test_report'
        assert message['s3_key'] == 'reports/test.pdf'
    
    def test_send_failure_notification(self, mock_dependencies):
        """Test failure notification sending"""
        mock_config = Mock()
        mock_config.sns_topic_arn = 'arn:aws:sns:us-east-1:123456789012:test-topic'
        
        send_failure_notification(
            report_id='test_report',
            report_type=ReportType.COMPLIANCE_SUMMARY,
            generated_by='test_user',
            error_message='Test error',
            config=mock_config
        )
        
        mock_dependencies['sns'].publish.assert_called_once()
        call_args = mock_dependencies['sns'].publish.call_args
        
        message = json.loads(call_args[1]['Message'])
        assert message['event_type'] == 'report_failed'
        assert message['error_message'] == 'Test error'


class TestReportValidation:
    """Test report request validation"""
    
    @pytest.fixture
    def report_generator(self):
        """Report generator fixture"""
        with patch('src.reporter.report_generator.get_db_helper'), \
             patch('src.reporter.report_generator.BedrockClient'):
            return ReportGenerator()
    
    def test_validate_report_request_success(self, report_generator):
        """Test successful report request validation"""
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        is_valid, error_msg = report_generator.validate_report_request(
            'compliance_summary',
            date_range,
            'test_user'
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_report_request_invalid_type(self, report_generator):
        """Test validation with invalid report type"""
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        is_valid, error_msg = report_generator.validate_report_request(
            'invalid_type',
            date_range,
            'test_user'
        )
        
        assert is_valid is False
        assert "Invalid report type" in error_msg
    
    def test_validate_report_request_invalid_date_range(self, report_generator):
        """Test validation with invalid date range"""
        # Test with start_date after end_date
        date_range = {
            'start_date': datetime(2024, 12, 31),
            'end_date': datetime(2024, 1, 1)
        }
        
        is_valid, error_msg = report_generator.validate_report_request(
            'compliance_summary',
            date_range,
            'test_user'
        )
        
        assert is_valid is False
        assert "start_date must be before end_date" in error_msg
    
    def test_validate_report_request_date_range_too_large(self, report_generator):
        """Test validation with date range exceeding maximum"""
        date_range = {
            'start_date': datetime(2023, 1, 1),
            'end_date': datetime(2025, 1, 1)  # More than 365 days
        }
        
        is_valid, error_msg = report_generator.validate_report_request(
            'compliance_summary',
            date_range,
            'test_user'
        )
        
        assert is_valid is False
        assert "cannot exceed 365 days" in error_msg
    
    def test_validate_report_request_missing_user(self, report_generator):
        """Test validation with missing user ID"""
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        is_valid, error_msg = report_generator.validate_report_request(
            'compliance_summary',
            date_range,
            ''
        )
        
        assert is_valid is False
        assert "User ID is required" in error_msg


class TestConvenienceFunctions:
    """Test convenience functions for report generation"""
    
    def test_generate_compliance_summary_report(self):
        """Test compliance summary report generation function"""
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        with patch('src.reporter.report_generator.ReportGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            
            mock_data = Mock()
            mock_generator.compile_report_data.return_value = mock_data
            mock_generator.generate_report_content.return_value = "Report content"
            
            content, data = generate_compliance_summary_report(
                date_range=date_range,
                user_id='test_user'
            )
            
            assert content == "Report content"
            assert data == mock_data
            mock_generator.compile_report_data.assert_called_with(
                ReportType.COMPLIANCE_SUMMARY, date_range, None
            )
    
    def test_generate_audit_readiness_report(self):
        """Test audit readiness report generation function"""
        date_range = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 12, 31)
        }
        
        filters = {'category': 'reporting'}
        
        with patch('src.reporter.report_generator.ReportGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator_class.return_value = mock_generator
            
            mock_data = Mock()
            mock_generator.compile_report_data.return_value = mock_data
            mock_generator.generate_report_content.return_value = "Audit report content"
            
            content, data = generate_audit_readiness_report(
                date_range=date_range,
                user_id='test_user',
                filters=filters
            )
            
            assert content == "Audit report content"
            assert data == mock_data
            mock_generator.compile_report_data.assert_called_with(
                ReportType.AUDIT_READINESS, date_range, filters
            )