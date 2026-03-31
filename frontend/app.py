import streamlit as st

st.set_page_config(
    page_title="CV Search",
    page_icon="🔍",
    layout="centered"
)

pages = {
    "Search": [
        st.Page("pages/search.py", title="Search Candidates", icon="🔍"),
        st.Page("pages/upload.py", title="Upload CVs",        icon="📁"),
    ]
}

pg = st.navigation(pages)
pg.run()