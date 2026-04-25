import streamlit as st
import requests

# 1. Page Configuration
st.set_page_config(page_title="IPC to BNS Model", layout="wide")

st.title("⚖️ IPC to BNS — Legal Model Explorer")
st.caption("A Databricks Streamlit App that connects to your background API to map IPC to BNS.")

# Because your API is running in the background of the same cluster, we use localhost!
API_URL = "http://127.0.0.1:8000"

# 2. Sidebar with Setup & Health Check
with st.sidebar:
    st.header("⚙️ System Status")
    st.write("This frontend connects to the local FastAPI backend running on port `8000`.")
    
    # Try to ping the backend API to see if it is alive
    try:
        # Assuming your API has a basic root ("/") or health endpoint
        res = requests.get(API_URL, timeout=2)
        if res.status_code == 200 or res.status_code == 404: 
            # 404 just means the root path isn't defined, but the server is awake!
            st.success("✅ Backend API is Online")
        else:
            st.warning(f"⚠️ API returned status: {res.status_code}")
    except Exception:
        st.error("❌ Backend API is Offline. Make sure Uvicorn is running!")
        
    st.divider()
    st.markdown("**Model Version:** `v1.0-databricks`")

# 3. Main Application Area
st.markdown("### Enter IPC Details")
ipc_query = st.text_input(
    "Indian Penal Code (IPC) Section or Description:", 
    placeholder="e.g., Section 420 or 'Theft'"
)

if st.button("Translate to BNS", type="primary"):
    if ipc_query:
        with st.spinner("Querying the model..."):
            try:
                # IMPORTANT: Change "/predict" to whatever your actual API endpoint is named!
                response = requests.post(f"{API_URL}/predict", json={"query": ipc_query})
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Mapping Successful!")
                    st.write("### 📜 BNS Result:")
                    st.json(data) # Displays the API response beautifully
                else:
                    st.error(f"API Error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                st.error(f"Failed to connect to the backend API. Did you write the correct endpoint? Error: {e}")
    else:
        st.warning("Please enter an IPC section to proceed.")

# 4. Next Ideas Footer
st.divider()
# FIX: Removed the backslashes from the triple quotes below!
st.markdown(
    """
    **Next ideas for development**
    - Format the JSON output into a clean, readable UI table instead of raw data.
    - Add a secondary tab to upload bulk CSV files for batch IPC-to-BNS translation.
    - Add a chat interface connecting to your Langchain/OpenAI agent to ask legal questions.
    """
)
