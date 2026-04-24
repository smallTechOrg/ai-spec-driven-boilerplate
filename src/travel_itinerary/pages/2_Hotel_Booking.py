from __future__ import annotations

import datetime

import streamlit as st

from travel_itinerary.domain.models import HotelSearchParams
from travel_itinerary.llm.client import create_client

st.set_page_config(page_title="Hotel Booking", page_icon="🏨")

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

st.title("🏨 Hotel Booking")
st.write("Fill in your trip details to get AI-curated hotel recommendations with a direct booking link.")

with st.form("hotel_search_form"):
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City", placeholder="e.g. Tokyo")
        checkin = st.date_input(
            "Check-in date",
            value=datetime.date.today() + datetime.timedelta(days=7),
            min_value=datetime.date.today(),
        )
        guests = st.number_input("Guests", min_value=1, max_value=10, value=2, step=1)

    with col2:
        star_rating = st.selectbox("Star rating", options=[3, 4, 5], index=0, format_func=lambda x: f"{'⭐' * x} ({x}-star)")
        checkout = st.date_input(
            "Check-out date",
            value=datetime.date.today() + datetime.timedelta(days=10),
            min_value=datetime.date.today() + datetime.timedelta(days=1),
        )
        budget_range = st.slider(
            "Budget per night (USD)",
            min_value=30,
            max_value=500,
            value=(80, 180),
            step=10,
        )

    submitted = st.form_submit_button("Find Hotels", type="primary")

if submitted:
    if not city.strip():
        st.warning("Please enter a city name.")
    elif checkout <= checkin:
        st.warning("Check-out date must be after check-in date.")
    else:
        params = HotelSearchParams(
            city=city.strip(),
            checkin=checkin,
            checkout=checkout,
            guests=int(guests),
            budget_min=budget_range[0],
            budget_max=budget_range[1],
            star_rating=star_rating,
        )
        nights = (checkout - checkin).days

        with st.spinner(f"Finding {star_rating}-star hotels in {city}…"):
            try:
                result = client.search_hotels(params)
            except Exception as exc:
                st.error(f"Failed to find hotels. Please try again. ({exc})")
                st.stop()

        st.subheader(
            f"{'⭐' * star_rating} Hotels in {result.city} "
            f"· {checkin.strftime('%d %b')} – {checkout.strftime('%d %b %Y')} "
            f"· {nights} night{'s' if nights != 1 else ''} · {int(guests)} guest{'s' if int(guests) != 1 else ''}"
        )

        for i, hotel in enumerate(result.hotels, start=1):
            with st.container(border=True):
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    st.markdown(f"### {i}. {hotel.name}")
                    st.write(hotel.description)
                    st.markdown(
                        " · ".join(f"✓ {a}" for a in hotel.amenities)
                    )
                with col_btn:
                    st.markdown(f"**{hotel.estimated_price}**")
                    st.markdown(
                        f"[Book on Booking.com ↗]({hotel.booking_url})"
                    )

        st.caption(
            f"ℹ Prices are AI estimates based on training data and may not reflect current availability. "
            f"The booking link searches Booking.com for {star_rating}-star hotels matching your criteria."
        )
