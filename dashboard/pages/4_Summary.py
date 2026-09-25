import pandas as pd
import plotly.express as px
import streamlit as st

from common import api_get, meta, page, require_backend

page("Summary", "📊")
st.title("Summary")
require_backend()

countries = [c for c in meta()["countries"] if c["has_data"]]
c1, c2 = st.columns(2)
country_name = c1.selectbox("Country", ["All"] + [c["name"] for c in countries])
country = next((c["code"] for c in countries if c["name"] == country_name), None)
states = [s for s in api_get("/api/leads/summary", country=country)["by_state"] if s != "Unknown"]
state = c2.selectbox("State / Region", ["All"] + states)
state = None if state == "All" else state
s = api_get("/api/leads/summary", country=country, state=state)

total = s["total"] or 0


def share(n: int) -> str:
    return f"{n:,}  ({n / total * 100:.0f}%)" if total else "0"


m1, m2, m3 = st.columns(3)
m1.metric("Leads", f"{total:,}")
m2.metric("With phone", share(s["with_phone"]))
m3.metric("With website", share(s["with_website"]))

if total:
    left, right = st.columns(2)
    group = "by_council" if state else "by_state"
    title = "Top councils" if state else "Leads by state / region"
    data = pd.DataFrame(list(s[group].items())[:25], columns=["Area", "Leads"])
    left.plotly_chart(px.bar(data, x="Leads", y="Area", orientation="h", title=title).update_yaxes(autorange="reversed"),
                      use_container_width=True)
    types = pd.DataFrame(list(s["by_business_type"].items())[:25], columns=["Business type", "Leads"])
    right.plotly_chart(px.bar(types, x="Leads", y="Business type", orientation="h", title="Top business types")
                       .update_yaxes(autorange="reversed"), use_container_width=True)
else:
    st.info("No leads yet - run a crawl first.")

st.subheader("Crawl history")
runs = api_get("/api/crawl/history", country=country, state=state, limit=500)
if runs:
    hist = pd.DataFrame([{
        "Started": (r.get("started_at") or "")[:16].replace("T", " "), "Area": r.get("area"), "State": r.get("state"),
        "Level": r.get("level"), "Types": r.get("business_types"), "Dense": "yes" if r.get("dense") else "",
        "Status": (r.get("status") or "").replace("_", " "), "Leads": r.get("leads_found"), "New": r.get("leads_new"),
        "Requests": r.get("requests"), "Excel file": r.get("excel_file"),
    } for r in runs])
    st.dataframe(hist, use_container_width=True, hide_index=True)
else:
    st.caption("No crawls yet.")
