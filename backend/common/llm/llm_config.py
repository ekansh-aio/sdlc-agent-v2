from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
import os
from dotenv import load_dotenv
load_dotenv()

class LLMConfig:
    def __init__(self):
        self.model = os.getenv("AZURE_CHAT_MODEL_NAME")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.azure_deployment = os.getenv("AZURE_MODEL_DEPLOYMENT_NAME")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.temperature = os.getenv("AZURE_OPENAI_TEMPERATURE")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not self.api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY environment variable is not set")


    def get_model_client(self) -> AzureOpenAIChatCompletionClient:

         return AzureOpenAIChatCompletionClient(
                 azure_deployment=self.azure_deployment,
                 model=self.model,
                 api_version=self.api_version,
                 azure_endpoint=self.azure_endpoint,
                 api_key=self.api_key,
                 temperature=float(self.temperature)
             )