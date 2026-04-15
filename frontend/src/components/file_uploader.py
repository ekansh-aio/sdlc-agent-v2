import streamlit as st
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv
load_dotenv()

def upload_file_to_azure_blob():
        # Config - Use account key authentication
        storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME")
        storage_account_key = os.getenv("STORAGE_ACCOUNT_KEY")
        
        storage_account_url = f"https://{storage_account_name}.blob.core.windows.net"
        container_name  = "qe-helper-blob-container"

        # Set up Blob Service Client with account key
        blob_service_client = BlobServiceClient(
                account_url=storage_account_url,
                credential=storage_account_key)
        container_client = blob_service_client.get_container_client(container_name)

        st.title("Upload File to Azure Blob Storage")

        # Upload
        uploaded_file = st.file_uploader("Choose a file", type=None)


        if uploaded_file is not None:
            try:
                # Upload to Azure
                
                blob_client = container_client.get_blob_client(uploaded_file.name)
                
                blob_client.upload_blob(uploaded_file, overwrite=True)

                st.success(f"✅ File '{uploaded_file.name}' uploaded to Azure Blob Storage.")
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")
