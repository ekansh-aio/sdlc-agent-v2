import os
import io
import uuid
import json
import logging
import pandas as pd
import re
from typing import List, Dict
from azure.storage.blob import BlobClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField,
    VectorSearch, VectorSearchAlgorithmConfiguration, HnswAlgorithmConfiguration, SemanticConfiguration, SemanticPrioritizedFields
)
from azure.core.credentials import AzureKeyCredential
import requests


# ========== Preprocessing ==========

def clean_text(text):
    """Clean markdown-like formatting and control characters from text."""
    if not isinstance(text, str):
        return ""
    text = text.replace("\n", " ").replace("\r", " ")  # Replace newlines with space
    text = re.sub(r"[*_`]", "", text)  # Remove *, _, `
    text = re.sub(r"\s+", " ", text)  # Collapse multiple spaces
    return text.strip()


def process_csv_bytes(file_bytes: bytes) -> List[Dict]:
    df = pd.read_csv(io.BytesIO(file_bytes))
    if df.empty:
        raise ValueError("CSV file is empty.")

    df = df.fillna("")
    documents = []

    for _, row in df.iterrows():
        document = {
            "description": clean_text(row.get("description", "")),
            "acceptance_criteria": clean_text(row.get("acceptance_criteria", "")),
            "summary": clean_text(row.get("summary", "")),
            "priority": clean_text(row.get("priority", "")),
            "story_point": clean_text(str(row.get("story_point", ""))),
            "epic_link": clean_text(row.get("epic_link", "")),
            "metadata": clean_text(f"project_id: {row.get('project_id', '')}, issue_type: {row.get('issue_type', '')}")
        }
        documents.append(document)

    return documents


# ========== Azure Blob ==========

class BlobFileProcessor:
    def __init__(self, container_name: str):
        ##Pass Blob Storage Name
        self.account_url = f"https://{os.getenv('STORAGE_ACCOUNT_NAME')}.blob.core.windows.net"
        self.account_key = os.getenv("STORAGE_ACCOUNT_KEY")
        self.container_name = container_name

    def download_blob_to_memory(self, blob_name: str) -> bytes:
        blob_client = BlobClient(
            account_url=self.account_url,
            container_name=self.container_name,
            blob_name=blob_name,
            credential=self.account_key
        )
        stream = io.BytesIO()
        downloader = blob_client.download_blob()
        downloader.readinto(stream)
        stream.seek(0)
        return stream.read()


# ========== Azure Search Index Manager ==========

class AzureSearchIndexManager:
    def __init__(self):
        ########Pass AI Search Endpoint name
        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        self.credential = AzureKeyCredential(self.search_key)
        self.index_client = SearchIndexClient(endpoint=self.endpoint, credential=self.credential)

    def create_or_replace_index(self, index_name: str):
        fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="description", type="Edm.String", analyzer_name="en.lucene"),
            SearchableField(name="acceptance_criteria", type="Edm.String", analyzer_name="en.lucene"),
            SearchableField(name="summary", type="Edm.String", analyzer_name="en.lucene"),
            SearchableField(name="priority", type="Edm.String", analyzer_name="en.lucene"),
            SearchableField(name="story_point", type="Edm.String", analyzer_name="en.lucene"),
            SearchableField(name="epic_link", type="Edm.String", analyzer_name="en.lucene"),
            SimpleField(name="metadata", type="Edm.String", filterable=True),
            SimpleField(name="embedding", type="Collection(Edm.Single)", searchable=True, dimensions=1536, vector_search_configuration="vector-configuration")
        ]

        vector_search = VectorSearch(
            algorithm_configurations=[
                VectorSearchAlgorithmConfiguration(
                    name="vector-configuration",
                    kind="hnsw",
                    hnsw=HnswAlgorithmConfiguration(metric="cosine", ef_construction=400, m=4)
                )
            ]
        )

        if index_name in [idx.name for idx in self.index_client.list_indexes()]:
            logging.info(f"Deleting existing index: {index_name}")
            self.index_client.delete_index(index_name)

        semantic_config = SemanticConfiguration(
            name="default",
            prioritized_fields=SemanticPrioritizedFields(
            content_fields=["acceptance_criteria", "description"]
            )
        )

        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_configurations=[semantic_config]
        )
        self.index_client.create_index(index)
        logging.info(f"Index '{index_name}' created.")
        return f"Index '{index_name}' created."


# ========== Embedding ==========

def get_embedding(input_text: str) -> List[float]:
    #pass Azure OpenAI endpoint
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    DEPLOYMENT_NAME = os.getenv("AZURE_EMBEDDING")
    API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/embeddings?api-version={API_VERSION}"

    headers = {
        "api-key": AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json"
    }

    json_payload = {
        "input": input_text
    }

    try:
        response = requests.post(url, headers=headers, json=json_payload)
        response.raise_for_status()

        result = response.json()
        embedding = result["data"][0]["embedding"]
        return embedding

    except Exception as e:
        logging.error("Error while getting embeddings", exc_info=True)
        raise Exception(f"Failed to get embeddings: {str(e)}")


# ========== Azure Search Ingestor ==========

class AzureSearchIngestor:
    def __init__(self, index_name: str):
        #pass Azure AI Search Endpoint 
        self.index_name = index_name
        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        self.credential = AzureKeyCredential(self.search_key)
        self.search_client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)

    def ingest_documents(self, documents: List[Dict]) -> str:
        for doc in documents:
            doc["id"] = str(uuid.uuid4())

        result = self.search_client.upload_documents(documents=documents)
        failures = [r for r in result if not r.succeeded]

        if failures:
            error_msgs = ", ".join(f"[{r.key}] {r.error_message}" for r in failures)
            raise Exception(f"Failed to ingest some documents: {error_msgs}")

        logging.info(f"Successfully ingested {len(documents)} documents.")
        return f"{len(documents)} documents successfully ingested into index '{self.index_name}'."


# ========== Main Entrypoint ==========

def main(name: str) -> str:
    try:
        params = json.loads(name) if isinstance(name, str) else name
        blob_name = params.get("blob_name")
        container_name = params.get("container_name")
        index_name = params.get("index_name")

        if not (blob_name and container_name and index_name):
            return "Missing required parameters."

        logging.info(f"Processing blob '{blob_name}' from container '{container_name}'...")

        # Step 1: Download and preprocess
        processor = BlobFileProcessor(container_name=container_name)
        file_bytes = processor.download_blob_to_memory(blob_name)

        if not blob_name.endswith(".csv"):
            return "Only CSV files are supported in this version."

        docs = process_csv_bytes(file_bytes)

        # Step 2: Add embeddings to documents
        for doc in docs:
            input_text = f"{doc['description']} {doc['acceptance_criteria']}"
            doc["embedding"] = get_embedding(input_text)
            doc["id"] = str(uuid.uuid4())

        # Step 3: Create index if not exists
        index_manager = AzureSearchIndexManager()
        existing_indexes = [idx.name for idx in index_manager.index_client.list_indexes()]
        if index_name not in existing_indexes:
            index_manager.create_or_replace_index(index_name=index_name)

        # Step 4: Ingest documents
        ingestor = AzureSearchIngestor(index_name=index_name)
        result = ingestor.ingest_documents(docs)
        return result

    except Exception as e:
        logging.exception("An error occurred in main.")
        return str(e)


