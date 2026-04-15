import streamlit as st
import time
import json
from utils.css_loader import load_css
from utils.session_manager import initialize_session_state
from components.sidebar import sidebar_display
from components.buttons import button_container, clipboard_button
from services.jira_client import JiraClient
from components.jira_auth import jira_auth
import requests
import urllib3
import warnings

# Suppress SSL warnings for Jira connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
import re
import os
from dotenv import load_dotenv
from streamlit_extras.stylable_container import stylable_container
from components.emoji_rating import emoji_rating
from components.star_rating import star_rating
from components.dialogs import chat_dialog
import streamlit.components.v1 as cp
from utils.pgdb_operations import log_user_request, log_user_feedback
import logging
import base64
load_dotenv()

#Get Azure finction name from .env file
azure_function_app = os.getenv("AZURE_FUNCTION_APP","")

def placeholder_for_agent(payload=None):
    print("Jira Session: ", st.session_state.logged_in_user)
    try:
        headers = {'Content-Type': 'application/json'}
        #url = f"https://{azure_function_app}.azurewebsites.net/api/DurableFunctionsOrchestrator"
        # For local testing, uncomment the line below:
        url = f"http://localhost:7071/api/DurableFunctionsOrchestrator"
        start_time = time.time()
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        st.session_state.response_duration = duration
        result = "No Data Return From LLM"
        if response.status_code == 202:
            resp_data = response.json()
            get_url = resp_data['statusQueryGetUri']
            for i in range(70):
                status_resp = requests.get(get_url)
                status_data = status_resp.json()
                runtime_status = status_data.get("runtimeStatus")

                if runtime_status == 'Completed':
                    result = status_data.get('output')
                    break
                elif runtime_status in ["Failed", "Terminated"]:
                    result = runtime_status.lower()
                    break
                time.sleep(20)
        return result

    except:
        return f"Exception occured: {str(e)}"

def log_into_pgdb(jira_id, original_description, new_content):
    request_id = None
    feedback_id = None
    try:
        print("user:", st.session_state.logged_in_user)
        print("helper : ", st.session_state.selected_helper)
        print("input type:", st.session_state.selected_input_type)
        print("jira id", jira_id)
        print("original_description", original_description)
        print("new_content", new_content)
        print("Duration: ", st.session_state.response_duration)
        
        request_id = log_user_request(st.session_state.logged_in_user,
                                        st.session_state.selected_helper, 
                                        st.session_state.selected_input_type,
                                        jira_id, original_description, 
                                    new_content, 30, 
                    'success', '',{},{} )
        print("User logs inserted for Requestid: ", request_id)
        logging.info(f"User logs inserted for Requestid: {request_id}")
    except Exception as e:
        error_msg = f"User logs not inserted for Requestid: {request_id}. Error in insert request log:  {str(e)}"
        print(error_msg)
        logging.info(error_msg)
        raise RuntimeError(error_msg)

    if request_id is not None:
        try:
            feedback_id = log_user_feedback(request_id, 
                                            st.session_state.logged_in_user, 
                                            st.session_state.selected_helper,
                                            jira_id, st.session_state.selected_input_type,
                                            3)
            print(f"User ratings inserted for Requestid: {request_id} and feedback_id: {feedback_id} ")
            logging.info(f"User ratings inserted for Requestid: {request_id} and feedback_id: {feedback_id} ")
        except Exception as e:
            error_msg = f"User ratings not inserted for Requestid: {request_id}. Error in insert ratings log:  {str(e)}"
            print(error_msg)
            logging.info(error_msg)
            raise RuntimeError(error_msg)

def is_garbage_input(text):
    stripped = text.strip()

    # Too many special characters
    special_chars = re.findall(r"[^\w\s]", stripped)
    if len(special_chars) > len(stripped) // 2:
        return True

    # Repeated same character
    if len(set(stripped)) <= 2:
        return True

    return False

#configuration streamlit page settings
st.set_page_config(page_title="AI Helper", layout="centered")

# sentiment_mapping = ["one","two","three","four","five"]
# Jira API Endpoint
JIRA_ENDPOINT = os.getenv("JIRA_ENDPOINT","")
PROJ_KEY = os.getenv("PROJ_KEY","")

#initialize session state
initialize_session_state()

if "jira" not in st.session_state:
    st.session_state.jira = JiraClient(JIRA_ENDPOINT) 

jira = st.session_state.jira

#jira authentication
jira_auth(jira, JIRA_ENDPOINT)   

def fetch_issue_details(jira_id):
        """
        Fetch issue details from Jira API
        """
        issue_url = f"{JIRA_ENDPOINT}rest/api/2/issue/{jira_id}"
        response = requests.get(issue_url, headers=jira.headers,verify=False)
        if response.status_code == 200:
            issue_data = response.json()
            #print(issue_data)
            issue_type = issue_data["fields"]["issuetype"]["name"]
            if issue_type.lower() != "story":
                raise ValueError(f"Issue {jira_id} is not a 'Story'. It is a '{issue_type}'.")
            project_name = issue_data["fields"]["project"]["name"]
            description = issue_data["fields"].get("description", "No Description Available")
            summary = issue_data["fields"]["summary"]
            acceptance_criteria = issue_data["fields"].get("customfield_12077", "Not Given")
            epic_id = issue_data["fields"].get("customfield_10100", "Not Given")
            st.session_state[f"epic_id_{jira_id}"] = epic_id or ""
            return {
                "key": issue_data["key"],
                "project_name": project_name,
                "description": description,
                "summary": summary,
                "acceptance_criteria": acceptance_criteria
            }
        else:
            raise Exception(f"Failed to fetch issue details: {response.status_code} - {response.text}")

def parse_ras_rewritten_content(content: str):
    title_match = re.search(r"\*\*Title:\*\*\s*(.+)", content)
    priority_match = re.search(r"\*\*Priority:\*\*\s*(.+)", content)
    effort_match = re.search(r"\*\*Estimated Effort:\*\*\s*(.+)", content)
    
    # Extract Description block
    description_match = re.search(r"\*\*Description:\*\*\s*(.*?)(?=\n\*\*Acceptance Criteria:\*\*)", content, re.DOTALL)
    
    # Extract Acceptance Criteria block
    acceptance_match = re.search(r"\*\*Acceptance Criteria:\*\*\s*(.*?)(?=\n\*\*Priority:\*\*)", content, re.DOTALL)

    effort_text = effort_match.group(1).strip() if effort_match else "N/A"
    effort_number = re.search(r"\d+", effort_text)
    effort_value = effort_number.group() if effort_number else "N/A"

    return {
        "title": title_match.group(1).strip() if title_match else "N/A",
        "description": description_match.group(1).strip() if description_match else "N/A",
        "acceptance_criteria": acceptance_match.group(1).strip() if acceptance_match else "N/A",
        "priority": priority_match.group(1).strip() if priority_match else "N/A",
        "estimated_effort": effort_value
    } 

def escape_jira_formatting(text: str):
    return text.replace("**", "*")

def load_css_agent_chat(file_path):
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", file_path)
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def update_jira_issue(headers,jira_id, title, description,helper_name):
        
        """Update the Jira issue with the refined title and description."""
        if helper_name == "RAS":
            issue_url = f"{JIRA_ENDPOINT}rest/api/2/issue/{jira_id}"
            parsed = parse_ras_rewritten_content(description)
            
            # Only include fields that are safe to update
            payload = {
                "fields": {
                    "summary": title,
                    "description": escape_jira_formatting(parsed["description"])
                    # Removed customfield_12077 and priority as they cause 400 errors
                }
            }

            response = requests.put(issue_url, headers=headers, data=json.dumps(payload), verify=False)
            if response.status_code == 204:
                success_msg = f"Jira issue {jira_id} updated successfully!"
                return response.status_code, success_msg
            else:
                error_msg = f"Failed to update issue ({response.status_code}): {response.text}"
                print(error_msg)
                return response.status_code, error_msg
        
        # Return default values if helper_name is not RAS
        return 400, "Helper not supported for Jira updates"

def get_base64_image(image_path):
    # static/ lives at frontend/static/, one level above frontend/src/ where this script is.
    if not os.path.isabs(image_path):
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", image_path)
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


if st.session_state.jira_auth_popup_actioned:
    

    img_base64 = get_base64_image("static/image.jpg")

    st.markdown(f"""
    <div class="custom-title">
        <img src="data:image/jpeg;base64,{img_base64}" alt="Logo" style="height: 40px;">
        <h3 style="margin: 0;">AI Helpers for Quality Engineering</h3>
    </div>
    """, unsafe_allow_html=True)

    #Load CSS styles
    load_css("static/styles.css") 

    #display sidebar options
    sidebar_display(jira)

    # #Welcome message
    # if not st.session_state.welcome_message:
    #     st.markdown(f"<h4>Welcome, \n\n Please select one of the listed AI Helpers for QE in sidebar to proceed.</h4>", unsafe_allow_html=True)
    #     st.session_state.welcome_message = True

    if not st.session_state.get("welcome_message"):
            st.markdown(f"<h4>Welcome, \n\n Please select one of the listed AI Helpers for QE in sidebar to proceed.</h4>", unsafe_allow_html=True)
            st.session_state.welcome_message = True
  
    button_css_style = [
        """
        button {
            background-color: white !important;
            color: black !important;
            font-weight: bold !important;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 16px;
            border: 2px solid red !important;
        }
        """,
        """
        button:hover {
            background-color: darkred !important;
            color: white !important;
        }
        """
    ]
    if st.session_state.selected_helper and not st.session_state.selected_input_type:
         st.markdown(f"Please select the Input type to proceed with **{st.session_state.selected_helper}** helper.")

    elif st.session_state.selected_helper and st.session_state.selected_input_type:
        #clear rewritten content and pushed status if input type changes
        if "previous_input_type" not in st.session_state or st.session_state.previous_input_type != st.session_state.selected_input_type:
            st.session_state.rewritten_content = {}
            st.session_state.pushed_status = {}
            st.session_state.previous_input_type = st.session_state.selected_input_type
        
        if st.session_state.selected_input_type == "Jira ID":
            st.markdown(f"Once done with selecting Jira ID in sidebar, please click on Run Helper Agent to generate response")
            jira_ids_input = st.session_state.jira_selected
            #print("jira_ids_input:", jira_ids_input)
            jira_ids = [id for id in jira_ids_input]
            #print("jira_ids:", jira_ids)
        
            jira_content = {}
            if jira_ids:
                for jira_id in jira_ids:
                    try:
                        details = fetch_issue_details(jira_id)
                        content = f"**Summary**: {details['summary']} \n\n **Description**:\n\n {details['description']}\n\n **Acceptance Criteria**:\n\n {details['acceptance_criteria']}"
                        with st.expander(f"{details['key']} - {details['summary']}"):
                            st.markdown( content)
                        jira_content[jira_id] = content
                        
                    except Exception as e:
                        st.error(f"{jira_id}: {str(e)}")

        elif st.session_state.selected_helper and st.session_state.selected_input_type == "Free Text Requirement" :
            st.session_state.jira_selected = []
            st.session_state["invalid_len_input"] = False
            if not st.session_state["free_text_input"]:
                st.markdown(f"Please provide the requirement in the user input box below to proceed with **{st.session_state.selected_helper}** helper.")
        
            selected_helper = st.session_state.get("selected_helper")
            selected_input_type = st.session_state.get("selected_input_type")
            message = "Type a requirement as per the specified format."
            user_input = st.chat_input(message )

            if user_input:
                words_in_input = user_input.strip().split()
                
                if len(words_in_input) < 3 or is_garbage_input(user_input):
                    st.warning(
                                "Please enter a valid input before submitting:\n\n"
                                "- The input must contain at least 2 words.\n"
                                "- Excessive special characters (e.g., `#$@&!`) are not allowed.\n"
                                "- Repeated or meaningless characters are not accepted."
                    )
                    st.session_state["invalid_len_input"]  = True
                st.session_state["free_text_input"] = user_input
                st.session_state["free_text_response"] = None
                st.session_state["rewritten_content"] = {}
                
            free_text_input = st.session_state.get("free_text_input")
            invalid_input = st.session_state["invalid_len_input"]

            #print("free_text_input:", free_text_input)
            if free_text_input is not None and selected_input_type == "Free Text Requirement" and not invalid_input:
                with st.expander(f"**Requirement**"):
                    st.session_state["free_text_input"] = st.text_area(
                                                            "Issue Details",
                                                            value=st.session_state["free_text_input"],
                                                            height=250,
                                                            key="editable_text_area"
                                                        )
                with stylable_container(key="run_helper_btn", css_styles=button_css_style):
                    if st.button("Run Helper", key="run_helper_agent"):
                        free_text_input = st.session_state["free_text_input"]

                        if st.session_state.selected_helper == 'Test Case Generator':
                            test_type = 'text_manual' if st.session_state.tcg_selected_btn == 'Manual' else 'text_automatic'
                            req_data = {
                                'issue_type': test_type,
                                'input_type': 'text_input',
                                'request_data': free_text_input,
                                'process_type': 'get_data',
                                "helper_name": "TCG"
                            }
                            response_body = placeholder_for_agent(req_data)

                        elif st.session_state.selected_helper == 'Requirement Analysis & Standardization':
                            request_body = {
                                "helper_name": "RAS",
                                "requirement": free_text_input
                            }
                            
                            response_body = placeholder_for_agent(request_body)
                                                        
                        if response_body is None or "response" not in response_body:
                            response = "Not Able to connect to Function App and get response."
                            agent_conversation = "Not Able to connect to Function App and get response."
                        else:
                            response = response_body["response"]
                            agent_conversation = response_body.get("chat_history", [])
                            if st.session_state.selected_helper == 'Test Case Generator':
                                response = response.replace("TestCaseID:", "**TestCaseID:** ")
                                response = response.replace("Summary:", "**Summary:** ")
                                response = response.replace("Description:", "**Description:** ")
                                response = response.replace("Action:", "**Action:** ")
                                response = response.replace("Data:", "**Data:** ")
                                response = response.replace("Expected Result:", "**Expected Result:** ")
                                response = response.replace("Priority:", "**Priority:** ")
                                response = response.replace("ManualSteps:", "**Manual Steps:** ")
                                response = response.replace("cucumber_steps:", "**Cucumber Steps:** ")

                        st.session_state["free_text_response"] = response
                        st.session_state["free_text_agent_conversation"] = agent_conversation

                if "free_text_response" in st.session_state and st.session_state["free_text_response"]:
                    response = st.session_state["free_text_response"]
                    agent_conversation = st.session_state["free_text_agent_conversation"]
                    if "edit_mode_free_text" not in st.session_state:
                        st.session_state["edit_mode_free_text"] = False
                    if "edited_free_text_response" not in st.session_state:
                        st.session_state["edited_free_text_response"] = response
                    if response:
                        with st.expander(f"**Agent Response**"):
                            with st.container(border=True):
                                #IF Edit Mode
                                if st.session_state["edit_mode_free_text"]:
                                    edited_text = st.text_area(
                                        label="Edit Content",
                                        value=st.session_state["edited_free_text_response"],
                                        height=250,
                                        key="text_area_free_text"
                                    )
                                    st.session_state["edited_free_text_response"] = edited_text
                                else:
                                    converted_response = response.replace('\n', '<br>')
                                    st.markdown(f"{converted_response}", unsafe_allow_html=True)
                                col1,col2,col3 = st.columns(3)
                                load_css_agent_chat("static/agent_chat.css")
                                with col1:
                                    if st.button(f"Analyze Agents", key="analyze_agent"):
                                        #data = get_agentic_response()
                                        #chat_history = data.get("output", {}).get("chat_history", [])
                                        chat_dialog(agent_conversation)
                                with col2:
                                    escaped_response = json.dumps(response)                           
                                    clipboard_button(escaped_response)

                                with col3:
                                   toggle_btn_label = "Save Edit" if st.session_state["edit_mode_free_text"] else "Edit"
                                   if st.button(toggle_btn_label, key=f"edit_toggle_free_text"):
                                        if st.session_state["edit_mode_free_text"]:
                                            st.session_state["free_text_response"] = st.session_state["edited_free_text_response"]
                                        st.session_state["edit_mode_free_text"] = not st.session_state["edit_mode_free_text"]
                                        st.rerun()

                                # st.markdown(rating, unsafe_allow_html=True)
                                star_rating("Rate the response:", "star_rating_1")

                                #log_into_pgdb(None, free_text_input, response)


    if "rewritten_content" not  in st.session_state:
        st.session_state.rewriten_content = {}   
    if "pushed_status" not in st.session_state:
        st.session_state.pushed_status = {}

    #Remove rewritten content for Jira IDs that are no longer selected
    current_selected_ids = set(st.session_state.jira_selected)
    previous_selected_ids = set(st.session_state.get("previous_jira_selected",[]))
    removed_ids = previous_selected_ids - current_selected_ids

    for jira_id in removed_ids:
        if jira_id in st.session_state.rewritten_content:
            del st.session_state.rewritten_content[jira_id]
        if jira_id in st.session_state.pushed_status:
            del st.session_state.pushed_status[jira_id]

    #update the previous selection state            
    
    if st.session_state.jira_selected:
        with stylable_container(key="run_helper_btn",css_styles=button_css_style):
            if st.button("Run Helper"):
                for jira_id in st.session_state.jira_selected:
                    #print("After Helper Agent Run jira_id:", jira_id)
                    original_description = jira_content.get(jira_id, None)
                    print("original_description:", original_description)
                    with st.spinner("Processing..."):
                        time.sleep(2)
                        if st.session_state.selected_helper == "Test Case Generator":
                            pattern = r"\*\*(.*?)\*\*:\s*(.*?)(?=(\*\*|$))"
                            matches = re.findall(pattern, original_description, re.DOTALL)
                            request_data = {key.strip(): value.strip() for key, value, _ in matches}
                            request_data['parent'] = jira_id
                            req_data ={
                                'issue_type': st.session_state.tcg_selected_btn,
                                'input_type': 'jira_id',
                                'request_data': str(request_data),
                                'process_type': 'get_data',
                                "helper_name":"TCG"
                            }
                            response_body= placeholder_for_agent(req_data)
                            if response_body is None or "response" not in response_body:
                                new_content = "Not Able to connect to Function App and get response."
                                agent_conversation = "Not Able to connect to Function App and get response."
                            else:
                                new_content = response_body["response"]
                                agent_conversation = response_body["chat_history"]
                                new_content = new_content.replace("TestCaseID:", "**TestCaseID:** ")
                                new_content = new_content.replace("Summary:", "**Summary:** ")
                                new_content = new_content.replace("Description:", "**Description:** ")
                                new_content = new_content.replace("Action:", "**Action:** ")
                                new_content = new_content.replace("Data:", "**Data:** ")
                                new_content = new_content.replace("Expected Result:", "**Expected Result:** ")
                                new_content = new_content.replace("Priority:", "**Priority:** ")
                                new_content = new_content.replace("ManualSteps:", "**Manual Steps:** ")
                                new_content = new_content.replace("cucumber_steps:", "**Cucumber Steps:** ")
                                st.session_state.rewritten_content[jira_id] = new_content.replace('\n','<br>')
                                st.session_state.pushed_status[jira_id] = False
                                st.session_state[f"agent_conversation_{jira_id}"] = agent_conversation
                        elif st.session_state.selected_helper == "Requirement Analysis & Standardization":
                            request_body = {
                                "helper_name": "RAS", 
                                "requirement": original_description 
                                }
                            response_body = placeholder_for_agent(request_body)
                            #st.write("Test clicked with response_body:", response_body)  ## Remove this line after testing
                            if response_body is None or "response" not in response_body:
                                new_content = "Not Able to connect to Function App and get response."
                                agent_conversation = "Not Able to connect to Function App and get response."
                            else:
                                new_content = response_body["response"]
                                agent_conversation = response_body["chat_history"]
                            
                            #print("response_body:", response_body)
                            #print("new_content:", new_content)
                            print("Eipic id ", st.session_state[f"epic_id_{jira_id}"])

                            #title_match = re.search(r"\*\*Title:\*\*\s*(.+)", new_content)
                            #priority_match = re.search(r"\*\*Priority:\*\*\s*(.+)", new_content)
                            #effort_match = re.search(r"\*\*Estimated Effort:\*\*\s*(.+)", new_content)
                            ##acceptance_match = re.search(r"\*\*Acceptance Criteria:\*\*\s*(.+)", new_content, re.DOTALL)

                            title_match = re.search(r"(?:\*\*Title:\*\*|###\s*Title[:\s]*)\s*(.+)", new_content)
                            priority_match = re.search(r"(?:\*\*Priority:\*\*|###\s*Priority[:\s]*)\s*(.+)", new_content)
                            effort_match = re.search(r"(?:\*\*Estimated Effort:\*\*|###\s*Estimated Effort[:\s]*)\s*(.+)", new_content)

                            title = title_match.group(1) if title_match else "N/A"
                            priority = priority_match.group(1) if priority_match else "N/A"
                            effort = effort_match.group(1) if effort_match else "N/A"
                            #acceptance_criteria = acceptance_match.group(1).strip() if acceptance_match else "N/A"

                            # Remove trailing metadata fields from description
                            #description_md = re.sub(r"\n?\*\*Title:\*\*.*", "", new_content).strip()
                            #description_md = re.sub(r"\n?\*\*Priority:\*\*.*", "", description_md)
                            #description_md = re.sub(r"\n?\*\*Estimated Effort:\*\*.*", "", description_md)
                            ##description_md = re.sub(r"\n?\*\*Acceptance Criteria:\*\*.*", "", description_md)

                            description_md = re.sub(r"\n?(?:\*\*Title:\*\*|###\s*Title[:\s]*).*", "", new_content).strip()
                            description_md = re.sub(r"\n?(?:\*\*Priority:\*\*|###\s*Priority[:\s]*).*", "", description_md)
                            description_md = re.sub(r"\n?(?:\*\*Estimated Effort:\*\*|###\s*Estimated Effort[:\s]*).*", "", description_md)

                            #acceptance_criteria = re.sub(r"(?:\*\*Description:\*\*|###\s*Description[:\s]*)\s*\n(?:.*\n)*?(?=(\*\*|###|\Z))", "", description_md, flags=re.MULTILINE)
                            match = re.search(
                                r"\*\*Acceptance Criteria:\*\*(.*?)(?=\n\*\*Priority:\*\*|\Z)",
                                description_md,
                                flags=re.DOTALL
                            )

                            acceptance_criteria = match.group(0).strip() if match else ""
                            
                            #description_md = re.sub(r"\*\*Acceptance Criteria:\*\*\s*\n(?:.*(?:\n|$))*?(?=(\*\*|###|\Z))", "", description_md, flags=re.MULTILINE)
                            description_md = re.sub(r'\*\*Acceptance Criteria:\*\*.*', '', description_md, flags=re.DOTALL).strip()
                            description_md = description_md + "\n\n *Note: This is AI generated content*"
                            
                            print(f"**Title:** {title}")
                            print(f"**description_md:** {description_md}")
                            print(f"**acceptance_criteria:** {acceptance_criteria}")
                            epic_id = st.session_state[f"epic_id_{jira_id}"] + "-"
                            if epic_id not in title:
                                title = epic_id + title
                            #rewritten_content = f"**Title:** {title} \n\n**Description:** {description_md} \n\n**Acceptance Criteria:** {acceptance_criteria} \n\n**Priority:** {priority} \n\n**Estimated Effort:** {effort}"
                            rewritten_content = f"**Title:** {title} \n\n{description_md} \n\n{acceptance_criteria} \n\n**Priority:** {priority} \n\n**Estimated Effort:** {effort}"
                            #print("rewritten_content:", rewritten_content)
                            st.session_state.rewritten_content[jira_id]  = rewritten_content
                            
                            
                            st.session_state.pushed_status[jira_id] = False

                            st.session_state[f"title_{jira_id}"] = title
                            st.session_state[f"priority{jira_id}"] = priority
                            st.session_state[f"effort_{jira_id}"] = effort
                            st.session_state[f"description_md_{jira_id}"] = description_md
                            st.session_state[f"acceptance_criteria_{jira_id}"] = acceptance_criteria
                            st.session_state[f"agent_conversation_{jira_id}"] = agent_conversation
                            st.session_state[f"original_description{jira_id}"] = original_description

            if any(jira_id in st.session_state.rewritten_content for jira_id in st.session_state.jira_selected):
                for jira_id in st.session_state.jira_selected:
                        #print("rewritten jira_id:", jira_id)
                        rewritten_text = st.session_state.rewritten_content.get(jira_id)
                        agent_conversation = st.session_state.get(f"agent_conversation_{jira_id}", [])
                        original_description = st.session_state.get(f"original_description{jira_id}", "")
                        #print("agent_conversation:", agent_conversation)
                        #print("rewritten_text:", rewritten_text)
                        
                        if rewritten_text:
                            with st.expander(f"Refined Content for {jira_id}"):
                                text_area_key = f"rewritten_text_{jira_id}"
                                edit_mode_key = f"edit_mode_{jira_id}"

                                if edit_mode_key not in st.session_state:
                                    st.session_state[edit_mode_key] = False
                                #updated_text = st.text_area(
                                #    label="Content",
                                #    value=rewritten_text,
                                #    height=250,
                                #    key=text_area_key
                                #)
                                if st.session_state[edit_mode_key]:
                                    if st.session_state.selected_helper == "Test Case Generator":
                                        rewritten_text = rewritten_text.replace('<br>', '\n')
                                    edited_text = st.text_area(
                                    label="Edit Content",
                                    value=rewritten_text,
                                    height=250,
                                    key=text_area_key
                                    )
                                    st.session_state.rewritten_content[jira_id] = edited_text
                                else:
                                    if st.session_state.selected_helper == "Test Case Generator":
                                        rewritten_text = rewritten_text.replace('\n', '<br>')
                                    st.markdown(rewritten_text, unsafe_allow_html=True)
                                
                                #st.markdown(rating, unsafe_allow_html=True)
                                col1,col2,col3,col4 = st.columns(4)
                                load_css_agent_chat("static/agent_chat.css")
                                with col1:
                                    if st.button("Analyze Agents",key=f"analyze_{jira_id}"):
                                        chat_dialog(agent_conversation)
                                with col2:

                                    escaped_response = json.dumps(rewritten_text)                           
                                    clipboard_button(escaped_response)
                                    
                                        
                                with col3:
                                    toggle_btn_label = "Save Edit" if st.session_state[edit_mode_key] else "Edit"
                                    if st.button(toggle_btn_label, key=f"edit_toggle_{jira_id}"):
                                        st.session_state[edit_mode_key] = not st.session_state[edit_mode_key]
                                        st.rerun()
                                with col4:  
                                    if st.button("Approve and Push to Jira", key=f"push_{jira_id}"):
                                        st.session_state[f"show_confirmation_{jira_id}"] = True
                                
                                # Confirmation logic
                                if st.session_state.get(f"show_confirmation_{jira_id}", False):
                                    st.write(f"Are you sure you want to push the content of {jira_id} to Jira?")
                                    confirm_col1, confirm_col2, _ = st.columns(3)

                                    with confirm_col1:
                                        if st.button("Yes", key=f"confirm_{jira_id}"):
                                            title = st.session_state.get(f"title_{jira_id}", "Default Title")
                                            description = st.session_state.rewritten_content[jira_id]

                                            if st.session_state.selected_helper == "Test Case Generator":
                                                description = description.replace("**TestCaseID:** ", "TestCaseID:")
                                                description = description.replace("**Summary:** ", "Summary:")
                                                description = description.replace("**Description:** ", "Description:")
                                                description = description.replace("**Action:** ", "Action:")
                                                description = description.replace("**Data:** ", "Data:")
                                                description = description.replace("**Expected Result:** ",
                                                                                  "Expected Result:")
                                                description = description.replace("**Priority:** ", "Priority:")
                                                description = description.replace("**Manual Steps:** ", "ManualSteps:")
                                                description = description.replace("**Cucumber Steps:** ", "cucumber_steps:")
                                                issue_data = description.replace('<br>', '\n')                                                
                                                req_data = {
                                                    'issue_type': st.session_state.tcg_selected_btn,
                                                    'input_type': 'jira_id',
                                                    'request_data': issue_data,
                                                    'process_type': 'push_data',
                                                    'base_url':JIRA_ENDPOINT,
                                                    'proj_key':PROJ_KEY,
                                                    'jira_id':jira_id,
                                                    "activity":"PushtoJira",
                                                    'jira_username': st.session_state.get('jira_username'),
                                                    'jira_password': st.session_state.get('jira_password'),
                                                    "helper_name":"TCG"
                                                }
                                                response_body = placeholder_for_agent(req_data)
                                                if response_body and "status_code" in response_body:
                                                    status_code = response_body["status_code"]
                                                    success_msg = response_body.get("response_msg", "Updated successfully")
                                                else:
                                                    status_code = 500
                                                    success_msg = "Failed to update Jira via Azure Function"
                                            elif st.session_state.selected_helper == "Requirement Analysis & Standardization":
                                                helper_name = "RAS"
                                                req_data = {
                                                    'title': title, 
                                                    'description': description, 
                                                    'acceptance_criteria': description,
                                                    'base_url': JIRA_ENDPOINT,
                                                    'proj_key': PROJ_KEY, 
                                                    'jira_id': jira_id, 
                                                    'helper_name': "RAS", 
                                                    'activity': "PushtoJira",
                                                    'jira_username': st.session_state.get('jira_username'),
                                                    'jira_password': st.session_state.get('jira_password')
                                                }
                                                # Use Azure Function approach for consistency
                                                response_body = placeholder_for_agent(req_data)
                                                if response_body and "status_code" in response_body:
                                                    status_code = response_body["status_code"]
                                                    success_msg = response_body.get("response_msg", "Updated successfully")
                                                else:
                                                    status_code = 500
                                                    success_msg = "Failed to update Jira via Azure Function"
                                                
                                                
                                            st.session_state.pushed_status[jira_id] = True
                                            st.success(f"Content pushed to Jira for {jira_id}: {success_msg}")
                                            st.session_state[f"show_confirmation_{jira_id}"] = False
                                            st.rerun()

                                    with confirm_col2:
                                        if st.button("No", key=f"cancel_{jira_id}"):
                                            st.info(f"Push to Jira for {jira_id} was cancelled.")
                                            st.session_state[f"show_confirmation_{jira_id}"] = False
                                            st.rerun()

                                # Show Jira link if already pushed
                                if st.session_state.pushed_status.get(jira_id, False):
                                    jira_url = f"{JIRA_ENDPOINT}browse/{jira_id}"
                                    st.info(f"✅ Content for {jira_id} has been pushed to Jira: [View in Jira]({jira_url})")                                

                                star_rating("Rate the response:", f"star_rating_{jira_id}")  
                                # if not st.session_state.get(f"response_inserted_{jira_id}", False):
                                #     log_into_pgdb(jira_id, original_description, rewritten_text)
                                #     st.session_state[f"response_inserted_{jira_id}"] = True
