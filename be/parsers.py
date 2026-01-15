"""OCR and document parsing utilities.

Supports PDF (text extraction + OCR fallback), CSV, Excel with proper
error handling and free/open-source tooling.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from pypdf import PdfReader

from .config import OCRBackend, settings

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Supported file types."""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    UNKNOWN = "unknown"


class ParseError(Exception):
    """Raised when document parsing fails."""
    pass


@dataclass
class ParsedDocument:
    """Result of document parsing."""
    text: str
    file_type: FileType
    metadata: dict[str, any]
    confidence: float = 1.0


def detect_file_type(filename: str, content: bytes | None = None) -> FileType:
    """Detect file type from filename or content.
    
    Args:
        filename: Original filename
        content: Optional file content for magic number detection
        
    Returns:
        Detected FileType
    """
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return FileType.PDF
    elif filename_lower.endswith('.csv'):
        return FileType.CSV
    elif filename_lower.endswith(('.xls', '.xlsx', '.xlsm')):
        return FileType.EXCEL
    
    # Magic number detection if content provided
    if content:
        if content.startswith(b'%PDF'):
            return FileType.PDF
        elif content.startswith(b'PK\x03\x04'):  # ZIP/Office
            return FileType.EXCEL
    
    return FileType.UNKNOWN


def extract_text_from_pdf_native(file_obj: BinaryIO) -> tuple[str, float]:
    """Extract text from PDF using native text extraction.
    
    Args:
        file_obj: Binary file object
        
    Returns:
        Tuple of (extracted_text, confidence_score)
    """
    try:
        # Try pdfplumber first (better text extraction)
        with pdfplumber.open(file_obj) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            text = "\n\n".join(text_parts)
            
            # Estimate confidence based on text density
            if len(text.strip()) > 100:
                return text, 0.95
            elif len(text.strip()) > 20:
                return text, 0.7
            else:
                return text, 0.3
                
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}, trying pypdf")
        
        # Fallback to pypdf
        try:
            file_obj.seek(0)
            reader = PdfReader(file_obj)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            text = "\n\n".join(text_parts)
            confidence = 0.8 if len(text.strip()) > 100 else 0.5
            return text, confidence
            
        except Exception as e2:
            logger.error(f"pypdf extraction also failed: {e2}")
            return "", 0.0


def extract_text_from_pdf_ocr(file_content: bytes) -> tuple[str, float]:
    """Extract text from PDF using OCR (Tesseract).
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Tuple of (extracted_text, confidence_score)
    """
    try:
        logger.info(f"Running OCR with backend: {settings.ocr.backend.value}")
        
        # Convert PDF to images
        images = convert_from_bytes(
            file_content,
            dpi=settings.ocr.dpi,
            fmt='jpeg',
        )
        
        if not images:
            logger.warning("No images extracted from PDF")
            return "", 0.0
        
        logger.info(f"Extracted {len(images)} pages as images")
        
        # Run OCR on each page
        text_parts = []
        confidences = []
        
        for idx, image in enumerate(images):
            try:
                # Get OCR data with confidence
                ocr_data = pytesseract.image_to_data(
                    image,
                    lang=settings.ocr.tesseract_lang,
                    output_type=pytesseract.Output.DICT,
                )
                
                # Extract text and average confidence
                page_text = pytesseract.image_to_string(
                    image,
                    lang=settings.ocr.tesseract_lang,
                )
                
                if page_text.strip():
                    text_parts.append(page_text)
                    
                    # Calculate average confidence for this page
                    conf_values = [c for c in ocr_data['conf'] if c != -1]
                    if conf_values:
                        avg_conf = sum(conf_values) / len(conf_values) / 100.0
                        confidences.append(avg_conf)
                
            except Exception as e:
                logger.error(f"OCR failed for page {idx + 1}: {e}")
                continue
        
        text = "\n\n".join(text_parts)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        logger.info(f"OCR completed. Extracted {len(text)} chars with confidence {confidence:.2f}")
        return text, confidence
        
    except Exception as e:
        logger.error(f"PDF OCR failed: {e}")
        raise ParseError(f"OCR processing failed: {e}") from e


def parse_pdf(file_obj: BinaryIO, filename: str) -> ParsedDocument:
    """Parse PDF with text extraction + OCR fallback.
    
    Args:
        file_obj: Binary file object
        filename: Original filename
        
    Returns:
        ParsedDocument with extracted text
        
    Raises:
        ParseError: If parsing fails completely
    """
    try:
        # First try native text extraction
        text, confidence = extract_text_from_pdf_native(file_obj)
        
        # If confidence is low or text is empty, try OCR
        if confidence < settings.ocr.confidence_threshold or len(text.strip()) < 50:
            logger.info(f"Native extraction confidence {confidence:.2f} too low, trying OCR")
            file_obj.seek(0)
            content = file_obj.read()
            text_ocr, conf_ocr = extract_text_from_pdf_ocr(content)
            
            # Use OCR result if better
            if conf_ocr > confidence or len(text_ocr) > len(text):
                text = text_ocr
                confidence = conf_ocr
        
        if not text.strip():
            raise ParseError("No text could be extracted from PDF")
        
        return ParsedDocument(
            text=text,
            file_type=FileType.PDF,
            confidence=confidence,
            metadata={
                "filename": filename,
                "method": "ocr" if confidence < 0.8 else "native",
            },
        )
        
    except ParseError:
        raise
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise ParseError(f"Failed to parse PDF: {e}") from e


def parse_csv(file_obj: BinaryIO, filename: str) -> list[dict[str, any]]:
    """Parse CSV file into structured records.
    
    Args:
        file_obj: Binary file object
        filename: Original filename
        
    Returns:
        List of dictionaries (one per row)
        
    Raises:
        ParseError: If CSV parsing fails
    """
    try:
        df = pd.read_csv(file_obj, encoding='utf-8')
        
        if df.empty:
            raise ParseError("CSV file is empty")
        
        logger.info(f"Parsed CSV with {len(df)} rows and {len(df.columns)} columns")
        
        # Convert to list of dicts
        records = df.to_dict('records')
        return records
        
    except Exception as e:
        logger.error(f"CSV parsing failed: {e}")
        raise ParseError(f"Failed to parse CSV: {e}") from e


def parse_excel(file_obj: BinaryIO, filename: str, sheet_name: str | int = 0) -> list[dict[str, any]]:
    """Parse Excel file into structured records.
    
    Args:
        file_obj: Binary file object
        filename: Original filename
        sheet_name: Sheet name or index (default: first sheet)
        
    Returns:
        List of dictionaries (one per row)
        
    Raises:
        ParseError: If Excel parsing fails
    """
    try:
        df = pd.read_excel(file_obj, sheet_name=sheet_name, engine='openpyxl')
        
        if df.empty:
            raise ParseError("Excel sheet is empty")
        
        logger.info(f"Parsed Excel with {len(df)} rows and {len(df.columns)} columns")
        
        # Convert to list of dicts
        records = df.to_dict('records')
        return records
        
    except Exception as e:
        logger.error(f"Excel parsing failed: {e}")
        raise ParseError(f"Failed to parse Excel: {e}") from e


def parse_file(file_obj: BinaryIO, filename: str) -> ParsedDocument | list[dict[str, any]]:
    """Parse uploaded file based on type.
    
    Args:
        file_obj: Binary file object
        filename: Original filename
        
    Returns:
        ParsedDocument for PDFs, list of dicts for CSV/Excel
        
    Raises:
        ParseError: If file type unsupported or parsing fails
    """
    file_type = detect_file_type(filename)
    
    if file_type == FileType.PDF:
        return parse_pdf(file_obj, filename)
    elif file_type == FileType.CSV:
        return parse_csv(file_obj, filename)
    elif file_type == FileType.EXCEL:
        return parse_excel(file_obj, filename)
    else:
        raise ParseError(f"Unsupported file type: {filename}")
