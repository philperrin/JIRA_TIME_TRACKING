import streamlit as st

pages = {
    "Jira Time Tracker App": [
        st.Page("main.py", title="Log time to Jira"),
        st.Page("config.py", title="Configure"),
        st.Page("reports.py", title="Reports"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()
