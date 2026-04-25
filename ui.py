import streamlit as st
import requests
from database import Session, LegalSection

# 1. Page Configuration
st.set_page_config(page_title="Legal Logo", layout="wide")

# Because your API is running in the background of the same cluster, we use localhost!
API_URL = "http://127.0.0.1:8000"

def highlight_text(text, query):
    """Highlight search terms in the results"""
    if not query:
        return text
    return text.replace(query, f"**{query}**")

def main():
    # Title requested by you
    st.title("Legal Logo")
    st.caption("A Databricks Streamlit App to map IPC to BNS.")

    # 2. Sidebar with Setup & Health Check
    with st.sidebar:
        st.header("⚙️ System Status")
        st.write("This frontend connects to the local FastAPI backend running on port `8000`.")
        
        # Try to ping the backend API to see if it is alive
        try:
            res = requests.get(API_URL, timeout=2)
            # 200, 404, or 405 all indicate the server is awake and responding!
            if res.status_code in [200, 404, 405]: 
                st.success("✅ Backend API is Online")
            else:
                st.warning(f"⚠️ API returned status: {res.status_code}")
        except Exception:
            st.error("❌ Backend API is Offline. Make sure Uvicorn is running!")
            
        st.divider()
        st.markdown("**Model Version:** `v1.0-databricks`")

    # 3. Main Application Area (Your Original Logic)
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
                # ⬇️ This is the crucial fix: GET request to /legal-action
                action_resp = requests.get(
                    f"{API_URL}/legal-action",
                    params=params
                )
                
                if action_resp.status_code != 200:
                    st.error(f"API Error: {action_resp.status_code} - {action_resp.text}")
                    return
                    
                action_data = action_resp.json()

                results = action_data.get("results", [])
                extracted_keywords = action_data.get("extracted_keywords", [])
                
                if extracted_keywords:
                    st.caption(f"Auto-extracted keywords: {', '.join(extracted_keywords)}")

                if not results:
                    st.warning("No matching sections found")
                    return

                # Displaying the results using your expanders
                for item in results:
                    section = item["section"]
                    section_num = section["section_number"]
                    title = section["section_title"]
                    
                    with st.expander(
                        f"{section['code_type']} Section {section_num}: {title} "
                        f"(relevance: {item.get('relevance_score', 0)})"
                    ):
                        highlighted_text = highlight_text(section["full_text"], search_query)
                        st.markdown(f"**Full Text:** {highlighted_text}")

                        matched = item.get("matched_keywords", [])
                        if matched:
                            st.markdown(f"**Matched Keywords:** {', '.join(matched)}")

                        mappings = item.get("mappings", [])
                        if mappings:
                            st.markdown("**Related Mappings:**")
                            for mapping in mappings:
                                counterpart = mapping["counterpart_section"]
                                st.write(
                                    f"- {mapping['direction']} -> {counterpart['code_type']} "
                                    f"{counterpart['section_number']}: {counterpart['section_title']} "
                                    f"(Confidence: {mapping['confidence']}%, Type: {mapping['mapping_type']})"
                                )
                        st.write("---")

            except Exception as e:
                st.error(f"Search failed: {str(e)}")

if __name__ == "__main__":
    main()
