#!/bin/bash

# 1. Start the FastAPI backend in the background (notice the '&' at the end)
echo "Starting FastAPI backend..."
uvicorn api:app --host 127.0.0.1 --port 8001 &

python database.py
python ingest.py
python mapping_creator.py

# 2. Wait a couple of seconds
sleep 3

# 3. Start Streamlit in the foreground on the PUBLIC port (8000)
echo "Starting Streamlit frontend..."
streamlit run ui.py --server.port 8000 --server.address 0.0.0.0
