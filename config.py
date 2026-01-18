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
COL2 = "API_KEY" 
COL3 = "UPDATED_AT"
COL4 = "JIRA_USER_ID"


st.title("Time Tracking Configuration")
st.text("Use this page to provide your Jira API key and update your weekly project allocations.")

active_session = get_active_session()

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=['USER_EMAIL','FILTER_ID','API_KEY','UPDATED_AT'])

#Config Modal
@st.dialog("Add API Key")
def config_modal():
  with st.form("config_form", clear_on_submit=True):
    user_email = st.user["email"]
    username = user_email.split('@')[0]
    jira_cred_name = "jira_credentials_"+username
    api_key = st.text_input("Jira API key")
    submitted = st.form_submit_button("Submit Details")
    secret_string = "'{ \"email\": \"" + user_email + "\" , \"api_token\": \"" + api_key + "\" }';"
    url = f"https://phdata.atlassian.net/rest/api/3/user/search?query={user_email}"
    if submitted:
      create_secret_sql = f"""
      CREATE OR REPLACE SECRET {jira_cred_name}
          TYPE = GENERIC_STRING
          SECRET_STRING = {secret_string}
      """
      active_session.sql(create_secret_sql).collect()
      
      secret_show = f"""
      SHOW SECRETS;
      """
      secret_list = f"""
      SELECT LISTAGG("name", ', ') WITHIN GROUP (ORDER BY "name") AS secret_names_string
      FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
      """
      active_session.sql(secret_show).collect()
      secret_list_res = active_session.sql(secret_list)
      secret_list_res_arr = secret_list_res.collect()[0]['SECRET_NAMES_STRING']
      
      update_auth_sec = f"""
      ALTER EXTERNAL ACCESS INTEGRATION jira_access_integration 
          SET ALLOWED_AUTHENTICATION_SECRETS = ({secret_list_res_arr})
          ENABLED = TRUE;
      """
      active_session.sql(update_auth_sec)
      
      st.session_state["submission_data"] = {"email": user_email, "api_key": api_key}
      updated_at = datetime.now()
      
      auth = HTTPBasicAuth(user_email, api_key)
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

      if user_email and api_key:
          try:
              jira_user_id_r = json.loads(response.text)
              jira_user_id = jira_user_id_r[0]['accountId']
              insert_query = f"INSERT INTO {TABLE_NAME} ({COL1},{COL2},{COL3},{COL4}) VALUES (UPPER('{user_email}'),'{api_key}','{updated_at}','{jira_user_id}')"
              active_session.sql(insert_query).collect()
              st.success("API key securely stored and configuration complete!")
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
  if st.button("Add API Key", use_container_width=True):
    config_modal()
with col2:
  if st.button("Add Allocations", use_container_width=True):
    allocation_modal()

#Check if user has an API_KEY.
#If there is no api_key then none of this happens.
#If there is an api_key then try:

user_email = st.user["email"].upper()
api_query = f"""
SELECT API_KEY FROM JIRA_TIME_TRACKING.TEST.CONFIG_DETAILS_LATEST WHERE USER_EMAIL = \'{user_email}\';
"""
active_session.sql(api_query).collect()
api_query_res = active_session.sql(api_query)
api_query_res_arr = api_query_res.collect()[0]['API_KEY']
GET_ISSUES = "https://phdata.atlassian.net/rest/api/3/search/jql"
auth = HTTPBasicAuth(user_email, api_query_res_arr)
headers = {
    "Accept": "application/json"
}
params = {
    "jql": '(assignee = currentUser() OR watcher = currentUser()) AND status != Done ORDER BY key ASC',
    "fields": 'key, summary, status, created, customfield_10201, project',
    "maxResults": 200,
    "startAt": 0,
    "expand": "string"
}
try:
    response2 = requests.get(
        GET_ISSUES,
        headers=headers,
        params=params,
        auth=auth
    )
except requests.exceptions.RequestException as e:
    st.error(f"Error connecting to Jira: {e}")
    st.error(f"Response: {response2.text if 'response' in locals() else 'No response'}")
issue_result = json.loads(response2.text)


normalized_df = pd.json_normalize(issue_result['issues'])
base_url = "https://phdata.atlassian.net/browse/"
normalized_df['link'] = base_url + normalized_df['key'] + '#' + normalized_df['key']
columns_to_show = ['link', 'fields.summary']

filtered_df = normalized_df[columns_to_show]
issue_count = len(filtered_df)
st.text(f"You currently are assigned to or are watching {issue_count} issues.")
st.dataframe(filtered_df,hide_index=True,
    column_config={
    "link": st.column_config.LinkColumn(
        "Issue Key",
        display_text=r".*#(.+)$"
    ),
    "fields.summary": "Summary",
}
)

      

with st.expander("Components to build:"):
  st.markdown(":white_check_mark:   Input user email")
  st.markdown(":white_check_mark:   Input Jira filter id")
  st.markdown(":white_check_mark:   Input Jira API key")
  st.markdown(":white_check_mark:   Mask Jira API key")
  st.markdown(":white_check_mark:   Create view showing user's most recent submission")
  st.markdown(":white_check_mark:   Collect user Jira id (requires user email and API key)")
  st.markdown(":white_check_mark:   For issues: use (assigned or watching) and != Done")
  st.markdown(":white_check_mark:   Build a display of issues")
  st.markdown(":pencil2:   Hyperlink issue key")  
  st.markdown(":pencil2:   Input allocations")
  

with st.expander("Functionalities:"):
  st.markdown(":firecracker:   Button to pop up base config modal")
  st.markdown(":white_check_mark:   Modal to collect API key")
  st.markdown(":white_check_mark:   On modal submit -> collect API key, user Jira id and store with config details")
  st.markdown(":firecracker:   Button to pop up allocation modal")
  st.markdown("  :boom:   Modal has input table for: Jira project id, client name, project name, weekly hrs, effective dates")
  st.markdown("  :boom:   If allocation table has data in it, display current allocation details - including link to Jira board")
