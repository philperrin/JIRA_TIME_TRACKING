import streamlit as st

pages = {
    "Your account": [
        st.Page("main.py", title="Log time to Jira"),
        st.Page("config.py", title="Configure"),
        st.Page("reports.py", title="Reports"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()
