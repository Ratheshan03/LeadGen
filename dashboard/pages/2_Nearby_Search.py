import streamlit as st

from common import (
    BackendError, api_get, api_post, business_type_picker, country_picker, job_monitor, page, require_backend,
    show_estimate,
)

page("Nearby Search", "📍")
st.title("Nearby Search")
st.caption("Finds up to 20 businesses per business type within a radius of a city centre - a quick sample, "
           "not full coverage. For complete coverage of an area use the Crawl page.")
require_backend()

JOB_KEY = "nearby_job"
if st.session_state.get(JOB_KEY):
    job_monitor(JOB_KEY)
    st.stop()

country = country_picker("nearby_country")
cities = api_get("/api/cities", country=country["code"])
if not cities:
    st.warning(f"No city list for {country['name']} yet.")
    st.stop()
states = sorted({c["state"] for c in cities})
c1, c2 = st.columns(2)
state = c1.selectbox(country["state_label"], states)
names = [c["name"] for c in cities if c["state"] == state]
chosen = c2.multiselect("Cities (leave empty for all)", names)
radius_km = st.slider("Search radius (km)", 1, 50, 5)
types = business_type_picker("nearby")
if not types:
    st.warning("Choose at least one business type.")
    st.stop()

body = {"mode": "nearby", "country": country["code"], "state": state, "cities": chosen or None,
        "business_types": types, "radius_m": radius_km * 1000}
try:
    est = api_post("/api/crawl/estimate", body)
    show_estimate(est)
except BackendError as exc:
    st.error(str(exc))
    st.stop()

ok = st.checkbox("I understand this uses Google requests from my account.")
if st.button("Start Nearby Search", type="primary", disabled=not ok):
    try:
        st.session_state[JOB_KEY] = api_post("/api/crawl/jobs", body)["id"]
        st.rerun()
    except BackendError as exc:
        st.error(str(exc))
