import uuid
import json
from datetime import datetime
import psycopg2
import logging
from services.postgres_client import PostgresClient


def log_user_request(lid, ai_helper_name, segment, jira_issue_id, request_content, 
                     original_response, response_time, request_status, error_message, 
                     chat_history, tokens_used
                     ) :        
        
        client = PostgresClient()
        chat_history_json = json.dumps(chat_history)
        tokens_used_json = json.dumps(tokens_used)                                   

        request_id = str(uuid.uuid4())
        insert_query = """
        INSERT INTO user_request_logs (request_id, lid, ai_helper_name, segment, jira_issue_id, request_content, 
        original_response, response_time, request_status, error_message, chat_history, tokens_used)
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (request_id, lid, ai_helper_name, segment, jira_issue_id, request_content, 
                     original_response, response_time, request_status, error_message, 
                     chat_history_json, tokens_used_json)
        try:
            client.execute_query(insert_query, params)
            return request_id
        except psycopg2.OperationalError as oe:
            error_message = f"Operational error: {oe}"
            return error_message
        except Exception as e:
            error_msg = "Error in PG execution: " + str(e)
            logging.exception(error_msg)
            return error_msg

def update_edited_response(request_id, user_edited_response):
    client = PostgresClient()
    update_query = """
    UPDATE user_request_logs
    SET user_edited_response = %s,
    is_edited=TRUE
    where request_id = %s
    """
    params = (user_edited_response, request_id)
    try:
        client.execute_query(update_query, params)
        return request_id
    except psycopg2.OperationalError as oe:
        error_message = f"Operational error: {oe}"
        return error_message
    except Exception as e:
        error_msg = "Error in PG execution: " + str(e)
        logging.exception(error_msg)
        return error_msg


def log_user_feedback(request_id, lid, ai_helper_name, jira_issue_id, segment, rating ):
    client = PostgresClient()
    feedback_id = str(uuid.uuid4())
    insert_query = """
    INSERT INTO user_feedback(
    feedback_id, request_id, lid, ai_helper_name, jira_issue_id, segment, rating)
    VALUES (%s, %s, %s, %s, %s, %s, %s
    )
    """
    params = (feedback_id, request_id, lid, ai_helper_name, jira_issue_id, segment, rating)
    try:
        client.execute_query(insert_query, params)
        return feedback_id
    except psycopg2.OperationalError as oe:
        error_message = f"Operational error: {oe}"
        return error_message
    except Exception as e:
        error_msg = "Error in PG execution: " + str(e)
        logging.exception(error_msg)
        return error_msg