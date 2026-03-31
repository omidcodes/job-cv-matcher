import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8001"

def get_content_type(filename: str) -> str:
    if filename.endswith(".pdf"):
        return "application/pdf"
    elif filename.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"

st.title("Find Top Candidates")
st.write("Upload a job description to find the best matching candidates.")

uploaded_jd = st.file_uploader("Upload Job Description", type=["pdf", "docx"])

n_top_applicants = st.number_input(
    "Number of top candidates",
    min_value=1,
    max_value=10,
    value=5
)

if uploaded_jd and st.button("Find top candidates", type="primary"):
    with st.spinner("Finding best candidates..."):
        uploaded_jd.seek(0)
        response = requests.post(
            f"{API_URL}/find_candidates",
            files={"job_desc": (uploaded_jd.name, uploaded_jd.read(), uploaded_jd.type)},
            data={'n_top_applicants': n_top_applicants}
        )
    

    if response.status_code == 200:
        data = response.json()

        if data['result']['status'] == 'failed':
            st.warning(f"⚠️ Database is empty!")
        else:
            results = data['result']['result']

            st.success(f"{len(results)} candidates found")
            st.divider()

            # build dataframe from results
            df = pd.DataFrame(results)

            # rename and reorder columns for display
            df = df[["rank", "name", "location", "experience", "compatibility"]]
            df.columns = ["Rank", "Name", "Location", "Experience (yrs)", "Compatibility"]
            df = df.set_index(keys='Rank', drop=True)

            st.write(df)

            # colour compatibility column based on score value
            def colour_score(val):
                score = float(val.strip("%"))
                if score >= 75:
                    color = "#1D9E75"   # green
                elif score >= 50:
                    color = "#BA7517"   # amber
                else:
                    color = "#E24B4A"   # red
                return f"color: {color}; font-weight: 500"

            styled_df = (
                df.style
                .applymap(colour_score, subset=["Compatibility"])
                .set_properties(**{
                    "text-align": "left",
                    "font-size":  "14px",
                    "padding":    "8px 12px",
                })
                .set_table_styles([{
                    "selector": "th",
                    "props": [
                        ("font-size",        "13px"),
                        ("font-weight",      "500"),
                        ("text-align",       "left"),
                        ("padding",          "8px 12px"),
                        ("background-color", "#e2d1a5"),
                    ]
                }])
                .hide(axis="index")
            )

            st.dataframe(styled_df, use_container_width=True)

    elif response.status_code == 422:
        st.error("Validation error")
        st.json(response.json())
    else:
        st.error(f"Something went wrong — status {response.status_code}")