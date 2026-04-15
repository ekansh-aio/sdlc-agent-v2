import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from components.dialogs import user_confirm
import uuid
import pyperclip
import io
import pandas as pd


def set_feedback(sentiment_mapping):
    with st.container(border=True):
            st.markdown("***Please provide feedback about the response***")
            selected = st.feedback("stars", key=st.session_state['feedback_key'])
            if selected is not None:
                st.markdown(f"You selected {sentiment_mapping[selected]} star(s).")

def push_to_jira(key):
    with stylable_container(
                    key= key,
                    css_styles=[
                        """
                        button{
                            border: solid .1em red;
                            border-radius: 10px;
                            color:black;
                            background-color: white;
                            padding: 5px 19px;
                            white-space: nowrap;
                            margin: -5px 0;
                        }
                        """,
                        """
                        button:hover {
                            background-color: white;
                            border: solid .2em red;
                            border-radius: 10px;
                            color: red;

                        }
                        """
                    ]
                ):       
                    if st.button("Push to Jira"):
                        user_confirm()
                    st.session_state.file_uploaded_push_to_jira = True



def display_response_options(bot_response,sentiment_mapping):
    st.markdown(""" """)
    col = st.columns([0.55, 0.3, 0.6]) 
    with col[0]:
        set_feedback(sentiment_mapping)

    with col[1]:
        with stylable_container(
            key="button_07",
            css_styles=[
                """
                button {
                    border: solid .1em red;
                    border-radius: 10px;
                    color: black;
                    background-color: white;
                    padding: 5px 15px;
                    white-space: nowrap;
                    margin: -2px 0;
                }
                """,
                """
                button:hover{
                    background-color: white;
                    border: solid .2em red;
                    border-radius: 10px;
                    color: red;

                    }
                """,
            ],
        ):
            if st.button("Copy Response"):
                pyperclip.copy(st.session_state.assistant_message_value)
                st.toast("Response copied to clipboard!")

        with stylable_container(
            key= "button_08",
            css_styles=[
                """
                button {
                    border: solid .1em red;
                    border-radius: 10px;
                    color: black;
                    background-color: white;
                    padding: 5px 15px;
                    white-space: nowrap;
                    margin: -5px 0;
                }
                """,
                """
                button:hover{
                    background-color: white;
                    border: solid .2em red;
                    border-radius: 10px;
                    color: red;

                    }
                """,
            ]
        ):
            #create a dataframe with only the assistant's response
            response_data = {
                "Assistant Response": [st.session_state.assistant_message_value]
            }    
            df = pd.DataFrame(response_data)

            #Use BytesIO to create an in-memory buffer
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)#move cursor to the beginning of the buffer

            #Provide the download button
            st.download_button(
                label="Download Response",
                data=buffer,
                file_name= "assistant_response.xlsx",
                mime= "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        if st.session_state.selected_input_type == "Jira ID" or st.session_state.selected_input_type == "Upload Excel":
            with col[2]:
                upload_excel("button09")

                push_to_jira("button_10")

def display_response_option_fileupload(sentiment_mapping):
    st.markdown(f""" """)
    col = st.columns(2) 
    with col[0]:
        set_feedback(sentiment_mapping)

    with col[1]:
        upload_excel("button11")
        push_to_jira("button_12")
      
def upload_excel(key):
     with stylable_container(
                    key=key,
                    css_styles=[
                        """
                        button{
                            border: solid .1em red;
                            border-radius: 10px;
                            color:black;
                            background-color: white;
                            padding: 5px 15px;
                            white-space: nowrap;
                            margin: -3px 0;
                        }
                        """,
                        """
                        button:hover {
                            background-color: white;
                            border: solid .2em red;
                            border-radius: 10px;
                            color: red;

                        }
                        """
                    ]
                ):
                    if st.button("Upload Excel"):
                        uploaded_file =  st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])
                        if uploaded_file:
                            st.session_state.chat_history.append({"role": "user", "content": f"Uploaded file: {uploaded_file.name}"})
                            st.success("Excel file uploaded successfully!")

