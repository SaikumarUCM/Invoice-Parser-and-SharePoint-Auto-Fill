# Pydantic Schemas for Invoice Parser

from pydantic import BaseModel, Field
from typing import Optional


class InvoiceData(BaseModel):
    """Structured invoice data extracted by LLM."""
    invoice_number: str = Field(default="", description="Invoice number/ID")
    invoice_date: str = Field(default="", description="Invoice date")
    due_date: str = Field(default="", description="Due date")
    contract_number: str = Field(default="", description="Contract number")
    status: str = Field(default="", description="Invoice status")
    vendor_name: str = Field(default="", description="Vendor/Seller name")
    vendor_id: str = Field(default="", description="Vendor ID")
    vendor_address: str = Field(default="", description="Vendor full address")
    vendor_contact: str = Field(default="", description="Vendor contact information")
    vendor_bank_mail: str = Field(default="", description="Vendor bank or email")
    vendor_gst: str = Field(default="", description="Vendor GST/Tax ID")
    customer_name: str = Field(default="", description="Customer/Buyer name")
    customer_company: str = Field(default="", description="Customer company name")
    customer_contact: str = Field(default="", description="Customer contact information")
    customer_id: str = Field(default="", description="Customer ID")
    subtotal: str = Field(default="", description="Subtotal before tax")
    discount_percent: str = Field(default="", description="Discount percentage")
    tax: str = Field(default="", description="Tax amount")
    total_amount: str = Field(default="", description="Total invoice amount")
    currency: str = Field(default="", description="Currency code (INR, USD, etc.)")
    payment_terms: str = Field(default="", description="Payment terms/due date")


class ParseResponse(BaseModel):
    """API response for invoice parsing."""
    parsed_data: InvoiceData
    sharepoint_status: str = Field(
        default="skipped",
        description="Status: success, failed, or skipped"
    )
    error: str = Field(default="", description="Error message if any")


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
