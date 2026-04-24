from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Travel & Hotel Agent", page_icon="🌍")

st.title("🌍 Travel & Hotel Agent")
st.write(
    "Use the pages in the sidebar to plan your trip:"
)
st.markdown(
    """
- **✈️ Itinerary** — Top 3 places to visit + local dish + hotel price estimate for any city
- **🏨 Hotel Booking** — Search for hotels by dates, guests, budget and star rating
"""
)

