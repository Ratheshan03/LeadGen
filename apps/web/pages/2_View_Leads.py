import os
import sys
import streamlit as st
import pandas as pd
from utils.api import get_leads

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from api.config.constants import AU_REGIONS, BUSINESS_TYPES

st.set_page_config(page_title="View Leads", layout="wide")
st.title("📂 View Saved Leads")

# --- Filters ---
state_options = ["All"] + list(AU_REGIONS.keys())
type_options = ["All"] + BUSINESS_TYPES

col1, col2 = st.columns(2)
selected_state = col1.selectbox("Filter by State", state_options)
selected_type = col2.selectbox("Filter by Business Type", type_options)

# Convert "All" to None for API query
query_state = None if selected_state == "All" else selected_state
query_type = None if selected_type == "All" else selected_type

# --- Fetch Leads ---
with st.spinner("Fetching leads from database..."):
    result = get_leads(state=query_state, type_=query_type)

# --- Display Results ---
if isinstance(result, dict) and "error" in result:
    st.error(result["error"])
elif not result or not isinstance(result, list):
    st.info("No leads found for the selected filters.")
else:
    df = pd.DataFrame(result)
    if not df.empty:
        st.markdown(f"### Showing {len(df)} result(s)")
        columns_to_display = ["name", "address", "phone", "website", "state", "tags"]
        display_df = df[columns_to_display] if set(columns_to_display).issubset(df.columns) else df
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No matching results found.")
