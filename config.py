import streamlit as st
import pandas as pd
from datetime import datetime
from snowflake.snowpark.context import get_active_session
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

TABLE_NAME = "CONFIG_DETAILS"
COL1 = "USER_EMAIL" 
COL2 = "FILTER_ID"
COL3 = "API_KEY" 
COL4 = "UPDATED_AT"
COL5 = "JIRA_USER_ID"


st.title("Config")
st.text("Use this page to provide configuration details necessary for the app.")

active_session = get_active_session()

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=['USER_EMAIL','FILTER_ID','API_KEY','UPDATED_AT'])

#Config Modal
@st.dialog("Jira Configuration Details")
def config_modal():
  if st.user and "email" in st.user:
    user_email = st.user["email"]
  else:
    user_email = "EMAIL REQUIRED"
  with st.form("config_form", clear_on_submit=True):
    user_email_input = st.text_input("Email", value=user_email)
    username = user_email_input.split('@')[0]
    jira_cred_name = "jira_credentials_"+username
    filter_id = st.text_input("Jira filter id")
    api_key = st.text_input("Jira API key")
    submitted = st.form_submit_button("Submit Details")
    if submitted:
      #First will need to run CREATE OR REPLACE SECRET jira_credentials_username ((NEED TO REMOVE @PHDATA.IO)) TYPE = GENERIC_STRING SECRET_STRING = '{"email": "email", "api_token": "token"}';
      #Then ALTER EXTERNAL ACCESS INTEGRATION jira_access_integration ALLOWED_AUTHENTICATION_SECRETS = (jira_credentials) ENABLED = TRUE;
      secret_string = "'{ \"email\": \"" + user_email_input + "\" , \"api_token\": \"" + api_key + "\" }';"
      #secret_token = "\"api_token\": \""+api_key+"\" \};"
      create_secret_sql = f"""
      CREATE OR REPLACE SECRET {jira_cred_name}
          TYPE = GENERIC_STRING
          SECRET_STRING = {secret_string}
      """
      update_auth_sec = f"""
      ALTER EXTERNAL ACCESS INTEGRATION jira_access_integration 
          SET ALLOWED_AUTHENTICATION_SECRETS = ({jira_cred_name})
          ENABLED = TRUE;
      """
      ###create_int = f"CREATE OR REPLACE SECRET {jira_cred_name} TYPE = GENERIC_STRING SECRET_STRING = {"email": "user_email_input, "api_token": '{api_key}'};"
      active_session.sql(create_secret_sql).collect()
      ###update_auth_sec = f"ALTER EXTERNAL ACCESS INTEGRATION jira_access_integration ALLOWED_AUTHENTICATION_SECRET = ({jira_cred_name}) ENABLED = TRUE;"
      active_session.sql(update_auth_sec).collect()
      st.session_state["submission_data"] = {"email": user_email_input, "filter_id": filter_id, "api_key": api_key}
      updated_at = datetime.now()
      url = f"https://phdata.atlassian.net/rest/api/3/user/search?query={user_email}"
      auth = HTTPBasicAuth(user_email_input, api_key)
      headers = {
          "Accept": "application/json"
      }
      try:
          response = requests.get(
              url,
              headers=headers,
              auth=auth
          )
      except requests.exceptions.RequestException as e:
          st.error(f"Error connecting to Jira: {e}")
          st.error(f"Response: {response.text if 'response' in locals() else 'No response'}")

      if user_email_input and filter_id and api_key:
          try:
              jira_user_id_r = json.loads(response.text)
              jira_user_id = jira_user_id_r[0]['accountId']
              insert_query = f"INSERT INTO {TABLE_NAME} ({COL1},{COL2},{COL3},{COL4},{COL5}) VALUES (UPPER('{user_email_input}'),'{filter_id}','{api_key}','{updated_at}','{jira_user_id}')"
              active_session.sql(insert_query).collect()
              st.success("Config details saved!")
          except Exception as e:
              st.error(f"Error: {e}")
      else:
          st.warning("Please fill in all fields.")

if "submission_data" not in st.session_state:
  st.session_state["submission_data"] = None

#Allocation Modal
@st.dialog("Allocation Details")
def allocation_modal():
  with st.form("allocation_form", clear_on_submit=True):
    st.markdown("Insert a set of columns here for allocation details")
    submitted = st.form_submit_button("Save Allocations")
    if submitted:
      st.rerun()


#Standard Page
col1, col2 = st.columns(2)
with col1:
  if st.button("Open config form", use_container_width=True):
    config_modal()
with col2:
  if st.button("Open allocation form", use_container_width=True):
    allocation_modal()

with st.expander("Components to build:"):
  st.markdown(":white_check_mark:   Input user email")
  st.markdown(":white_check_mark:   Input Jira filter id")
  st.markdown(":white_check_mark:   Input Jira API key")
  st.markdown(":white_check_mark:   Mask Jira API key")
  st.markdown(":white_check_mark:   Create view showing user's most recent submission")
  st.markdown(":pencil2:   Collect user Jira id (requires user email and API key)")
  st.markdown(":pencil2:   Input allocations")
  st.markdown(":pencil2:   Collect issues from Jira filter id")
  st.markdown(":pencil2:   Create row access policies based on CURRENT_USER in tables in env schema")
  st.markdown(":pencil2:   If filter id exists, show current filter logic")

with st.expander("Functionalities:"):
  st.markdown(":firecracker:   Button to pop up base config modal")
  st.markdown(":white_check_mark:   Modal to collect user email, filter id, API key")
  st.markdown(":white_check_mark:   On modal submit -> store details in config table")
  st.markdown(":boom:   On modal submit -> collect user Jira id and store with config details")
  st.markdown(":firecracker:   Button to pop up allocation modal")
  st.markdown("  :boom:   Modal has input table for: Jira project id, client name, project name, weekly hrs, effective dates")
  st.markdown("  :boom:   If allocation table has data in it, display current allocation details - including link to Jira board")
