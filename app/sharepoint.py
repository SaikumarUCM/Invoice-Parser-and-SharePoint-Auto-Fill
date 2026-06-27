# SharePoint Integration - Microsoft Graph API
# Handles OAuth2 authentication and List item creation

import requests
from typing import Optional
from msal import ConfidentialClientApplication

from app.config import (
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    SHAREPOINT_SITE_ID,
    SHAREPOINT_LIST_ID,
    GRAPH_API_BASE
)
from app.schemas import InvoiceData

# =============================================================================
# MSAL Client (Singleton)
# =============================================================================
_msal_app: Optional[ConfidentialClientApplication] = None
_access_token: Optional[str] = None


def _get_msal_app() -> ConfidentialClientApplication:
    """Get or create MSAL application."""
    global _msal_app
    
    if _msal_app is None:
        if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET]):
            raise ValueError("Azure credentials not configured. Check .env file.")
        
        authority = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
        _msal_app = ConfidentialClientApplication(
            client_id=AZURE_CLIENT_ID,
            client_credential=AZURE_CLIENT_SECRET,
            authority=authority
        )
    
    return _msal_app


def get_access_token() -> str:
    """
    Get access token for Microsoft Graph API.
    
    Uses client credentials flow with automatic token refresh.
    
    Returns:
        Valid access token string
    """
    app = _get_msal_app()
    
    scopes = ["https://graph.microsoft.com/.default"]
    
    # Try to get token from cache first
    result = app.acquire_token_silent(scopes, account=None)
    
    if not result:
        # No cached token, acquire new one
        result = app.acquire_token_for_client(scopes=scopes)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        error = result.get("error_description", "Unknown error")
        raise Exception(f"Failed to acquire token: {error}")


def _map_invoice_to_list_fields(invoice: InvoiceData) -> dict:
    """
    Map InvoiceData fields to SharePoint List column names.
    
    SharePoint List must have columns with these internal names.
    """
    return {
        "fields": {
            "InvoiceNumber": invoice.invoice_number,
            "InvoiceDate": invoice.invoice_date,
            "DueDate": invoice.due_date,
            "ContractNumber": invoice.contract_number,
            "Status": invoice.status,
            "VendorName": invoice.vendor_name,
            "VendorID": invoice.vendor_id,
            "VendorAddress": invoice.vendor_address,
            "VendorContact": invoice.vendor_contact,
            "VendorBankMail": invoice.vendor_bank_mail,
            "VendorGST": invoice.vendor_gst,
            "CustomerName": invoice.customer_name,
            "CustomerCompany": invoice.customer_company,
            "CustomerContact": invoice.customer_contact,
            "CustomerID": invoice.customer_id,
            "Subtotal": invoice.subtotal,
            "DiscountPercent": invoice.discount_percent,
            "Tax": invoice.tax,
            "TotalAmount": invoice.total_amount,
            "Currency": invoice.currency,
            "PaymentTerms": invoice.payment_terms
        }
    }


def create_list_item(invoice: InvoiceData) -> dict:
    """
    Create a new item in SharePoint List.
    
    Args:
        invoice: InvoiceData object with extracted fields
        
    Returns:
        Dict with status and any error message
    """
    # Check if SharePoint is configured
    if not all([SHAREPOINT_SITE_ID, SHAREPOINT_LIST_ID]):
        return {
            "status": "skipped",
            "error": "SharePoint not configured. Set SHAREPOINT_SITE_ID and SHAREPOINT_LIST_ID in .env"
        }
    
    try:
        # Get access token
        print("[SharePoint] Acquiring access token...")
        token = get_access_token()
        print("[SharePoint] Token acquired successfully")
        
        # Build request
        url = f"{GRAPH_API_BASE}/sites/{SHAREPOINT_SITE_ID}/lists/{SHAREPOINT_LIST_ID}/items"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = _map_invoice_to_list_fields(invoice)
        
        print(f"[SharePoint] POST to: {url}")
        print(f"[SharePoint] Body: {body}")
        
        # Make request
        response = requests.post(url, headers=headers, json=body, timeout=30)
        
        print(f"[SharePoint] Response status: {response.status_code}")
        print(f"[SharePoint] Response body: {response.text[:500]}")
        
        if response.status_code in (200, 201):
            return {"status": "success", "error": ""}
        else:
            try:
                error_json = response.json()
                error_detail = error_json.get("error", {}).get("message", response.text)
                error_code = error_json.get("error", {}).get("code", "Unknown")
                full_error = f"[{error_code}] {error_detail}"
            except:
                full_error = response.text
            return {"status": "failed", "error": f"SharePoint API error: {full_error}"}
    
    except ValueError as e:
        # Azure credentials not configured
        return {"status": "skipped", "error": str(e)}
    
    except Exception as e:
        import traceback
        print(f"[SharePoint] Exception: {traceback.format_exc()}")
        return {"status": "failed", "error": f"SharePoint error: {str(e)}"}


def is_sharepoint_configured() -> bool:
    """Check if SharePoint integration is properly configured."""
    return all([
        AZURE_TENANT_ID,
        AZURE_CLIENT_ID,
        AZURE_CLIENT_SECRET,
        SHAREPOINT_SITE_ID,
        SHAREPOINT_LIST_ID
    ])
