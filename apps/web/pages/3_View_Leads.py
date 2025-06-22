import os
import sys
import streamlit as st
import pandas as pd
from utils.api import get_leads

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from api.config.constants import AU_REGIONS, BUSINESS_CATEGORIES

st.set_page_config(page_title="📂 View Leads", layout="wide")
st.title("📂 View Saved Business Leads")

# --- Filter Setup ---
st.markdown("Use filters below to search stored business leads. All filters are optional.")

col1, col2, col3 = st.columns(3)

state_options = ["All"] + list(AU_REGIONS.keys())
category_options = ["All"] + list(BUSINESS_CATEGORIES.keys())

selected_state = col1.selectbox("Filter by State", state_options)
selected_category = col2.selectbox("Filter by Category", category_options)

# Dynamically load business types based on selected category
if selected_category == "All":
    type_options = ["All"]
else:
    type_options = ["All"] + BUSINESS_CATEGORIES[selected_category]

selected_type = col3.selectbox("Filter by Business Type", type_options)

# Prepare query params
query_state = None if selected_state == "All" else selected_state
query_type = None if selected_type == "All" else selected_type

# === Fetch Leads ===
with st.spinner("🔄 Fetching filtered leads from database..."):
    leads = get_leads(state=query_state, type_=query_type)

# === Results Display ===
if isinstance(leads, dict) and "error" in leads:
    st.error(leads["error"])
elif not leads:
    st.info("No leads found for the selected filters.")
else:
    df = pd.DataFrame(leads)

    if df.empty:
        st.info("No matching results.")
    else:
        st.markdown(f"### 🧾 Showing `{len(df)}` result(s)")

        # Select and format columns
        columns_to_display = [
            "name", "address", "phone", "website",
            "state", "region", "types", "retrieved_at"
        ]
        displayable = [col for col in columns_to_display if col in df.columns]

        # Format timestamps
        if "retrieved_at" in df.columns:
            df["retrieved_at"] = pd.to_datetime(df["retrieved_at"]).dt.strftime("%Y-%m-%d %H:%M")

        # Optional: preview table
        st.dataframe(df[displayable], use_container_width=True, hide_index=True)

        with st.expander("🔍 View Full Table"):
            st.dataframe(df, use_container_width=True)
