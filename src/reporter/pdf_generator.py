"""
PDF Generation Utilities for EnergyGrid.AI Compliance Reports
Creates professional PDF reports with charts and tables using ReportLab
"""

import io
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import base64

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from .report_templates import ChartData, TableData, ChartType
    from ..shared.models import ReportType
except ImportError:
    from report_templates import ChartData, TableData, ChartType
    from src.shared.models import ReportType

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors"""
    pass


class PDFReportGenerator:
    """
    Professional PDF report generator using ReportLab
    Creates formatted compliance reports with charts and tables
    """
    
    def __init__(self, page_size=A4):
        """
        Initialize PDF generator
        
        Args:
            page_size: Page size for the PDF (default: A4)
        """
        if not REPORTLAB_AVAILABLE:
            raise PDFGenerationError("ReportLab is not available. Install with: pip install reportlab")
        
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Color scheme
        self.colors = {
            'primary': colors.Color(0.2, 0.4, 0.8),      # Blue
            'secondary': colors.Color(0.8, 0.4, 0.2),    # Orange
            'success': colors.Color(0.2, 0.8, 0.4),      # Green
            'warning': colors.Color(1.0, 0.8, 0.2),      # Yellow
            'danger': colors.Color(0.8, 0.2, 0.2),       # Red
            'light_gray': colors.Color(0.95, 0.95, 0.95),
            'dark_gray': colors.Color(0.3, 0.3, 0.3)
        }
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.Color(0.2, 0.4, 0.8),
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.Color(0.3, 0.3, 0.3),
            alignment=TA_CENTER
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.Color(0.2, 0.4, 0.8),
            borderWidth=1,
            borderColor=colors.Color(0.2, 0.4, 0.8),
            borderPadding=5
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.Color(0.4, 0.4, 0.4)
        ))
        
        # Body text with justify
        self.styles.add(ParagraphStyle(
            name='BodyJustify',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            spaceBefore=6,
            spaceAfter=6
        ))
        
        # Bullet point style
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))
    
    def generate_pdf_report(
        self,
        title: str,
        content_sections: List[Dict[str, Any]],
        charts: Optional[List[ChartData]] = None,
        tables: Optional[List[TableData]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate a complete PDF report
        
        Args:
            title: Report title
            content_sections: List of content sections
            charts: Optional list of charts to include
            tables: Optional list of tables to include
            metadata: Optional metadata for the report
            
        Returns:
            PDF content as bytes
            
        Raises:
            PDFGenerationError: If PDF generation fails
        """
        logger.info(f"Generating PDF report: {title}")
        
        try:
            # Create PDF buffer
            buffer = io.BytesIO()
            
            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=self.page_size,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build story (content elements)
            story = []
            
            # Add title page
            story.extend(self._create_title_page(title, metadata))
            
            # Add table of contents
            story.extend(self._create_table_of_contents(content_sections))
            
            # Add content sections
            for section in content_sections:
                story.extend(self._create_content_section(section))
            
            # Add charts section
            if charts:
                story.extend(self._create_charts_section(charts))
            
            # Add tables section
            if tables:
                story.extend(self._create_tables_section(tables))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF content
            pdf_content = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Successfully generated PDF report ({len(pdf_content)} bytes)")
            return pdf_content
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise PDFGenerationError(f"PDF generation failed: {e}")
    
    def _create_title_page(
        self,
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Create title page elements"""
        elements = []
        
        # Add spacer
        elements.append(Spacer(1, 2*inch))
        
        # Main title
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Subtitle with metadata
        if metadata:
            date_range = metadata.get('date_range', '')
            if date_range:
                elements.append(Paragraph(f"Report Period: {date_range}", self.styles['CustomSubtitle']))
            
            generated_at = metadata.get('generated_at', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            elements.append(Paragraph(f"Generated: {generated_at} UTC", self.styles['CustomSubtitle']))
            
            generated_by = metadata.get('generated_by', '')
            if generated_by:
                elements.append(Paragraph(f"Generated by: {generated_by}", self.styles['CustomSubtitle']))
        
        # Add spacer and page break
        elements.append(Spacer(1, 2*inch))
        elements.append(PageBreak())
        
        return elements
    
    def _create_table_of_contents(
        self,
        content_sections: List[Dict[str, Any]]
    ) -> List[Any]:
        """Create table of contents"""
        elements = []
        
        # TOC title
        elements.append(Paragraph("Table of Contents", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
        # TOC entries
        for i, section in enumerate(content_sections, 1):
            section_title = section.get('title', f'Section {i}')
            elements.append(Paragraph(f"{i}. {section_title}", self.styles['Normal']))
            elements.append(Spacer(1, 6))
        
        elements.append(PageBreak())
        return elements
    
    def _create_content_section(
        self,
        section: Dict[str, Any]
    ) -> List[Any]:
        """Create a content section"""
        elements = []
        
        # Section title
        title = section.get('title', 'Untitled Section')
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        
        # Section content
        content = section.get('content', '')
        if content:
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    # Handle bullet points
                    if paragraph.strip().startswith('•') or paragraph.strip().startswith('-'):
                        elements.append(Paragraph(paragraph.strip(), self.styles['BulletPoint']))
                    else:
                        elements.append(Paragraph(paragraph.strip(), self.styles['BodyJustify']))
                    elements.append(Spacer(1, 6))
        
        # Add subsections
        subsections = section.get('subsections', [])
        for subsection in subsections:
            elements.extend(self._create_subsection(subsection))
        
        elements.append(Spacer(1, 0.2*inch))
        return elements
    
    def _create_subsection(
        self,
        subsection: Dict[str, Any]
    ) -> List[Any]:
        """Create a subsection"""
        elements = []
        
        # Subsection title
        title = subsection.get('title', 'Untitled Subsection')
        elements.append(Paragraph(title, self.styles['SubsectionHeader']))
        
        # Subsection content
        content = subsection.get('content', '')
        if content:
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    elements.append(Paragraph(paragraph.strip(), self.styles['BodyJustify']))
                    elements.append(Spacer(1, 6))
        
        return elements
    
    def _create_charts_section(
        self,
        charts: List[ChartData]
    ) -> List[Any]:
        """Create charts section"""
        elements = []
        
        # Section title
        elements.append(Paragraph("Data Visualization", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add each chart
        for chart in charts:
            chart_elements = self._create_chart(chart)
            if chart_elements:
                elements.extend(chart_elements)
                elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_chart(
        self,
        chart_data: ChartData
    ) -> List[Any]:
        """Create a chart element"""
        elements = []
        
        try:
            # Chart title
            elements.append(Paragraph(chart_data.title, self.styles['SubsectionHeader']))
            
            # Create chart based on type
            if chart_data.chart_type in [ChartType.PIE, ChartType.DONUT]:
                chart_drawing = self._create_pie_chart(chart_data)
            elif chart_data.chart_type == ChartType.BAR:
                chart_drawing = self._create_bar_chart(chart_data)
            else:
                # Fallback to table representation
                return self._create_chart_table(chart_data)
            
            if chart_drawing:
                elements.append(chart_drawing)
            
            return elements
            
        except Exception as e:
            logger.error(f"Failed to create chart {chart_data.title}: {e}")
            # Return table fallback
            return self._create_chart_table(chart_data)
    
    def _create_pie_chart(
        self,
        chart_data: ChartData
    ) -> Optional[Drawing]:
        """Create a pie chart"""
        try:
            drawing = Drawing(400, 300)
            
            # Create pie chart
            pie = Pie()
            pie.x = 50
            pie.y = 50
            pie.width = 200
            pie.height = 200
            pie.data = chart_data.values
            pie.labels = chart_data.labels
            
            # Set colors if provided
            if chart_data.colors:
                pie.slices.strokeColor = colors.white
                pie.slices.strokeWidth = 1
                for i, color_hex in enumerate(chart_data.colors):
                    if i < len(pie.slices):
                        # Convert hex color to ReportLab color
                        color = self._hex_to_color(color_hex)
                        pie.slices[i].fillColor = color
            
            drawing.add(pie)
            
            # Add legend
            legend = Legend()
            legend.x = 280
            legend.y = 150
            legend.deltax = 60
            legend.deltay = 20
            legend.boxAnchor = 'nw'
            legend.columnMaximum = 10
            legend.strokeWidth = 1
            legend.strokeColor = colors.black
            legend.subCols.rpad = 30
            
            legend.colorNamePairs = [
                (pie.slices[i].fillColor if i < len(pie.slices) else colors.gray, label)
                for i, label in enumerate(chart_data.labels)
            ]
            
            drawing.add(legend)
            
            return drawing
            
        except Exception as e:
            logger.error(f"Failed to create pie chart: {e}")
            return None
    
    def _create_bar_chart(
        self,
        chart_data: ChartData
    ) -> Optional[Drawing]:
        """Create a bar chart"""
        try:
            drawing = Drawing(400, 300)
            
            # Create bar chart
            bar_chart = VerticalBarChart()
            bar_chart.x = 50
            bar_chart.y = 50
            bar_chart.height = 200
            bar_chart.width = 300
            bar_chart.data = [chart_data.values]
            bar_chart.categoryAxis.categoryNames = chart_data.labels
            
            # Styling
            bar_chart.bars[0].fillColor = self.colors['primary']
            bar_chart.valueAxis.valueMin = 0
            bar_chart.valueAxis.valueMax = max(chart_data.values) * 1.1 if chart_data.values else 1
            
            drawing.add(bar_chart)
            
            return drawing
            
        except Exception as e:
            logger.error(f"Failed to create bar chart: {e}")
            return None
    
    def _create_chart_table(
        self,
        chart_data: ChartData
    ) -> List[Any]:
        """Create a table representation of chart data"""
        elements = []
        
        # Create table data
        table_data = [['Category', 'Value']]
        for label, value in zip(chart_data.labels, chart_data.values):
            table_data.append([label, str(value)])
        
        # Create table
        table = Table(table_data, colWidths=[3*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['light_gray']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        return elements
    
    def _create_tables_section(
        self,
        tables: List[TableData]
    ) -> List[Any]:
        """Create tables section"""
        elements = []
        
        # Section title
        elements.append(Paragraph("Detailed Data", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add each table
        for table_data in tables:
            table_elements = self._create_table(table_data)
            if table_elements:
                elements.extend(table_elements)
                elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_table(
        self,
        table_data: TableData
    ) -> List[Any]:
        """Create a table element"""
        elements = []
        
        try:
            # Table title
            elements.append(Paragraph(table_data.title, self.styles['SubsectionHeader']))
            elements.append(Spacer(1, 0.1*inch))
            
            # Prepare table data
            data = [table_data.headers] + table_data.rows
            
            # Calculate column widths
            num_cols = len(table_data.headers)
            col_width = (self.page_size[0] - 144) / num_cols  # 144 = margins
            col_widths = [col_width] * num_cols
            
            # Create table
            table = Table(data, colWidths=col_widths, repeatRows=1)
            
            # Apply styling
            table_style = [
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']])
            ]
            
            table.setStyle(TableStyle(table_style))
            
            # Wrap table to keep it together
            elements.append(KeepTogether(table))
            
            # Add footer if present
            if table_data.footer:
                elements.append(Spacer(1, 6))
                for footer_line in table_data.footer:
                    elements.append(Paragraph(f"<i>{footer_line}</i>", self.styles['Normal']))
            
            return elements
            
        except Exception as e:
            logger.error(f"Failed to create table {table_data.title}: {e}")
            return [Paragraph(f"Error creating table: {table_data.title}", self.styles['Normal'])]
    
    def _hex_to_color(self, hex_color: str) -> colors.Color:
        """Convert hex color to ReportLab Color"""
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                return colors.Color(r, g, b)
            else:
                return colors.gray
        except:
            return colors.gray


def create_compliance_report_pdf(
    title: str,
    report_content: str,
    charts: Optional[List[ChartData]] = None,
    tables: Optional[List[TableData]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Create a compliance report PDF from content
    
    Args:
        title: Report title
        report_content: Report content in markdown format
        charts: Optional list of charts
        tables: Optional list of tables
        metadata: Optional metadata
        
    Returns:
        PDF content as bytes
    """
    try:
        generator = PDFReportGenerator()
        
        # Parse content into sections
        sections = _parse_content_sections(report_content)
        
        # Generate PDF
        pdf_content = generator.generate_pdf_report(
            title=title,
            content_sections=sections,
            charts=charts,
            tables=tables,
            metadata=metadata
        )
        
        return pdf_content
        
    except Exception as e:
        logger.error(f"Failed to create compliance report PDF: {e}")
        raise PDFGenerationError(f"PDF creation failed: {e}")


def _parse_content_sections(content: str) -> List[Dict[str, Any]]:
    """Parse markdown content into sections"""
    sections = []
    
    try:
        # Split content by main headers (##)
        parts = content.split('\n## ')
        
        for i, part in enumerate(parts):
            if i == 0:
                # First part might not have ## prefix
                if part.startswith('# '):
                    continue  # Skip main title
                section_content = part
            else:
                section_content = '## ' + part
            
            # Extract section title
            lines = section_content.split('\n')
            title_line = lines[0] if lines else 'Untitled Section'
            
            # Remove markdown formatting from title
            title = title_line.replace('## ', '').replace('# ', '').strip()
            
            # Get section content (everything after title)
            content_lines = lines[1:] if len(lines) > 1 else []
            section_text = '\n'.join(content_lines).strip()
            
            if title and section_text:
                sections.append({
                    'title': title,
                    'content': section_text
                })
    
    except Exception as e:
        logger.error(f"Failed to parse content sections: {e}")
        # Return single section with all content
        sections = [{
            'title': 'Report Content',
            'content': content
        }]
    
    return sections


# Fallback simple PDF generator for when ReportLab is not available
def create_simple_pdf(content: str, title: str) -> bytes:
    """
    Create a simple PDF when ReportLab is not available
    
    Args:
        content: Report content
        title: Report title
        
    Returns:
        Simple PDF content as bytes
    """
    # This is a very basic PDF structure
    # In production, ensure ReportLab is available
    
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length {len(content) + len(title) + 100}
>>
stream
BT
/F1 12 Tf
72 720 Td
({title}) Tj
0 -20 Td
({content[:1000]}...) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
{len(content) + 400}
%%EOF"""
    
    return pdf_content.encode('utf-8')