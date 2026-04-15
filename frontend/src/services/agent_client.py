import os
import time
import json
import logging
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_FUNCTION_APP = os.getenv("AZURE_FUNCTION_APP", "")
_LOCAL_URL = "http://localhost:7071/api/DurableFunctionsOrchestrator"


def call_agent(payload: dict):
    """
    Send payload to Azure Durable Functions orchestrator.
    Polls until Completed / Failed / Terminated.
    Returns the output dict, a status string, or None on connection failure.
    """
    url = _LOCAL_URL  # swap to cloud URL when deployed
    try:
        start = time.time()
        resp = requests.post(url, json=payload, timeout=60)
        st.session_state.response_duration = round(time.time() - start, 2)

        if resp.status_code != 202:
            return None

        poll_data = resp.json()
        poll_url = poll_data.get("statusQueryGetUri")
        if not poll_url:
            logging.error("agent_client: no statusQueryGetUri in 202 response")
            return None

        # Poll with a 5-second interval for up to ~10 minutes (120 iterations)
        for i in range(120):
            time.sleep(5)
            status_resp = requests.get(poll_url, timeout=60)
            if status_resp.status_code not in (200, 202):
                logging.warning(f"agent_client: poll returned {status_resp.status_code}")
                continue
            data = status_resp.json()
            runtime = data.get("runtimeStatus")
            logging.info(f"agent_client: poll #{i+1} runtimeStatus={runtime}")
            if runtime == "Completed":
                output = data.get("output")
                logging.info(f"agent_client: completed, output type={type(output).__name__}, keys={list(output.keys()) if isinstance(output, dict) else 'n/a'}")
                if output is None:
                    return {"response": "Agent returned no output.", "chat_history": []}
                return output
            if runtime in ("Failed", "Terminated"):
                error_detail = data.get("output", runtime)
                logging.error(f"agent_client: orchestration {runtime}: {error_detail}")
                return {"response": f"Agent {runtime.lower()}: {error_detail}", "chat_history": []}
        logging.error("agent_client: polling timed out after 120 attempts")
        return None

    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        return f"Exception: {str(e)}"
