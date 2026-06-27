"""
Vision Model Core — Invoice text extraction using Groq LLaMA Vision.

Converts PDF/image invoices → raw text (via vision model) → structured JSON (via LLM).
Based on the logic from invoice-optimised.ipynb.
"""

import json
import os
import base64
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
from groq import Groq
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ── Load .env from the project root ──────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Models ───────────────────────────────────────────────────────────────────
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
JSON_MODEL = "llama-3.1-8b-instant"


def get_groq_client() -> Groq:
    """Create and return a Groq client using the API key from .env."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment. Check your .env file.")
    return Groq(api_key=api_key)


# ── Image helpers ────────────────────────────────────────────────────────────

def pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[Image.Image]:
    """Convert PDF bytes into a list of PIL images (one per page)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def image_to_base64(image: Image.Image) -> str:
    """Encode a PIL image as a JPEG base64 string."""
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ── Groq vision extraction ──────────────────────────────────────────────────

VISION_PROMPT = """
Extract all readable text from this document.
Preserve layout and line breaks.
Do NOT summarize.
Return only raw extracted text.
"""


def extract_text_with_vision(client: Groq, image: Image.Image) -> str:
    """Use the Groq LLaMA vision model to OCR a single image."""
    b64 = image_to_base64(image)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": VISION_PROMPT},
            ],
        }],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


# ── Structured JSON extraction ───────────────────────────────────────────────

INVOICE_JSON_PROMPT = """
Extract structured invoice data from the text below. Do not explain or hallucinate.

Use semantic reasoning to match fields even if formatting is inconsistent.

Return exactly the following JSON structure with values or null if missing:

{{
  "InvoiceNumber": null,
  "InvoiceDate": null,
  "DueDate": null,
  "Vendor": {{
    "BusinessName": null,
    "Address": null,
    "GSTIN": null,
    "PAN": null,
    "Phone": null,
    "Email": null,
    "CIN": null
  }},
  "Buyer": {{
    "Name": null,
    "BillingAddress": null,
    "ShippingAddress": null,
    "GSTIN": null,
    "Phone": null,
    "Email": null
  }},
  "Items": [
    {{
      "Description": null,
      "Quantity": null,
      "Unit": null,
      "RatePerUnit": null,
      "Discount": null,
      "TaxableValue": null,
      "GSTRatePercent": null,
      "CGSTAmount": null,
      "SGSTAmount": null,
      "IGSTAmount": null,
      "Cess": null,
      "TotalItemAmount": null
    }}
  ],
  "Totals": {{
    "Subtotal": null,
    "TotalTaxableValue": null,
    "TotalCGST": null,
    "TotalSGST": null,
    "TotalIGST": null,
    "TotalCess": null,
    "RoundOff": null,
    "GrandTotal": null,
    "AmountInWords": null
  }},
  "PaymentDetails": {{
    "ModeOfPayment": null,
    "UPIID": null,
    "BankName": null,
    "AccountNumber": null,
    "IFSCCode": null,
    "TransactionReferenceID": null
  }}
}}

TEXT:
{text}
"""


def extract_invoice_fields(client: Groq, text: str) -> str:
    """Call the LLM to extract structured JSON from raw invoice text."""
    prompt = INVOICE_JSON_PROMPT.format(text=text)

    response = client.chat.completions.create(
        model=JSON_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def process_llm_output(llm_output: str, threshold: float = 0.6) -> dict | None:
    """Parse the LLM JSON output and sanitise low-confidence fields."""
    # Strip markdown code fences if present
    cleaned = llm_output.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    def sanitize(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, dict) and "confidence" in v:
                    if v["confidence"] < threshold:
                        v["value"] = None
                else:
                    sanitize(v)
        elif isinstance(obj, list):
            for item in obj:
                sanitize(item)

    sanitize(data)
    return data


# ── End-to-end pipeline ─────────────────────────────────────────────────────

def process_document(file_bytes: bytes, filename: str) -> tuple[str, dict | None]:
    """
    Full pipeline: file bytes → (raw_text, structured_json).
    """
    client = get_groq_client()
    full_text = ""

    if filename.lower().endswith(".pdf"):
        images = pdf_bytes_to_images(file_bytes)
        for img in images:
            full_text += extract_text_with_vision(client, img) + "\n"
    else:
        image = Image.open(BytesIO(file_bytes)).convert("RGB")
        full_text = extract_text_with_vision(client, image)

    llm_output = extract_invoice_fields(client, full_text)
    structured_data = process_llm_output(llm_output)

    return full_text.strip(), structured_data


# ── SharePoint upload ────────────────────────────────────────────────────────

def _safe(val) -> str:
    """Convert a value to string, returning empty string for None."""
    return str(val) if val is not None else ""


def _format_items_summary(items: list[dict]) -> str:
    """Create a readable multi-line summary of invoice items."""
    lines = []
    for i, item in enumerate(items, 1):
        desc = _safe(item.get("Description"))
        qty = _safe(item.get("Quantity"))
        unit = _safe(item.get("Unit"))
        rate = _safe(item.get("RatePerUnit"))
        total = _safe(item.get("TotalItemAmount"))
        lines.append(f"{i}. {desc} | Qty: {qty} {unit} | Rate: {rate} | Total: {total}")
    return "\n".join(lines)


def map_vision_json_to_sharepoint(data: dict) -> dict:
    """
    Flatten the nested vision model JSON into the SharePoint List column format.
    Maps to the same column names used by app/sharepoint.py.
    """
    vendor = data.get("Vendor", {})
    buyer = data.get("Buyer", {})
    totals = data.get("Totals", {})
    items = data.get("Items", [])
    payment = data.get("PaymentDetails", {})

    # Build tax string: combine CGST + SGST + IGST
    tax_parts = []
    if totals.get("TotalCGST"):
        tax_parts.append(f"CGST: {totals['TotalCGST']}")
    if totals.get("TotalSGST"):
        tax_parts.append(f"SGST: {totals['TotalSGST']}")
    if totals.get("TotalIGST"):
        tax_parts.append(f"IGST: {totals['TotalIGST']}")
    if totals.get("TotalCess"):
        tax_parts.append(f"Cess: {totals['TotalCess']}")
    tax_str = " | ".join(tax_parts) if tax_parts else ""

    # Build vendor contact: phone + email combined
    contact_parts = [_safe(vendor.get("Phone")), _safe(vendor.get("Email"))]
    vendor_contact = " | ".join([p for p in contact_parts if p])

    # Build bank/payment info
    bank_parts = [_safe(payment.get("BankName")), _safe(payment.get("AccountNumber")),
                  _safe(payment.get("IFSCCode"))]
    bank_info = " | ".join([p for p in bank_parts if p])

    return {
        "fields": {
            "InvoiceNumber": _safe(data.get("InvoiceNumber")),
            "InvoiceDate": _safe(data.get("InvoiceDate")),
            "DueDate": _safe(data.get("DueDate")),
            "ContractNumber": _safe(data.get("ContractNumber")),
            "Status": _safe(data.get("Status")),
            "VendorName": _safe(vendor.get("BusinessName")),
            "VendorID": _safe(vendor.get("GSTIN")),
            "VendorAddress": _safe(vendor.get("Address")),
            "VendorContact": vendor_contact,
            "VendorBankMail": bank_info,
            "VendorGST": _safe(vendor.get("GSTIN")),
            "CustomerName": _safe(buyer.get("Name")),
            "CustomerCompany": _safe(buyer.get("Name")),
            "CustomerContact": _safe(buyer.get("Phone")),
            "CustomerID": _safe(buyer.get("GSTIN")),
            "Subtotal": _safe(totals.get("Subtotal")),
            "DiscountPercent": "",
            "Tax": tax_str,
            "TotalAmount": _safe(totals.get("GrandTotal")),
            "Currency": "INR",
            "PaymentTerms": _safe(payment.get("ModeOfPayment")),
        }
    }


def upload_to_sharepoint(structured_data: dict) -> dict:
    """
    Upload the parsed invoice JSON to SharePoint List.

    Returns dict with 'status' ('success', 'failed', 'skipped') and 'error' message.
    """
    import sys
    import requests as req
    from msal import ConfidentialClientApplication

    # Read SharePoint config from env
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
    site_id = os.getenv("SHAREPOINT_SITE_ID", "")
    list_id = os.getenv("SHAREPOINT_LIST_ID", "")

    if not all([tenant_id, client_id, client_secret, site_id, list_id]):
        return {"status": "skipped", "error": "SharePoint not configured. Check Azure credentials in .env"}

    try:
        # Acquire token
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )
        scopes = ["https://graph.microsoft.com/.default"]
        result = app.acquire_token_silent(scopes, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" not in result:
            error = result.get("error_description", "Unknown auth error")
            return {"status": "failed", "error": f"Token error: {error}"}

        token = result["access_token"]

        # Map and send
        body = map_vision_json_to_sharepoint(structured_data)
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = req.post(url, headers=headers, json=body, timeout=30)

        if response.status_code in (200, 201):
            return {"status": "success", "error": ""}
        else:
            try:
                err = response.json().get("error", {}).get("message", response.text)
            except Exception:
                err = response.text
            return {"status": "failed", "error": f"SharePoint API: {err}"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ── Google Forms / Sheets integration ─────────────────────────────────────────

GFORM_SPREADSHEET_ID = os.getenv("GFORM_SPREADSHEET_ID", "")
GFORM_WORKSHEET_NAME = os.getenv("GFORM_WORKSHEET_NAME", "Form Responses 1")
GOOGLE_SERVICE_ACCOUNT_JSON_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "")


def get_gforms_worksheet():
    """
    Return a gspread worksheet connected to the Google Form responses sheet.

    Requires the following env vars (set in .env, but DO NOT commit secrets to Git):
      - GOOGLE_SERVICE_ACCOUNT_JSON_PATH: path to service account JSON file
      - GFORM_SPREADSHEET_ID: ID of the Google Sheet that stores form responses
      - GFORM_WORKSHEET_NAME: Tab name (default: 'Form Responses 1')
    """
    if not GOOGLE_SERVICE_ACCOUNT_JSON_PATH:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON_PATH is not set in .env")
    if not GFORM_SPREADSHEET_ID:
        raise ValueError("GFORM_SPREADSHEET_ID is not set in .env")

    # Full Sheets scope so we can read and append responses
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON_PATH,
        scopes=scopes,
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GFORM_SPREADSHEET_ID)
    ws = sh.worksheet(GFORM_WORKSHEET_NAME)
    return ws


def fetch_gform_invoice_row(invoice_id: str) -> dict | None:
    """
    Fetch a single Google Form response row matching the given invoice id/number.

    This assumes your Google Form / Sheet has a column named either:
      - 'InvoiceNumber'  OR
      - 'Invoice Number'
    You can adjust the logic below to match your actual header names.
    """
    ws = get_gforms_worksheet()
    records = ws.get_all_records()

    invoice_id = str(invoice_id).strip()
    candidates = ("InvoiceNumber", "Invoice Number")

    for row in records:
        for key in candidates:
            if key in row and str(row[key]).strip() == invoice_id:
                return row
    return None


def merge_gform_into_structured(structured: dict, gform_row: dict) -> dict:
    """
    Merge Google Form data into the structured JSON from the LLM.

    This is an example mapping; adjust the column names to match
    your actual Google Form fields and the nested JSON schema.
    """
    if structured is None:
        structured = {}

    data = json.loads(json.dumps(structured))  # shallow clone

    vendor = data.setdefault("Vendor", {})
    buyer = data.setdefault("Buyer", {})
    totals = data.setdefault("Totals", {})
    payment = data.setdefault("PaymentDetails", {})

    # Example column names from Google Form -> JSON fields
    col = gform_row  # shorthand

    # Top-level invoice metadata
    invoice_number = col.get("InvoiceNumber") or col.get("Invoice Number")
    if invoice_number:
        data["InvoiceNumber"] = invoice_number

    invoice_date = col.get("InvoiceDate") or col.get("Invoice Date")
    if invoice_date:
        data["InvoiceDate"] = invoice_date

    due_date = col.get("DueDate") or col.get("Due Date")
    if due_date:
        data["DueDate"] = due_date

    # Vendor
    vendor_name = col.get("Vendor Business Name") or col.get("VendorName")
    if vendor_name:
        vendor["BusinessName"] = vendor_name

    vendor_addr = col.get("Vendor Address")
    if vendor_addr:
        vendor["Address"] = vendor_addr

    vendor_gstin = col.get("Vendor GSTIN")
    if vendor_gstin:
        vendor["GSTIN"] = vendor_gstin

    vendor_phone = col.get("Vendor Phone")
    if vendor_phone:
        vendor["Phone"] = vendor_phone

    vendor_email = col.get("Vendor Email")
    if vendor_email:
        vendor["Email"] = vendor_email

    # Buyer
    buyer_name = col.get("Buyer Name") or col.get("Customer Name")
    if buyer_name:
        buyer["Name"] = buyer_name

    billing_addr = col.get("Billing Address")
    if billing_addr:
        buyer["BillingAddress"] = billing_addr

    shipping_addr = col.get("Shipping Address")
    if shipping_addr:
        buyer["ShippingAddress"] = shipping_addr

    buyer_phone = col.get("Buyer Phone")
    if buyer_phone:
        buyer["Phone"] = buyer_phone

    buyer_email = col.get("Buyer Email")
    if buyer_email:
        buyer["Email"] = buyer_email

    # Totals (if present in the sheet)
    if col.get("Subtotal") not in (None, ""):
        totals["Subtotal"] = col["Subtotal"]
    if col.get("Total Taxable Value") not in (None, ""):
        totals["TotalTaxableValue"] = col["Total Taxable Value"]
    if col.get("Total CGST") not in (None, ""):
        totals["TotalCGST"] = col["Total CGST"]
    if col.get("Total SGST") not in (None, ""):
        totals["TotalSGST"] = col["Total SGST"]
    if col.get("Grand Total") not in (None, ""):
        totals["GrandTotal"] = col["Grand Total"]
    if col.get("Amount In Words"):
        totals["AmountInWords"] = col["Amount In Words"]

    # Payment details
    payment_mode = col.get("Payment Mode") or col.get("PaymentMode")
    if payment_mode:
        payment["ModeOfPayment"] = payment_mode

    return data


def upload_to_gforms_sheet(structured_data: dict) -> dict:
    """
    Append the current structured invoice JSON as a new row
    into the Google Form responses sheet.

    This writes to the same sheet that the form uses, so each
    call is equivalent to submitting a new response with those fields.
    """
    if not structured_data:
        return {"status": "skipped", "error": "No structured data to upload"}

    try:
        ws = get_gforms_worksheet()
    except Exception as e:
        return {"status": "failed", "error": f"Worksheet error: {e}"}

    data = structured_data
    vendor = data.get("Vendor", {}) or {}
    buyer = data.get("Buyer", {}) or {}
    totals = data.get("Totals", {}) or {}

    # Map JSON fields to expected sheet headers
    values_by_header = {
    # both no-space and space variants
    "InvoiceNumber": data.get("InvoiceNumber"),
    "Invoice Number": data.get("InvoiceNumber"),

    "InvoiceDate": data.get("InvoiceDate"),
    "Invoice Date": data.get("InvoiceDate"),

    "DueDate": data.get("DueDate"),
    "Due Date": data.get("DueDate"),

    "Vendor Business Name": vendor.get("BusinessName"),
    "Vendor Address": vendor.get("Address"),
    "Vendor GSTIN": vendor.get("GSTIN"),
    "Vendor Phone": vendor.get("Phone"),
    "Vendor Email": vendor.get("Email"),
    "Buyer Name": buyer.get("Name"),
    "Buyer Billing Address": buyer.get("BillingAddress"),
    "Buyer GSTIN": buyer.get("GSTIN"),
    "Buyer Phone": buyer.get("Phone"),
    "Buyer Email": buyer.get("Email"),
    "Subtotal": totals.get("Subtotal"),
    "Total Taxable Value": totals.get("TotalTaxableValue"),
    "Total CGST": totals.get("TotalCGST"),
    "Total SGST": totals.get("TotalSGST"),
    "Grand Total": totals.get("GrandTotal"),
    "Amount In Words": totals.get("AmountInWords"),
}
    try:
        headers = ws.row_values(1)
        if not headers:
            return {"status": "failed", "error": "Google Sheet has no header row"}

        row_values = [_safe(values_by_header.get(h, "")) for h in headers]
        ws.append_row(row_values, value_input_option="USER_ENTERED")
        return {"status": "success", "error": ""}
    except Exception as e:
        return {"status": "failed", "error": f"Append error: {e}"}
