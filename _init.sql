-- Run these in your SQL environment first to get the bones set up.

-- Set session variables.
SET wh_var = JIRA_TIME_TRACKING_WH;
SET db_var = JIRA_TIME_TRACKING;
SET schema_var = TEST;
SET role_var = JIRA_TIME_TRACKER;
SET net_rule = JIRA_NETWORK_RULE;
SET api_int = JIRA_TIME_TRACKING_API;
SET repo_name = JIRA_TIME_TRACKING;
SET app_name = JIRA_TIME_TRACKER;
SET app_title = 'JIRA TIME TRACKER';

-- Create warehouse, set details per your needs.
CREATE WAREHOUSE IF NOT EXISTS $wh_var 
  WITH WAREHOUSE_SIZE = XSMALL
  GENERATION = '2'
  AUTO_RESUME = TRUE
  AUTO_SUSPEND = 120
  ENABLE_QUERY_ACCELERATION = TRUE
  QUERY_ACCELERATION_MAX_SCALE_FACTOR = 2;
USE WAREHOUSE $wh_var;

-- Database & schema.
CREATE DATABASE IF NOT EXISTS $db_var;
CREATE SCHEMA IF NOT EXISTS $db_var.$schema_var;
USE SCHEMA $db_var.$schema_var;

-- Create role.
CREATE ROLE IF NOT EXISTS $role_var;
USE ROLE $role_var;

-- Create a network rule so Snowflake can access Jira.
CREATE NETWORK RULE $net_rule
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = ('phdata.atlassian.net:443');

-- Create an API integration profile.
CREATE API INTEGRATION IF NOT EXISTS $api_int
  API_PROVIDER = GIT_HTTPS_API
  API_ALLOWED_PREFIXES = ('https://github.com')
  API_USER_AUTHENTICATION = (
    TYPE = snowflake_github_app)
  ENABLED = TRUE;

-- Access Git repo for codebase.
CREATE GIT REPOSITORY IF NOT EXISTS $repo_name
  ORIGIN = 'https://github.com/philperrin/JIRA_TIME_TRACKING/'
  API_INTEGRATION = $api_int;

-- Create tables.
CREATE TABLE $db_var.$schema_var.CONFIG_DETAILS (
	USER_EMAIL VARCHAR(50),
	UPDATED_AT TIMESTAMP_NTZ(9),
	API_KEY VARCHAR(250),
	JIRA_USER_ID VARCHAR(50)
);
CREATE TABLE $db_var.$schema_var.USER_PROJECTS (
	USERNAME VARCHAR(50),
	UPDATED_AT TIMESTAMP_NTZ(9),
	PROJ VARCHAR(50)
);
CREATE TABLE $db_var.$schema_var.ALLOCATION_DETAILS (
	USER_EMAIL VARCHAR(50),
	UPDATED_AT VARCHAR(50),
	JIRA_PROJ_ID VARCHAR(50),
	HRS_WK VARCHAR(50),
	EFFECTIVE_START VARCHAR(50),
	EFFECTIVE_END VARCHAR(50)
);
CREATE TABLE $db_var.$schema_var.TIME_LOG (
	USER_EMAIL VARCHAR(50),
	UPDATED_AT VARCHAR(50),
	JIRA_ID VARCHAR(50),
	JIRA_DATE VARCHAR(50),
	START_TIME VARCHAR(50),
	END_TIME VARCHAR(50)
);

-- Create views.
CREATE VIEW $db_var.$schema_var.CONFIG_DETAILS_LATEST(
	USER_EMAIL,
	UPDATED_AT,
	API_KEY,
	JIRA_USER_ID
) as
    WITH mostrecentconfig AS (
        SELECT
            USER_EMAIL,
            UPDATED_AT,
            API_KEY,
            JIRA_USER_ID,
            ROW_NUMBER() OVER (
                PARTITION BY USER_EMAIL
                ORDER BY UPDATED_AT DESC
            ) AS rn
        FROM
            $db_var.$schema_var.CONFIG_DETAILS
    )
    SELECT
        USER_EMAIL,
        UPDATED_AT,
        API_KEY,
        JIRA_USER_ID
    FROM
        mostrecentconfig
    WHERE
        rn = 1;

-- Update internal repo files.
ALTER GIT REPOSITORY $repo_name FETCH;

-- Create Streamlit app from internal repo.
CREATE OR REPLACE STREAMLIT $db_var.$schema_var.$app_name
    ROOT_LOCATION = '@$db_var.$schema_var.$repo_name/branches/main'
    MAIN_FILE = '/streamlit_app.py'
    QUERY_WAREHOUSE = JIRA_TIME_TRACKING_WH
    TITLE = $app_title;

-- It should already have the files loaded, but let's be explicit.
ALTER STREAMLIT $app_name PULL;
