import streamlit as st

def page_2():
    st.title("Config")
def page_3():
    st.title("Page 3")

pg = st.navigation(["main.py", config, page_3])
pg.run()
