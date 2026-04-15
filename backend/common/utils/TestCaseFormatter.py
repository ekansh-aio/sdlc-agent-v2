import re
from typing import Dict, List


class TestCaseParser:
    """
    A parser class to convert structured test case text into JSON format for
    cucumber-style and manual test cases.
    """

    @staticmethod
    def convert_sring_to_json_cucumber(text: str) -> List[Dict]:
        """
        Parses a cucumber-style test case string into a list of dictionaries.

        Args:
            text (str): The input text containing cucumber test cases separated by '**********'.

        Returns:
            List[Dict]: A list of parsed test cases with fields like Scenario, Description,
                        Summary, Priority, and cucumber_steps.
        """
        scenarios = []
        scenario_blocks = text.strip().split("**********")

        for block in scenario_blocks:
            block = block.strip()
            if not block:
                continue

            # Extract the main components using regex
            scenario_match = re.search(r"Scenario:(.+)", block)
            description_match = re.search(r"Description:(.+)", block)
            summary_match = re.search(r"Summary:(.+)", block)
            priority_match = re.search(r"Priority:(.+)", block)

            # Extract cucumber_steps section
            cucumber_steps_match = re.search(r"cucumber_steps:(.+)", block, re.DOTALL)
            cucumber_steps = []
            if cucumber_steps_match:
                # Clean and split cucumber steps, removing leading whitespace
                cucumber_steps_raw = cucumber_steps_match.group(1).strip()
                cucumber_steps = [step.strip() for step in cucumber_steps_raw.split('\n') if step.strip()]

            scenario_dict = {
                "Scenario": scenario_match.group(1).strip() if scenario_match else "",
                "Description": description_match.group(1).strip() if description_match else "",
                "Summary": summary_match.group(1).strip() if summary_match else "",
                "Priority": priority_match.group(1).strip() if priority_match else "",
                "cucumber_steps": cucumber_steps
            }

            scenarios.append(scenario_dict)

        return scenarios


    @staticmethod
    def convert_sring_to_json_manual(text: str) -> List[Dict]:
        """
        Parses a manual-style test case string into a list of dictionaries.

        Args:
            text (str): The input text containing manual test cases separated by '**********'.

        Returns:
            List[Dict]: A list of parsed test cases with TestCaseID, Summary, Description,
                        Priority, and ManualSteps.
        """
        # Split input into blocks for each test case
        test_cases_raw = re.split(r'\*{10,}', text)
        parsed_cases = []

        for case in test_cases_raw:
            if not case.strip():
                continue

            case_dict = {}

            # Extract TestCaseID
            match = re.search(r'TestCaseID:(.*?)\n', case)
            if match:
                case_dict['TestCaseID'] = match.group(1).strip()

            # Extract Summary
            match = re.search(r'Summary:(.*?)\n', case)
            if match:
                case_dict['Summary'] = match.group(1).strip()

            # Extract Description
            match = re.search(r'Description:(.*?)\nManualSteps:', case, re.DOTALL)
            if match:
                case_dict['Description'] = match.group(1).strip()

            # Extract Priority
            match = re.search(r'Priority:(.*)', case)
            if match:
                case_dict['Priority'] = match.group(1).strip()

            # Extract Steps
            # steps_raw = re.findall(
            #     r'Step:(\d+)\s+Action:(.*?)\s+Data:(.*?)\s+Expected Result:(.*?)(?=\s+Step:\d+|Priority:|$)',
            #     case, re.DOTALL
            # )

            steps_raw = re.findall(
                r'Action:\s*(.*?)\s+Data:\s*(.*?)\s+Expected Result:\s*(.*?)(?=\s+Action:|\s+Priority:|$)',
                case,
                re.DOTALL
            )

            steps = []
            step_num = 0
            for action, data, expected in steps_raw:
                step_num += 1
                steps.append({
                    "Step": step_num,
                    "Action": action.strip(),
                    "Data": data.strip(),
                    "ExpectedResult": expected.strip()
                })

            case_dict['ManualSteps'] = steps
            parsed_cases.append(case_dict)

        return parsed_cases