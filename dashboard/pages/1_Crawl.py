import streamlit as st

from common import (
    BackendError, api_get, api_post, business_type_picker, country_picker, job_monitor, level_picker, lookup, page,
    require_backend, show_estimate,
)

page("Crawl", "🔍")
st.title("Crawl")
require_backend()

JOB_KEY = "crawl_job"
if st.session_state.get(JOB_KEY):
    job_monitor(JOB_KEY)
    st.stop()

mode_label = st.radio("What do you want to crawl?",
                      ["One area", "Every area in a state / region (one by one)", "A whole country"], horizontal=True)
mode = {"One area": "area", "A whole country": "full"}.get(mode_label, "state")

c1, c2 = st.columns(2)
with c1:
    country = country_picker("crawl_country")
with c2:
    level = level_picker(country, "crawl_level")
areas_by_state = lookup(country["code"], level)

body = {"mode": mode, "country": country["code"], "level": level}
if mode in ("area", "state"):
    c3, c4 = st.columns(2)
    with c3:
        state = st.selectbox(country["state_label"], list(areas_by_state), key="crawl_state")
    body["state"] = state
    if mode == "area":
        with c4:
            body["area"] = st.selectbox("Area (type to search)", areas_by_state[state], key="crawl_area")
    else:
        with c4:
            subset = st.multiselect(f"Only these areas (leave empty for all {len(areas_by_state[state])})",
                                    areas_by_state[state], key="crawl_subset")
        body["areas"] = subset or None
else:
    states = st.multiselect(f"Only these {country['state_label'].lower()}s (leave empty for all)", list(areas_by_state))
    body["states"] = states or None

body["business_types"] = business_type_picker("crawl")
o1, o2 = st.columns(2)
body["dense"] = o1.checkbox(
    "Dense-city mode", help="Crawls big cities neighbourhood by neighbourhood (SA2 areas) so busy centres are not cut "
                            "off at Google's 60-results-per-search limit. Much more complete in cities - and much "
                            "more expensive. Check the estimate.")
if mode != "area":
    body["skip_completed"] = not o2.checkbox("Re-crawl areas already done", help="By default, areas already crawled "
                                             "with the same settings are skipped, so a stopped crawl simply continues.")

if not body["business_types"]:
    st.warning("Choose at least one business type.")
    st.stop()

if st.button("Estimate cost", type="secondary"):
    with st.spinner("Working out the search tiles..."):
        try:
            st.session_state["crawl_estimate"] = (body, api_post("/api/crawl/estimate", body))
        except BackendError as exc:
            st.error(str(exc))

saved = st.session_state.get("crawl_estimate")
if saved and saved[0] == body:
    est = saved[1]
    st.markdown(f"**{est['title']}**")
    show_estimate(est)
    if est["areas"]:
        ok = st.checkbox("I understand this uses Google requests from my account.")
        if st.button("Start crawl", type="primary", disabled=not ok):
            try:
                job = api_post("/api/crawl/jobs", body)
                st.session_state[JOB_KEY] = job["id"]
                st.session_state.pop("crawl_estimate", None)
                st.rerun()
            except BackendError as exc:
                st.error(str(exc))
    else:
        st.success("Nothing to do - every selected area was already crawled with these settings.")

with st.expander("Recent crawl jobs (since the backend started)"):
    jobs = api_get("/api/crawl/jobs")
    if not jobs:
        st.caption("None yet.")
    for j in jobs[:15]:
        cols = st.columns([5, 2, 1])
        cols[0].write(j["title"])
        cols[1].write(j["status"].replace("_", " "))
        if cols[2].button("Open", key=f"open_{j['id']}"):
            st.session_state[JOB_KEY] = j["id"]
            st.rerun()
