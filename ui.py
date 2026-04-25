import streamlit as st
import requests

# 1. MUST BE FIRST! Move this above everything else.
st.set_page_config(page_title="Legal Logo", layout="wide")

# ==========================================
# 🎨 STREAMLIT UI CODE BELOW
# ==========================================

# The API is running secretly on port 8001
API_URL = "http://127.0.0.1:8001"

def highlight_text(text, query):
    """Highlight search terms in the results"""
    if not query:
        return text
    return text.replace(query, f"**{query}**")

def main():
    st.title("Legal Logo")
    st.caption("A Databricks Streamlit App to map IPC to BNS.")

    # 2. Sidebar with Setup & Health Check
    with st.sidebar:
        st.header("⚙️ System Status")
        st.write("This frontend connects to a FastAPI backend that is prepared separately.")
        st.caption("Run the Databricks setup notebook first, then start your API service.")
        
        try:
            # We check the /docs or /health endpoint of your API
            res = requests.get(API_URL, timeout=2)
            if res.status_code in [200, 404, 405]: 
                st.success("✅ Backend API is Online")
            else:
                st.warning(f"⚠️ API Status: {res.status_code}")
        except Exception:
            st.error("❌ Backend API is Offline")
            
        st.divider()
        st.markdown("**Model Version:** `v1.0-databricks`")

    # 3. Main Application Area
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search legal sections / legal actions", key="search_input")
    with col2:
        code_type = st.selectbox("Code", ["All", "IPC", "BNS"], index=0)
    
    if search_query:
        st.subheader("Search Results")

        params = {"q": search_query}
        if code_type != "All":
            params["code_type"] = code_type
        
        with st.spinner("Searching the legal database..."):
            try:
                action_resp = requests.get(f"{API_URL}/legal-action", params=params)
                
                if action_resp.status_code == 200:
                    action_data = action_resp.json()
                    results = action_data.get("results", [])
                    
                    if not results:
                        st.warning("No matching sections found")
                    else:
                        for item in results:
                            section = item["section"]
                            with st.expander(f"{section['code_type']} Section {section['section_number']}: {section['section_title']}"):
                                st.markdown(f"**Full Text:** {highlight_text(section['full_text'], search_query)}")
                                if item.get("mappings"):
                                    st.info("Mapping found to counterpart code.")
                else:
                    st.error(f"API Error: {action_resp.status_code}")

            except Exception as e:
                st.error(f"Search failed: {str(e)}")

if __name__ == "__main__":
    main()
