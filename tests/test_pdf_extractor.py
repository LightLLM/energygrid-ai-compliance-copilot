"""
Unit tests for PDF text extraction functionality
"""

import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from src.analyzer.pdf_extractor import PDFExtractor, PDFExtractionError, extract_text_from_pdf


class TestPDFExtractor:
    """Test cases for PDFExtractor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = PDFExtractor()
        
        # Sample PDF content (minimal valid PDF)
        self.sample_pdf_content = b"""%PDF-1.4
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
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Sample compliance text) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000189 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
284
%%EOF"""
    
    def test_initialization(self):
        """Test PDFExtractor initialization"""
        extractor = PDFExtractor()
        assert extractor is not None
        # Textract client may or may not be available in test environment
    
    def test_validate_pdf_valid(self):
        """Test PDF validation with valid PDF"""
        is_valid, message = self.extractor.validate_pdf(self.sample_pdf_content)
        assert is_valid is True
        assert "valid" in message.lower()
    
    def test_validate_pdf_invalid_header(self):
        """Test PDF validation with invalid header"""
        invalid_content = b"Not a PDF file"
        is_valid, message = self.extractor.validate_pdf(invalid_content)
        assert is_valid is False
        assert "header" in message.lower()
    
    def test_validate_pdf_empty(self):
        """Test PDF validation with empty content"""
        is_valid, message = self.extractor.validate_pdf(b"")
        assert is_valid is False
        assert "header" in message.lower()
    
    def test_is_text_valid_sufficient_text(self):
        """Test text validation with sufficient text"""
        text = "This is a compliance document with sufficient text content to be considered valid for processing. " * 2  # Make it longer
        assert self.extractor._is_text_valid(text) is True
    
    def test_is_text_valid_insufficient_text(self):
        """Test text validation with insufficient text"""
        text = "Short"
        assert self.extractor._is_text_valid(text) is False
    
    def test_is_text_valid_empty_text(self):
        """Test text validation with empty text"""
        assert self.extractor._is_text_valid("") is False
        assert self.extractor._is_text_valid(None) is False
    
    def test_is_text_valid_mostly_symbols(self):
        """Test text validation with mostly symbols"""
        text = "!@#$%^&*()_+{}|:<>?[]\\;'\",./" * 10  # 300+ characters of symbols
        assert self.extractor._is_text_valid(text) is False
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    def test_extract_with_pypdf2_success(self, mock_pdf_reader):
        """Test successful text extraction with PyPDF2"""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample compliance text from PDF document"
        
        mock_reader_instance = Mock()
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        result = self.extractor._extract_with_pypdf2(self.sample_pdf_content)
        
        assert 'text' in result
        assert 'page_count' in result
        assert result['page_count'] == 1
        assert "Sample compliance text" in result['text']
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    def test_extract_with_pypdf2_encrypted(self, mock_pdf_reader):
        """Test PyPDF2 extraction with encrypted PDF"""
        mock_reader_instance = Mock()
        mock_reader_instance.is_encrypted = True
        mock_pdf_reader.return_value = mock_reader_instance
        
        with pytest.raises(PDFExtractionError, match="encrypted"):
            self.extractor._extract_with_pypdf2(self.sample_pdf_content)
    
    @patch('src.analyzer.pdf_extractor.pdfplumber.open')
    def test_extract_with_pdfplumber_success(self, mock_pdfplumber_open):
        """Test successful text extraction with pdfplumber"""
        # Mock pdfplumber
        mock_page = Mock()
        mock_page.extract_text.return_value = "Compliance regulation text extracted with pdfplumber"
        mock_page.extract_tables.return_value = [
            [["Header 1", "Header 2"], ["Value 1", "Value 2"]]
        ]
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdfplumber_open.return_value = mock_pdf
        
        result = self.extractor._extract_with_pdfplumber(self.sample_pdf_content)
        
        assert 'text' in result
        assert 'page_count' in result
        assert result['page_count'] == 1
        assert "Compliance regulation text" in result['text']
        assert "Header 1" in result['text']  # Table content should be included
        assert result['metadata']['tables_found'] == 1
    
    @patch('boto3.client')
    def test_extract_with_textract_success(self, mock_boto_client):
        """Test successful text extraction with Textract"""
        # Mock Textract response
        mock_textract_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'Compliance obligation extracted via OCR',
                    'Confidence': 95.5
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Additional regulatory text from scanned document',
                    'Confidence': 92.3
                }
            ],
            'ResponseMetadata': {'RequestId': 'test-request-id'}
        }
        
        mock_client = Mock()
        mock_client.detect_document_text.return_value = mock_textract_response
        mock_boto_client.return_value = mock_client
        
        # Reinitialize extractor to use mocked client
        extractor = PDFExtractor()
        extractor.textract_client = mock_client
        
        result = extractor._extract_with_textract(self.sample_pdf_content)
        
        assert 'text' in result
        assert 'page_count' in result
        assert "Compliance obligation extracted via OCR" in result['text']
        assert "Additional regulatory text" in result['text']
        assert result['metadata']['average_confidence'] > 90
    
    @patch('boto3.client')
    def test_extract_with_textract_large_file(self, mock_boto_client):
        """Test Textract extraction with file too large"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        extractor = PDFExtractor()
        extractor.textract_client = mock_client
        
        # Create content larger than 10MB
        large_content = b'x' * (11 * 1024 * 1024)
        
        with pytest.raises(PDFExtractionError, match="too large"):
            extractor._extract_with_textract(large_content)
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    @patch('src.analyzer.pdf_extractor.pdfplumber.open')
    def test_extract_text_fallback_chain(self, mock_pdfplumber_open, mock_pdf_reader):
        """Test extraction fallback chain when methods fail"""
        # Make PyPDF2 fail
        mock_pdf_reader.side_effect = Exception("PyPDF2 failed")
        
        # Make pdfplumber succeed
        mock_page = Mock()
        mock_page.extract_text.return_value = "Text extracted successfully with pdfplumber fallback. " * 10  # Make it longer
        mock_page.extract_tables.return_value = []
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdfplumber_open.return_value = mock_pdf
        
        result = self.extractor.extract_text(self.sample_pdf_content, "test.pdf")
        
        assert result['extraction_method'] == 'pdfplumber'
        assert result['confidence_score'] == 0.95
        assert "Text extracted successfully" in result['text']
        assert len(result['metadata']['extraction_attempts']) == 1  # PyPDF2 failed
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    @patch('src.analyzer.pdf_extractor.pdfplumber.open')
    @patch('boto3.client')
    def test_extract_text_all_methods_fail(self, mock_boto_client, mock_pdfplumber_open, mock_pdf_reader):
        """Test extraction when all methods fail"""
        # Make all methods fail
        mock_pdf_reader.side_effect = Exception("PyPDF2 failed")
        mock_pdfplumber_open.side_effect = Exception("pdfplumber failed")
        
        mock_client = Mock()
        mock_client.detect_document_text.side_effect = Exception("Textract failed")
        mock_boto_client.return_value = mock_client
        
        extractor = PDFExtractor()
        extractor.textract_client = mock_client
        
        with pytest.raises(PDFExtractionError, match="All text extraction methods failed"):
            extractor.extract_text(self.sample_pdf_content, "test.pdf")
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    def test_get_pdf_metadata_success(self, mock_pdf_reader):
        """Test PDF metadata extraction"""
        # Mock PDF reader with metadata
        mock_metadata = {
            '/Title': 'Compliance Regulation Document',
            '/Author': 'Regulatory Authority',
            '/Subject': 'Energy Sector Compliance',
            '/Creator': 'Document Creator',
            '/Producer': 'PDF Producer',
            '/CreationDate': 'D:20231201120000Z',
            '/ModDate': 'D:20231201130000Z'
        }
        
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [Mock(), Mock()]  # 2 pages
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.metadata = mock_metadata
        mock_reader_instance.pdf_header = '%PDF-1.4'
        mock_pdf_reader.return_value = mock_reader_instance
        
        metadata = self.extractor.get_pdf_metadata(self.sample_pdf_content)
        
        assert metadata['page_count'] == 2
        assert metadata['is_encrypted'] is False
        assert metadata['title'] == 'Compliance Regulation Document'
        assert metadata['author'] == 'Regulatory Authority'
        assert metadata['subject'] == 'Energy Sector Compliance'
    
    @patch('src.analyzer.pdf_extractor.PyPDF2.PdfReader')
    def test_get_pdf_metadata_no_metadata(self, mock_pdf_reader):
        """Test PDF metadata extraction when no metadata available"""
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [Mock()]
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.metadata = None
        mock_pdf_reader.return_value = mock_reader_instance
        
        metadata = self.extractor.get_pdf_metadata(self.sample_pdf_content)
        
        assert metadata['page_count'] == 1
        assert metadata['is_encrypted'] is False
        assert 'title' not in metadata  # No metadata should be present


class TestConvenienceFunction:
    """Test cases for convenience functions"""
    
    @patch('src.analyzer.pdf_extractor.PDFExtractor')
    def test_extract_text_from_pdf(self, mock_extractor_class):
        """Test convenience function for text extraction"""
        mock_extractor = Mock()
        mock_extractor.extract_text.return_value = {
            'text': 'Extracted compliance text',
            'extraction_method': 'PyPDF2',
            'confidence_score': 0.9
        }
        mock_extractor_class.return_value = mock_extractor
        
        result = extract_text_from_pdf(b"sample pdf content", "test.pdf")
        
        assert result == 'Extracted compliance text'
        mock_extractor.extract_text.assert_called_once_with(b"sample pdf content", "test.pdf")


# Integration test fixtures
@pytest.fixture
def sample_pdf_bytes():
    """Fixture providing sample PDF content"""
    return b"""%PDF-1.4
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
/Length 100
>>
stream
BT
/F1 12 Tf
72 720 Td
(This is a sample compliance regulation document with sufficient text content for testing.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000189 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
340
%%EOF"""


class TestPDFExtractorIntegration:
    """Integration tests for PDF extraction"""
    
    def test_real_pdf_validation(self, sample_pdf_bytes):
        """Test PDF validation with real PDF structure"""
        extractor = PDFExtractor()
        is_valid, message = extractor.validate_pdf(sample_pdf_bytes)
        assert is_valid is True
    
    def test_real_pdf_metadata(self, sample_pdf_bytes):
        """Test metadata extraction with real PDF structure"""
        extractor = PDFExtractor()
        metadata = extractor.get_pdf_metadata(sample_pdf_bytes)
        assert metadata['page_count'] >= 0
        assert 'file_size' in metadata
        assert metadata['file_size'] == len(sample_pdf_bytes)