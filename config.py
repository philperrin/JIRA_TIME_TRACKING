import streamlit as st
st.title("Config")

st.text("Use this page to provide configuration details necessary for the app.")

st.subheader("Components to build:", divider="gray")
st.markdown(":pencil2:   Input user email")
st.markdown(":pencil2:   Input Jira filter id")
st.markdown(":pencil2:   Input Jira API key")
st.markdown(":pencil2:   Collect user Jira id (requires user email and API key)")
st.markdown(":pencil2:   Input allocations")
st.markdown(":pencil2:   Collect issues from Jira filter id")

st.subheader("Functionalities:", divider="gray")
st.markdown(":firecracker:   Button to pop up base config modal")
st.markdown(":boom:   Modal to collect user email, filter id, API key")
st.markdown(":boom:   On modal submit -> create Schema for user with: config table, allocation table, history table")
st.markdown(":boom:   On modal submit -> collect user Jira id")
st.markdown(":firecracker:   Button to pop up allocation modal")
st.markdown(":boom:   Modal has input table for: Jira project id, client name, project name, weekly hrs, effective dates")
st.markdown(":boom:   If allocation table has data in it, display current allocation details - including link to Jira board")
