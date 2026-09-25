import pandas as pd
import streamlit as st

from common import BackendError, api_get, client, meta, page, require_backend

page("Leads", "📂")
st.title("Leads")
require_backend()

countries = [c for c in meta()["countries"] if c["has_data"]]
PAGE_SIZE = 100

f1, f2, f3, f4 = st.columns(4)
country_name = f1.selectbox("Country", ["All"] + [c["name"] for c in countries])
country = next((c["code"] for c in countries if c["name"] == country_name), None)
summary = api_get("/api/leads/summary", country=country)
state_names = [s for s in summary["by_state"] if s != "Unknown"]
state = f2.selectbox("State / Region", ["All"] + state_names)
state = None if state == "All" else state
council = None
if state:
    councils = [c for c in api_get("/api/leads/summary", country=country, state=state)["by_council"] if c != "Unknown"]
    council = f3.selectbox("Council", ["All"] + councils)
    council = None if council == "All" else council
btype = f4.selectbox("Business type", ["All"] + meta()["business_types"]["all"])
btype = None if btype == "All" else btype

g1, g2, g3 = st.columns([2, 1, 1])
text = g1.text_input("Name contains")
has_phone = g2.selectbox("Phone", ["Any", "Has phone", "No phone"])
has_web = g3.selectbox("Website", ["Any", "Has website", "No website"])
filters = {"country": country, "state": state, "council": council, "business_type": btype, "q": text or None,
           "has_phone": {"Has phone": True, "No phone": False}.get(has_phone),
           "has_website": {"Has website": True, "No website": False}.get(has_web)}

page_no = st.session_state.get("leads_page", 0)
if st.session_state.get("leads_filters") != filters:
    st.session_state["leads_filters"], page_no = filters, 0
result = api_get("/api/leads", offset=page_no * PAGE_SIZE, limit=PAGE_SIZE, **filters)
total = result["total"]
pages = max(1, -(-total // PAGE_SIZE))

st.markdown(f"**{total:,} leads** match")
if result["items"]:
    df = pd.DataFrame([{
        "Name": l.get("name"), "Business types": ", ".join(l.get("business_types") or []),
        "Phone": l.get("phone") or l.get("phone_local"), "Website": l.get("website"),
        "Address": l.get("address"), "Council": l.get("council"), "State": l.get("state"),
        "Rating": l.get("rating"), "Reviews": l.get("review_count"), "Status": l.get("business_status"),
        "Google Maps": l.get("google_maps_url"),
    } for l in result["items"]])
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "Website": st.column_config.LinkColumn(),
        "Google Maps": st.column_config.LinkColumn(display_text="Open"),
    })
    p1, p2, p3 = st.columns([1, 2, 1])
    if p1.button("Previous", disabled=page_no == 0):
        st.session_state["leads_page"] = page_no - 1
        st.rerun()
    p2.markdown(f"<div style='text-align:center'>Page {page_no + 1} of {pages}</div>", unsafe_allow_html=True)
    if p3.button("Next", disabled=page_no + 1 >= pages):
        st.session_state["leads_page"] = page_no + 1
        st.rerun()

    st.divider()
    if st.button(f"Prepare Excel of all {total:,} matching leads"):
        with st.spinner("Building the Excel file..."):
            try:
                st.session_state["leads_export"] = client().fetch_file("/api/leads/export", **filters)
            except BackendError as exc:
                st.error(str(exc))
    if st.session_state.get("leads_export"):
        name, data = st.session_state["leads_export"]
        st.download_button(f"Download {name}", data, file_name=name, type="primary")
else:
    st.info("No leads match these filters yet.")
