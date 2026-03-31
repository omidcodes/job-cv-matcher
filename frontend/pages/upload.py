import streamlit as st
import requests

API_URL = "http://localhost:8001"


st.title("Upload CVs")
st.write("Upload PDF or DOCX")

uploaded_files = st.file_uploader(
    "Choose CV files",
    type=["pdf", "docx"],
    accept_multiple_files=True
)


if uploaded_files:
    st.info(f"{len(uploaded_files)} file(s) selected")

if uploaded_files and st.button("Upload All", type="primary"):
    with st.spinner("Uploading CVs..."):

        files = []
        for f in uploaded_files:
            f.seek(0)   # reset buffer to start before reading
            files.append(
                ("files", (f.name, f.read(), f.type))
            )

        response = requests.post(f"{API_URL}/upload_cvs", files=files)

    if response.status_code == 200:
        

         
        data = response.json()
        if data['total'] == data['success']:
            st.success(f"✅ All files uploaded successfully!")

        elif data['total'] > data['success'] and data['success'] > 0:
            st.warning(f"⚠️ {data['success']} out of {data['total']} files uploaded successfully!")

        else:
            st.error(f"❌ No file was uploaded successfully!")

    else:
        st.error(f"❌ An error occurred while uploading CVs!")




