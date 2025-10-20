"""
PDF Text Extraction Module
Handles PDF parsing using PyPDF2 and pdfplumber with OCR fallback
"""

import io
import logging
from typing import Dict, Any, Optional, Tuple
import PyPDF2
import pdfplumber
from PIL import Image
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors"""
    pass


class PDFExtractor:
    """
    PDF text extraction class with multiple extraction methods and OCR fallback
    """
    
    def __init__(self):
        """Initialize PDF extractor"""
        self.textract_client = None
        self._initialize_textract()
    
    def _initialize_textract(self):
        """Initialize AWS Textract client for OCR fallback"""
        try:
            self.textract_client = boto3.client('textract')
            logger.info("Textract client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Textract client: {e}")
            self.textract_client = None
    
    def extract_text(self, pdf_content: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
        """
        Extract text from PDF using multiple methods with fallback
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename for logging
            
        Returns:
            Dictionary containing extracted text and metadata
            
        Raises:
            PDFExtractionError: If all extraction methods fail
        """
        logger.info(f"Starting text extraction for {filename}")
        
        extraction_result = {
            'text': '',
            'page_count': 0,
            'extraction_method': '',
            'confidence_score': 0.0,
            'metadata': {
                'filename': filename,
                'file_size': len(pdf_content),
                'extraction_attempts': []
            }
        }
        
        # Try PyPDF2 first (fastest)
        try:
            result = self._extract_with_pypdf2(pdf_content)
            if self._is_text_valid(result['text']):
                # Preserve original metadata and add extraction attempts
                original_metadata = extraction_result['metadata'].copy()
                extraction_result.update(result)
                extraction_result['metadata'].update(original_metadata)
                extraction_result['extraction_method'] = 'PyPDF2'
                extraction_result['confidence_score'] = 0.9
                logger.info(f"Successfully extracted text using PyPDF2 for {filename}")
                return extraction_result
            else:
                extraction_result['metadata']['extraction_attempts'].append({
                    'method': 'PyPDF2',
                    'success': False,
                    'reason': 'Insufficient text extracted'
                })
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed for {filename}: {e}")
            extraction_result['metadata']['extraction_attempts'].append({
                'method': 'PyPDF2',
                'success': False,
                'reason': str(e)
            })
        
        # Try pdfplumber (better for complex layouts)
        try:
            result = self._extract_with_pdfplumber(pdf_content)
            if self._is_text_valid(result['text']):
                # Preserve original metadata and add extraction attempts
                original_metadata = extraction_result['metadata'].copy()
                extraction_result.update(result)
                extraction_result['metadata'].update(original_metadata)
                extraction_result['extraction_method'] = 'pdfplumber'
                extraction_result['confidence_score'] = 0.95
                logger.info(f"Successfully extracted text using pdfplumber for {filename}")
                return extraction_result
            else:
                extraction_result['metadata']['extraction_attempts'].append({
                    'method': 'pdfplumber',
                    'success': False,
                    'reason': 'Insufficient text extracted'
                })
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {filename}: {e}")
            extraction_result['metadata']['extraction_attempts'].append({
                'method': 'pdfplumber',
                'success': False,
                'reason': str(e)
            })
        
        # Try OCR with Textract as fallback (for scanned documents)
        if self.textract_client:
            try:
                result = self._extract_with_textract(pdf_content)
                if self._is_text_valid(result['text']):
                    # Preserve original metadata and add extraction attempts
                    original_metadata = extraction_result['metadata'].copy()
                    extraction_result.update(result)
                    extraction_result['metadata'].update(original_metadata)
                    extraction_result['extraction_method'] = 'Textract_OCR'
                    extraction_result['confidence_score'] = 0.8
                    logger.info(f"Successfully extracted text using Textract OCR for {filename}")
                    return extraction_result
                else:
                    extraction_result['metadata']['extraction_attempts'].append({
                        'method': 'Textract_OCR',
                        'success': False,
                        'reason': 'Insufficient text extracted'
                    })
            except Exception as e:
                logger.warning(f"Textract OCR extraction failed for {filename}: {e}")
                extraction_result['metadata']['extraction_attempts'].append({
                    'method': 'Textract_OCR',
                    'success': False,
                    'reason': str(e)
                })
        
        # If all methods failed
        raise PDFExtractionError(
            f"All text extraction methods failed for {filename}. "
            f"Attempts: {extraction_result['metadata']['extraction_attempts']}"
        )
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract text using PyPDF2
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary with extracted text and metadata
        """
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        if pdf_reader.is_encrypted:
            raise PDFExtractionError("PDF is encrypted and cannot be processed")
        
        text_parts = []
        page_count = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                continue
        
        return {
            'text': '\n'.join(text_parts),
            'page_count': page_count,
            'metadata': {
                'pages_processed': len(text_parts),
                'pages_failed': page_count - len(text_parts)
            }
        }
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract text using pdfplumber (better for tables and complex layouts)
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary with extracted text and metadata
        """
        pdf_file = io.BytesIO(pdf_content)
        text_parts = []
        page_count = 0
        tables_found = 0
        
        with pdfplumber.open(pdf_file) as pdf:
            page_count = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract regular text
                    page_text = page.extract_text()
                    
                    # Extract tables if present
                    tables = page.extract_tables()
                    table_text = ""
                    if tables:
                        tables_found += len(tables)
                        for table_num, table in enumerate(tables):
                            table_text += f"\n--- Table {table_num + 1} on Page {page_num + 1} ---\n"
                            for row in table:
                                if row:  # Skip empty rows
                                    table_text += " | ".join([cell or "" for cell in row]) + "\n"
                    
                    # Combine text and tables
                    combined_text = ""
                    if page_text and page_text.strip():
                        combined_text += page_text
                    if table_text:
                        combined_text += table_text
                    
                    if combined_text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{combined_text}\n")
                        
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1} with pdfplumber: {e}")
                    continue
        
        return {
            'text': '\n'.join(text_parts),
            'page_count': page_count,
            'metadata': {
                'pages_processed': len(text_parts),
                'pages_failed': page_count - len(text_parts),
                'tables_found': tables_found
            }
        }
    
    def _extract_with_textract(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract text using AWS Textract OCR (for scanned documents)
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not self.textract_client:
            raise PDFExtractionError("Textract client not available")
        
        # Textract has a 10MB limit for synchronous operations
        if len(pdf_content) > 10 * 1024 * 1024:
            raise PDFExtractionError("PDF too large for Textract synchronous processing (>10MB)")
        
        try:
            response = self.textract_client.detect_document_text(
                Document={'Bytes': pdf_content}
            )
            
            # Extract text from Textract response
            text_parts = []
            line_text = []
            confidence_scores = []
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    line_text.append(block.get('Text', ''))
                    confidence_scores.append(block.get('Confidence', 0))
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                'text': '\n'.join(line_text),
                'page_count': 1,  # Textract processes the entire document
                'metadata': {
                    'blocks_processed': len(response.get('Blocks', [])),
                    'lines_extracted': len(line_text),
                    'average_confidence': avg_confidence,
                    'textract_response_metadata': response.get('ResponseMetadata', {})
                }
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidParameterException':
                raise PDFExtractionError(f"Invalid PDF format for Textract: {e}")
            elif error_code == 'DocumentTooLargeException':
                raise PDFExtractionError(f"PDF too large for Textract: {e}")
            else:
                raise PDFExtractionError(f"Textract error ({error_code}): {e}")
        except BotoCoreError as e:
            raise PDFExtractionError(f"AWS connection error: {e}")
    
    def _is_text_valid(self, text: str, min_length: int = 100) -> bool:
        """
        Validate if extracted text is meaningful
        
        Args:
            text: Extracted text
            min_length: Minimum text length to consider valid
            
        Returns:
            True if text is valid, False otherwise
        """
        if not text or not text.strip():
            return False
        
        # Remove whitespace and check length
        clean_text = text.strip()
        if len(clean_text) < min_length:
            return False
        
        # Check if text contains mostly readable characters
        # (not just symbols or garbled text)
        readable_chars = sum(1 for c in clean_text if c.isalnum() or c.isspace())
        readable_ratio = readable_chars / len(clean_text)
        
        return readable_ratio > 0.7  # At least 70% readable characters
    
    def validate_pdf(self, pdf_content: bytes) -> Tuple[bool, str]:
        """
        Validate PDF file format and structure
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check PDF header
            if not pdf_content.startswith(b'%PDF-'):
                return False, "Invalid PDF header"
            
            # Try to open with PyPDF2 for basic validation
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Check if PDF has pages
            if len(pdf_reader.pages) == 0:
                return False, "PDF contains no pages"
            
            # Check if PDF is corrupted by trying to access first page
            try:
                first_page = pdf_reader.pages[0]
                # Try to extract some basic info
                _ = first_page.mediabox
            except Exception as e:
                return False, f"PDF appears to be corrupted: {e}"
            
            return True, "PDF is valid"
            
        except Exception as e:
            return False, f"PDF validation failed: {e}"
    
    def get_pdf_metadata(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract metadata from PDF
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            metadata = {
                'page_count': len(pdf_reader.pages),
                'is_encrypted': pdf_reader.is_encrypted,
                'file_size': len(pdf_content),
                'pdf_version': getattr(pdf_reader, 'pdf_header', 'Unknown')
            }
            
            # Extract document info if available
            if pdf_reader.metadata:
                doc_info = pdf_reader.metadata
                metadata.update({
                    'title': doc_info.get('/Title', ''),
                    'author': doc_info.get('/Author', ''),
                    'subject': doc_info.get('/Subject', ''),
                    'creator': doc_info.get('/Creator', ''),
                    'producer': doc_info.get('/Producer', ''),
                    'creation_date': doc_info.get('/CreationDate', ''),
                    'modification_date': doc_info.get('/ModDate', '')
                })
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {e}")
            return {
                'page_count': 0,
                'is_encrypted': False,
                'file_size': len(pdf_content),
                'error': str(e)
            }


# Convenience function for simple text extraction
def extract_text_from_pdf(pdf_content: bytes, filename: str = "document.pdf") -> str:
    """
    Simple function to extract text from PDF
    
    Args:
        pdf_content: PDF file content as bytes
        filename: Original filename for logging
        
    Returns:
        Extracted text as string
        
    Raises:
        PDFExtractionError: If extraction fails
    """
    extractor = PDFExtractor()
    result = extractor.extract_text(pdf_content, filename)
    return result['text']