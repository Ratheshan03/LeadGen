import streamlit as st
import os
import sys
import json
from api.config.constants import ALL_BUSINESS_TYPES, GCCSA_REGIONS, AU_REGIONS, GEOJSON_MAP_PATHS
from utils.api import crawl_text_search_full, crawl_custom_text_search, crawl_text_search_trial, get_region_coverage

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Load LGA and Region maps (should be placed in your frontend data directory or read via API)
with open(GEOJSON_MAP_PATHS["state_to_lgas"]) as f:
    STATE_TO_LGAS = json.load(f)

with open(GEOJSON_MAP_PATHS["state_to_regions"]) as f:
    STATE_TO_REGIONS = json.load(f)


st.set_page_config(page_title="🔍 Text Search Crawler", layout="wide")

# === Header ===
st.title("Text Based Business/Leads Generator")
st.markdown("""
Use the Google Places **Text Search API** to retrieve business leads.

- Manually enter a query (e.g., `Offices, Universities`) to crawl with text bias.
- Or trigger a **full automated crawl** using your predefined regions and business types.
""")  

# === Manual Text Search Form with Dynamic Region Input ===
st.subheader("🛠️ Manual Text Search Crawl")

business_type_options = ["ALL"] + ALL_BUSINESS_TYPES

# Select Business Type
selected_business_type = st.selectbox(
    "Select Business Type",
    options=business_type_options,
    index=0,  # Default to "ALL"
    help="Choose the type of business to search (or 'ALL' for all types)"
)

# Select State
selected_state = st.selectbox("Select State", options=list(AU_REGIONS.keys()), index=0)

# Select Geo Type
geo_type = st.selectbox(
    "Select Geography Level",
    options=["Regions", "LGA", "GCCSA"],
    help="Choose which geo-level to select region from."
)

# Get available region options based on geo type and state
region_options = []
if geo_type == "Regions":
    region_options = STATE_TO_REGIONS.get(selected_state, [])
elif geo_type == "LGA":
    region_options = STATE_TO_LGAS.get(selected_state, [])
elif geo_type == "GCCSA":
    region_options = GCCSA_REGIONS.get(selected_state, [])

# Region Selection
selected_region_option = st.selectbox(
    "Select Area",
    options=region_options + ["<Enter custom region>"],
    index=0
)

# If "custom region" selected, prompt for input
custom_region = ""
if selected_region_option == "<Enter custom region>":
    custom_region = st.text_input("Enter custom region/city name manually")

# Dry run checkbox
run_custom_dry = st.checkbox("🔬 Dry Run (simulate only)", value=True)

# Submit button
if st.button("Start Text Search Crawl"):
    region_to_use = custom_region.strip() if selected_region_option == "<Enter custom region>" else selected_region_option

    if not selected_business_type or not region_to_use:
        st.warning("Please select a business type and a region.")
    else:
        with st.spinner(f"Running crawl for '{selected_business_type}' in {region_to_use}, {selected_state}..."):
            result = crawl_custom_text_search(
                query=selected_business_type,
                state=selected_state,
                region=region_to_use,
                dry_run=run_custom_dry
            )

        if "error" in result:
            st.error(result["error"])
        else:
            if run_custom_dry:
                st.success("✅ Dry Run Simulation Completed")
                st.markdown(f"**Tiles estimated:** `{result.get('total_tiles', 0)}`")
                st.markdown(f"**Estimated Requests:** `{result.get('expected_requests', 0)}`")
                st.markdown("### 🔍 Dry Run Details")
                st.json(result.get("details", []))
            else:
                st.success("✅ Text Search Crawl Completed")
                st.markdown(f"**Businesses saved:** `{result.get('total_saved', 0)}`")
                st.markdown(f"**Tiles scanned:** `{result.get('tiles_scanned', 0)}`")

                if result.get("details"):
                    st.markdown("### 📍 Results Per Region")
                    st.dataframe(result["details"], use_container_width=True)

                if result.get("failures"):
                    st.markdown("### ⚠️ Failures / Errors")
                    st.json(result["failures"])


# === Divider ===
st.divider()

# === Automated Text Search Crawl ===
st.subheader("🌏 Full-Australia Automated Text Search Crawl")

with st.form("auto_textsearch_form"):
    dry_run = st.checkbox("🔬 Run as Dry Run (no DB writes)", value=True)
    auto_submit = st.form_submit_button("🚀 Start Full Automated Text Search Crawl")

if auto_submit:
    with st.spinner("Running full-text search crawl across AU regions..."):
        result = crawl_text_search_full(dry_run=dry_run)

    if "error" in result:
        st.error(result["error"])
    else:
        st.success(result.get("message", "✅ Automated Crawl Completed!"))

        if dry_run:
            st.markdown(f"**Total Business Types:** `{result.get('total_business_types', 0)}`")
            st.markdown(f"**Total Tiles:** `{result.get('total_tiles', 0)}`")
            st.markdown(f"**Simulated API Requests:** `{result.get('total_simulated_requests', 0)}`")
            st.markdown("### 🔍 Sample Planned Requests (first 10)")
            st.dataframe(result.get("planned_requests", []), use_container_width=True)
            st.info(result.get("note", "No actual API or DB calls were made."))
        else:
            st.markdown(f"**Total businesses saved:** `{result.get('total_saved', 0)}`")
            st.markdown(f"**Tiles scanned:** `{result.get('tiles_scanned', 0)}`")

            if result.get("details"):
                st.markdown("### 📍 Saved Results per Region")
                st.dataframe(result["details"], use_container_width=True)

            if result.get("failures"):
                st.markdown("### ⚠️ Failures or Skipped Tiles")
                st.json(result["failures"])

# === Divider ===
st.divider()

# === 🚧 Trial Run ===
st.subheader("🧪 Trial Run - Limited Region Scan")

with st.form("trial_run_form"):
    trial_limit = st.slider("Number of tiles to scan", min_value=5, max_value=100, step=5, value=20)
    run_trial = st.form_submit_button("🔁 Run Trial Crawl")

if run_trial:
    with st.spinner(f"Running trial crawl with {trial_limit} tiles..."):
        trial_result = crawl_text_search_trial(limit_tiles=trial_limit)

    if "error" in trial_result:
        st.error(trial_result["error"])
    else:
        st.success(trial_result.get("message", "✅ Trial Completed!"))
        st.markdown(f"**Tiles Scanned:** `{trial_result.get('tiles_scanned', 0)}`")
        st.markdown(f"**Businesses Saved:** `{trial_result.get('total_saved', 0)}`")

        if trial_result.get("details"):
            st.markdown("### ✅ Trial Crawl - Region-wise Results")
            st.dataframe(trial_result["details"], use_container_width=True)

# === Divider ===
st.divider()

# === 🗺️ Coverage Checker ===
st.subheader("📍 Check Region Coverage")

with st.form("coverage_form"):
    coverage_state = st.selectbox("State", options=["All"] + list(AU_REGIONS.keys()))
    coverage_region = st.text_input("Region / City (Optional)", placeholder="Leave blank for all")

    run_check = st.form_submit_button("🔍 Check Coverage")

if run_check:
    with st.spinner("Checking lead coverage in region..."):
        coverage_data = get_region_coverage(state=coverage_state if coverage_state != "All" else None,
                                            region=coverage_region if coverage_region.strip() else None)

    if "error" in coverage_data:
        st.error(coverage_data["error"])
    else:
        st.success("✅ Region Coverage Retrieved")
        st.markdown(f"**State:** `{coverage_data['state']}`")
        st.markdown(f"**Region:** `{coverage_data['region']}`")
        st.markdown(f"**Total Leads Stored:** `{coverage_data['total_leads']}`")