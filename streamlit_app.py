import streamlit as st
st.set_page_config(
    layout="centered")
pages = {
    "Menu": [
        st.Page("log.py", title="Log time to Jira"),
        st.Page("config.py", title="Configure"),
        st.Page("timeboxer.py", title="Timeboxer"),
        st.Page("reports.py", title="Reports"),
    ],
}
pg = st.navigation(pages, position="top")
pg.run()
