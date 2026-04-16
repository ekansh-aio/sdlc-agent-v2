import threading
import time

import requests
import logging
import json

import base64


def _to_adf(text: str) -> dict:
    """
    Convert a plain-text string to Atlassian Document Format (ADF).
    Required by Jira Cloud REST API v3 for description and comment body fields.
    Preserves line breaks by splitting on newlines into separate paragraph nodes.
    """
    if not text:
        return {"version": 1, "type": "doc", "content": []}

    paragraphs = []
    for line in text.splitlines():
        if line.strip():
            paragraphs.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line}]
            })
        else:
            paragraphs.append({"type": "paragraph", "content": []})

    return {"version": 1, "type": "doc", "content": paragraphs or [{"type": "paragraph", "content": []}]}


def _from_adf(adf) -> str:
    """
    Extract plain text from an ADF node (for reading description/comments back).
    """
    if adf is None:
        return ""
    if isinstance(adf, str):
        return adf
    if not isinstance(adf, dict):
        return str(adf)

    def _walk(node) -> str:
        if node.get("type") == "text":
            return node.get("text", "")
        parts = [_walk(child) for child in node.get("content", [])]
        joined = "".join(parts)
        if node.get("type") in ("paragraph", "heading", "bulletList", "orderedList", "listItem", "blockquote", "codeBlock"):
            joined += "\n"
        return joined

    return _walk(adf).strip()


class JiraClient:
    """
       A class to manage Jira sessions using basic authentication.
       This includes login, logout, automatic session timeout, and
       utility methods like  creating and managing issues,
       specifically aimed at test case management using Jira endpoints.
       """

    def __init__(self, base_url=None, username=None, password=None, cookies=None):
        """
        Initialize Jira client with base URL and auth
        """
        self.basic_auth = None
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session_info = None
        self.cookies = cookies
        self.logout_timer = None
        self.headers = {'Content-Type': 'application/json'}
        self.default_message = json.dumps({'msg': 'Not logged in. Call login() first.'})

        # Set up Basic Auth if credentials are provided
        if username and password:
            self.set_credentials(username, password)

    def set_credentials(self, username: str, password: str):
        self.username = username
        self.password = password
        # Encode credentials for Basic Auth
        self.basic_auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        # Request Headers
        self.headers = {
            "Authorization": f"Basic {self.basic_auth}",
            "X-Atlassian-Token": "nocheck",
            "Content-Type": "application/json"
        }

    def authenticate_user(self) -> bool:
        """
        authenticate jira username by calling myself api. Return true is success else raises exception.
        """
        url = f"{self.base_url}/rest/api/3/myself"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            username = response.json()
            logging.info(f"Authenticated Jira username: {username['displayName']}")
            return True
        elif response.status_code == 401:
            logging.warning(f"Authentication failed: Invalid username or password")
            return False
        else:
            logging.error(f"Authentication failed: {response.status_code} - {response.text}")
            return False

    def get_accessible_issues(self, issues_types: list[str]) -> list[str]:
        """
        fetch all jira ids that are accessible to the username
        """

        issue_type_query = ", ".join([f'"{type}"' for type in issues_types])
        jql = f"issuetype in ({issue_type_query}) order by updated DESC"

        url = f"{self.base_url}/rest/api/3/search/jql"
        start_at = 0
        all_issue_keys = []
        max_results = 200
        try:
            while True:
                params = {
                    "jql": jql,
                    "fields": "key,issuetype",
                    "startAt": start_at,
                    "maxResults": max_results
                }
                response = requests.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    issues = data.get("issues", [])
                    issue_keys = [issue["key"] for issue in issues]
                    all_issue_keys.extend(issue_keys)

                    if start_at + max_results >= data.get("total", 0):
                        break
                    else:
                        start_at += max_results
                else:
                    logging.error(f"Failed to fetch issues: {response.status_code} - {response.text}")
                    break

            logging.info(f"Total filtered issues fetched: {len(all_issue_keys)}")
            return all_issue_keys
        except requests.RequestException:
            logging.exception("Error occured while fetching filtered issue.")
            raise

    def fetch_issue_details(self, jira_id):
        """Fetch issue details from Jira."""
        issue_url = f"{self.base_url}/rest/api/3/issue/{jira_id}"
        response = requests.get(issue_url, headers=self.headers, verify=False)
        if response.status_code == 200:
            issue_data = response.json()
            project_name = issue_data["fields"]["project"]["name"]
            # API v3 returns description as ADF — extract plain text
            description = _from_adf(issue_data["fields"].get("description")) or "No Description Available"
            summary = issue_data["fields"]["summary"]
            logging.info(f"Fetched {jira_id} — project={project_name}, summary={summary}")
            return issue_data["key"], summary, description
        elif response.status_code == 401:
            logging.warning(f"Authentication failed fetching {jira_id}")
        else:
            logging.error(f"Request failed ({response.status_code}): {response.text}")

        return None, None, None

    def update_jira_issue(self, jira_id, agent_title, agent_description, acceptance_criteria):
        """Update the Jira issue with the refined title and description."""
        
        # Check authentication method
        if self.username and self.password:
            # Use Basic Auth (preferred for API tokens)
            use_basic_auth = True
            auth_headers = self.headers.copy()  # Already contains Basic Auth
            logging.info("Using Basic Auth for Jira update")
        elif self.cookies:
            # Fall back to session cookies
            use_basic_auth = False
            if not isinstance(self.cookies, dict) or 'JSESSIONID' not in self.cookies:
                return 401, "Invalid session format. Expected cookies dict with JSESSIONID."
            auth_headers = {'Content-Type': 'application/json'}
            logging.info("Using session cookies for Jira update")
        else:
            return 401, "Not authenticated. No valid credentials or session cookies found."
            
        issue_url = f"{self.base_url}/rest/api/3/issue/{jira_id}"

        # Build payload with only valid Jira fields, handling None values
        # API v3 requires ADF for description
        fields = {}
        if agent_title is not None and str(agent_title).strip():
            fields["summary"] = str(agent_title).strip()
        if agent_description is not None and str(agent_description).strip():
            fields["description"] = _to_adf(str(agent_description).strip())

        if not fields:
            return 400, "No valid fields to update. Both title and description are empty or None."

        payload = {"fields": fields}

        logging.info(f"Updating Jira issue {jira_id} with payload: {json.dumps(payload, indent=2)}")
        
        try:
            logging.info(f"Making PUT request to {issue_url}")
            logging.info(f"Authentication method: {'Basic Auth' if use_basic_auth else 'Session Cookies'}")

            if use_basic_auth:
                # Use Basic Auth headers
                response = requests.put(
                    issue_url,
                    headers=auth_headers,
                    data=json.dumps(payload),
                    verify=False,
                    timeout=30
                )
            else:
                # Use session cookies for authentication
                response = requests.put(
                    issue_url,
                    cookies=self.cookies,
                    data=json.dumps(payload),
                    headers=auth_headers,
                    verify=False,
                    timeout=30
                )

            logging.info(f"Jira API response: Status={response.status_code}")
            logging.info(f"Response headers: {dict(response.headers)}")

            if response.status_code == 204:
                # Successfully updated
                logging.info(f"Successfully updated Jira issue {jira_id}")

                # Add acceptance criteria as a comment if provided
                if acceptance_criteria and acceptance_criteria.strip():
                    logging.info(f"Adding acceptance criteria as comment to {jira_id}")
                    self._add_comment(jira_id, f"Acceptance Criteria:\n{acceptance_criteria}")

                return_message = f"Successfully updated Jira issue {jira_id}"
                return response.status_code, return_message

            elif response.status_code == 400:
                error_details = "Bad Request - Invalid field values or missing required fields"
                try:
                    error_json = response.json()
                    if 'errors' in error_json:
                        error_details = f"Field errors: {error_json['errors']}"
                    elif 'errorMessages' in error_json:
                        error_details = f"Error messages: {error_json['errorMessages']}"
                except:
                    error_details = f"Bad Request: {response.text}"

                return_message = f"Failed to update issue {jira_id} - {error_details}"
                logging.error(return_message)
                return response.status_code, return_message

            elif response.status_code == 401:
                return_message = f"Authentication failed for issue {jira_id} - Check credentials"
                logging.error(return_message)
                return response.status_code, return_message

            elif response.status_code == 403:
                return_message = f"Permission denied for issue {jira_id} - Check user permissions"
                logging.error(return_message)
                return response.status_code, return_message

            elif response.status_code == 404:
                return_message = f"Issue {jira_id} not found - Check issue key"
                logging.error(return_message)
                return response.status_code, return_message

            else:
                return_message = f"Failed to update issue {jira_id} ({response.status_code}): {response.text}"
                logging.error(return_message)
                return response.status_code, return_message

        except requests.exceptions.Timeout:
            error_message = f"Timeout while updating Jira issue {jira_id}"
            logging.error(error_message)
            return 408, error_message

        except requests.exceptions.ConnectionError:
            error_message = f"Connection error while updating Jira issue {jira_id}"
            logging.error(error_message)
            return 503, error_message

        except Exception as e:
            error_message = f"Unexpected exception during Jira update for {jira_id}: {str(e)}"
            logging.error(error_message, exc_info=True)
            return 500, error_message

    def login(self):
        """
        Authenticate with Jira and establish a session.

        On successful login, session cookies are stored and a timer
        is started to automatically log out after 120 seconds.
        """
        url = f'{self.base_url}/rest/auth/1/session'
        auth_data = {
            'username': self.username,
            'password': self.password
        }

        response = requests.post(url, json=auth_data)

        if response.status_code == 200:
            # Store session info and cookies
            self.session_info = response.json()['session']
            self.cookies = {'JSESSIONID': self.session_info['value']}
            logging.info("Session created:", self.session_info)

            # Start auto-logout timer
            self.start_logout_timer()
            return self.cookies
        else:
            logging.info("Failed to create session:", response.text)

    def start_logout_timer(self):
        """
        Start a 120-second timer to automatically log out the user.

        Cancels any existing timer to prevent multiple timers running simultaneously.
        """
        if self.logout_timer is not None:
            self.logout_timer.cancel()  # Cancel existing timer

        # Start new timer
        self.logout_timer = threading.Timer(120, self.logout)
        self.logout_timer.start()
        print('time extended')

    def get_user_info(self):
        """
        Fetch details about the currently authenticated user.

        Returns:
            dict: JSON response containing user information if successful.
        """
        if not self.cookies:
            logging.info("Not logged in. Call login() first.")
            return None
        url = f'{self.base_url}/rest/api/3/myself'
        user_info_response = self.execute_jira_request_until_sucess(url, 'get')

        if user_info_response.status_code == 200:
            return user_info_response.json()
        else:
            logging.info(f"Failed to fetch user info: {user_info_response.text}")
            return None

    def get_issue_data(self, issue_key):
        """
        Fetch issue details by its key.

        Args:
            issue_key (str): Key of the Jira issue (e.g., 'AIHQE-120')

        Returns:
            dict: JSON response with issue data if successful.
        """
        if not self.cookies:
            logging.info("Not logged in. Call login() first.")
            return None
        url = f'{self.base_url}/rest/api/3/issue/{issue_key}'
        issue_response = self.execute_jira_request_until_sucess(url, 'get')

        if issue_response.status_code == 200:
            return issue_response.json()
        else:
            logging.info(f"Failed to fetch issue {issue_key}: {issue_response.text}")
            return None

    def logout(self):
        """
        Clear the current session and cookies.

        Called automatically after 120 seconds or can be invoked manually.
        """
        if self.cookies:
            self.session_info = None
            self.cookies = None
            logging.info("Session closed after 120 seconds.")
        else:
            logging.info("No active session to close.")

    def cancel_logout_timer(self):
        """
        Cancel the auto-logout timer manually if needed.
        """
        if self.logout_timer is not None:
            self.logout_timer.cancel()
            logging.info("Logout timer cancelled.")

    def create_issue(self, project_key, summary, description, priority, test_type):
        """
        Create a new Jira issue of type 'Test'.

        :param project_key: Key of the Jira project (e.g., "PROJ")
        :param summary: Summary/title of the issue
        :param description: Description of the issue
        :param priority: Priority level (e.g., "High", "Medium", "Low")
        :param test_type: Type of test ("Manual" or "Cucumber")
        :return: JSON response from the Jira API containing the new issue details
        """
        url = f"{self.base_url}/rest/api/3/issue/"
        if not self.cookies:
            return self.default_message
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": _to_adf(description),
                "issuetype": {"name": "Test"},
                "priority": {"name": priority},
                "customfield_10125": {
                    "value": test_type  # This custom field may vary by Jira setup
                }
            }
        }
        response = self.execute_jira_request_until_sucess(url, 'post', payload)
        return response

    def add_test_step_manual(self, issue_key, step, data, result):
        """
        Add a manual test step to a test case in Jira using Xray API.

        :param issue_key: Key of the Jira test issue (e.g., "PROJ-123")
        :param step: Test step action
        :param data: Test data associated with the step
        :param result: Expected result of the step
        :return: Response object from the PUT request
        """
        if not self.cookies:
            return self.default_message
        url = f"{self.base_url}/rest/raven/1.0/api/test/{issue_key}/step"
        payload = {
            "step": step,
            "data": data,
            "result": result,
        }
        response = self.execute_jira_request_until_sucess(url, 'put', payload)
        return response

    def add_test_cucumber(self, issue_key, cucumber_data):
        """
        Add Cucumber-style test definition to a Jira issue.

        :param issue_key: Key of the Jira test issue
        :param cucumber_data: String representing the Cucumber feature or scenario
        :return: Response object from the PUT request
        """
        if not self.cookies:
            return self.default_message
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        payload = {
            "fields": {
                "customfield_10127": cucumber_data  # Custom field for Cucumber data
            }
        }
        response = self.execute_jira_request_until_sucess(url, 'put', payload)
        return response

    def link_issues(self, parent_key, child_key, link_type="Tests", comment="Linked test to story via API"):
        """
        Link two Jira issues together using a specified link type.

        :param parent_key: Key of the parent issue (e.g., user story or epic)
        :param child_key: Key of the child issue (e.g., test case)
        :param link_type: Type of issue link (default is "Tests")
        :param comment: Optional comment to include with the link
        :return: Response object from the POST request
        """
        if not self.cookies:
            return self.default_message
        url = f"{self.base_url}/rest/api/3/issueLink"
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": child_key},
            "outwardIssue": {"key": parent_key}
        }
        response = self.execute_jira_request_until_sucess(url, 'post', payload)
        return response

    def get_jira_issue_details(self, jira_id):
        """
        Retrieve details of a specific Jira issue.

        :param jira_id: Key of the Jira issue
        :return: Response object containing issue details
        """
        if not self.cookies:
            return self.default_message
        issue_url = f"{self.base_url}/rest/api/3/issue/{jira_id}"
        response = self.execute_jira_request_until_sucess(issue_url, 'get')
        return response

    def update_jira_issue_details(self, jira_id, summary, description, acceptance_criteria):
        """
        Update summary and description of an existing Jira issue.

        :param jira_id: Key of the Jira issue
        :param summary: New summary for the issue
        :param description: New description for the issue
        :return: Response object from the PUT request
        """
        if not self.cookies:
            return self.default_message
        url = f"{self.base_url}/rest/api/3/issue/{jira_id}"
        payload = {
            "fields": {
                "summary": summary,
                "description": description,
                "acceptance_criteria": acceptance_criteria
            }
        }
        response =  self.execute_jira_request_until_sucess(url, 'put', payload)
        return response

    def _add_comment(self, jira_id, comment_text):
        """Add a comment to a Jira issue."""
        try:
            comment_url = f"{self.base_url}/rest/api/3/issue/{jira_id}/comment"
            # API v3 requires ADF for comment body
            comment_payload = {
                "body": _to_adf(comment_text)
            }
            
            # Use the same authentication method as update_jira_issue
            if self.username and self.password:
                # Use Basic Auth
                response = requests.post(
                    comment_url,
                    headers=self.headers,
                    data=json.dumps(comment_payload),
                    verify=False
                )
            else:
                # Use session cookies
                response = requests.post(
                    comment_url,
                    cookies=self.cookies,
                    data=json.dumps(comment_payload),
                    headers={'Content-Type': 'application/json'},
                    verify=False
                )
            
            if response.status_code != 201:
                logging.warning(f"Failed to add comment to {jira_id}: {response.status_code} - {response.text}")
            else:
                logging.info(f"Successfully added comment to {jira_id}")
                
        except Exception as e:
            logging.error(f"Exception while adding comment to {jira_id}: {str(e)}")

    def execute_jira_request_until_sucess(self, url, request_type, payload=None):
        try:
            time.sleep(3)
            # Use proper headers and cookies separately
            headers = {'Content-Type': 'application/json'}
            
            if request_type == 'get':
                response = requests.get(url, headers=headers, cookies=self.cookies, verify=False)
            elif request_type == 'post':
                response = requests.post(url, headers=headers, cookies=self.cookies, data=json.dumps(payload), verify=False)
            else:  # PUT request
                response = requests.put(url, headers=headers, cookies=self.cookies, data=json.dumps(payload), verify=False)
                
            if response.status_code in [401]:
                logging.warning(f"Authentication failed (401) for {url}, retrying...")
                return self.execute_jira_request_until_sucess(url, request_type, payload)
            else:
                return response
        except Exception as e:
            logging.error(f"Exception in execute_jira_request_until_sucess: {str(e)}")
            return self.execute_jira_request_until_sucess(url, request_type, payload)
