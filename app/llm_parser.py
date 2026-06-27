# LLM Parsing Layer - Groq API
# Extracts structured invoice data from OCR text using Groq's fast inference API

import json
from groq import Groq
from typing import Optional

from app.config import GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK_MODELS, MAX_NEW_TOKENS
from app.schemas import InvoiceData

# =============================================================================
# Groq Client (Singleton)
# =============================================================================
_groq_client: Optional[Groq] = None


def _get_groq_client() -> Groq:
    """Get or create Groq client."""
    global _groq_client
    
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured. Set it in your .env file.")
        _groq_client = Groq(api_key=GROQ_API_KEY)
        print(f"[Groq] Client initialized with model: {GROQ_MODEL}")
    
    return _groq_client


# =============================================================================
# Prompt Template
# =============================================================================
INVOICE_EXTRACTION_PROMPT = """Extract invoice information from the text below. Return ONLY a valid JSON object - no markdown, no code blocks, no explanations, just pure JSON.

Required JSON structure (use empty string "" for missing fields):
{{
  "invoice_number": "",
  "invoice_date": "",
  "due_date": "",
  "contract_number": "",
  "status": "",
  "vendor_name": "",
  "vendor_id": "",
  "vendor_address": "",
  "vendor_contact": "",
  "vendor_bank_mail": "",
  "vendor_gst": "",
  "customer_name": "",
  "customer_company": "",
  "customer_contact": "",
  "customer_id": "",
  "subtotal": "",
  "discount_percent": "",
  "tax": "",
  "total_amount": "",
  "currency": "",
  "payment_terms": ""
}}

Invoice Text:
{text}

IMPORTANT: Return ONLY the JSON object starting with {{ and ending with }}. No other text."""


# =============================================================================
# JSON Extraction
# =============================================================================
def _extract_json_from_response(response: str) -> dict:
    """Extract JSON object from LLM response."""
    if not response:
        print("[DEBUG] Empty response from LLM")
        return _get_empty_extraction()
    
    print(f"[DEBUG] Raw LLM response (first 500 chars): {response[:500]}")
    
    # Clean response - remove markdown code blocks if present
    cleaned = response.strip()
    
    # Remove markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    
    # Try direct JSON parse first
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            print("[DEBUG] Successfully parsed JSON directly")
            return parsed
    except json.JSONDecodeError as e:
        print(f"[DEBUG] Direct JSON parse failed: {e}")
    
    # Find JSON object in response (handle cases where there's extra text)
    brace_count = 0
    start_idx = -1
    for i, char in enumerate(cleaned):
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                try:
                    json_str = cleaned[start_idx:i+1]
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        print(f"[DEBUG] Successfully extracted JSON from position {start_idx} to {i+1}")
                        return parsed
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] JSON extraction failed at position {start_idx}-{i+1}: {e}")
                    start_idx = -1
    
    print("[DEBUG] Could not parse JSON from response")
    print(f"[DEBUG] Full response was: {response}")
    return _get_empty_extraction()


def _get_empty_extraction() -> dict:
    """Return empty extraction dict with all required fields."""
    return {
        "invoice_number": "", "invoice_date": "", "due_date": "", "contract_number": "",
        "status": "", "vendor_name": "", "vendor_id": "", "vendor_address": "",
        "vendor_contact": "", "vendor_bank_mail": "", "vendor_gst": "",
        "customer_name": "", "customer_company": "", "customer_contact": "",
        "customer_id": "", "subtotal": "", "discount_percent": "", "tax": "",
        "total_amount": "", "currency": "", "payment_terms": ""
    }


# =============================================================================
# Main Parsing Function
# =============================================================================
def parse_invoice_text(ocr_text: str) -> InvoiceData:
    """
    Parse OCR text and extract structured invoice data using Groq API.
    
    Args:
        ocr_text: Raw OCR text from invoice image
        
    Returns:
        InvoiceData object with extracted fields
    """
    client = _get_groq_client()
    
    # Clean and prepare OCR text (increase limit for better context)
    ocr_text = ocr_text.strip()[:4000]  # Groq models can handle larger context
    print(f"[DEBUG] OCR text length: {len(ocr_text)}")
    
    # Prepare prompt
    prompt = INVOICE_EXTRACTION_PROMPT.format(text=ocr_text)
    
    # Call Groq API with fallback models
    models_to_try = [GROQ_MODEL] + [m for m in GROQ_FALLBACK_MODELS if m != GROQ_MODEL]
    response_text = ""
    last_error = None
    
    for model_name in models_to_try:
        try:
            print(f"[Groq] Calling API with model: {model_name}")
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured data from invoices. Always return ONLY valid JSON with no additional text, explanations, or markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Create completion request
            completion_params = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.1,  # Low temperature for consistent, structured output
                "max_tokens": MAX_NEW_TOKENS
            }
            
            # Add JSON mode for models that support it (Llama 3.1+)
            if "llama-3.1" in model_name.lower() or "llama-3" in model_name.lower():
                try:
                    completion_params["response_format"] = {"type": "json_object"}
                except:
                    pass  # Some Groq SDK versions might not support this
            
            response = client.chat.completions.create(**completion_params)
            
            # Extract response text
            response_text = response.choices[0].message.content
            if response_text:
                print(f"[Groq] Success with model {model_name}: {len(response_text)} characters")
                break  # Success, exit loop
            else:
                print(f"[Groq] Empty response from {model_name}, trying next model...")
                
        except Exception as e:
            last_error = e
            error_msg = str(e)
            print(f"[ERROR] Groq API error with {model_name}: {error_msg[:200]}")
            
            # Check if it's a model decommissioned error
            if "decommissioned" in error_msg.lower() or "not found" in error_msg.lower():
                print(f"[WARNING] Model {model_name} is not available, trying next model...")
                continue
            else:
                # For other errors, try next model but log the error
                import traceback
                print(f"[DEBUG] Full error trace:")
                traceback.print_exc()
                continue
    
    # If all models failed
    if not response_text:
        print(f"[ERROR] All Groq models failed. Last error: {last_error}")
        if last_error:
            error_str = str(last_error)
            if "decommissioned" in error_str.lower():
                print("[ERROR] The configured model has been decommissioned.")
                print(f"[INFO] Please update GROQ_MODEL in your .env file to one of: llama-3.1-8b-instant, mixtral-8x7b-32768")
        response_text = ""
    
    # Parse response
    extracted = _extract_json_from_response(response_text)
    
    # Return InvoiceData with all fields
    return InvoiceData(
        invoice_number=str(extracted.get("invoice_number", "")),
        invoice_date=str(extracted.get("invoice_date", "")),
        due_date=str(extracted.get("due_date", "")),
        contract_number=str(extracted.get("contract_number", "")),
        status=str(extracted.get("status", "")),
        vendor_name=str(extracted.get("vendor_name", "")),
        vendor_id=str(extracted.get("vendor_id", "")),
        vendor_address=str(extracted.get("vendor_address", "")),
        vendor_contact=str(extracted.get("vendor_contact", "")),
        vendor_bank_mail=str(extracted.get("vendor_bank_mail", "")),
        vendor_gst=str(extracted.get("vendor_gst", "")),
        customer_name=str(extracted.get("customer_name", "")),
        customer_company=str(extracted.get("customer_company", "")),
        customer_contact=str(extracted.get("customer_contact", "")),
        customer_id=str(extracted.get("customer_id", "")),
        subtotal=str(extracted.get("subtotal", "")),
        discount_percent=str(extracted.get("discount_percent", "")),
        tax=str(extracted.get("tax", "")),
        total_amount=str(extracted.get("total_amount", "")),
        currency=str(extracted.get("currency", "")),
        payment_terms=str(extracted.get("payment_terms", ""))
    )


def init_model():
    """Initialize Groq client at startup (validates API key)."""
    try:
        _get_groq_client()
        print("[Groq] Model initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Groq: {e}")
        raise
