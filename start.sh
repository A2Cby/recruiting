#!/usr/bin/env bash
set -e
uvicorn main:app --host 0.0.0.0 --port 8910 &
# launch Streamlit in foreground (keeps container alive)
streamlit run website_demo.py \
          --server.address 0.0.0.0 \
          --server.port 8912
