from __future__ import annotations

import streamlit as st

from travel_itinerary.llm.client import create_client

st.set_page_config(page_title="Travel & Food Itinerary", page_icon="✈️")

# Initialise LLM client once per session
if "client" not in st.session_state:
    st.session_state.client = create_client()

client = st.session_state.client

# --- Stub mode banner ---
if client.is_stub:
    st.warning(
        "⚠ Running in stub mode — no API key detected. "
        "Output is hardcoded demo data. "
        "Set GOOGLE_API_KEY in your .env file to use real Gemini responses."
    )

st.title("✈️ Travel & Food Itinerary")
st.write("Enter a city and get the top 3 places to visit plus a local dish to try.")

city = st.text_input("Enter a city name", placeholder="e.g. Paris")

if st.button("Get Itinerary", type="primary"):
    if not city.strip():
        st.warning("Please enter a city name.")
    else:
        with st.spinner(f"Generating itinerary for {city}…"):
            try:
                result = client.get_itinerary(city.strip())
            except Exception as exc:
                st.error(f"Failed to generate itinerary. Please try again. ({exc})")
                st.stop()

        st.subheader(f"Top 3 Places to Visit in {result.city}")
        for i, place in enumerate(result.places, start=1):
            with st.container(border=True):
                st.markdown(f"### {i}. {place.name}")
                st.write(place.description)
                st.caption(f"🕐 {place.tips}")

        st.subheader("🍽 Local Dish to Try")
        with st.container(border=True):
            st.markdown(f"### {result.dish.name}")
            st.write(result.dish.description)

        st.subheader("🏨 3-Star Hotel Pricing")
        with st.container(border=True):
            st.markdown(f"**Estimated price:** {result.hotel.estimated_price_range}")
            st.caption(result.hotel.notes)
            st.markdown(
                f"[🔗 Search 3-star hotels in {result.city} on Booking.com]({result.hotel.booking_url})"
            )
