import streamlit as st
from PIL import Image

# --- Page Config ---
st.set_page_config(
    page_title="Business Lead Generator",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Title Section ---
st.markdown("<h1 style='text-align: center;'>📍 Business Lead Generator</h1>", unsafe_allow_html=True)

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
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🔎 Search Leads")
    st.markdown("Select region, state, and business type to crawl.")

with col2:
    st.subheader("📂 View Results")
    st.markdown("Access all saved leads with filters.")

with col3:
    st.subheader("📊 Dashboard")
    st.markdown("Visual summary by state and business type.")

st.markdown("---")

# --- Getting Started Section ---
st.markdown("### 🚀 Get Started")
st.markdown("""
Use the **sidebar** to navigate between:
- Lead Search
- View Saved Businesses
- Business Summary Dashboard
""")

# Optional Image or Logo
# image = Image.open("apps/web/assets/logo.png")
# st.image(image, width=150)
