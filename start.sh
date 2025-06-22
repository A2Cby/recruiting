#!/usr/bin/env bash
set -e            # exit on any error
# launch API in background
uvicorn main:app --host 0.0.0.0 --port 8910 &
# launch Streamlit in foreground (keeps container alive)
streamlit run streamlit_app.py \
          --server.address 0.0.0.0 \
          --server.port 8501
