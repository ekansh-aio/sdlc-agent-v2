import requests
import streamlit as st
import json
import load_dotenv


#Get Azure finction name from .env file
azure_function_app = os.getenv("AZURE_FUNCTION_APP","")

def call_function_app():
#call the function app
    http_endpoint=f"https://{azure_function_app}.azurewebsites.net/api/DurableFunctionsOrchestrator"
    #http_endpoint=f"https://{azure_function_app}.azurewebsites.net/api/http_trigger_function?name=Ashish"
    payload = {
            "helper_name":"RAS",
            "requirement":"This is test requirement",
            "name":"Test"
            }
    headers = {
        "Content-Type": "application/json"
        }
        
    response = requests.post(http_endpoint, headers=headers, data=json.dumps(payload),verify=False)
    if response.status_code == 202:
        result = response.json()
        status_url = result.get("statusQueryGetUri")
        st.success("Durable function started successfully.")
        st.write("Status Check URL:", status_url)
        # Check the status of the function
        status_response = requests.get(status_url,verify=False)
        if status_response.status_code == 200:
            status_result = status_response.json()
            st.write("Function Status:", status_result)
        else:
            st.error(f"Failed to get function status: {status_response.status_code}")
    elif response.status_code == 200:
        st.success("FunctionApp call succeeded.")
        result = response.json()
        st.write("Result:", result)

        
    else:
        st.error(f"FunctionApp call failed with status code: {response.status_code}")