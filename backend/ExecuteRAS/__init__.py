import asyncio
import logging
import json
from autogen_agentchat.conditions import TextMessageTermination, TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import SelectorGroupChat
from agents.ras.agent_builder import RASAgentBuilder
from common.llm.llm_config import LLMConfig
from common.prompts.prompt_manager import PromptManager
from common.prompts.ras_prompts import team_prompt
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from common.health_check import run_all_checks
logging.basicConfig(level=logging.INFO)

logging.info("ExecuteRAS module loaded.")


async def main(inputData) -> str:
    try:
        helper_name = inputData.get("helper_name")
        requirement_text = inputData.get("requirement")
        input_type = inputData.get("input_type")

        logging.info("Requirement analysis and standardization starting")
        
        team = await build_selector_groupchat(helper_name, input_type)
        
        final_data = []
        chat_history = []
        frg_messages = []
        stream = team.run_stream(task=requirement_text)

        async for message in stream:
            msg_obj = getattr(message, "message", message)
            chat_history.append(msg_obj)

        serialized_history = []
        agent_token_usage = {}
        for msg in chat_history:
            source = getattr(msg, "source", None)
            content = getattr(msg, "content", None)
            models_usage = getattr(msg, "models_usage", None)

            if source == 'FinalResponseGeneratorAgent':
                frg_messages.append(content)
                if 'TERMINATE' in (content or ''):
                    final_data.append(content)

            if models_usage and source:
                if source not in agent_token_usage:
                    agent_token_usage[source] = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                agent_token_usage[source]["prompt_tokens"] += getattr(models_usage, "prompt_tokens", 0)
                agent_token_usage[source]["completion_tokens"] += getattr(models_usage, "completion_tokens", 0)
                agent_token_usage[source]["total_tokens"] += (
                    getattr(models_usage, "prompt_tokens", 0) +
                    getattr(models_usage, "completion_tokens", 0)
                )

            try:
                json.dumps(content)
            except (TypeError, OverflowError):
                content = str(content)

            serialized_history.append({
                "source": source,
                "content": content
            })

        if not final_data and frg_messages:
            final_data.append(frg_messages[-1])

        # Ensure chat_history is fully JSON-serializable before returning
        safe_history = []
        for entry in serialized_history:
            try:
                json.dumps(entry)
                safe_history.append(entry)
            except (TypeError, OverflowError, ValueError):
                safe_history.append({
                    "source": str(entry.get("source", "")),
                    "content": str(entry.get("content", ""))
                })

        filtered_data = [msg for msg in final_data if msg and msg.strip() != '']
        if filtered_data:
            response = filtered_data[0].rstrip()
            if response.upper().endswith("TERMINATE"):
                response = response[:-len("TERMINATE")].rstrip()
            return {
                "response": response,
                "chat_history": safe_history,
                "agent_token_usage": agent_token_usage
            }
        else:
            return {
                "response": "No valid response found",
                "chat_history": safe_history,
                "agent_token_usage": agent_token_usage
            }

    except Exception as e:
        error_msg = f"Error in RAS helper:  {str(e)}"
        logging.exception(error_msg)
        raise RuntimeError(error_msg)
        

async def build_selector_groupchat(helper_name:str, input_type:str) -> SelectorGroupChat:
    
    builder = RASAgentBuilder(helper_name, input_type)
    requestHandlerAgent = await builder.create_request_handler_agent()
    analyserAgent = await builder.create_analyser_agent()
    reviewerAgent = await builder.create_reviewer_agent()
    finalResponseGeneratorAgent = await builder.create_final_response_generator_agent()
    
    prompt_manager = PromptManager()
    # TODO: move prompt to DB — insert row ('RAS', 'team_prompt') in agent_prompts
    # and replace hardcoded below with:
    #   prompt = prompt_manager.get_prompt(ai_helper_name=helper_name, agent_name='team_prompt')
    # Keep hardcoded import as fallback (same pattern as ExecuteTCG).
    prompt = team_prompt
    
    model_client = LLMConfig().get_model_client()
    termination = TextMessageTermination('TERMINATE') | TextMentionTermination('TERMINATE') | MaxMessageTermination(max_messages=26)
    try:
        team = SelectorGroupChat(
                        [requestHandlerAgent, analyserAgent, reviewerAgent, finalResponseGeneratorAgent],
                        termination_condition=termination, 
                        model_client=model_client,
                        selector_prompt=prompt
                    )
        return team
    except Exception as e:
        error_msg = f"Error in building agent team {str(e)}"
        logging.exception(error_msg)
        raise RuntimeError(error_msg)
