from autogen_agentchat.agents import AssistantAgent

from common.ai_search.azure_ai_search_client import AzureAISearchClient
from common.llm.llm_config import LLMConfig
from common.prompts.prompt_manager import PromptManager
from common.prompts.tcg_prompts import data_extractor_prompt, data_extractor_prompt_jira, analyser_prompt_manual, \
    analyser_prompt_automatic
from common.utils.utility import check_pii_exist, get_user_story_data

llm_config = LLMConfig()
prompt_manager = PromptManager()
model_client = llm_config.get_model_client()
azure_ai_search_tool = AzureAISearchClient()



class TCGAgentBuilder:
    def __init__(self, test_type: str):
        self.test_type = test_type
        self.ai_helper_name = 'TCG'

    def create_analyser_agent(self) -> AssistantAgent:

        # prompt_name = "analyser_prompt_text_automatic" if self.test_type == 'text_automatic' else (
        #     "analyser_prompt_text_manual") if self.test_type == 'text_manual' else "analyser_prompt_manual" \
        #     if self.test_type == 'Manual' else "analyser_prompt_automatic"
        prompt_name=''
        prompt=''
        if self.test_type == 'text_automatic':
            prompt_name = 'analyser_prompt_text_automatic'
            prompt = prompt_manager.get_prompt(
                ai_helper_name=self.ai_helper_name,
                agent_name=prompt_name
            )
        elif self.test_type == 'text_manual':
            prompt_name =  'analyser_prompt_text_manual'
            prompt = prompt_manager.get_prompt(
                ai_helper_name=self.ai_helper_name,
                agent_name=prompt_name
            )
        elif self.test_type == 'Manual':
            prompt = analyser_prompt_manual
        else:
            prompt = analyser_prompt_automatic



        return AssistantAgent(
            name="analyser_agent",
            model_client=model_client,
            system_message=prompt,
        )

    def create_request_handler_agent(self) -> AssistantAgent:


        if self.test_type in ['text_automatic', 'text_manual']:
            search_tool = []
            system_msg = data_extractor_prompt
        elif self.test_type == 'Manual':
            search_tool = [azure_ai_search_tool.semantic_search_tcg_manual]
            system_msg = data_extractor_prompt_jira
        else:
            search_tool = [azure_ai_search_tool.semantic_search_tcg_cucumber]
            system_msg = data_extractor_prompt_jira

        # prompt = prompt_manager.get_prompt(
        #     ai_helper_name=self.ai_helper_name,
        #     agent_name="data_extractor_prompt"
        # )

        return AssistantAgent(
            name="request_handler_agent",
            model_client=model_client,
            tools=search_tool,
            system_message=system_msg,
        )

    def create_reviewer_agent(self) -> AssistantAgent:

        prompt = prompt_manager.get_prompt(
            ai_helper_name=self.ai_helper_name,
            agent_name="reviewer_prompt"
        )

        return AssistantAgent(
            name="reviewer_agent",
            model_client=model_client,
            system_message=prompt,
        )

    def create_final_response_generator_agent(self) -> AssistantAgent:
        prompt_name = "final_response_generator_prompt" if self.test_type in ['text_manual', 'Manual'] else \
            "final_response_generator_prompt_cucumber"

        prompt = prompt_manager.get_prompt(
            ai_helper_name=self.ai_helper_name,
            agent_name=prompt_name
        )

        return AssistantAgent(
            name="final_response_generator_agent",
            model_client=model_client,
            system_message=prompt
        )