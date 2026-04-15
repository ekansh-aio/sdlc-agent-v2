
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.ui import Console
import logging
from common.llm.llm_config import LLMConfig
from common.prompts.prompt_manager import PromptManager
from common.prompts.ras_prompts import request_handler_agent, analyser_prompt,reviewer_prompt,final_response_generator_prompt
from common.ai_search.azure_ai_search_client import AzureAISearchClient

class RASAgentBuilder:
    def __init__(self, ai_helper_name: str, input_type: str):
        self.ai_helper_name = ai_helper_name
        self.prompt_manager = PromptManager()
        self.llm_config = LLMConfig()
        self.model_client = self.llm_config.get_model_client()
        self.input_type = input_type

    async def create_request_handler_agent(self) -> AssistantAgent:
        try:
            agent_name = None
            prompt = None
            
            if self.input_type == "text_input":
                agent_name = "RequestHandlerAgent"
                prompt = self.prompt_manager.get_prompt(
                    ai_helper_name=self.ai_helper_name, 
                    agent_name= agent_name
                )
                return AssistantAgent(
                    name = agent_name,
                    model_client = self.model_client,
                    system_message = prompt
                )
            elif self.input_type == "jira_id":
                agent_name = "RequestHandlerAgent_jira"
                # TODO: move prompt to DB — insert row ('RAS', 'RequestHandlerAgent_jira') in agent_prompts
                # and replace hardcoded fallback below with:
                #   prompt = self.prompt_manager.get_prompt(ai_helper_name=self.ai_helper_name, agent_name=agent_name)
                # Keep hardcoded import as fallback (same try/except pattern as ExecuteTCG team_prompt).
                prompt = request_handler_agent
                azure_ai_search_tool = AzureAISearchClient()

                return AssistantAgent(
                    name = agent_name,
                    model_client = self.model_client,
                    tools = [azure_ai_search_tool.semantic_search_ras],
                    system_message = prompt,
                )
            else:
                # Default fallback
                agent_name = "RequestHandlerAgent"
                prompt = self.prompt_manager.get_prompt(
                    ai_helper_name=self.ai_helper_name, 
                    agent_name= agent_name
                )
                return AssistantAgent(
                    name = agent_name,
                    model_client = self.model_client,
                    system_message = prompt
                )
        except Exception as e:
            raise RuntimeError(f"Error in building RequestHandlerAgent {str(e)}")

    async def create_analyser_agent(self) -> AssistantAgent:
        agent_name = None
        prompt = None
        
        if self.input_type == "text_input":
            agent_name = "AnalyserAgent"
            prompt = self.prompt_manager.get_prompt(
                ai_helper_name=self.ai_helper_name, 
                agent_name= agent_name
            )
        elif self.input_type == "jira_id":
            agent_name = "AnalyserAgent_jira"
            # TODO: move prompt to DB — insert row ('RAS', 'AnalyserAgent_jira') in agent_prompts
            # and replace hardcoded fallback below with:
            #   prompt = self.prompt_manager.get_prompt(ai_helper_name=self.ai_helper_name, agent_name=agent_name)
            # Keep hardcoded import as fallback.
            prompt = analyser_prompt
        else:
            agent_name = "AnalyserAgent"  # Default fallback
            prompt = self.prompt_manager.get_prompt(
                ai_helper_name=self.ai_helper_name, 
                agent_name= agent_name
            )

        try:
            return AssistantAgent(
                name = agent_name,
                model_client = self.model_client,
                system_message = prompt,
            )
        except Exception as e:
            message = f"Error while creating Analyser Agent: {e}"
            logging.error(message)
            raise RuntimeError(message)

    async def create_reviewer_agent(self) -> AssistantAgent:
        agent_name = "ReviewerAgent"
        prompt = self.prompt_manager.get_prompt(
            ai_helper_name=self.ai_helper_name, 
            agent_name= agent_name
        )
        
        try:
            return AssistantAgent(
                name = agent_name,
                model_client = self.model_client,
                system_message = prompt,
            )
        except Exception as e:
            message = f"Error while creating Reviewer Agent: {e}"
            logging.error(message)
            raise RuntimeError(message)

    async def create_final_response_generator_agent(self) -> AssistantAgent:
        agent_name = "FinalResponseGeneratorAgent"
        # TODO: move prompt to DB — insert row ('RAS', 'FinalResponseGeneratorAgent') in agent_prompts
        # and replace hardcoded fallback below with:
        #   prompt = self.prompt_manager.get_prompt(ai_helper_name=self.ai_helper_name, agent_name=agent_name)
        # Keep hardcoded import as fallback.
        prompt = final_response_generator_prompt

        try:
            return AssistantAgent(
                name = agent_name,
                model_client = self.model_client,
                system_message = prompt,
            )
        except Exception as e:
            message = f"Error while creating final_response_generator Agent: {e}"
            logging.error(message)
            raise RuntimeError(message)
