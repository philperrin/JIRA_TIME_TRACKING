import streamlit as st

st.title("🥊 Timeboxer")

st.text("Use this page to create events on your calendar for specific Jira tasks.")

with st.expander("Components to build:"):
  st.markdown(":pencil2:   Modal to create Google Cal event.")
  st.markdown(":pencil2:   Pull in Jira tasks (Jira API)")
  st.markdown(":pencil2:   Modal fields: date/time start, date/time end, title (Jira id); optional field: details")
  st.markdown(":pencil2:   Save button")
