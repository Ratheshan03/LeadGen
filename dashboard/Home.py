import streamlit as st

from common import money, page, require_backend

page("Home")
st.title("LeadGen")
st.caption("Business leads for Australia and New Zealand from Google Places - by council, suburb area or city.")

status = require_backend()
q = status["quota"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads stored", f"{status['total_leads']:,}")
c2.metric("Google requests this month", f"{q['used']:,}", help=f"{q['remaining']:,} left of your {q['cap']:,} monthly cap")
c3.metric("Cost this month (approx.)", money(q["used"] / 1000 * status["cost_per_1000_requests_usd"]))
c4.metric("Google API keys", status["google_keys_configured"])
st.progress(min(q["used"] / max(q["cap"], 1), 1.0), text=f"Monthly request cap: {q['used']:,} / {q['cap']:,}")

if not status["google_keys_configured"]:
    st.error("No Google API key found. Add GOOGLE_API_KEYS=your-key to the .env file and restart the backend.")

if status.get("active_job"):
    job = status["active_job"]
    st.info(f"A crawl is running: **{job['title']}** - open the Crawl page to watch it.")

st.divider()
left, right = st.columns(2)
with left:
    st.subheader("What you can do")
    st.markdown(
        "- **Crawl** - pick a council (or a whole state / country), see the cost estimate, start it and watch it live.\n"
        "- **Nearby Search** - quick search around a city centre.\n"
        "- **Leads** - filter everything collected so far and download it as Excel.\n"
        "- **Summary** - counts by state, council and business type, plus crawl history."
    )
    st.caption("Prefer the command line? `python custom_crawl.py` and `python full_crawl.py` do the same.")
with right:
    st.subheader("Setup")
    st.markdown(f"- Storage: `{status['storage']}`\n- Output folder: `{status['output_folder']}`")
    for c in status["countries"]:
        st.markdown(f"- {c['name']} boundary data: {'available' if c['has_data'] else 'missing - see data/README.md'}")
