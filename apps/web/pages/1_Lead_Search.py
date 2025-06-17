import os
import sys
import streamlit as st
from utils.api import crawl_businesses

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from api.config.constants import AU_REGIONS, BUSINESS_TYPES


st.set_page_config(page_title="Lead Search", layout="wide")

st.title("🔍 Lead Search")
st.markdown("Use the filters below to crawl businesses from Google Places API and store them in MongoDB.")

# --- Form UI ---
with st.form("search_form"):
    col1, col2 = st.columns(2)

    with col1:
        state = st.selectbox("Select State", list(AU_REGIONS.keys()))
    with col2:
        region = st.selectbox("Select Region", AU_REGIONS[state])

    selected_types = st.multiselect("Select Business Types", BUSINESS_TYPES)

    submitted = st.form_submit_button("Search Businesses")

# --- Trigger Crawl ---
if submitted:
    if not selected_types:
        st.warning("Please select at least one business type.")
    else:
        with st.spinner("🔍 Crawling businesses..."):
            result = crawl_businesses(state, region, selected_types)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(f"Crawling complete! ✅ {result['businesses_saved']} new businesses saved.")
                if result["businesses_saved"] > 0:
                    # Display saved count or sample table
                    st.markdown("### Sample Result Preview")
                    sample_data = result.get("sample", []) or []
                    if sample_data:
                        st.dataframe(sample_data)
                    else:
                        st.info("No sample data to preview.")

# --- Try Again ---
if st.button("🔄 Try Again"):
    st.experimental_rerun()
