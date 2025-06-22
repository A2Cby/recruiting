"""
Streamlit UI for manual testing of the matching pipeline — **now password‑protected**.

Pages:
1. **Submit Vacancy** – build `vacancy_text` and POST to
   `http://93.127.132.57:8910/api/v1/matching/match_candidates_batch`.
2. **Inspect Vacancy** – query `recruting_selected_candidates` by `vacancy_id`, show
   the parsed `data_json → candidates` list.

> **Tip:** if you hit `AttributeError: module 'streamlit' has no attribute 'experimental_rerun'`,
> you are on a Streamlit version where the function graduated to `st.rerun()`. The
> code below now handles both APIs automatically.

Quick start:
```bash
pip install "streamlit>=1.25" psycopg2-binary sshtunnel python-dotenv requests pandas
export APP_PASSWORD=supersecret        # 🔑 app‑level password
export SSH_HOST=... DB_NAME=...        # same env vars as before
streamlit run streamlit_app.py
```
"""

import json
import os
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()
API_URL = "http://93.127.132.57:8910/api/v1/matching/match_candidates_batch"
APP_PASSWORD = os.getenv("APP_PASSWORD", "8910")


def check_password() -> bool:
    """Return True if user already authenticated or just entered correct password."""
    if st.session_state.get("_auth_ok"):
        return True

    st.subheader("🔒 Login required")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == APP_PASSWORD:
            st.session_state["_auth_ok"] = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False

# ---------------------------------------------------------------------------
# SSH‑>Postgres helper
# ---------------------------------------------------------------------------

def get_db_tunnel_and_conn():
    """Open an SSH tunnel and return (tunnel, psycopg2 connection)."""
    tunnel = SSHTunnelForwarder(
        ssh_address_or_host=os.getenv("SSH_HOST"),
        ssh_port=int(os.getenv("SSH_PORT")),
        ssh_username=os.getenv("SSH_USER"),
        ssh_password=os.getenv("SSH_PASSWORD"),
        remote_bind_address=(os.getenv("DB_HOST"), int(os.getenv("DB_PORT"))),
    )
    tunnel.start()

    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=tunnel.local_bind_host,
        port=tunnel.local_bind_port,
        cursor_factory=DictCursor,
    )
    return tunnel, conn

# ---------------------------------------------------------------------------
# Page: submit vacancy
# ---------------------------------------------------------------------------

def page_submit():
    st.header("Send a Vacancy to Matching API")
    with st.form("vacancy_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            vacancy_id = st.number_input("Vacancy ID", step=1, min_value=1)
            location = st.text_input("Location", value="everywhere")
            experience = st.number_input("Experience (years)", min_value=0, step=1)
        with col2:
            title = st.text_input("Title")
            skills = st.text_input("Skills (comma‑separated)")
        description = st.text_area("Description", height=150)

        submitted = st.form_submit_button("Send to API 🚀")

    if submitted:
        vacancy_text = (
            f"Vacancy title: {title}\n"
            f"Vacancy Description: {description}\n"
            f"From: {location}\n"
            f"Skillset: {skills}\n"
            f"With {experience} years of experience\n"
        )
        payload = {"vacancy_id": int(vacancy_id), "vacancy_text": vacancy_text}

        with st.spinner("Calling API…"):
            try:
                res = requests.post(API_URL, json=payload, timeout=60)
                if res.status_code == 202:
                    st.success("✅ Accepted (202)")
                    try:
                        st.json(res.json())
                    except Exception:
                        st.text(res.text)
                else:
                    st.error(f"API responded {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Request error: {e}")

# ---------------------------------------------------------------------------
# Page: Inspect vacancy
# ---------------------------------------------------------------------------

def page_inspect():
    st.header("Inspect a Vacancy by ID")

    col1, col2 = st.columns([2, 1])
    with col1:
        vacancy_id = st.number_input("vacancy_id", min_value=1, step=1)
    with col2:
        submitted = st.button("🔍 Load")

    if submitted:
        with st.spinner("Loading data_json …"):
            try:
                tunnel, conn = get_db_tunnel_and_conn()
                df = pd.read_sql(
                    """
                    SELECT data_json
                    FROM recruting_selected_candidates
                    WHERE vacancy_id = %s
                    ORDER BY date_time DESC
                    LIMIT 1;
                    """,
                    conn,
                    params=(int(vacancy_id),),
                )
            finally:
                conn.close(); tunnel.stop()

        if df.empty:
            st.warning(f"Vacancy {vacancy_id} not found.")
            return

        raw = df.loc[0, "data_json"]
        try:
            parsed = json.loads(raw)["candidates"]
        except Exception as e:
            st.error(f"Parse error → showing raw string. {e}")
            st.text(raw)
            return

        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            st.dataframe(pd.json_normalize(parsed), use_container_width=True)
        else:
            st.json(parsed)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not check_password():
        st.stop()  # halt execution until logged in

    st.sidebar.title("Vacancy Tools")
    page = st.sidebar.radio("Go to", ("Submit Vacancy", "Inspect Vacancy"))
    if page == "Submit Vacancy":
        page_submit()
    else:
        page_inspect()

if __name__ == "__main__":
    main()
