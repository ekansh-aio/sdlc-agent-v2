import asyncio
import json
import logging
import re
from autogen_agentchat.conditions import TextMessageTermination, TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import SelectorGroupChat
from agents.tcg.agent_builder import TCGAgentBuilder
from common.jira.jira_request_processor import JiraTestCaseProcessor
from common.utils.TestCaseFormatter import TestCaseParser
from common.prompts.prompt_manager import PromptManager
from common.llm.llm_config import LLMConfig
from common.health_check import run_all_checks

logging.info("ExecuteTCG module loaded.")

test_parser = TestCaseParser()
_model_client = None

def _get_model_client():
    global _model_client
    if _model_client is None:
        _model_client = LLMConfig().get_model_client()
    return _model_client
termination = TextMessageTermination('TERMINATE') | TextMentionTermination('TERMINATE')| MaxMessageTermination(max_messages=16)


from common.prompts.tcg_prompts import team_prompt as _fallback_team_prompt
team_prompt = _fallback_team_prompt  # default; overridden on first invocation if DB is available

_team_prompt_loaded = False

def _load_team_prompt_if_needed():
    global team_prompt, _team_prompt_loaded
    if _team_prompt_loaded:
        return
    _team_prompt_loaded = True
    try:
        prompt = PromptManager().get_prompt(ai_helper_name='TCG', agent_name='team_prompt')
        team_prompt = prompt
        logging.info("ExecuteTCG: loaded team_prompt from database")
    except Exception as _prompt_err:
        logging.warning(
            f"ExecuteTCG: could not load 'team_prompt' from DB — using hardcoded fallback. Error: {_prompt_err}"
        )



# team_prompt = """
#     You are a supervisor who is co-ordinating team of professionals:
#     yo are supervising professionals with below roles
#     {roles}.
#     you will be provided the conversation between the participants
#     current conversation context : {history}
#     Read the above conversation.
#     Then select the next role from {participants} to work on.
#     thoroughly analysing the conversation, understand the context and return the role.
#     Note:-Only return the role.
#     context on the roles:
#     * "request_handler_agent" is the first agent in the team who will receive the user input and Respond only once per workflow.
#     * "analyser_agent" is the testing expert tasked with generating test cases.
#     * "reviewer_agent" is the quality reviewer of test cases.
#     * "final_response_generator_agent" is the last agent in the team who will finalize the output only when
#       "reviewer_agent" confirms finalResult = "SUCCESS".
#     """



class TestCaseProcessor:
    """
    A class to process and generate manual and cucumber test cases using a multi-agent system,
    and creat, update, linking corresponding Jira issues.
    """

    def __init__(self, issue_type):
        self.issue_type = issue_type
        self.result = "No data return from LLM"
        self.final_response = {}
        self.serialized_history = []
        self.agent_token_usage = {}

    def process_test_issues(self, user_qry):
        """
        Process a list of Jira issues to generate Manual test cases.
        """
        if user_qry.strip():
            async def process_team():
                """
                Runs the team agent conversation to generate test cases.
                """
                request_handler_agent = TCGAgentBuilder(self.issue_type).create_request_handler_agent()
                analyser_agent = TCGAgentBuilder(self.issue_type).create_analyser_agent()
                reviewer_agent = TCGAgentBuilder(self.issue_type).create_reviewer_agent()
                final_response_generator_agent = TCGAgentBuilder(
                    self.issue_type).create_final_response_generator_agent()
                team = SelectorGroupChat(
                    [request_handler_agent, analyser_agent, reviewer_agent, final_response_generator_agent],
                    termination_condition=termination, max_turns=26, model_client=_get_model_client(),
                    selector_prompt=team_prompt
                )

                display_data = ''
                final_data = []
                chat_history = []
                filter_data = []

                # Run the multi-agent conversation
                stream = team.run_stream(task=user_qry)
                async for message in stream:
                    chat_history.append(message)
                    source = getattr(message, "source", None)
                    content = getattr(message, "content", None)
                    models_usage = getattr(message, "models_usage", None)

                    if models_usage and source:
                        if source not in self.agent_token_usage:
                            self.agent_token_usage[source] = {
                                "prompt_tokens": 0,
                                "completion_tokens": 0,
                                "total_tokens": 0
                            }
                        self.agent_token_usage[source]["prompt_tokens"] += getattr(models_usage, "prompt_tokens", 0)
                        self.agent_token_usage[source]["completion_tokens"] += getattr(models_usage,
                                                                                       "completion_tokens", 0)
                        self.agent_token_usage[source]["total_tokens"] += (
                                getattr(models_usage, "prompt_tokens", 0) +
                                getattr(models_usage, "completion_tokens", 0)
                        )
                    try:
                        json.dumps(content)
                    except (TypeError, OverflowError):
                        content = str(content)
                    self.serialized_history.append({
                        "source": source,
                        "content": content
                    })

                for msg in chat_history:
                    try:
                        if msg.source == 'final_response_generator_agent':
                            final_data.append(msg.content)
                    except:
                        pass

                # Keep a raw copy of the agent's JSON block for fallback
                raw_json_block = ""
                try:
                    filter_data = [i for i in final_data if "```json" in i]
                    if filter_data:
                        raw_json_block = filter_data[0]

                    # Extract JSON from the code fence — handle both ```json{ and ```json\n{
                    raw_content = filter_data[0]
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_content, re.DOTALL)
                    if not json_match:
                        raise ValueError("No JSON block found in agent output")
                    parsed = json.loads(json_match.group(1))

                    # Support both finalData and finalResponse.finalData
                    lst_of_tests = (
                        parsed.get('finalData')
                        or parsed.get('finalResponse', {}).get('finalData')
                    )
                    if not lst_of_tests:
                        raise ValueError(f"No finalData key in parsed JSON: {list(parsed.keys())}")
                    idx = 0
                    tests_len = len(lst_of_tests)
                    if self.issue_type in ['text_manual', 'Manual']:
                        for txt in lst_of_tests:
                            idx += 1
                            all_str = ''
                            for key in txt.keys():
                                if key != 'ManualSteps':
                                    all_str += key + ':' + str(txt[key]) + '\n'
                                else:
                                    all_str += 'ManualSteps: \n'
                                    for nested_data in txt[key]:
                                        if not isinstance(nested_data, dict):
                                            all_str += '    ' + str(nested_data) + '\n'
                                            continue
                                        # Handle {"Step": {"Action":...}} and flat {"Action":...} both
                                        step_content = nested_data.get('Step', nested_data)
                                        if isinstance(step_content, dict):
                                            for sub_key, sub_val in step_content.items():
                                                all_str += '    ' + sub_key + ': ' + str(sub_val) + '\n'
                                        else:
                                            for nested_key, nested_val in nested_data.items():
                                                all_str += '    ' + nested_key + ': ' + str(nested_val) + '\n'
                            display_data += (all_str + ('\n ********** \n' if idx != tests_len else ''))
                        self.result = display_data
                    else:
                        for txt in lst_of_tests:
                            idx += 1
                            all_str = ''
                            for key in txt.keys():
                                if key == 'cucumber_steps' and isinstance(txt[key], list):
                                    all_str += key + ':' + '\n'.join(txt[key]) + '\n'
                                else:
                                    all_str += key + ':' + str(txt[key]) + '\n'
                            display_data += (all_str + ('\n ********** \n' if idx != tests_len else ''))
                        self.result = display_data
                    logging.info(f"TCG parsed {len(lst_of_tests)} test cases successfully.")
                    # Fallback: if formatted output is empty, use the raw JSON block
                    if not self.result and raw_json_block:
                        self.result = raw_json_block
                except Exception as _parse_err:
                    logging.exception(f"TCG response parsing failed: {_parse_err}")
                    # Fall back to raw JSON block so the user sees something
                    self.result = raw_json_block if raw_json_block else f"Parsing error: {_parse_err}"

                # Ensure chat_history is fully JSON-serializable before returning
                safe_history = []
                for entry in self.serialized_history:
                    try:
                        json.dumps(entry)
                        safe_history.append(entry)
                    except (TypeError, OverflowError, ValueError):
                        safe_history.append({
                            "source": str(entry.get("source", "")),
                            "content": str(entry.get("content", ""))
                        })

                self.final_response = {
                    "response": self.result or ("No test cases parsed — check agent output." if filter_data else "No filter_data from agent."),
                    "chat_history": safe_history,
                    "agent_token_usage": self.agent_token_usage
                }

            asyncio.run(process_team())
            return self.final_response



    def create_test_issues(self, issue_data, parent_key, session, base_url, proj_key):
        """
        Create test issues in Jira based on the issue type.

        This function processes the provided issue data and creates corresponding
        Jira issues either as manual test cases or cucumber-style test cases,
        depending on the format of the input.

        :param issue_data: Either a string "Manual" to indicate manual test cases,
                           or data representing cucumber test cases.
        :param parent_key: The Jira issue key under which the test cases will be created.
        :param session: The requests session object used for making HTTP requests to Jira.
        :param base_url: The base URL of the Jira instance.
        :param proj_key: The key of the Jira project where the issues will be created.
        """
        if self.issue_type == "Manual":
            # Convert the manual test issue data from string to JSON format
            json_data = test_parser.convert_sring_to_json_manual(issue_data)
            # Processing the manual test issues to Jira for creating , updating and linking Jira issues
            status_code, response_msg = JiraTestCaseProcessor(session, base_url).processing_data_to_jira_manual(json_data,proj_key,
                                                                                               parent_key)
            return status_code, response_msg
        else:
            # Convert the automatic test issue data from string to JSON format
            json_data = test_parser.convert_sring_to_json_cucumber(issue_data)
            # Processing the automatic test issues to Jira for creating , updating and linking Jira issues
            status_code, response_msg = JiraTestCaseProcessor(session, base_url).processing_data_to_jira_cucumber(json_data,
                                                                                                 proj_key, parent_key)
            return status_code, response_msg



def main(inputData):
    _load_team_prompt_if_needed()
    issue_type = inputData.get("issue_type", None)
    input_type = inputData.get("input_type", None)
    request_data = inputData.get("request_data", None)
    process_type = inputData.get("process_type", None)
    jira_session = inputData.get("jira_session", None)
    base_url = inputData.get("base_url", None)
    proj_key = inputData.get("proj_key", None)
    jira_id = inputData.get("jira_id", None)


    if process_type == 'get_data':
        response = TestCaseProcessor(issue_type).process_test_issues(request_data)
        return response
    else:

        status_code, response_msg = TestCaseProcessor(issue_type).create_test_issues(request_data, jira_id, jira_session, base_url,
                                                                    proj_key)
        return status_code, response_msg