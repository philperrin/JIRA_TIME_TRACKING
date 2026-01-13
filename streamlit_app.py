import streamlit as st

def page_2():
    st.title("Page 2")
def page_3():
    st.title("Page 3")

pg = st.navigation(["main.py", page_2, page_3])
pg.run()
