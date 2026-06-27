import easyocr
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from pdf2image import convert_from_path
from typing import List, Optional
import torch

from app.config import POPPLER_PATH, OCR_LANGUAGES, OCR_DPI, OCR_MAX_PAGES, OCR_MAX_IMAGE_SIZE, OCR_FAST_MODE

# =============================================================================
# EasyOCR Reader (Singleton)
# =============================================================================
_reader: Optional[easyocr.Reader] = None


def _get_reader(languages: Optional[List[str]] = None) -> easyocr.Reader:
    """
    Get or create EasyOCR reader instance.
    
    Args:
        languages: List of language codes (default: ['en'] for English)
        
    Returns:
        EasyOCR Reader instance
    """
    global _reader
    
    if _reader is None:
        # Use config languages if not specified
        if languages is None:
            languages = OCR_LANGUAGES if OCR_LANGUAGES else ['en']
        
        # Check if GPU is available (EasyOCR will use it automatically)
        use_gpu = torch.cuda.is_available()
        print(f"[EasyOCR] Initializing reader (GPU: {use_gpu}, Languages: {languages})...")
        
        try:
            _reader = easyocr.Reader(
                languages,
                gpu=use_gpu,
                verbose=False  # Set to True for debugging
            )
            print(f"[EasyOCR] Reader initialized successfully")
        except Exception as e:
            print(f"[EasyOCR] Error initializing: {e}")
            # Fallback to CPU if GPU fails
            if use_gpu:
                print("[EasyOCR] Falling back to CPU...")
                _reader = easyocr.Reader(languages, gpu=False, verbose=False)
            else:
                raise
    
    return _reader


# =============================================================================
# Image Preprocessing
# =============================================================================
def preprocess_image(image: Image.Image) -> np.ndarray:
    """
    Preprocess image for OCR - optimized for speed.
    
    Args:
        image: PIL Image object
        
    Returns:
        Preprocessed numpy array (BGR format for EasyOCR)
    """
    # Resize if image is too large (faster processing)
    if OCR_MAX_IMAGE_SIZE > 0:
        width, height = image.size
        if width > OCR_MAX_IMAGE_SIZE or height > OCR_MAX_IMAGE_SIZE:
            # Maintain aspect ratio
            if width > height:
                new_width = OCR_MAX_IMAGE_SIZE
                new_height = int(height * (OCR_MAX_IMAGE_SIZE / width))
            else:
                new_height = OCR_MAX_IMAGE_SIZE
                new_width = int(width * (OCR_MAX_IMAGE_SIZE / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Convert PIL Image to numpy array
    img_array = np.array(image)
    
    # Convert RGBA to RGB if needed
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:  # RGBA
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    
    # Convert RGB to BGR (EasyOCR expects BGR)
    if len(img_array.shape) == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        # Grayscale to BGR
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    
    # Fast mode: skip heavy preprocessing for speed
    if OCR_FAST_MODE:
        return img_bgr
    
    # Full preprocessing mode: enhance contrast and denoise (slower but better accuracy)
    # Enhance contrast using CLAHE
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    # Light denoising (faster than heavy denoising)
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)
    
    return denoised


# =============================================================================
# Text Extraction
# =============================================================================
def extract_text_from_image(image: Image.Image, reader: Optional[easyocr.Reader] = None) -> str:
    """
    Extract text from a single image using EasyOCR - optimized for speed.
    
    Args:
        image: PIL Image object
        reader: Optional EasyOCR reader (will create if not provided)
        
    Returns:
        Extracted text string
    """
    if reader is None:
        reader = _get_reader()
    
    # Preprocess the image
    processed = preprocess_image(image)
    
    # Extract text using EasyOCR with optimized parameters
    # EasyOCR returns list of (bbox, text, confidence)
    # Using paragraph=False for faster processing
    results = reader.readtext(
        processed,
        paragraph=False,  # Faster processing
        width_ths=0.7,   # Adjust text grouping (lower = faster)
        height_ths=0.7
    )
    
    # Combine all detected text
    text_lines = []
    for (bbox, text, confidence) in results:
        # Filter out low-confidence detections
        if confidence > 0.3:  # Adjust threshold as needed
            text_lines.append(text)
    
    # Join with newlines to preserve structure
    extracted_text = '\n'.join(text_lines)
    
    return extracted_text


def convert_pdf_to_images(pdf_path: Path) -> List[Image.Image]:
    """
    Convert PDF pages to PIL Images - optimized for speed.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of PIL Image objects (one per page, limited by OCR_MAX_PAGES)
    """
    kwargs = {}
    if POPPLER_PATH:
        kwargs['poppler_path'] = POPPLER_PATH
    
    # Convert PDF to images with optimized DPI (lower = faster)
    # DPI 200 is still good quality but much faster than 300
    convert_params = {
        'dpi': OCR_DPI,
        **kwargs
    }
    
    # Limit pages if specified (0 = all pages)
    if OCR_MAX_PAGES > 0:
        convert_params['first_page'] = 1
        convert_params['last_page'] = OCR_MAX_PAGES
    
    images = convert_from_path(str(pdf_path), **convert_params)
    return images


def extract_text(file_path: Path, languages: Optional[List[str]] = None) -> str:
    """
    Main OCR function - routes based on file type.
    
    Supports: PDF, JPG, JPEG, PNG
    
    Args:
        file_path: Path to the document
        languages: List of language codes for OCR (default: ['en'])
                   Common options: ['en', 'hi', 'ta', 'te', 'kn', 'mr', 'gu', 'pa', 'bn', 'ml', 'or', 'as']
        
    Returns:
        Extracted text from all pages/image
    """
    # Use config languages if not specified
    if languages is None:
        languages = OCR_LANGUAGES if OCR_LANGUAGES else ['en']
    
    # Initialize reader with specified languages
    reader = _get_reader(languages)
    
    ext = file_path.suffix.lower()
    all_text = []
    
    if ext == '.pdf':
        # Handle PDF - convert to images first
        print(f"[EasyOCR] Processing PDF: {file_path.name} (DPI: {OCR_DPI}, Max Pages: {OCR_MAX_PAGES if OCR_MAX_PAGES > 0 else 'All'})")
        images = convert_pdf_to_images(file_path)
        print(f"[EasyOCR] Converted {len(images)} pages to images")
        
        for i, img in enumerate(images):
            print(f"[EasyOCR] Extracting text from page {i+1}/{len(images)}...")
            page_text = extract_text_from_image(img, reader)
            all_text.append(f"--- Page {i+1} ---\n{page_text}")
            print(f"[EasyOCR] Page {i+1} complete ({len(page_text)} characters)")
    
    elif ext in {'.jpg', '.jpeg', '.png'}:
        # Handle image directly
        print(f"[EasyOCR] Processing image: {file_path.name}")
        image = Image.open(file_path)
        text = extract_text_from_image(image, reader)
        all_text.append(text)
        print(f"[EasyOCR] Extraction complete ({len(text)} characters)")
    
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    return '\n\n'.join(all_text)


def init_ocr(languages: Optional[List[str]] = None):
    """
    Initialize EasyOCR reader at startup.
    
    Args:
        languages: List of language codes to load (uses config if None)
    """
    try:
        if languages is None:
            languages = OCR_LANGUAGES if OCR_LANGUAGES else ['en']
        _get_reader(languages)
        print("[EasyOCR] OCR initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize EasyOCR: {e}")
        raise
