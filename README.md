# Invoice Parser + SharePoint + Vision UI + Google Forms

End‑to‑end invoice parsing system that:
- Extracts text from invoices (PDF / images) using **EasyOCR** or **Groq Vision (LLaMA)**  
- Parses structured JSON using **Groq LLMs**  
- Sends data to **SharePoint** and optionally **Google Forms / Sheets**  
- Exposes both a **FastAPI API** and a **Streamlit Vision UI**

---

## 1. Features

- **Backend (app/)**  
  - OCR with **EasyOCR** (GPU‑accelerated, good for invoices)  
  - LLM parsing with **Groq API** (e.g. `llama-3.1-8b-instant`)  
  - SharePoint auto‑fill via Microsoft Graph API  
  - FastAPI endpoint `/parse-invoice`

- **Vision UI (vision_model/)**  
  - Uses **Groq LLaMA Vision** to read invoices directly (no local OCR)  
  - Uses **Groq JSON model** to produce rich nested JSON (`Vendor`, `Buyer`, `Items`, `Totals`, `PaymentDetails`)  
  - Can **append parsed data to a Google Form’s response Sheet**



---

## 2. Prerequisites

- **OS**: Windows 10/11 (64‑bit)
- **Python**: 3.11+
- **GPU**: RTX 3050 4GB (optional but recommended)
- **Accounts**:
  - Groq account + API key
  - Azure AD app + SharePoint site/list
  - Google Cloud service account + Google Form / Sheet

Check Python:
```bash
python --version
```

---

## 3. Installation

```bash
cd D:\invoice_parser

# Create venv
python -m venv .venv
.\.venv\Scripts\activate

# Install deps
pip install -r requirements.txt
```

> `.gitignore` already ignores `.venv`, `.env`, and your temp files.

---

## 4. Environment Configuration (`.env`)

Create `.env` in project root (next to `requirements.txt`):

```bash
##########################
# Groq / LLM
##########################
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.1-8b-instant
MAX_NEW_TOKENS=1024

##########################
# OCR / EasyOCR (app/)
##########################
OCR_LANGUAGES=en
OCR_DPI=200
# 0 = all pages, N = only first N pages
OCR_MAX_PAGES=0
OCR_MAX_IMAGE_SIZE=2000
OCR_FAST_MODE=true

##########################
# Azure / SharePoint (both app/ and vision_model/)
##########################
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SHAREPOINT_SITE_ID=your-sharepoint-site-id
SHAREPOINT_LIST_ID=your-sharepoint-list-id

##########################
# Google Forms / Sheets (vision_model/)
##########################
# Absolute path to your Google service account key JSON (do NOT commit)
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=D:\keys\invoice-parser-sa.json

# ID from your responses sheet URL:
# https://docs.google.com/spreadsheets/d/<THIS_PART>/edit#gid=...
GFORM_SPREADSHEET_ID=1n72-zW2ThFaBGEX9PAH6oIp3EkFCBNmYcYOu8d_Ufk0

# Tab name at bottom of Sheet (usually "Form Responses 1")
GFORM_WORKSHEET_NAME=Form Responses 1

##########################
# Misc
##########################
# If using app/ocr.py PDF2Image with Poppler
POPPLER_PATH=
```

### Google service account JSON

The file at `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` must be a **Google service account key**, with fields like:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "....iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/....iam.gserviceaccount.com"
}
```

Share your **Form responses Sheet** with this `client_email` as Viewer/Editor.

---

## 5. Running the FastAPI Backend (`app/`)

In one terminal:

```bash
cd D:\invoice_parser
.\.venv\Scripts\activate

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

This will:
- Initialize EasyOCR for PDFs/images
- Initialize Groq LLM for text → JSON
- Expose `/parse-invoice`

### API usage

```bash
curl -X POST "http://localhost:8000/parse-invoice" \
  -H "accept: application/json" \
  -F "file=@path/to/invoice.pdf"
```

Returns:
- `parsed_data`: structured invoice (simple schema used by `app/`)  
- `sharepoint_status`: `success` / `failed` / `skipped`

---

## 6. Running the Vision Streamlit UI (`vision_model/`)

In another terminal:

```bash
cd D:\invoice_parser
.\.venv\Scripts\activate

cd vision_model
streamlit run streamlit_app.py
```

The UI will open in browser (default `http://localhost:8501`).

### Flow

1. **Upload invoice** (PDF or image).  
2. Vision model `meta-llama/llama-4-scout-17b-16e-instruct` extracts raw text.  
3. JSON model `llama-3.1-8b-instant` produces nested JSON with schema:
   - `InvoiceNumber`, `InvoiceDate`, `DueDate`
   - `Vendor` (BusinessName, Address, GSTIN, PAN, Phone, Email, CIN)
   - `Buyer` (Name, BillingAddress, ShippingAddress, GSTIN, Phone, Email)
   - `Items` (Description, Quantity, Unit, RatePerUnit, Discount, TaxableValue, GSTRatePercent, CGSTAmount, SGSTAmount, IGSTAmount, Cess, TotalItemAmount)
   - `Totals` (Subtotal, TotalTaxableValue, TotalCGST, TotalSGST, TotalIGST, TotalCess, RoundOff, GrandTotal, AmountInWords)
   - `PaymentDetails` (ModeOfPayment, UPIID, BankName, AccountNumber, IFSCCode, TransactionReferenceID)
4. UI shows:
   - Raw extracted text (for debugging)
   - Structured JSON
5. Action buttons:
   - **⬇️ Download JSON** — saves the structured JSON
   - **📤 Upload to SharePoint** — sends flattened data to your SharePoint list
   - **📥 Upload to Google Form (Sheet)** — appends a new row to the Form’s response sheet

### Why InvoiceNumber / InvoiceDate / DueDate might be empty

The LLM now has an explicit schema that **includes** these fields, so new extractions will produce:

```json
{
  "InvoiceNumber": "...",
  "InvoiceDate": "...",
  "DueDate": "...",
  "Vendor": { ... },
  "Buyer": { ... },
  "Items": [ ... ],
  "Totals": { ... },
  "PaymentDetails": { ... }
}
```

If an older JSON file (e.g. `invoice3_parsed.json`) doesn’t have these keys, they will be blank in the sheet. Re‑run the invoice through the Vision UI to regenerate JSON with the updated schema.

---

## 7. Google Form / Sheet Integration

Your Google Form should have questions that map to these sheet headers:

- `InvoiceNumber`, `InvoiceDate`, `DueDate`
- `Vendor Business Name`, `Vendor Address`, `Vendor GSTIN`, `Vendor Phone`, `Vendor Email`
- `Buyer Name`, `Buyer Billing Address`, `Buyer GSTIN`, `Buyer Phone`, `Buyer Email`
- `Subtotal`, `Total Taxable Value`, `Total CGST`, `Total SGST`, `Grand Total`, `Amount In Words`

In `vision_core.py`, `upload_to_gforms_sheet` does:

- Read header row (`ws.row_values(1)`)
- Build a dict `values_by_header` from your JSON
- Append a new row in the same column order

So when you press **“Upload to Google Form (Sheet)”** in the Vision UI, it is equivalent to submitting a Form with those answers.

> Items array is not currently written to the sheet. You can extend it by adding columns like `Item1 Description`, `Item1 Quantity`, etc., and mapping from `Items[0]`, `Items[1]`, etc.

---

## 8. SharePoint Integration (Quick Summary)

1. Register an app in Azure AD.  
2. Grant `Sites.ReadWrite.All` application permission, admin consent.  
3. Get `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`.  
4. Use Graph API or UI to find your `SHAREPOINT_SITE_ID` and `SHAREPOINT_LIST_ID`.  
5. Create list columns matching those used in `map_vision_json_to_sharepoint` or `app/sharepoint.py`.

Vision UI and FastAPI backend both use these env vars.

---

## 9. Project Structure

```text
invoice_parser/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── ocr.py           # EasyOCR-based OCR
│   ├── llm_parser.py    # Groq-based LLM parsing (simple schema)
│   ├── sharepoint.py    # SharePoint integration
│   ├── schemas.py       # Pydantic models for API
│   ├── config.py        # Global config and env loading
│   └── utils.py         # File helpers, validation, text cleaning
├── vision_model/
│   ├── streamlit_app.py # Vision-based Streamlit UI
│   ├── vision_core.py   # Groq Vision + JSON core + Sheets/SharePoint helpers
│   └── invoice-optimised.ipynb # Experiment notebook
├── requirements.txt
├── .env                 # Your local configuration (not committed)
└── README.md
```

---

## 10. Troubleshooting

- **Groq errors**:  
  - Check `GROQ_API_KEY` in `.env`  
  - Make sure model name is valid (see [`https://console.groq.com/docs/models`](https://console.groq.com/docs/models))

- **Google Sheets errors**:  
  - Ensure `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` points to a valid service‑account key JSON.  
  - Share the responses sheet with `client_email` from that JSON.  
  - Check `GFORM_SPREADSHEET_ID` and `GFORM_WORKSHEET_NAME` are correct.

- **SharePoint errors**:  
  - Verify Azure app permissions and admin consent.  
  - Make sure site/list IDs and credentials in `.env` are correct.

- **Performance (OCR)**:  
  - For huge PDFs, adjust `OCR_DPI`, `OCR_MAX_PAGES`, `OCR_MAX_IMAGE_SIZE` in `.env`.

---

