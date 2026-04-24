import streamlit as st
import requests
from database import Session, LegalSection

BASE_API_URL = "http://localhost:8000"  # Or your API endpoint

def highlight_text(text, query):
    """Highlight search terms in the results"""
    if not query:
        return text
    return text.replace(query, f"**{query}**")

def search_sections():
    st.title("IPC to BNS Mapping Tool")
    
    # Search functionality with improved layout
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
        
        try:
            action_resp = requests.get(
                f"{BASE_API_URL}/legal-action",
                params=params
            ).json()

            results = action_resp.get("results", [])
            extracted_keywords = action_resp.get("extracted_keywords", [])
            if extracted_keywords:
                st.caption(f"Auto-extracted keywords: {', '.join(extracted_keywords)}")

            if not results:
                st.warning("No matching sections found")
                return

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
    search_sections()