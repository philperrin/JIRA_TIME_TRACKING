import streamlit as st

st.title("⏰ Log time to Jira")

st.text("Use this page to assign your time to specific tasks in Jira.")

with st.expander("First time here?"):
  st.markdown("Put in some 'Read Me' info here.")

with st.expander("Components to build:"):
  st.markdown(":pencil2:   Quick summary - hrs in Jira for day and week")
  st.markdown(":pencil2:   How to best populate time to task.... log line to populate to df w/ commit button?")
  st.markdown(":pencil2:   Required: date, task, start datetime, duration (or end time)")
  st.markdown(":pencil2:   Optional: comments")
  st.markdown(":pencil2:   Commit button")

with st.expander("Functionalities:"):
  st.markdown(":firecracker:   Time log input device")
  st.markdown("&nbsp;&nbsp;:boom:   Only show if config details present")
  st.markdown("&nbsp;&nbsp;:boom:   Show input elements: date (cal input), task (dropdown from allocations), start (time), end (time), capture button")
  st.markdown("&nbsp;&nbsp;:boom:   Capture dataframe: each time capture button is clicked, add log details to dataframe")
  st.markdown("&nbsp;&nbsp;:boom:   Submit dataframe: send each log details to Jira, store log details to table (with extra details)")
  st.markdown(":firecracker:   Create new Jira")
  st.markdown("&nbsp;&nbsp;:boom:   Modal to create new Jira (drop down from current projects, assigns to self, etc)")
  st.markdown("&nbsp;&nbsp;:boom:   Then runs the script to pull in jiras based on filter.")
  
