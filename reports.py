import streamlit as st

st.set_page_config(
    layout="wide"
)

st.title("📊 Reports")

st.text("Show user insights.")

with st.expander("Components to build:"):
  st.markdown(":pencil2:   Current week: hours to allcations")
  st.markdown(":pencil2:   Current month: hours to allocations")
  st.markdown(":pencil2:   Current year: hours to allocations")
