import pandas as pd

def get_response_from_excel(file_path, sheet_name, request_value):
    """
    fetches the response value for a given request value from a specified sheet.
    """
    try:
        #read the specific sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        #validate required columns
        if 'request' not in df.columns or 'response' not in df.columns:
            return "Error: 'request' and 'response' column not found in sheet"
        
        #Find the response where request matches
        match = df[df['request'] == request_value]

        if not match.empty:
            return match['response'].values[0]
        else:
            return f"No response found for request '{request_value}"
    except Exception as e:
        return f"Error: {str(e)}"
