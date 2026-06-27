import streamlit as st
import requests
import json
import os
from pathlib import Path

# Set page config
st.set_page_config(
    page_title="Invoice Parsing System",
    page_icon="📄",
    layout="wide"
)

# Constants
API_URL = "http://localhost:8000/parse-invoice"

# App title and description
st.title("📄 AI Invoice Parsing System")
st.markdown("""
Upload an invoice (PDF or Image) to extract structured data and automatically sync with SharePoint.
""")

# Sidebar for information
with st.sidebar:
    st.header("About")
    st.info("""
    This system uses:
    - **OCR**: easyocr
    - **LLM**: Groq API
    - **Integration**: Microsoft Graph API (SharePoint)
    """)
# File uploader
uploaded_file = st.file_uploader(
    "Choose an invoice file", 
    type=["pdf", "jpg", "jpeg", "png"],
    help="Supported formats: PDF, JPG, PNG"
)

if uploaded_file is not None:
    # Display file details
    st.write(f"**Filename:** {uploaded_file.name}")
    
    # Create two columns: Left for visualization, Right for results
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Preview")
        if uploaded_file.type.startswith("image/"):
            st.image(uploaded_file, use_column_width=True)
    with col2:
        st.subheader("Actions")
        if st.button("🚀 Parse & Sync", type="primary"):
            with st.spinner("Extracting text and parsing data..."):
                try:
                    # Prepare file for upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    
                    # Call FastAPI backend
                    response = requests.post(API_URL, files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        parsed_data = result.get("parsed_data", {})
                        sp_status = result.get("sharepoint_status", "unknown")
                        error_msg = result.get("error", "")
                        
                        st.success("✅ Parsing Complete!")
                        
                        # SharePoint Status
                        if sp_status == "success":
                            st.info("📦 **SharePoint Sync:** Successfully added to List.")
                        elif sp_status == "failed":
                            st.error(f" **SharePoint Sync Failed:**")
                        else:
                            st.warning(f" **SharePoint Status:** {sp_status}. {error_msg}")
                        
                        # Raw JSON
                        with st.expander("View Raw JSON"):
                            st.json(parsed_data)
                            
                    else:
                        st.error(f"Backend Error ({response.status_code}): {response.text}")
                        
                except Exception as e:
                    st.error(f"Failed to connect to backend: {str(e)}")
                    st.info("Make sure the FastAPI server is running with: `uvicorn app.main:app --reload`")

# Footer
st.divider()
st.caption("AI Document Intelligence - Secure, Local, Fast.")
