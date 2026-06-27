# Utility Functions for Invoice Parser

import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.config import TEMP_DIR, ALLOWED_EXTENSIONS


def save_upload_file(file: UploadFile) -> Path:
    """
    Save uploaded file to temp directory with unique name.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Path to saved file
    """
    # Get file extension
    ext = Path(file.filename).suffix.lower()
    
    # Generate unique filename
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = TEMP_DIR / unique_name
    
    # Save file
    with open(file_path, "wb") as f:
        content = file.file.read()
        f.write(content)
    
    return file_path


def cleanup_temp_file(file_path: Path) -> None:
    """
    Remove temporary file after processing.
    
    Args:
        file_path: Path to file to remove
    """
    try:
        if file_path.exists():
            os.remove(file_path)
    except Exception:
        pass  # Ignore cleanup errors


def validate_file_type(filename: str) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        True if file type is allowed
    """
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def clean_text(text: str) -> str:
    """
    Clean OCR text for LLM processing.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(cleaned_lines)
