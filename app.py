import html as _html
import time
from typing import Optional

import requests
import streamlit as st

# =============================
# CONFIG
# =============================
API_BASE = "https://movie-rec-466x.onrender.com"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
TMDB_BACK = "https://image.tmdb.org/t/p/w1280"

# Render free plan par server so jata hai, pehli request me 30-60s lag sakte hain
REQUEST_TIMEOUT = 90
MAX_RETRIES = 3

st.set_page_config(
    page_title="CineWave",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def html_block(s: str) -> str:
    """HTML ko ek hi line me badal deta hai.

    Streamlit markdown me 4+ spaces ki indentation ya blank line aajaye to HTML
    code-block ban jata hai aur '</div>' text ki surat me dikhne lagta hai.
    Is helper se ye masla nahi hota.
    """
    return "".join(line.strip() for line in s.strip().splitlines())


def esc(x) -> str:
    return _html.escape(str(x or ""), quote=True)


# =============================
# NETFLIX-STYLE CSS + ANIMATIONS
# =============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1117 50%, #0a0e1a 100%);
    color: #e8e8e8;
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

.cinewave-header {
    text-align: center;
    padding: 2rem 0 1.5rem;
    animation: fadeSlideDown 0.8s ease forwards;
}

.cinewave-logo {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #e50914, #ff6b35, #e50914);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmerText 3s linear infinite;
    letter-spacing: -1px;
}

.cinewave-sub {
    color: #888;
    font-size: 0.9rem;
    margin-top: 4px;
    letter-spacing: 0.05em;
}

@keyframes shimmerText {
    0%   { background-position: 0% center; }
    100% { background-position: 200% center; }
}
@keyframes fadeSlideDown {
    from { opacity: 0; transform: translateY(-24px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(229,9,20,0.4); }
    50%      { box-shadow: 0 0 0 10px rgba(229,9,20,0); }
}

/* Search bar */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1.5px solid rgba(255,255,255,0.1) !important;
    border-radius: 50px !important;
    color: #fff !important;
    padding: 0.65rem 1.2rem !important;
    font-size: 0.95rem !important;
    transition: all 0.3s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: #e50914 !important;
    background: rgba(255,255,255,0.09) !important;
    box-shadow: 0 0 0 3px rgba(229,9,20,0.15) !important;
}
.stTextInput > div > div > input::placeholder { color: #666 !important; }

/* Selectbox */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1.5px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #fff !important;
}

/* Movie card */
.movie-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    animation: fadeSlideUp 0.5s ease forwards;
    cursor: pointer;
}
.movie-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(229,9,20,0.3);
    border-color: rgba(229,9,20,0.4);
}

.movie-poster-wrap {
    position: relative;
    overflow: hidden;
    border-radius: 10px 10px 0 0;
}
.movie-poster-wrap img {
    width: 100%;
    display: block;
    transition: transform 0.4s ease;
}
.movie-card:hover .movie-poster-wrap img { transform: scale(1.05); }

.play-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s;
    border-radius: 10px 10px 0 0;
}
.movie-card:hover .play-overlay { opacity: 1; }

.play-btn-icon {
    width: 52px; height: 52px;
    background: rgba(229,9,20,0.9);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 4px 20px rgba(229,9,20,0.6);
}

.movie-card-body { padding: 10px 12px 12px; }

.movie-title-text {
    color: #e8e8e8;
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.3;
    height: 2.6rem;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    margin-bottom: 6px;
}

.movie-rating {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #fbbf24;
    font-size: 0.78rem;
    font-weight: 600;
}

.movie-genre {
    color: #666;
    font-size: 0.72rem;
    margin-top: 2px;
    min-height: 1rem;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #e50914, #b8060f) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 0.3rem 0.6rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.03em !important;
}
.stButton > button:hover {
    transform: scale(1.03) !important;
    box-shadow: 0 4px 16px rgba(229,9,20,0.4) !important;
}

/* Detail page */
.detail-backdrop {
    width: 100%;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 1.5rem;
    position: relative;
    animation: fadeIn 0.6s ease forwards;
}
.detail-backdrop img {
    width: 100%;
    display: block;
    max-height: 380px;
    object-fit: cover;
    border-radius: 16px;
    filter: brightness(0.75);
}
.detail-backdrop-overlay {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    background: linear-gradient(to top, rgba(10,14,26,0.95) 0%, transparent 100%);
    padding: 2rem 1.5rem 1.5rem;
    border-radius: 0 0 16px 16px;
}
.detail-backdrop-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 2px 8px rgba(0,0,0,0.5);
    line-height: 1.2;
}

.detail-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.5rem;
    animation: fadeSlideUp 0.5s ease forwards;
}
.detail-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
}
.detail-label {
    color: #e8e8e8;
    font-weight: 600;
    margin-top: 12px;
}

.info-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0;
}
.info-badge {
    background: rgba(229,9,20,0.15);
    border: 1px solid rgba(229,9,20,0.3);
    color: #ff6b6b;
    font-size: 0.75rem;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
}
.info-badge-dark {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.1);
    color: #aaa;
    font-size: 0.75rem;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
}
.rating-big {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(251,191,36,0.12);
    border: 1px solid rgba(251,191,36,0.3);
    color: #fbbf24;
    font-size: 0.9rem;
    font-weight: 700;
    padding: 5px 14px;
    border-radius: 20px;
}

.overview-text {
    color: #bbb;
    font-size: 0.95rem;
    line-height: 1.75;
    margin: 4px 0 0;
}

.section-heading {
    font-size: 1.3rem;
    font-weight: 700;
    color: #e8e8e8;
    margin: 1.8rem 0 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 8px;
    border-bottom: 2px solid rgba(229,9,20,0.4);
}
.section-heading::after {
    content: '';
    flex: 1;
    height: 2px;
    background: linear-gradient(to right, rgba(229,9,20,0.2), transparent);
    border-radius: 2px;
}

[data-testid="stSidebar"] {
    background: rgba(5,8,15,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] .stMarkdown { color: #ccc; }

hr { border-color: rgba(255,255,255,0.08) !important; }
.stSpinner > div { border-top-color: #e50914 !important; }
.stAlert { border-radius: 10px !important; }

/* Back button (st.button key="back_btn..." se class st-key-back_btn... milti hai) */
[class*="st-key-back_btn"] button {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #ccc !important;
    border-radius: 50px !important;
    font-size: 0.85rem !important;
    width: auto !important;
}
[class*="st-key-back_btn"] button:hover {
    background: rgba(255,255,255,0.14) !important;
    transform: none !important;
    box-shadow: none !important;
}

div[data-testid="column"]:nth-child(1) .movie-card { animation-delay: 0.05s; }
div[data-testid="column"]:nth-child(2) .movie-card { animation-delay: 0.10s; }
div[data-testid="column"]:nth-child(3) .movie-card { animation-delay: 0.15s; }
div[data-testid="column"]:nth-child(4) .movie-card { animation-delay: 0.20s; }
div[data-testid="column"]:nth-child(5) .movie-card { animation-delay: 0.25s; }
div[data-testid="column"]:nth-child(6) .movie-card { animation-delay: 0.30s; }
</style>
""", unsafe_allow_html=True)

# =============================
# STATE + ROUTING
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except (TypeError, ValueError):
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_json_cached(path: str, params_items: tuple):
    """Sirf kamyab response cache hota hai.

    Fail hone par exception raise hota hai, is liye error cache nahi hota
    (pehle 30 sec tak timeout error cache ho jata tha).
    """
    params = dict(params_items) if params_items else None
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(f"{API_BASE}{path}", params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code >= 400:
                # 4xx par dobara try karne ka faida nahi
                if r.status_code < 500:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
                last_err = RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            else:
                return r.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
        if attempt < MAX_RETRIES - 1:
            time.sleep(3)
    raise last_err or RuntimeError("Unknown error")


def api_get_json(path: str, params: Optional[dict] = None):
    try:
        items = tuple(sorted(params.items())) if params else ()
        return _fetch_json_cached(path, items), None
    except requests.exceptions.Timeout:
        return None, (
            "Server abhi wake up ho raha hai (free hosting). "
            "Thori der baad page refresh karein."
        )
    except Exception as e:
        return None, f"Request failed: {e}"


# =============================
# RENDER HELPERS
# =============================
GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    18: "Drama", 10751: "Family", 14: "Fantasy", 27: "Horror", 10749: "Romance",
    878: "Sci-Fi", 53: "Thriller", 10752: "War", 37: "Western",
}


def genre_label(ids):
    if not ids:
        return ""
    return " · ".join([GENRE_MAP[i] for i in ids[:2] if i in GENRE_MAP])


def rating_stars(score):
    if not score:
        return ""
    filled = max(0, min(5, round(score / 2)))
    return "★" * filled + "☆" * (5 - filled)


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols, gap="small")
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1
            tmdb_id = m.get("tmdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")
            rating = m.get("vote_average") or 0
            genres = genre_label(m.get("genre_ids", []))

            with colset[c]:
                if poster:
                    poster_html = (
                        '<div class="movie-poster-wrap">'
                        f'<img src="{esc(poster)}" alt="{esc(title)}">'
                        '<div class="play-overlay"><div class="play-btn-icon">▶</div></div>'
                        '</div>'
                    )
                else:
                    poster_html = (
                        '<div style="aspect-ratio:2/3;background:#1a1a2e;'
                        'border-radius:10px 10px 0 0;display:flex;align-items:center;'
                        'justify-content:center;color:#444;font-size:2rem;">🎬</div>'
                    )

                rating_html = (
                    f'<div class="movie-rating">⭐ {rating:.1f} &nbsp; {rating_stars(rating)}</div>'
                    if rating else ""
                )
                genre_html = f'<div class="movie-genre">{esc(genres)}</div>'

                card_html = (
                    '<div class="movie-card">'
                    f'{poster_html}'
                    '<div class="movie-card-body">'
                    f'<div class="movie-title-text">{esc(title)}</div>'
                    f'{rating_html}'
                    f'{genre_html}'
                    '</div>'
                    '</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                if st.button("▶ Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(tmdb_id)


def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append({
                "tmdb_id": tmdb["tmdb_id"],
                "title": tmdb.get("title") or x.get("title") or "Untitled",
                "poster_url": tmdb.get("poster_url"),
                "vote_average": tmdb.get("vote_average", 0),
                "genre_ids": tmdb.get("genre_ids", []),
            })
    return cards


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw_items = []
        for m in (data.get("results") or []):
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id": int(tmdb_id),
                "title": title,
                "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", 0),
                "genre_ids": m.get("genre_ids", []),
            })
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = (m.get("title") or "").strip()
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id": int(tmdb_id),
                "title": title,
                "poster_url": m.get("poster_url"),
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average", 0),
                "genre_ids": m.get("genre_ids", []),
            })
    else:
        return [], []

    matched = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    suggestions = []
    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    cards = [
        {
            "tmdb_id": x["tmdb_id"], "title": x["title"],
            "poster_url": x["poster_url"], "vote_average": x["vote_average"],
            "genre_ids": x["genre_ids"],
        }
        for x in final_list[:limit]
    ]
    return suggestions, cards


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown(html_block("""
    <div style="text-align:center;padding:1rem 0 0.5rem;">
    <div style="font-size:1.6rem;font-weight:700;
    background:linear-gradient(90deg,#e50914,#ff6b35);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;">🎬 CineWave</div>
    <div style="color:#666;font-size:0.78rem;margin-top:2px;">Movie Discovery</div>
    </div>
    """), unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🏠 Home", use_container_width=True):
        goto_home()

    st.markdown("---")
    st.markdown(
        "<div style='color:#888;font-size:0.8rem;font-weight:600;letter-spacing:0.08em;"
        "text-transform:uppercase;margin-bottom:8px;'>HOME FEED</div>",
        unsafe_allow_html=True,
    )

    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
        label_visibility="collapsed",
    )

    grid_cols = st.slider("Grid columns", 3, 8, 5)

    st.markdown("---")
    st.markdown(html_block("""
    <div style="color:#555;font-size:0.75rem;line-height:1.6;text-align:center;">
    Powered by TMDB &amp; FastAPI<br>
    <span style="color:#e50914;">●</span> Live Data
    </div>
    """), unsafe_allow_html=True)


# =============================
# ANIMATED HEADER
# =============================
st.markdown(html_block("""
<div class="cinewave-header">
<div class="cinewave-logo">🎬 CineWave</div>
<div class="cinewave-sub">Search · Discover · Recommend</div>
</div>
"""), unsafe_allow_html=True)

st.divider()

# ==========================================================
# VIEW: HOME
# ==========================================================
if st.session_state.view == "home":

    typed = st.text_input(
        "Search movies",
        placeholder="🔍  Search movies — avengers, batman, interstellar...",
        label_visibility="collapsed",
    )

    st.divider()

    # ── SEARCH MODE ──
    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters…")
        else:
            with st.spinner("Searching…"):
                data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"Search failed: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)

                if suggestions:
                    labels = ["— Select a movie —"] + [s[0] for s in suggestions]
                    selected = st.selectbox("Quick pick", labels, index=0, label_visibility="collapsed")
                    if selected != "— Select a movie —":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try another keyword.")

                st.markdown(
                    html_block(
                        f'<div class="section-heading">🔎 Search Results — '
                        f'<em style="font-weight:400;color:#888;">{esc(typed)}</em></div>'
                    ),
                    unsafe_allow_html=True,
                )
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")

        st.stop()

    # ── HOME FEED MODE ──
    cat_labels = {
        "trending": "🔥 Trending", "popular": "🌟 Popular",
        "top_rated": "⭐ Top Rated", "now_playing": "🎭 Now Playing",
        "upcoming": "🎬 Upcoming",
    }
    st.markdown(
        f'<div class="section-heading">{cat_labels.get(home_category, home_category)}</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Loading movies… (pehli baar server start hone me 1 minute tak lag sakta hai)"):
        home_cards, err = api_get_json("/home", params={"category": home_category, "limit": 24})

    if err or not home_cards:
        st.error(f"Could not load feed: {err or 'Unknown error'}")
        if st.button("🔄 Retry"):
            st.rerun()
        st.stop()

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")


# ==========================================================
# VIEW: DETAILS
# ==========================================================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.warning("No movie selected.")
        if st.button("← Back", key="back_btn_empty"):
            goto_home()
        st.stop()

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back", key="back_btn_top"):
            goto_home()

    with st.spinner("Loading movie…"):
        data, err = api_get_json(f"/movie/id/{tmdb_id}")
    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        st.stop()

    title = data.get("title", "")
    release = data.get("release_date") or ""
    overview = data.get("overview") or "No overview available."
    rating = data.get("vote_average") or 0
    genre_names = [g["name"] for g in data.get("genres", []) if g.get("name")]
    runtime = data.get("runtime")
    backdrop = data.get("backdrop_url")
    poster = data.get("poster_url")

    # ── BACKDROP HERO ──
    if backdrop:
        st.markdown(
            html_block(f"""
            <div class="detail-backdrop">
            <img src="{esc(backdrop)}" alt="{esc(title)}">
            <div class="detail-backdrop-overlay">
            <div class="detail-backdrop-title">{esc(title)}</div>
            </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # ── DETAIL LAYOUT ──
    left, right = st.columns([1, 2.6], gap="large")

    with left:
        if poster:
            st.image(poster, use_container_width=True)
        else:
            st.markdown(
                '<div style="aspect-ratio:2/3;background:#111;border-radius:12px;display:flex;'
                'align-items:center;justify-content:center;font-size:3rem;">🎬</div>',
                unsafe_allow_html=True,
            )

    with right:
        badges_html = ""
        if release:
            badges_html += f'<span class="info-badge-dark">📅 {esc(release[:4])}</span>'
        for g in genre_names[:3]:
            badges_html += f'<span class="info-badge">{esc(g)}</span>'
        if runtime:
            badges_html += f'<span class="info-badge-dark">⏱ {esc(runtime)} min</span>'
        if rating:
            badges_html += f'<span class="rating-big">⭐ {rating:.1f} / 10</span>'

        title_html = "" if backdrop else f'<div class="detail-title">{esc(title)}</div>'

        # Poora detail-card ek hi markdown call me (alag alag calls me div band nahi hota)
        st.markdown(
            html_block(f"""
            <div class="detail-card">
            {title_html}
            <div class="info-row">{badges_html}</div>
            <div class="detail-label">Overview</div>
            <p class="overview-text">{esc(overview)}</p>
            </div>
            """),
            unsafe_allow_html=True,
        )

    st.divider()

    # ── RECOMMENDATIONS ──
    with st.spinner("Finding recommendations…"):
        bundle, err2 = api_get_json(
            "/movie/search",
            params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
        )

    if not err2 and bundle:
        tfidf_cards = to_cards_from_tfidf_items(bundle.get("tfidf_recommendations"))
        genre_cards = bundle.get("genre_recommendations", [])

        if tfidf_cards:
            st.markdown('<div class="section-heading">🔎 Similar Movies (AI Match)</div>', unsafe_allow_html=True)
            poster_grid(tfidf_cards, cols=grid_cols, key_prefix="details_tfidf")

        if genre_cards:
            st.markdown('<div class="section-heading">🎭 More Like This</div>', unsafe_allow_html=True)
            poster_grid(genre_cards, cols=grid_cols, key_prefix="details_genre")

        if not tfidf_cards and not genre_cards:
            st.info("No recommendations available right now.")
    else:
        with st.spinner("Loading genre recommendations…"):
            genre_only, err3 = api_get_json(
                "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
            )
        if not err3 and genre_only:
            st.markdown('<div class="section-heading">🎭 More Like This</div>', unsafe_allow_html=True)
            poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
        else:
            st.info("No recommendations available right now.")