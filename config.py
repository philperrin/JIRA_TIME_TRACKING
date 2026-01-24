import streamlit as st
import pandas as pd
from datetime import datetime
from snowflake.snowpark.context import get_active_session
import requests
from requests.auth import HTTPBasicAuth
import json

active_session = get_active_session()
db_var = "JIRA_TIME_TRACKING"
env = "TEST"

# Constants
JIRA_BASE_URL = "https://phdata.atlassian.net"
JIRA_API_BASE = f"{JIRA_BASE_URL}/rest/api/3"
JIRA_BROWSE_URL = f"{JIRA_BASE_URL}/browse/"
JIRA_PROJECTS_URL = f"{JIRA_BASE_URL}/jira/software/c/projects/"
JIRA_TOKEN_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"

# Table names
TABLE_CONFIG = "CONFIG_DETAILS"
TABLE_CONFIG_LATEST = "CONFIG_DETAILS_LATEST"
TABLE_ALLOCATIONS = "ALLOCATION_DETAILS"
TABLE_USER_PROJECTS = "USER_PROJECTS"

st.title("🛠 Time Tracking Configuration")
st.text("Use this page to provide a Jira API token and update your weekly project allocations.")

# Config Modal
@st.dialog("Add API Token")
def config_modal():
    with st.form("config_form", clear_on_submit=True):
        user_email = st.user["email"]
        username = user_email.split('@')[0]
        jira_cred_name = f"jira_credentials_{username}"
        st.markdown(f"Click [here]({JIRA_TOKEN_URL}) to generate a Jira API token.")
        api_key = st.text_input("Jira API token", type="password")
        submitted = st.form_submit_button("Submit Details")
        secret_dict = {"email": user_email, "api_token": api_key}
        secret_string = f"'{json.dumps(secret_dict)}';"
        url = f"{JIRA_API_BASE}/user/search?query={user_email}"
        
        if not submitted:
            return
        
        if not user_email or not api_key:
            st.warning("Please fill in all fields.")
            return
        
        try:
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
            
            active_session.sql(update_auth_sec).collect()
            
            # Verify API token with Jira
            auth = HTTPBasicAuth(user_email, api_key)
            headers = {"Accept": "application/json"}
            
            response = requests.get(url, headers=headers, auth=auth, timeout=10)
            response.raise_for_status()
            jira_users = response.json()
            
            if not jira_users:
                st.error("Could not find Jira user account.")
                return
            
            jira_user_id = jira_users[0]['accountId']
            updated_at = datetime.now()
            
            # Store configuration
            insert_query = f"""
            INSERT INTO {db_var}.{env}.{TABLE_CONFIG} 
            (USER_EMAIL, API_KEY, UPDATED_AT, JIRA_USER_ID) 
            VALUES (UPPER('{user_email}'), '{api_key}', '{updated_at}', '{jira_user_id}')
            """
            active_session.sql(insert_query).collect()
            
            st.session_state["submission_data"] = {"email": user_email, "api_key": api_key}
            st.success("API token securely stored and configuration complete!")
            st.rerun()
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to Jira: {e}")
            if hasattr(e, 'response') and e.response is not None:
                st.error(f"Response: {e.response.text}")
        except Exception as e:
            st.error(f"Configuration error: {e}")

if "submission_data" not in st.session_state:
  st.session_state["submission_data"] = None

# Allocation Modal
@st.dialog("Allocation Details")
def allocation_modal():
    st.markdown("Input details for a scheduled project allocation here. Submit this form once per project. These details are optional and only used on the reporting tab.")
    with st.form("allocation_form", clear_on_submit=True):
        user_email = st.user["email"].upper()
        
        try:
            proj_df = active_session.sql(
                f"SELECT PROJ FROM {db_var}.{env}.{TABLE_USER_PROJECTS} WHERE USERNAME = '{user_email}'"
            ).to_pandas()
            proj_sel = proj_df['PROJ'].tolist()
        except Exception as e:
            st.error(f"Error loading projects: {e}")
            return
        
        if not proj_sel:
            st.warning("No projects found. Please add an API token first to populate your projects.")
            return
        
        selected_proj = st.selectbox('Select project:', proj_sel)
        hrs_wk = st.number_input(label="Hours per week:", format="%.2f", min_value=0.0)
        proj_start = st.date_input("Start date:", format="MM/DD/YYYY")
        proj_end = st.date_input("End date:", format="MM/DD/YYYY")
        submitted = st.form_submit_button("Save Allocation")
        
        if submitted:
            if proj_start > proj_end:
                st.error("Start date must be before end date.")
                return
            
            updated_at = datetime.now()
            try:
                insert_query = f"""
                INSERT INTO {db_var}.{env}.{TABLE_ALLOCATIONS} 
                (USER_EMAIL, JIRA_PROJ_ID, HRS_WK, EFFECTIVE_START, EFFECTIVE_END, UPDATED_AT) 
                VALUES ('{user_email}', '{selected_proj}', {hrs_wk}, '{proj_start}', '{proj_end}', '{updated_at}')
                """
                active_session.sql(insert_query).collect()
                st.success("Allocation stored.")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving allocation: {e}")

# Top of page buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Add API Token", use_container_width=True):
        config_modal()
with col2:
    if st.button("Add Project Allocations", use_container_width=True):
        allocation_modal()

# Jira Issues Section
user_email = st.user["email"].upper()
st.header("Jira Issues", divider="gray")

try:
    # Combined query to get API key and check existence
    api_query = f"""
    SELECT API_KEY 
    FROM {db_var}.{env}.{TABLE_CONFIG_LATEST} 
    WHERE USER_EMAIL = '{user_email}'
    """
    api_result = active_session.sql(api_query).collect()
    
    if not api_result:
        st.warning("Please add an API token to generate a summary of Jira issues.")
    else:
        api_key = api_result[0]['API_KEY']
        
        # Fetch Jira issues
        auth = HTTPBasicAuth(user_email, api_key)
        headers = {"Accept": "application/json"}
        params = {
            "jql": '(assignee = currentUser() OR watcher = currentUser()) AND status != Done ORDER BY key ASC',
            "fields": 'key,summary,status,created,customfield_10201,project',
            "maxResults": 200,
            "startAt": 0
        }
        
        response2 = requests.get(
            f"{JIRA_API_BASE}/search/jql",
            headers=headers,
            params=params,
            auth=auth,
            timeout=30
        )
        response2.raise_for_status()
        issue_result = response2.json()
        
        if not issue_result.get('issues'):
            st.info("No Jira issues found.")
        else:
            normalized_df = pd.json_normalize(issue_result['issues'])
            
            # Filter out archived projects first
            normalized_df = normalized_df[~normalized_df['fields.project.name'].str.contains("Archived", na=False)]
            
            ##### Need to send this to a table to use as needed.
            st.dataframe(normalized_df[['id', 'key', 'fields.summary', 'fields.project.key','fields.project.name']])

            
            # Create link column
            normalized_df['link'] = JIRA_BROWSE_URL + normalized_df['key'] + '#' + normalized_df['key']
            
            # Get unique projects
            unique_projects = normalized_df[['fields.project.key', 'fields.project.name']].drop_duplicates()
            
            # Store user projects with batch insert
            try:
                updated_at = datetime.now()
                active_session.sql(
                    f"DELETE FROM {db_var}.{env}.{TABLE_USER_PROJECTS} WHERE USERNAME = '{user_email}'"
                ).collect()
                
                if not unique_projects.empty:
                    # Batch insert instead of loop
                    values = [
                        f"('{user_email}', '{updated_at}', '{row[0]}', '{row[1]}')"
                        for _, row in unique_projects.iterrows()
                    ]
                    insert_query = f"""
                    INSERT INTO {db_var}.{env}.{TABLE_USER_PROJECTS} 
                    (USERNAME, UPDATED_AT, PROJ, PROJ_NAME) 
                    VALUES {','.join(values)}
                    """
                    active_session.sql(insert_query).collect()
            except Exception as e:
                st.error(f"Error storing projects: {e}")
            
            # Display issue summary
            issue_count = len(normalized_df)
            unique_project_count = len(unique_projects)
            
            st.text(
                f"Below you will find the Jira issues that you are either assigned to or are watching, grouped by project.\\n\\n"
                f"You currently have {issue_count} Jira issue{'s' if issue_count != 1 else ''} in {unique_project_count} project{'s' if unique_project_count != 1 else ''}. "
                f"You may bill time against each of these issues on the main 'Log time to Jira' page."
            )
            st.text("You may click on any of these issues to change the assignee, status, or to stop watching them.")
            
            # Display issues grouped by project
            columns_to_show = ['link', 'fields.summary', 'fields.project.name']
            filtered_df = normalized_df[columns_to_show]
            
            unique_projects_sorted = unique_projects.sort_values(by='fields.project.name')
            for _, proj in unique_projects_sorted.iterrows():
                subset_df = filtered_df[normalized_df['fields.project.key'] == proj['fields.project.key']]
                with st.container(border=True):
                    proj_link = f"{JIRA_PROJECTS_URL}{proj['fields.project.key']}/summary"
                    st.markdown(f"[{proj['fields.project.name']}]({proj_link})")
                    st.dataframe(
                        subset_df,
                        hide_index=True,
                        column_order=("link", "fields.summary"),
                        column_config={
                            "link": st.column_config.LinkColumn(
                                "Issue Key",
                                display_text=r".*#(.+)$"
                            ),
                            "fields.summary": "Summary",
                        }
                    )
                
except requests.exceptions.RequestException as e:
    st.error(f"Error connecting to Jira API: {e}")
except Exception as e:
    st.error(f"Error loading Jira issues: {e}")

# Project Allocations Section
st.header("Project Allocations", divider="gray")

try:
    allocation_query = f"""
    SELECT JIRA_PROJ_ID, HRS_WK, EFFECTIVE_START, EFFECTIVE_END 
    FROM {db_var}.{env}.{TABLE_ALLOCATIONS} 
    WHERE USER_EMAIL = '{user_email}' 
    AND (EFFECTIVE_END >= CURRENT_DATE() OR EFFECTIVE_END IS NULL) 
    ORDER BY JIRA_PROJ_ID ASC
    """
    allocation_result = active_session.sql(allocation_query).collect()
    
    if not allocation_result:
        st.info("No active allocations found. Click 'Add Project Allocations' to add one.")
    else:
        allocation_container = st.container(border=True)
        allocation_df = active_session.sql(allocation_query)
        allocation_container.text(
            "You have provided these details for your weekly allocations. "
            "On the 'Reports' page, you can view your time spent compared to your allocations."
        )
        allocation_container.dataframe(
            allocation_df,
            column_config={
                "JIRA_PROJ_ID": "Project",
                "HRS_WK": "Hours per week",
                "EFFECTIVE_START": "Start",
                "EFFECTIVE_END": "End"
            },
            hide_index=True
        )
        
except Exception as e:
    st.error(f"Error loading allocations: {e}")
