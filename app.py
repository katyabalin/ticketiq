import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import datetime
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

TM_API_KEY = os.getenv("TICKETMASTER_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

st.set_page_config(page_title="TicketIQ", page_icon="🎟️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0a;
    color: #f0f0f0;
}
.stApp { background-color: #0a0a0a; }

[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #222222;
}
[data-testid="stSidebar"] * {
    color: #c0c0c0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

h1 {
    font-family: 'Syne', sans-serif !important;
    font-size: 3.5rem !important;
    font-weight: 800 !important;
    letter-spacing: -1px !important;
    color: #ffffff !important;
    text-transform: uppercase;
    line-height: 1 !important;
}
h2 {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #f5c842 !important;
    border-bottom: 1px solid #333;
    padding-bottom: 6px;
    margin-top: 1.5rem !important;
}
p, li {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 300 !important;
    color: #c0c0c0 !important;
    line-height: 1.7 !important;
}

[data-testid="stMetric"] {
    background-color: #111111;
    border: 1px solid #222222;
    border-radius: 4px;
    padding: 1.2rem 1.5rem !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.7rem !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    color: #888 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: #ffffff !important;
}

.stButton > button {
    background-color: #f5c842 !important;
    color: #0a0a0a !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 0.6rem 2rem !important;
}
.stButton > button:hover { background-color: #ffd84d !important; }

hr { border-color: #222222 !important; margin: 1.5rem 0 !important; }

.event-title {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 0.5rem;
    line-height: 1.2;
}

.ai-box {
    background: #111111;
    border: 1px solid #222222;
    border-top: 3px solid #f5c842;
    border-radius: 4px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
}
.ai-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.65rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #f5c842;
    margin-bottom: 0.75rem;
}
.ai-text {
    font-size: 0.95rem;
    font-weight: 300;
    color: #d0d0d0;
    line-height: 1.8;
}

[data-testid="stCaptionContainer"] p {
    color: #555 !important;
    font-size: 0.75rem !important;
}
</style>
""", unsafe_allow_html=True)


def search_events(query, category=None, size=10):
    params = {
        "apikey": TM_API_KEY,
        "keyword": query,
        "size": size,
        "sort": "date,asc",
        "countryCode": "US"
    }
    if category and category != "All":
        params["classificationName"] = category
    try:
        r = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=params, timeout=10
        )
        r.raise_for_status()
        data = r.json()
        return data.get("_embedded", {}).get("events", [])
    except Exception as e:
        st.error(f"Could not fetch events: {e}")
        return []


def generate_ai_insight(event, price_info):
    venue = event.get("_embedded", {}).get("venues", [{}])[0]
    dates = event.get("dates", {}).get("start", {})
    prompt = f"""You are an expert live events analyst helping consumers make smart ticket buying decisions.

Event: {event.get('name')}
Date: {dates.get('localDate', 'TBD')} at {dates.get('localTime', 'TBD')}
Venue: {venue.get('name', 'Unknown')} in {venue.get('city', {}).get('name', 'Unknown')}, {venue.get('state', {}).get('name', '')}
Category: {event.get('classifications', [{}])[0].get('segment', {}).get('name', 'Unknown')}
Price range: {price_info}

Write 3-4 sentences giving sharp, actionable buying advice:
- What does the price tell us about demand?
- When is the best time to buy?
- Anything notable about this event's market?
Sound like a smart friend who knows ticketing, not a robot. Be direct and specific."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Could not generate analysis: {e}"


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🎟️ TicketIQ")
st.sidebar.markdown("---")
category = st.sidebar.selectbox("Category", ["All", "Music", "Sports", "Arts & Theatre", "Comedy"])
size = st.sidebar.slider("Results to show", 5, 20, 10)
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size:0.8rem; color:#555;'>Live data: Ticketmaster API<br>AI analysis: Claude</p>", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🎟️ TicketIQ")
st.markdown("<p style='font-size:1.1rem; color:#888; margin-top:-0.5rem;'>Search any event. Understand the market. Know when to buy.</p>", unsafe_allow_html=True)
st.markdown("---")

# ── Search ────────────────────────────────────────────────────────────────────
st.markdown("## Search Events")
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("", placeholder="Search for an artist, team, show, or venue...", label_visibility="collapsed")
with col2:
    search_clicked = st.button("✦ Search")

if "events" not in st.session_state:
    st.session_state.events = []
if "selected_event" not in st.session_state:
    st.session_state.selected_event = None
if "ai_insight" not in st.session_state:
    st.session_state.ai_insight = None

if search_clicked and query:
    with st.spinner("Searching events..."):
        st.session_state.events = search_events(query, category, size)
        st.session_state.selected_event = None
        st.session_state.ai_insight = None

if not st.session_state.events and search_clicked:
    st.warning("No events found. Try a different search.")

# ── Event Results ─────────────────────────────────────────────────────────────
if st.session_state.events:
    count = len(st.session_state.events)
    st.markdown(f"## {count} Event{'s' if count != 1 else ''} Found")

    event_options = {}
    for e in st.session_state.events:
        dates = e.get("dates", {}).get("start", {})
        date_str = dates.get("localDate", "")
        date_fmt = ""
        if date_str:
            try:
                date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
            except:
                date_fmt = date_str
        venues = e.get("_embedded", {}).get("venues", [{}])
        venue_name = venues[0].get("name", "") if venues else ""
        city = venues[0].get("city", {}).get("name", "") if venues else ""
        label = f"{e['name']} — {date_fmt} @ {venue_name}, {city}"
        event_options[label] = e

    selected_label = st.selectbox("Select an event to analyze:", list(event_options.keys()), label_visibility="collapsed")
    if selected_label:
        st.session_state.selected_event = event_options[selected_label]

# ── Event Detail ──────────────────────────────────────────────────────────────
if st.session_state.selected_event:
    event = st.session_state.selected_event
    venues = event.get("_embedded", {}).get("venues", [{}])
    venue = venues[0] if venues else {}
    dates = event.get("dates", {}).get("start", {})
    date_str = dates.get("localDate", "")
    time_str = dates.get("localTime", "")
    date_fmt = ""
    if date_str:
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            date_fmt = dt.strftime("%A, %B %d %Y at %I:%M %p")
        except:
            date_fmt = date_str

    st.markdown("---")
    st.markdown(f'<div class="event-title">{event.get("name", "Event")}</div>', unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#888; margin-top:0.25rem;'>📍 {venue.get('name', '')}, "
        f"{venue.get('city', {}).get('name', '')}, {venue.get('state', {}).get('name', '')} "
        f"&nbsp;•&nbsp; 📅 {date_fmt}</p>",
        unsafe_allow_html=True
    )

    # Pricing
    price_ranges = event.get("priceRanges", [])
    price_info = "Not listed"
    st.markdown("## Pricing")

    if price_ranges:
        pr = price_ranges[0]
        currency = pr.get("currency", "USD")
        min_price = pr.get("min")
        max_price = pr.get("max")
        price_info = f"${min_price} - ${max_price} {currency}"

        m1, m2, m3 = st.columns(3)
        m1.metric("Starting From", f"${min_price:.0f}" if min_price else "N/A")
        m2.metric("Up To", f"${max_price:.0f}" if max_price else "N/A")
        m3.metric("Currency", currency)

        # Only show chart if there's a meaningful range
        if min_price and max_price and max_price > min_price:
            mpl.rcParams.update({
                "figure.facecolor": "#0a0a0a", "axes.facecolor": "#0a0a0a",
                "axes.edgecolor": "#222222", "axes.labelcolor": "#888888",
                "xtick.color": "#888888", "ytick.color": "#888888",
                "text.color": "#f0f0f0", "grid.color": "#1a1a1a",
            })
            fig, ax = plt.subplots(figsize=(10, 1.8))
            fig.patch.set_facecolor("#0a0a0a")
            ax.barh([""], [max_price - min_price], left=[min_price], color="#2a2a2a", height=0.5)
            mid = (min_price + max_price) / 2
            spread = (max_price - min_price) * 0.05
            ax.barh([""], [spread], left=[mid - spread/2], color="#f5c842", height=0.5)
            ax.text(min_price - (max_price * 0.01), 0, f"${min_price:.0f}", va="center", ha="right", fontsize=9, color="#888")
            ax.text(max_price + (max_price * 0.01), 0, f"${max_price:.0f}", va="center", ha="left", fontsize=9, color="#888")
            ax.set_xlim(min_price * 0.85, max_price * 1.15)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.spines["bottom"].set_visible(False)
            ax.set_yticks([])
            ax.set_xticks([])
            plt.tight_layout()
            st.pyplot(fig)
    else:
        st.info("Pricing not yet available for this event.")

    # Category + link
    classifications = event.get("classifications", [{}])
    if classifications:
        cl = classifications[0]
        segment = cl.get("segment", {}).get("name", "")
        genre = cl.get("genre", {}).get("name", "")
        if segment or genre:
            st.markdown(f"<p style='color:#555; font-size:0.8rem; margin-top:0.5rem;'>{segment}{' — ' + genre if genre and genre != 'Undefined' else ''}</p>", unsafe_allow_html=True)

    ticket_url = event.get("url", "")
    if ticket_url:
        st.markdown(f"<p style='margin-top:0.75rem;'><a href='{ticket_url}' target='_blank' style='color:#f5c842;'>→ Buy tickets on Ticketmaster</a></p>", unsafe_allow_html=True)

    # AI Analysis
    st.markdown("## AI Market Analysis")

    cache_key = f"ai_{event.get('id')}"
    if st.session_state.get("ai_cache_key") != cache_key:
        st.session_state.ai_insight = None
        st.session_state.ai_cache_key = cache_key

    if st.button("✦ Generate Market Insight"):
        with st.spinner("Analysing ticket market..."):
            insight = generate_ai_insight(event, price_info)
            st.session_state.ai_insight = insight

    if st.session_state.ai_insight:
        st.markdown(
            f'<div class="ai-box"><div class="ai-label">✦ AI Market Insight</div>'
            f'<div class="ai-text">{st.session_state.ai_insight}</div></div>',
            unsafe_allow_html=True
        )

elif not st.session_state.events:
    st.markdown("<p style='color:#555; text-align:center; margin-top:3rem; font-size:1.1rem;'>Search for any artist, team, show, or venue to get started.</p>", unsafe_allow_html=True)

st.markdown("---")
st.caption("Data: Ticketmaster API · AI analysis: Claude · Built with Python & Streamlit")