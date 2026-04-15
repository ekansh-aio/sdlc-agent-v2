import logging
import azure.functions as func
import azure.durable_functions as df

async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    logging.info("Received HTTP request to start agent workflow")

    try:
        client = df.DurableOrchestrationClient(starter)
        request_body = req.get_json()
        
        logging.info(f"Api request data : '{request_body}'")
    

        instance_id = await client.start_new(req.route_params['functionName'], None, request_body)

        logging.info(f"Started orchestration with ID = '{instance_id}'")
    

        return client.create_check_status_response(req, instance_id)

    except ValueError as e:
        logging.info(f"Error occur for getting json from API : '{e}'")
        return func.HttpResponse("Invalid JSON input", status_code=400)
    
    except Exception as e:
        logging.error(f"Error starting orchestration with ID = '{instance_id}'")
        return func.HttpResponse(f"Internal Server Error: {str(e)}", status_code=500)