-- Use these commands to create the objects needed in Snowflake. Note the useage of ACCOUNTADMIN. This is used to initially create the custom warehouse, role, db, schema and the API INTEGRATION.
-- The COMPUTE_WH is used initially but can be swapped out as needed.
-- I still need to put the RLS in here on the CONFIG_DETAILS table.


USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;

-- Set session variables.
---- Current user:
SET c_user = (SELECT CURRENT_USER());
---- Warehouse name:
SET wh_var = 'JIRA_TIME_TRACKING_WH';
---- Database name:
SET db_var = 'JIRA_TIME_TRACKING';
---- Schema name:
SET schema_var = 'TEST';
---- Role name:
SET role_var = 'JIRA_TIME_TRACKER';
---- Network rule name:
SET net_rule = 'JIRA_NETWORK_RULE';
---- API integration name:
SET api_int = 'JIRA_TIME_TRACKING_API';
---- Internal repository name:
SET repo_name = 'JIRA_TIME_TRACKING';
---- Streamlit app name:
SET app_name = 'JIRA_TIME_TRACKER';
---- Streamlit app title:
SET app_title = 'JIRA TIME TRACKER';

-- Create warehouse, role, database, and schema - set details per your needs.
EXECUTE IMMEDIATE $$
DECLARE
    c_user VARCHAR := $c_user;
    role_var VARCHAR := $role_var;
    wh_var VARCHAR := $wh_var;
    db_var VARCHAR := $db_var;
    schema_var VARCHAR := $schema_var;
BEGIN
    EXECUTE IMMEDIATE 'CREATE WAREHOUSE ' || wh_var || ' WITH WAREHOUSE_SIZE = XSMALL GENERATION = ''2'' AUTO_RESUME = TRUE AUTO_SUSPEND = 120 ENABLE_QUERY_ACCELERATION = TRUE QUERY_ACCELERATION_MAX_SCALE_FACTOR = 2';
    EXECUTE IMMEDIATE 'CREATE ROLE IF NOT EXISTS  ' || role_var ||'';
    EXECUTE IMMEDIATE 'GRANT ROLE ' || role_var ||' TO USER ' || c_user || '';
    EXECUTE IMMEDIATE 'CREATE DATABASE IF NOT EXISTS ' || db_var || '';
    EXECUTE IMMEDIATE 'CREATE SCHEMA IF NOT EXISTS ' || db_var || '.' || schema_var ||'';
    EXECUTE IMMEDIATE 'USE ROLE ACCOUNTADMIN';
    EXECUTE IMMEDIATE 'USE WAREHOUSE COMPUTE_WH';
END;
$$;

-- Use the new role, warehouse, and schema for the remainder of the script.
EXECUTE IMMEDIATE $$
DECLARE
    role_var VARCHAR := $role_var;
    wh_var VARCHAR := $wh_var;
    db_var VARCHAR := $db_var;
    schema_var VARCHAR := $schema_var;
BEGIN
    EXECUTE IMMEDIATE 'GRANT OPERATE ON WAREHOUSE ' || wh_var || ' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT USAGE ON WAREHOUSE ' || wh_var || ' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT USAGE ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT CREATE TABLE ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT CREATE VIEW ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT CREATE NETWORK RULE ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT CREATE GIT REPOSITORY ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT CREATE STAGE ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'GRANT CREATE STREAMLIT ON SCHEMA ' || db_var || '.' || schema_var ||' TO ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'USE ROLE ' || role_var ||'';
    EXECUTE IMMEDIATE 'USE WAREHOUSE ' || wh_var || '';
    EXECUTE IMMEDIATE 'USE SCHEMA ' || db_var || '.' || schema_var ||'';
END;
$$;

-- Create network rule, api integration, git repo, tables and view.
EXECUTE IMMEDIATE $$
DECLARE
    net_rule VARCHAR := $net_rule;
    api_int VARCHAR := $api_int;
    repo_name VARCHAR := $repo_name;
    db_var VARCHAR := $db_var;
    schema_var VARCHAR := $schema_var;
    role_var VARCHAR := $role_var;
BEGIN
    EXECUTE IMMEDIATE 'USE ROLE ACCOUNTADMIN';
    EXECUTE IMMEDIATE 'CREATE API INTEGRATION IF NOT EXISTS ' || api_int || ' API_PROVIDER = GIT_HTTPS_API API_ALLOWED_PREFIXES = (''https://github.com'') API_USER_AUTHENTICATION = (TYPE = snowflake_github_app) ENABLED = TRUE';
    EXECUTE IMMEDIATE 'USE ROLE ' || role_var || '';
    EXECUTE IMMEDIATE 'CREATE NETWORK RULE ' || net_rule || ' TYPE = HOST_PORT MODE = EGRESS VALUE_LIST = (''phdata.atlassian.net:443'')';
    EXECUTE IMMEDIATE 'CREATE GIT REPOSITORY IF NOT EXISTS ' || repo_name || ' ORIGIN = ''https://github.com/philperrin/JIRA_TIME_TRACKING/'' API_INTEGRATION = ' || api_int || '';
    EXECUTE IMMEDIATE 'CREATE TABLE ' || db_var || '.' || schema_var ||'.CONFIG_DETAILS (USER_EMAIL VARCHAR(50),UPDATED_AT TIMESTAMP_NTZ(9),API_KEY VARCHAR(250),JIRA_USER_ID VARCHAR(50))';
    EXECUTE IMMEDIATE 'CREATE TABLE ' || db_var || '.' || schema_var ||'.USER_PROJECTS (USERNAME VARCHAR(50),UPDATED_AT TIMESTAMP_NTZ(9),PROJ VARCHAR(50),PROJ_NAME VARCHAR(150)';
    EXECUTE IMMEDIATE 'CREATE TABLE ' || db_var || '.' || schema_var || '.ALLOCATION_DETAILS (USER_EMAIL VARCHAR(50),UPDATED_AT VARCHAR(50),JIRA_PROJ_ID VARCHAR(50),HRS_WK VARCHAR(50),EFFECTIVE_START VARCHAR(50),EFFECTIVE_END VARCHAR(50))';
    EXECUTE IMMEDIATE 'CREATE TABLE ' || db_var || '.' || schema_var ||'.TIME_LOG (USER_EMAIL VARCHAR(50),UPDATED_AT VARCHAR(50),JIRA_ID VARCHAR(50),JIRA_DATE VARCHAR(50),START_TIME VARCHAR(50),END_TIME VARCHAR(50))';
    EXECUTE IMMEDIATE 'CREATE VIEW ' || db_var || '.' || schema_var ||'.CONFIG_DETAILS_LATEST(USER_EMAIL,UPDATED_AT,API_KEY,JIRA_USER_ID) as WITH mostrecentconfig AS (SELECT USER_EMAIL,UPDATED_AT,API_KEY,JIRA_USER_ID,ROW_NUMBER() OVER (PARTITION BY USER_EMAIL ORDER BY UPDATED_AT DESC) AS rn FROM ' || db_var || '.' || schema_var ||'.CONFIG_DETAILS) SELECT USER_EMAIL,UPDATED_AT,API_KEY,JIRA_USER_ID FROM mostrecentconfig WHERE rn = 1';
END;
$$;

-- Internal repo should have collected files, but let's be explicit. Then create Streamlit app from internal repo.
EXECUTE IMMEDIATE $$
DECLARE
    repo_name VARCHAR := $repo_name;
    db_var VARCHAR := $db_var;
    schema_var VARCHAR := $schema_var;
    wh_var VARCHAR := $wh_var;
    app_name VARCHAR := $app_name;
    app_title VARCHAR := $app_title;
BEGIN
    EXECUTE IMMEDIATE 'ALTER GIT REPOSITORY ' || repo_name || ' FETCH';
    EXECUTE IMMEDIATE 'CREATE OR REPLACE STREAMLIT ' || db_var || '.' || schema_var || '.' || app_name || ' FROM @' || db_var || '.' || schema_var || '.' || repo_name || '/branches/main/ MAIN_FILE = ''streamlit_app.py'' QUERY_WAREHOUSE = ' || wh_var || ' TITLE = \' || app_title || \' ';
END;
$$;
