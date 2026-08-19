"""
Resume file parser — extracts plain text from PDF and DOCX files.
"""
from __future__ import annotations

import io

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using PyPDF2."""
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        logger.error("pdf_parse_error", error=str(e))
        raise ValueError(f"Failed to parse PDF: {e}") from e


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        import docx

        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error("docx_parse_error", error=str(e))
        raise ValueError(f"Failed to parse DOCX: {e}") from e


def extract_resume_text(file_bytes: bytes, mime_type: str) -> str:
    """Dispatch to the correct parser based on MIME type."""
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
