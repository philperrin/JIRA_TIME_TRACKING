import streamlit as st

def page_2():
    st.title("Config")
def page_3():
    st.title("Reports")

pg = st.navigation(["main.py", config, reports])
pg.run()
