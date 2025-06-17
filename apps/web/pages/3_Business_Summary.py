import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api import get_summary_data

st.set_page_config(page_title="Business Summary", layout="wide")
st.title("📊 Business Summary Dashboard")

# --- Fetch data ---
with st.spinner("Loading summary data..."):
    summary_data = get_summary_data()

if not summary_data or "error" in summary_data:
    st.error("Unable to load summary data. Please try again later.")
else:
    # --- Transform to flat DataFrame ---
    df = []
    for state, type_counts in summary_data.items():
        for btype, count in type_counts.items():
            df.append({"State": state, "Type": btype, "Count": count})
    df = pd.DataFrame(df)

    # --- Optional Filters ---
    col1, col2 = st.columns(2)
    selected_state = col1.selectbox("Filter by State", ["All"] + sorted(df["State"].unique().tolist()))
    selected_type = col2.selectbox("Filter by Type", ["All"] + sorted(df["Type"].unique().tolist()))

    if selected_state != "All":
        df = df[df["State"] == selected_state]
    if selected_type != "All":
        df = df[df["Type"] == selected_type]

    # --- Bar Chart ---
    st.markdown("### 📈 Business Counts by State and Type")
    fig = px.bar(
        df,
        x="State",
        y="Count",
        color="Type",
        barmode="group",
        title="Business Summary",
        labels={"Count": "Number of Businesses"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Summary Table ---
    st.markdown("### 🧾 Detailed Summary Table")
    st.dataframe(df, use_container_width=True)
