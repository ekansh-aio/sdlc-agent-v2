import logging
import azure.functions as func
import azure.durable_functions as df


def orchestrator_function(context: df.DurableOrchestrationContext):
    logging.info('Orchestrator Function Invoked')
    #Get the input text from the context
    inputs = context.get_input()
    helper_name = inputs.get('helper_name')
    activity = inputs.get('activity','UNKNOWN')

    #Call the activity function to process the text
    if helper_name == "RAS" and not activity == "PushtoJira":
        result = yield context.call_activity("ExecuteRAS", inputs)
    elif helper_name == "TCG" and not activity == "PushtoJira":
        result = yield context.call_activity("ExecuteTCG", inputs)
    elif activity == "PushtoJira" :
        status_code, response_msg = yield context.call_activity("PushtoJira", inputs)
        return {"status_code": status_code, "response_msg": response_msg}

    # elif helper_name == "Test_PG":
    #     result = yield context.call_activity("TestPosgresql", inputs)
    # elif helper_name == "Test_LLM_Client":
    #     result = yield context.call_activity("TestLLMClient", inputs)
    # elif helper_name == "Test_LLM_ChatClient":
    #     result = yield context.call_activity("TestLLMChatClient", inputs)
    # elif helper_name == "Test_LLM_ChatClientWOA":
    #     result = yield context.call_activity("TestLLMChatClientWOA", inputs)
    # elif helper_name == "TestOAuth":
    #     result = yield context.call_activity("TestOAuth", inputs)
    elif helper_name == "DocIngestionFunction":
        result = yield context.call_activity("DocIngestionFunction", inputs)
    
    
    return result

main = df.Orchestrator.create(orchestrator_function)

