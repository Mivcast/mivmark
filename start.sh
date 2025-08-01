#!/bin/bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
sleep 5
streamlit run frontend/app.py --server.port=8080 --server.address=0.0.0.0