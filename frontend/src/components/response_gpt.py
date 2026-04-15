import openai
import streamlit as st

# Function: Rewrite with OpenAI GPT
def rewrite_with_gpt(original_description):
    prompt = f"""
You are an expert business analyst. Rewrite the following Jira ticket description as a user story that follows the INVEST principle.

Original Description:
\"\"\"{original_description}\"\"\"

Use the format:
**As a** [role],  
**I want** [goal],  
**So that** [reason].

Then add:
**Acceptance Criteria:**  
- [criteria 1]  
- [criteria 2]  
- ...

Add:
**Summary:** [value]
**Priority:** [value]  
**Estimated Effort:** [value]
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional Jira expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI API error: {str(e)}")
        return None