import streamlit as st
st.title("Config")

st.text("Use this page to provide configuration details necessary for the app.")

st.subheader("Components to build:", divider="gray")
st.markdown(":pencil2:   Input user email")
st.markdown(":pencil2:   Input Jira filter id")
st.markdown(":pencil2:   Input Jira API key")
st.markdown(":pencil2:   Collect user Jira id (requires user email and API key)")
st.markdown(":pencil2:   Input allocations (Jira project id, client name, project name, weekly hrs, effective dates)")
st.markdown(":pencil2:   Collect issues from Jira filter id")
