import streamlit as st

def config():
    st.title("Config")
def reports():
    st.title("Reports")

pg = st.navigation(["main.py", config, reports])
pg.run()
