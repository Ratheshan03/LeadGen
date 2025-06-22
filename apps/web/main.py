import streamlit as st
from PIL import Image
from datetime import datetime

# --- Page Config ---
st.set_page_config(
    page_title="Business Lead Generator",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Title ---
st.markdown("<h1 style='text-align: center;'>Business Lead Generator</h1>", unsafe_allow_html=True)

st.markdown(
    """
    <div style='text-align: center; font-size: 18px; margin-top: -10px;'>
        Efficiently crawl, store, and analyze local businesses using the <b>Google Places API</b> and <b>MongoDB</b>.
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# --- Features Overview ---
st.markdown("### 🌟 Features")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🔎 Nearby Search")
    st.markdown("Crawl businesses based on location, category, and radius using Google Places Nearby Search.")

with col2:
    st.subheader("📝 Text Search")
    st.markdown("Search businesses using custom queries like keywords, names, or partial matches.")

with col3:
    st.subheader("📂 View Leads")
    st.markdown("Filter and explore all stored leads from the database by category, type, and state.")

st.markdown("")

col4, col5 = st.columns(2)

with col4:
    st.subheader("📊 Business Summary")
    st.markdown("Visualize your data — summary by business type and state, with tags and total counts.")

with col5:
    st.subheader("🛠️ Easy Integration")
    st.markdown("Built with Streamlit, MongoDB, and FastAPI. Designed to be extensible and developer-friendly.")

st.markdown("---")

# --- Getting Started ---
st.markdown("### 🚀 Get Started")
st.markdown(
    """
Use the **sidebar** to navigate through the app:
- **Nearby Search**
- **Text Search**
- **View Leads**
- **Business Summary**
"""
)

# Optional logo (uncomment if needed)
# image = Image.open("apps/web/assets/logo.png")
# st.image(image, width=150)

# --- Footer ---
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; font-size: 14px;'>© {datetime.now().year} Business Lead Generator • Built with using Streamlit & FastAPI</div>",
    unsafe_allow_html=True
)
