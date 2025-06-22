import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api import get_summary_data
from api.config.constants import BUSINESS_CATEGORIES, AU_REGIONS
from itertools import chain

st.set_page_config(page_title="📊 Business Summary", layout="wide")
st.title("📊 Business Summary Dashboard")

# === Flatten constants ===
ALL_STATES = sorted(list(AU_REGIONS.keys()))
ALL_TYPES = sorted(set(chain.from_iterable(BUSINESS_CATEGORIES.values())))

# === Filter Inputs ===
col1, col2 = st.columns(2)
selected_state = col1.selectbox("Filter by State", ["All"] + ALL_STATES)
selected_type = col2.selectbox("Filter by Business Type", ["All"] + ALL_TYPES)

# === Call API with Filters ===
with st.spinner("Loading summary data..."):
    response = get_summary_data(
        state=None if selected_state == "All" else selected_state,
        business_type=None if selected_type == "All" else selected_type
    )

if not response or "error" in response:
    st.error("Unable to load summary data.")
else:
    summary = response.get("summary", {})
    extra_types = response.get("extra_types", {})
    total_businesses = response.get("total_businesses", 0)

    st.markdown(f"### 📟 Total Businesses Stored: `{total_businesses}`")

    # --- Build Summary DataFrame ---
    rows = []
    for state, types in summary.items():
        for btype, count in types.items():
            rows.append({"State": state, "Business Type": btype, "Count": count})
    df = pd.DataFrame(rows)

    # --- Bar Chart ---
    st.markdown("### 📈 Business Counts by State and Type")
    if not df.empty:
        fig = px.bar(
            df,
            x="State",
            y="Count",
            color="Business Type",
            barmode="group",
            title="Business Summary",
            labels={"Count": "Number of Businesses"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for selected filters.")

    # --- Table ---
    st.markdown("### 📋 Detailed Summary Table")
    st.dataframe(df, use_container_width=True)

    # --- Other Tags ---
    if extra_types:
        st.markdown("### 🧹 Other Tags / Types Tracked")
        tag_df = pd.DataFrame([
            {"Tag": tag, "Count": count}
            for tag, count in extra_types.items()
            if tag not in ALL_TYPES
        ])
        st.dataframe(tag_df, use_container_width=True)
