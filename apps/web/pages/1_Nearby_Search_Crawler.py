import os
import sys
import streamlit as st
from utils.api import crawl_businesses, crawl_entire_state_or_all

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from api.config.constants import AU_REGIONS, BUSINESS_CATEGORIES

st.set_page_config(page_title="🏪 Business Crawler", layout="wide")
st.title("Nearby Search Business/Leads Generator")
st.markdown("Use the filters below to crawl businesses using the Google Places Nearby Search API.")

# ================================
# 🧍 Manual Search Form
# ================================
st.subheader("🔍 Manual Lead Search")

with st.form("manual_crawl_form"):
    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox("Select State", list(AU_REGIONS.keys()))
    with col2:
        region = st.selectbox("Select Region", AU_REGIONS[state])

    selected_category = st.selectbox("Select Business Category", list(BUSINESS_CATEGORIES.keys()))
    selected_types = st.multiselect(
        "Select Business Types",
        BUSINESS_CATEGORIES[selected_category]
    )

    manual_submit = st.form_submit_button("🚀 Search Businesses")

if manual_submit:
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
                    st.markdown("### 🧾 Sample Result Preview")
                    sample_data = result.get("sample", []) or []
                    if sample_data:
                        st.dataframe(sample_data)
                    else:
                        st.info("No sample data to preview.")

if st.button("🔄 Reset Manual Form"):
    st.experimental_rerun()

st.divider()

# ================================
# 🤖 Full Automated Crawler
# ================================
st.subheader("🤖 Full Region - Automatic Crawler")

st.markdown("Trigger a **full crawl** across all configured states, cities, categories, and business types.")

with st.form("automated_crawl_form"):
    dry_run = st.checkbox("🔬 Run as Dry Run (No database writes)", value=True)
    auto_submit = st.form_submit_button("🚀 Start Full Crawl")

if auto_submit:
    with st.spinner("Running full automated crawl..."):
        result = crawl_entire_state_or_all(dry_run=dry_run)

    if "error" in result:
        st.error(result["error"])
    else:
        if dry_run:
            st.success("✅ Dry Run Complete! No API calls or DB writes made.")
            total_tasks = result.get("total_found", 0)
            st.markdown(f"**Total planned tasks:** `{total_tasks}`")

            tasks = result.get("planned_tasks", [])
            if tasks:
                st.markdown("### 📋 Planned Crawl Summary")
                st.dataframe(tasks, use_container_width=True)

                with st.expander("📄 Log Preview"):
                    log_lines = [
                        f"{i+1}. {task['type']} in {task['region']} ({task['state']}) - {task['name'] or 'Unnamed'}"
                        for i, task in enumerate(tasks)
                    ]
                    st.text_area("Dry Run Logs", value="\n".join(log_lines), height=300)

                with st.expander("🔍 View JSON Output"):
                    st.json(tasks)
            else:
                st.info("No crawl tasks were generated in dry run.")
        else:
            st.success("✅ Full Crawl Completed!")
            total_saved = result.get("total_saved", 0)
            st.markdown(f"**Total businesses saved:** `{total_saved}`")

            regions_data = result.get("regions_processed", {})
            if regions_data:
                st.markdown("### 📍 Businesses Crawled Per Region & Type")
                flat_data = []
                for region, types in regions_data.items():
                    for btype, count in types.items():
                        flat_data.append({
                            "Region": region,
                            "Business Type": btype,
                            "Saved Count": count
                        })
                st.dataframe(flat_data, use_container_width=True)
            else:
                st.info("No businesses were saved during this run.")

st.markdown("ℹ️ Logs will be seen in the backend console.")
