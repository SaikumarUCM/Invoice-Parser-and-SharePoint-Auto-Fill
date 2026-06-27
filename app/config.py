# Configuration for Invoice Parser

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Paths
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# =============================================================================
# LLM Configuration - Groq API
# =============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Best models for structured JSON extraction (as of 2025):
# - llama-3.1-8b-instant (fastest, recommended)
# - mixtral-8x7b-32768 (good balance of speed and accuracy)
# - llama-3.1-70b-versatile (decommissioned - do not use)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
# Fallback models to try if primary fails
GROQ_FALLBACK_MODELS = ["mixtral-8x7b-32768", "llama-3.1-70b-versatile"]
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "1024"))

# =============================================================================
# Azure / SharePoint Configuration
# =============================================================================
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")

SHAREPOINT_SITE_ID = os.getenv("SHAREPOINT_SITE_ID", "")
SHAREPOINT_LIST_ID = os.getenv("SHAREPOINT_LIST_ID", "")

# Graph API endpoints
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# =============================================================================
# OCR Configuration - EasyOCR
# =============================================================================
# EasyOCR languages - comma-separated list (e.g., "en,hi" for English and Hindi)
# Common options: en, hi, ta, te, kn, mr, gu, pa, bn, ml, or, as
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "en").split(",")
OCR_LANGUAGES = [lang.strip() for lang in OCR_LANGUAGES if lang.strip()]

# OCR Performance Settings
OCR_DPI = int(os.getenv("OCR_DPI", "200"))  # Lower DPI = faster (150-200 recommended, default was 300)
# OCR_MAX_PAGES: 0 = process all pages, N = process first N pages only
# For production with multi-page invoices, set to 0 to process all pages
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "0"))  # Default: 0 (all pages) - Set to 2 for faster testing
OCR_MAX_IMAGE_SIZE = int(os.getenv("OCR_MAX_IMAGE_SIZE", "2000"))  # Max width/height in pixels (resize if larger)
OCR_FAST_MODE = os.getenv("OCR_FAST_MODE", "true").lower() == "true"  # Skip heavy preprocessing for speed

# Poppler path for PDF conversion (only needed for PDF files)
POPPLER_PATH = os.getenv("POPPLER_PATH", None)  # Set if not in PATH

# =============================================================================
# Allowed file types
# =============================================================================
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
