import asyncio
import logging
from common.utils.TestCaseFormatter import TestCaseParser
from common.jira.jira_request_processor import JiraTestCaseProcessor
from common.jira.jira_client import JiraClient


    
# def update_jira( title, description, acceptance_criteria, jira_id, jira_session, base_url, proj_key):
#     try:
#         client = JiraClient(base_url, None, None, cookies=jira_session)
#         #client.update_jira_issue(jira_id, title, description, acceptance_criteria)
#         response = client.update_jira_issue(jira_id, title, description, acceptance_criteria)
#         return response
#     except Exception as e:
#         error_msg = "Error pushing to Jira : " + str(e)
#         return error_msg

def create_test_issues(issue_data, parent_key, session, base_url, proj_key, issue_type):
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
    test_parser = TestCaseParser()
    if issue_type == "Manual":
        # Convert the manual test issue data from string to JSON format
        json_data = test_parser.convert_sring_to_json_manual(issue_data)
        # Processing the manual test issues to Jira for creating , updating and linking Jira issues
        status_code, success_msg = JiraTestCaseProcessor(session, base_url).processing_data_to_jira_manual(json_data,proj_key,
                                                                                           parent_key)
    else:
        # Convert the automatic test issue data from string to JSON format
        json_data = test_parser.convert_sring_to_json_cucumber(issue_data)
        # Processing the automatic test issues to Jira for creating , updating and linking Jira issues
        status_code, success_msg = JiraTestCaseProcessor(session, base_url).processing_data_to_jira_cucumber(json_data,
                                                                                             proj_key, parent_key)
    return status_code, success_msg


def main(inputData) -> any:

    try:
        helper_name = inputData.get("helper_name", None)
        issue_type = inputData.get("issue_type", None)
        base_url = inputData.get("base_url", None)
        jira_username = inputData.get("jira_username", None)
        jira_password = inputData.get("jira_password", None)
        # Keep old jira_session for backward compatibility, but prefer new auth
        jira_session = inputData.get("jira_session", None)
        request_data = inputData.get("request_data", None)
        jira_id = inputData.get("jira_id", None)
        proj_key = inputData.get("proj_key", None)

        title = inputData.get("title", None)
        description = inputData.get("description", None)
        acceptance_criteria = inputData.get("acceptance_criteria", None)

        # Validate required parameters for RAS
        if helper_name == "RAS":
            if not base_url:
                return 400, "Missing required parameter: base_url"
            if not jira_username or not jira_password:
                if not jira_session:  # Fallback to session if no basic auth provided
                    return 401, "Missing required parameter: jira_username and jira_password (authentication required)"
            if not jira_id:
                return 400, "Missing required parameter: jira_id"
            if not title and not description:
                return 400, "At least title or description must be provided"
                
            logging.info(f"Processing RAS push to Jira for issue: {jira_id}")
            logging.info(f"Base URL: {base_url}")
            logging.info(f"Using Basic Auth: {bool(jira_username and jira_password)}")
            
        if helper_name == "RAS":
            # Handle RAS push to Jira
            try:
                logging.info(f"Creating JiraClient with base_url: {base_url}")
                logging.info(f"Title: {title}")
                logging.info(f"Description length: {len(description) if description else 0}")
                logging.info(f"Acceptance criteria length: {len(acceptance_criteria) if acceptance_criteria else 0}")

                # Use Basic Auth if available, otherwise fall back to session cookies
                if jira_username and jira_password:
                    logging.info("Using Basic Auth credentials")
                    client = JiraClient(base_url, jira_username, jira_password)
                else:
                    logging.info("Using session cookies")
                    client = JiraClient(base_url, None, None, cookies=jira_session)

                logging.info(f"Calling update_jira_issue for {jira_id}")
                status_code, response_msg = client.update_jira_issue(jira_id, title, description, acceptance_criteria)
                logging.info(f"Jira update result: Status={status_code}, Message={response_msg}")

                if status_code == 204:
                    logging.info(f"Successfully updated Jira issue {jira_id}")
                else:
                    logging.warning(f"Jira update returned non-success status: {status_code}")

                return status_code, response_msg
            except Exception as e:
                error_msg = f"Error pushing RAS to Jira: {str(e)}"
                logging.error(error_msg, exc_info=True)
                return 500, error_msg
        elif helper_name == "TCG":
            # For TCG, we also need to update to use Basic Auth
            if jira_username and jira_password:
                # Pass credentials for Basic Auth
                status_code, success_msg = create_test_issues(request_data, jira_id, 
                                                            {'username': jira_username, 'password': jira_password}, 
                                                            base_url, proj_key, issue_type)
            else:
                # Fall back to session cookies
                status_code, success_msg = create_test_issues(request_data, jira_id, jira_session, 
                                                            base_url, proj_key, issue_type)
            return status_code, success_msg

    except Exception as e:
        error_msg = "Error in PG Service access: " + str(e)
        logging.exception(error_msg)
        return error_msg