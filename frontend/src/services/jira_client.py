import requests
import logging
import json
from requests.auth import HTTPBasicAuth
import base64
import streamlit as st


class JiraClient:
    def __init__(self, base_url: str):
        """
        Initialize Jira client with base URL and auth
        """
        self.base_url = base_url
        self.user = None
        self.password = None
        self.basic_auth = None
        self.headers = {}
        
        
        
    def set_credentials(self,user: str, password: str):
        self.user = user
        self.password = password
        # Encode credentials for Basic Auth
        self.basic_auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        # Request Headers
        self.headers = {
            "Authorization": f"Basic {self.basic_auth}",
            "X-Atlassian-Token": "nocheck",
            "Content-Type": "application/json"
        }
        
    def authenticate_user(self) -> bool:
        """
        authenticate jira user by calling myself api. Return true is success else raises exception.
        """
        url = f"{self.base_url}/rest/api/2/myself"
        response = requests.get(url, headers =self.headers,verify=False)
        if response.status_code == 200:
            user = response.json()
            logging.info(f"Authenticated Jira user: {user['displayName']}")
            st.success(f"Authenticated Jira user: **{user['displayName']}**")
            return True
        elif response.status_code == 401:
            logging.warning(f"Authentication failed: Invalid username or password")
            st.warning(f"Authentication failed: Invalid username or password")
            return False
        else:
            logging.error(f"Authentication failed: {response.status_code} - {response.text}")
            st.warning(f"Authentication failed: {response.text}")
            return False

    def get_accessible_issues(self, issues_types: list[str] ) -> list[str]:
        """
        fetch all jira ids that are accessible to the user
        """
        
        issue_type_query = ", ".join([f'"{type}"' for type in issues_types])
        jql = f"issuetype in ({issue_type_query}) order by updated DESC"

        url = f"{self.base_url}/rest/api/2/search"
        start_at = 0
        all_issue_keys = []
        max_results = st.session_state.jira_ids_max_results
        try:
            while True:
                params = {
                    "jql" : jql,
                    "fields": "key,issuetype",
                    "startAt": start_at,
                    "maxResults": max_results
                }
                response = requests.get(url, headers=self.headers, params=params,verify=False)
                if response.status_code == 200:
                    data = response.json()
                    issues = data.get("issues",[])
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

        
        

    def get_jira_issue(self):
        """Prompt user for Jira issue ID."""
        return input("Enter Jira Issue ID (e.g., AIHQE-2): ")

    def fetch_issue_details(self, jira_id):
        """Fetch issue details from Jira."""
        issue_url = f"{self.base_url}/rest/api/2/issue/{jira_id}"
        print("issue_url: ", issue_url)
        response = requests.get(issue_url, headers=self.headers, verify=False)
        print("response: ", response.status_code)
        if response.status_code == 200:
            print("response: ", response.status_code)
            issue_data = response.json()
            project_name = issue_data["fields"]["project"]["name"]
            description = issue_data["fields"].get("description", "No Description Available")
            summary = issue_data["fields"]["summary"]
            st.write(f"🔹 Project: {project_name}")
            st.write(f"🔹 Summary: {summary}")
            st.write(f"🔹 Description: {description}")
            print("tet")
            return  issue_data["key"],  summary, description
        elif response.status_code == 401:
            print("Authentication failed: Invalid credentials or missing permissions.")
        else:
            print(f"Request failed ({response.status_code}): {response.text}")

        return  None, None, None

    def update_jira_issue(self,headers,jira_id, agent_title, agent_description):
        """Update the Jira issue with the refined title and description."""
        issue_url = f"{self.base_url}/rest/api/2/issue/{jira_id}"
        
        payload = {
            "fields": {
                "summary": agent_title,
                "description": agent_description
            }
        }

        response = requests.put(issue_url, headers=headers, data=json.dumps(payload),verify=False)
        if response.status_code == 204:
            st.write(f"\n🔹Jira issue: {jira_id} updated successfully! {self.base_url}browse/{jira_id}")
        else:
            print(f"Failed to update issue ({response.status_code}): {response.text}")


    def login(self):
        """
        Authenticate with Jira and establish a session.

        On successful login, session cookies
        """
        url = f'{self.base_url}/rest/auth/1/session'
        auth_data = {
            'username': self.user,
            'password': self.password
        }

        response = requests.post(url, json=auth_data, verify=False)

        if response.status_code == 200:
            # Store session info and cookies
            self.session_info = response.json()['session']
            self.cookies = {'JSESSIONID': self.session_info['value']}
            logging.info("Session created:", self.session_info)
            return self.cookies  # Fixed: return cookies instead of headers
        else:
            logging.info("Failed to create session:", response.text)
            return None

       