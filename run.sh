#!/bin/bash

# 1. Start the FastAPI backend in the background (notice the '&' at the end)
echo "Starting FastAPI backend..."
uvicorn api:app --host 127.0.0.1 --port 8000 &

# Optional: If you need your database to build itself on startup, you can uncomment these!
# python database.py
# python ingest.py
# python mapping_creator.py

# 2. Wait a couple of seconds to let the API wake up
sleep 3

# 3. Start the Streamlit frontend in the foreground
echo "Starting Streamlit frontend..."
streamlit run ui.py --server.address 0.0.0.0
