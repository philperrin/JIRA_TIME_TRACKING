import streamlit as st
import pandas as pd
from datetime import datetime
from snowflake.snowpark.context import get_active_session
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

active_session = get_active_session()
db_var = "JIRA_TIME_TRACKING"
env = "TEST"

st.title("🛠 Time Tracking Configuration")
st.text("Use this page to provide a Jira API token and update your weekly project allocations.")

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=['USER_EMAIL','FILTER_ID','API_KEY','UPDATED_AT'])

#Config Modal
@st.dialog("Add API Token")
def config_modal():
  with st.form("config_form", clear_on_submit=True):
    user_email = st.user["email"]
    username = user_email.split('@')[0]
    jira_cred_name = "jira_credentials_"+username
    st.markdown(f"Click [here](https://id.atlassian.com/manage-profile/security/api-tokens) to generate a Jira API token.")
    api_key = st.text_input("Jira API token")
    submitted = st.form_submit_button("Submit Details")
    secret_string = "'{ \"email\": \"" + user_email + "\" , \"api_token\": \"" + api_key + "\" }';"
    url = f"https://phdata.atlassian.net/rest/api/3/user/search?query={user_email}"
    if submitted:
      create_secret_sql = f"""
      CREATE OR REPLACE SECRET {db_var}.{env}.{jira_cred_name}
          TYPE = GENERIC_STRING
          SECRET_STRING = {secret_string}
      """
      active_session.sql(create_secret_sql).collect()
      
      secret_show = f"""
      SHOW SECRETS IN {db_var}.{env};
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
              TABLE_NAME = "CONFIG_DETAILS"
              COL1 = "USER_EMAIL" 
              COL2 = "API_KEY" 
              COL3 = "UPDATED_AT"
              COL4 = "JIRA_USER_ID"
              jira_user_id_r = json.loads(response.text)
              jira_user_id = jira_user_id_r[0]['accountId']
              insert_query = f"INSERT INTO {TABLE_NAME} ({COL1},{COL2},{COL3},{COL4}) VALUES (UPPER('{user_email}'),'{api_key}','{updated_at}','{jira_user_id}')"
              active_session.sql(insert_query).collect()
              st.success("API token securely stored and configuration complete!")
              st.rerun()
          except Exception as e:
              st.error(f"Error: {e}")
      else:
          st.warning("Please fill in all fields.")

if "submission_data" not in st.session_state:
  st.session_state["submission_data"] = None

#Allocation Modal
@st.dialog("Allocation Details")
def allocation_modal():
  st.markdown("Input details for a scheduled project allocation here. Submit this form once per project. These details are optional and only used on the reporting tab.")
  with st.form("allocation_form", clear_on_submit=True):
    user_email = st.user["email"].upper()
    proj_df = active_session.sql(f"SELECT PROJ FROM {db_var}.{env}.USER_PROJECTS WHERE USERNAME = \'{user_email}\'").to_pandas()
    proj_sel = proj_df['PROJ'].tolist()
    selected_proj = st.selectbox(
    'Select project:',
    proj_sel
    )
    hrs_wk = st.number_input(
        label="Hours per week:",
    format="%.2f"
    )
    proj_start = st.date_input("Start date:",format="MM/DD/YYYY")
    proj_end   = st.date_input("End date:",format="MM/DD/YYYY")
    submitted = st.form_submit_button("Save Allocation",)
    if submitted:
        TABLE_NAME = "ALLOCATION_DETAILS"
        COL1 = "USER_EMAIL" 
        COL2 = "JIRA_PROJ_ID"
        COL3 = "HRS_WK"
        COL4 = "EFFECTIVE_START"
        COL5 = "EFFECTIVE_END"
        COL6 = "UPDATED_AT"
        updated_at = datetime.now()
        try:
            active_session.sql(f"INSERT INTO {db_var}.{env}.{TABLE_NAME} ({COL1},{COL2},{COL3},{COL4},{COL5},{COL6}) VALUES('{user_email}','{selected_proj}','{hrs_wk}','{proj_start}','{proj_end}','{updated_at}')").collect()
            st.success("Allocation stored.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    #else:
    #    st.warning("Allocation error")

#Top of page
col1,col2,col3 = st.columns(3)
with col1:
  if st.button("Add API Token", use_container_width=True):
    config_modal()
with col2:
  if st.button("Add Project Allocations", use_container_width=True):
    allocation_modal()

user_email = st.user["email"].upper()
api_query = f"""
SELECT API_KEY FROM {db_var}.{env}.CONFIG_DETAILS_LATEST WHERE USER_EMAIL = \'{user_email}\';
"""
api_query_count = f"""
SELECT COUNT(*) AS row_count FROM {db_var}.{env}.CONFIG_DETAILS_LATEST WHERE USER_EMAIL = \'{user_email}\';
"""
st.header("Jira Issues", divider="gray")
try:
    api_count = active_session.sql(api_query_count).to_pandas()
    if not api_count.empty:
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
        columns_to_show = ['link', 'fields.summary','fields.project.name']

        filtered_df = normalized_df[columns_to_show]
        
        issue_count = len(filtered_df[~filtered_df['fields.project.name'].str.contains("Archived")])

        unique_projects = normalized_df[['fields.project.key','fields.project.name']].drop_duplicates()
        unique_projects = unique_projects[~unique_projects['fields.project.name'].str.contains("Archived")]
        
        try:
            TABLE_NAME = "USER_PROJECTS"
            COL1 = "USERNAME"
            COL2 = "UPDATED_AT"
            COL3 = "PROJ"
            COL4 = "PROJ_NAME"
            user_email = st.user["email"].upper()
            updated_at = datetime.now()
            active_session.sql(f"DELETE FROM {db_var}.{env}.{TABLE_NAME} WHERE USERNAME = \'{user_email}\'").collect()
            for index,j in unique_projects.iterrows():
                proj=j[0]
                proj_name = j[1]
                insert_query = f"INSERT INTO {db_var}.{env}.{TABLE_NAME} ({COL1},{COL2},{COL3},{COL4}) VALUES (UPPER('{user_email}'),'{updated_at}','{proj}','{proj_name}')"
                active_session.sql(insert_query).collect()
        except Exception as e:
            st.error(e)

        unique_project_count = len(unique_projects)

        st.text(f"Below you will find the Jira issues that you are either assigned to or are watching, grouped by project.\n\nYou currrently have {issue_count} Jira issues in {unique_project_count} projects. You may bill time against each of these issues on the main 'Log time to Jira' page.")
        st.text("You may click on any of these issues to change the assignee, status, or to stop watching them.")

        unique_projects_list = unique_projects[['fields.project.key','fields.project.name']].drop_duplicates()
        for index,proj in unique_projects_list.iterrows():
            subset_df = filtered_df[normalized_df['fields.project.key'] == proj[0]]
            with st.container(border=True):
                proj_link = "https://phdata.atlassian.net/jira/software/c/projects/"+proj[0]+"/summary"
                st.markdown(f"[{proj[1]}]({proj_link})")
                st.dataframe(subset_df,hide_index=True,
                             column_order={"link","fields.summary"},
                             column_config={
                                 "link": st.column_config.LinkColumn(
                                     "Issue Key",
                                     display_text=r".*#(.+)$"
                                 ),
                                 "fields.summary": "Summary",
                             })
    else:
        st.warning("Please add an API token to generate a summary of Jira issues.")
except Exception as e:
    st.warning("Please add an API token to generate a summary of Jira issues.")

st.header("Project Allocations", divider="gray")
allocation_count_query = f"""
SELECT COUNT(*) FROM {db_var}.{env}.ALLOCATION_DETAILS WHERE USER_EMAIL = \'{user_email}\' AND (EFFECTIVE_END >= CURRENT_DATE() OR EFFECTIVE_END IS NULL) ORDER BY JIRA_PROJ_ID ASC
"""
try:
    allocation_count = active_session.sql(allocation_count_query).to_pandas()
    if not api_count.empty:
        allocation_container = st.container(border=True)
        allocation_query = f"""
        SELECT JIRA_PROJ_ID, HRS_WK, EFFECTIVE_START, EFFECTIVE_END FROM {db_var}.{env}.ALLOCATION_DETAILS WHERE USER_EMAIL = \'{user_email}\' AND (EFFECTIVE_END >= CURRENT_DATE() OR EFFECTIVE_END IS NULL) ORDER BY JIRA_PROJ_ID ASC
        """
        allocation_df = active_session.sql(allocation_query)
        allocation_container.text("You have provided these details for your weekly allocations. On the 'Reports' page, you can view your time spent compared to your allocations.")
        allocation_container.dataframe(allocation_df,
                                       column_config={
                                           "JIRA_PROJ_ID": "Project",
                                           "HRS_WK": "Hours per week",
                                           "EFFECTIVE_START": "Start",
                                           "EFFECTIVE_END": "End"
                                           }
                                       ,hide_index=True)
    else:
        st.warning("Please add API key and allocations.")
except Exception as e:
    st.warning("Please add API key and allocations.")
