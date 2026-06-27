# FastAPI Application - Invoice Parser API
# Main entry point with /parse-invoice endpoint

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import ParseResponse, ErrorResponse
from app.utils import save_upload_file, cleanup_temp_file, validate_file_type, clean_text
from app.ocr import extract_text, init_ocr
from app.llm_parser import parse_invoice_text, init_model
from app.sharepoint import create_list_item, is_sharepoint_configured
from app.config import OCR_LANGUAGES


# =============================================================================
# Lifespan - Load model at startup
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load OCR and LLM models at startup."""
    print("Starting Invoice Parser API...")
    print(f"SharePoint configured: {is_sharepoint_configured()}")
    
    # Initialize OCR
    print(f"Initializing EasyOCR with languages: {OCR_LANGUAGES}")
    init_ocr(OCR_LANGUAGES)
    
    # Initialize LLM
    init_model()
    
    print("All models loaded. Ready to process invoices.")
    yield
    print("Shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================
app = FastAPI(
    title="Invoice Parser API",
    description="Extract structured data from invoices using OCR and LLM, with SharePoint auto-fill",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Invoice Parser API is running",
        "sharepoint_configured": is_sharepoint_configured()
    }


@app.post(
    "/parse-invoice",
    response_model=ParseResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type"},
        500: {"model": ErrorResponse, "description": "Processing error"}
    }
)
async def parse_invoice(file: UploadFile = File(...)):
    """
    Parse an invoice and optionally push to SharePoint.
    
    Accepts: PDF, JPG, JPEG, PNG
    
    Returns:
        - parsed_data: Structured invoice fields
        - sharepoint_status: success | failed | skipped
        - error: Error message if any
    """
    file_path = None
    
    try:
        # Validate file type
        if not file.filename or not validate_file_type(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: PDF, JPG, JPEG, PNG"
            )
        
        # Save uploaded file
        file_path = save_upload_file(file)
        
        # Step 1: OCR
        print(f"Processing: {file.filename}")
        raw_text = extract_text(file_path)
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from document. Please check image quality."
            )
        
        # Step 2: LLM Parsing
        print("Parsing with LLM...")
        invoice_data = parse_invoice_text(cleaned_text)
        
        # Step 3: SharePoint (if configured)
        print("Pushing to SharePoint...")
        sp_result = create_list_item(invoice_data)
        
        return ParseResponse(
            parsed_data=invoice_data,
            sharepoint_status=sp_result["status"],
            error=sp_result.get("error", "")
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"Error processing invoice: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing invoice: {str(e)}"
        )
    
    finally:
        # Cleanup temp file
        if file_path:
            cleanup_temp_file(file_path)


@app.get("/health")
async def health_check():
    """Detailed health check."""
    from app.config import GROQ_MODEL
    
    return {
        "status": "healthy",
        "model": GROQ_MODEL,
        "provider": "Groq API",
        "sharepoint_configured": is_sharepoint_configured()
    }
