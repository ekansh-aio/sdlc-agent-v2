import logging

from common.jira.jira_client import JiraClient


class JiraTestCaseProcessor:

    def __init__(self, auth_data, base_url):
        """
        Initializes the processor with authentication data.
        
        Args:
            auth_data: Either session cookies (dict) or credentials (dict with 'username' and 'password')
            base_url: Base URL for Jira instance
        """
        self.base_url = base_url
        
        # Determine authentication method
        if isinstance(auth_data, dict) and 'username' in auth_data and 'password' in auth_data:
            # Basic Auth credentials
            self.use_basic_auth = True
            self.username = auth_data['username']
            self.password = auth_data['password']
            self.cookies = None
            logging.info("JiraTestCaseProcessor initialized with Basic Auth")
        else:
            # Session cookies (legacy)
            self.use_basic_auth = False
            self.cookies = auth_data
            self.username = None
            self.password = None
            logging.info("JiraTestCaseProcessor initialized with session cookies")

    def _get_jira_client(self):
        """Get a JiraClient instance with the appropriate authentication."""
        if self.use_basic_auth:
            return JiraClient(self.base_url, self.username, self.password)
        else:
            return JiraClient(self.base_url, None, None, cookies=self.cookies)

    def processing_data_to_jira_manual(self, test_issues, proj_key, parent_key):
        """
        Processes a list of test case data and creates manual test cases in JIRA,
        including their steps, and links each new issue to a specified parent issue.

        Args:
            test_issues (list): A list of dictionaries, each representing a test case.
                         Each dictionary should contain 'Summary', 'Description', 'Priority', and 'ManualSteps'.
            proj_key (str): The JIRA project key where the issues will be created.
            parent_key (str): The key of the parent JIRA issue to which new issues will be linked.

        Returns:

        """
        response_msg = ''
        status_codes = []
        for i in test_issues:
            # Extract test case fields
            summary = i['Summary']
            desc = i['Description'] + "\n\n *Note: This is AI generated content*"
            priority = i['Priority']
            manual_steps = i['ManualSteps']

            # Create a new manual test case issue in JIRA
            new_issue = self._get_jira_client().create_issue(proj_key, summary, desc,
                                                                                                 priority, "Manual")
            status_codes.append(new_issue.status_code)
            new_issue = new_issue.json()
            new_key = new_issue['key']
            insert_msg = f'{new_key} Test Issue Created.'
            response_msg += insert_msg + '\n'
            logging.info(insert_msg)

            # Add each manual test step to the newly created issue
            for step in manual_steps:
                action = step['Action']
                data = step['Data']
                exp_result = step['ExpectedResult'] if 'ExpectedResult' in step else step['Expected Result']

                # Add the test step to the issue
                step_added = self._get_jira_client().add_test_step_manual(new_key,
                                                                                                              action, data,
                                                                                                              exp_result)
                status_codes.append(step_added.status_code)
                if step_added.status_code == 200:
                    steps_msg = f'{new_key} Manual test steps added.'
                    response_msg += steps_msg + '\n'
                    logging.info(steps_msg)

            # Link the new issue to the parent issue
            response = self._get_jira_client().link_issues(parent_key, new_key)
            status_codes.append(response.status_code)
            link_msg = f'{new_key} test issue linked to {parent_key}'
            response_msg += link_msg + '\n'
            logging.info(link_msg)

        # TO DO Proper response return
        status_list = [i for i in status_codes if i > 299]
        return status_list[0] if status_list else 200, response_msg

    def processing_data_to_jira_cucumber(self, test_issues, proj_key, parent_key):
        """
        Processes a list of test case data and creates corresponding 'Cucumber' test issues in Jira.

        Args:
            test_issues (list): A list of dictionaries, each containing test case information with keys:
                         'Summary', 'Description', 'Priority', and 'cucumber_steps'.
            proj_key (str): The Jira project key where the issues should be created.
            parent_key (str): The Jira key of the parent issue to which new issues should be linked.

        Returns:
            None. The function performs operations via Jira API and prints results of each step.
        """
        response_msg = ''
        status_codes = []
        for i in test_issues:
            # Extract individual fields from the input dictionary
            summary = i['Summary']
            desc = i['Description'] + "\n\n *Note: This is AI generated content*"
            priority = i['Priority']

            # Combine cucumber steps into a newline-separated string
            steps = '\n'.join(i['cucumber_steps'])

            # Create a new issue in Jira of type 'Cucumber'
            new_issue = self._get_jira_client().create_issue(proj_key, summary, desc, priority, "Cucumber")

            status_codes.append(new_issue.status_code)
            new_issue = new_issue.json()
            new_key = new_issue['key']
            insert_msg = f'{new_key} Test Issue Created.'
            response_msg += insert_msg + '\n'
            logging.info(insert_msg)

            # Add cucumber test steps to the newly created issue
            cucumber_resp = self._get_jira_client().add_test_cucumber(new_key, steps)
            status_codes.append(cucumber_resp.status_code)
            if cucumber_resp.status_code == 200:
                steps_msg = f'{new_key} Manual test steps added.'
                response_msg += steps_msg + '\n'
                logging.info(steps_msg)


            # Link the new issue to the specified parent issue
            link_isses = self._get_jira_client().link_issues(parent_key, new_key)
            status_codes.append(link_isses.status_code)
            link_msg = f'{new_key} test issue linked to {parent_key}'
            response_msg += link_msg + '\n'
            logging.info(link_msg)

        # TO DO Proper response return
        status_list = [i for i in status_codes if i > 299]
        return status_list[0] if status_list else 200, response_msg
