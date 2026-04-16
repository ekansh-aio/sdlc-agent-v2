from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery, QueryType
from openai import AzureOpenAI
import requests
import logging
import json
import os
from dotenv import load_dotenv
load_dotenv()

class AzureAISearchClient:
    def __init__(self):
        # Use API key authentication for Azure Search
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        self.search_credential = AzureKeyCredential(self.search_key)

        # Azure OpenAI configuration
        self.AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
        self.DEPLOYMENT_NAME = os.getenv("AZURE_EMBEDDING")
        self.API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

    def get_embeddings(self, input_text: str):
        logging.info("Calling Azure OpenAI embedding model using API key")

        url = f"{self.AZURE_OPENAI_ENDPOINT}/openai/deployments/{self.DEPLOYMENT_NAME}/embeddings?api-version={self.API_VERSION}"

        headers = {
            "api-key": self.AZURE_OPENAI_API_KEY,
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
            return f"Exception occurred: {str(e)}"


    def semantic_search_ras(self, query: str):
        ##AI Search Endpoint address
        search_client = SearchClient(
            endpoint=self.search_endpoint,
            credential=self.search_credential,
            index_name="ras-helper-index-v1"
        )

        try:
            embedding = self.get_embeddings(query)
            vector_query = [VectorizedQuery(vector=embedding, k_nearest_neighbors=50, fields="embedding")]
            results = search_client.search(
                search_text = "",
                vector_queries = vector_query,
                search_fields = ["description","acceptance_criteria", "summary"],
                query_type = "semantic",
                semantic_configuration_name = "default",
                top = 3
            )
            result_list = list(results)

            documents = []
            for result in result_list:
                if result['@search.score'] >= 0.85:
                    description = result.get('description', '')
                    summary = result.get('summary', '')
                    acceptance_criteria = result.get('acceptance_criteria', '')
                    #score = result.get('@search.score', '')
                    documents.append(
                        {
                            "description":description,
                            "summary": summary,
                            "acceptance_criteria": acceptance_criteria
                            #"score": score
                        }
                    )
            print("Documents: ", documents)
            
            assistant_input = {
            "user_query": query,
            "retrieved_context": documents
            }

            print(json.dumps(assistant_input, indent=2))
            
            return assistant_input
        except Exception as e:
            msg = f"Error performing semantic search: {e}"
            return msg

    def _search_configured(self) -> bool:
        return bool(self.search_endpoint and self.search_key)

    def semantic_search_tcg_manual(self, query: str):
        if not self._search_configured():
            logging.warning("Azure AI Search not configured — skipping vector search for TCG manual")
            return []

        try:
            search_client = SearchClient(
                endpoint=self.search_endpoint,
                credential=self.search_credential,
                index_name="tcg-manual-index-v1"
            )

            embedding = self.get_embeddings(query)
            if isinstance(embedding, str):  # get_embeddings returned an error string
                logging.warning(f"Could not get embeddings: {embedding}")
                return []

            vector_query = [VectorizedQuery(vector=embedding, k_nearest_neighbors=50, fields="embedding")]
            results = list(search_client.search(
                search_text="",
                vector_queries=vector_query,
                search_fields=["description", "manual_test_steps", "summary"],
                query_type="semantic",
                semantic_configuration_name="default",
                top=1
            ))
            documents = []
            for result in results:
                if result['@search.score'] >= 0.85:
                    documents.append({
                        "description": result.get('description', ''),
                        "summary": result.get('summary', ''),
                        "priority": result.get('priority', ''),
                        "manual_test_steps": result.get('manual_test_steps', '')
                    })
            return documents
        except Exception as e:
            logging.warning(f"semantic_search_tcg_manual failed: {e}")
            return []

    def semantic_search_tcg_cucumber(self, query: str):
        if not self._search_configured():
            logging.warning("Azure AI Search not configured — skipping vector search for TCG cucumber")
            return []

        try:
            search_client = SearchClient(
                endpoint=self.search_endpoint,
                credential=self.search_credential,
                index_name="tcg-cucumber-index-v1"
            )

            embedding = self.get_embeddings(query)
            if isinstance(embedding, str):
                logging.warning(f"Could not get embeddings: {embedding}")
                return []

            vector_query = [VectorizedQuery(vector=embedding, k_nearest_neighbors=50, fields="embedding")]
            results = list(search_client.search(
                search_text="",
                vector_queries=vector_query,
                search_fields=["description", "cucumber_scenario", "summary"],
                query_type="semantic",
                semantic_configuration_name="default",
                top=1
            ))
            documents = []
            for result in results:
                if result['@search.score'] >= 0.85:
                    documents.append({
                        "description": result.get('description', ''),
                        "summary": result.get('summary', ''),
                        "priority": result.get('priority', ''),
                        "cucumber_scenario": result.get('cucumber_scenario', '')
                    })
            return documents
        except Exception as e:
            logging.warning(f"semantic_search_tcg_cucumber failed: {e}")
            return []

