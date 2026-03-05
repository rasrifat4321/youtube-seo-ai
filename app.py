import os, re, json, math, datetime
import requests
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

# ---------------- Page ----------------
st.set_page_config(page_title="YouTube SEO AI Tool (World v3)", layout="wide")
st.title("🌍 YouTube SEO AI Tool (World v3)")
st.caption("Worldwide + Any Language | SEO Pack + 5–8 Rank Tags + SERP Competition + VidIQ-style Checklist Score")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

if not GEMINI_API_KEY:
    st.warning("❗ GEMINI_API_KEY সেট করা নেই। Streamlit Secrets এ GEMINI_API_KEY বসাও।")

# ---------------- Searchable lists (type to search) ----------------
LANGUAGES = [
    "Auto",
    "English","Bengali","Hindi","Urdu","Turkish","Arabic","Spanish","French","German","Portuguese","Russian",
    "Chinese (Simplified)","Chinese (Traditional)","Japanese","Korean","Italian","Dutch","Polish","Ukrainian",
    "Indonesian","Malay","Thai","Vietnamese","Filipino","Swahili","Persian","Hebrew","Greek","Czech","Romanian",
    "Hungarian","Swedish","Norwegian","Danish","Finnish","Bulgarian","Serbian","Croatian","Slovak","Slovenian",
    "Lithuanian","Latvian","Estonian","Georgian","Armenian","Azerbaijani","Kazakh","Uzbek","Mongolian",
    "Tamil","Telugu","Kannada","Malayalam","Marathi","Gujarati","Punjabi","Sinhala","Nepali","Pashto",
    "Somali","Hausa","Yoruba","Igbo","Amharic","Zulu","Xhosa","Afrikaans","Burmese","Khmer","Lao"
]

COUNTRIES = [
    "Global","United States","United Kingdom","Canada","Australia","New Zealand",
    "Bangladesh","India","Pakistan","Nepal","Sri Lanka",
    "Turkey","United Arab Emirates","Saudi Arabia","Qatar","Kuwait","Oman",
    "Germany","France","Italy","Spain","Portugal","Netherlands","Belgium","Sweden","Norway","Denmark","Finland","Poland",
    "Russia","Ukraine",
    "Brazil","Mexico","Argentina","Chile","Colombia","Peru",
    "South Africa","Nigeria","Kenya","Ghana","Ethiopia","Tanzania","Uganda",
    "Japan","South Korea","China","Taiwan","Hong Kong","Singapore","Malaysia","Indonesia","Thailand","Vietnam","Philippines"
]

# ---------------- Helpers ----------------
def extract_video_id(url: str) -> str:
    m = re.search(r"(?:youtu\.be/|v=)([A-Za-z0-9_-]{11})", (url or "").strip())
    return m.group(1) if m else ""

def yt_api_get(endpoint: str, params: dict) -> dict:
    r = requests.get(endpoint, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

def fetch_youtube_metadata(video_id: str) -> dict:
    # title/desc/channel
    if not YOUTUBE_API_KEY:
        return {"title": "", "description": "", "channelTitle": "", "publishedAt": ""}

    endpoint = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet", "id": video_id, "key": YOUTUBE_API_KEY}
    data = yt_api_get(endpoint, params)
    items = data.get("items", [])
    if not items:
        return {"title": "", "description": "", "channelTitle": "", "publishedAt": ""}

    sn = items[0].get("snippet", {}) or {}
    return {
        "title": sn.get("title", "") or "",
        "description": sn.get("description", "") or "",
        "channelTitle": sn.get("channelTitle", "") or "",
        "publishedAt": sn.get("publishedAt", "") or "",
    }

def fetch_transcript(video_id: str) -> str:
    try:
        tl = YouTubeTranscriptApi.list_transcripts(video_id)
        t = None
        # try English first, then any available
        try:
            t = tl.find_transcript(["en"])
        except Exception:
            t = next(iter(tl), None)
        if not t:
            return ""
        parts = t.fetch()
        text = " ".join([p.get("text", "") for p in parts])
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""

def youtube_search_top(keyword: str, max_results: int = 10) -> list:
    # SERP sample for competition indicator
    if not YOUTUBE_API_KEY:
        return []
    endpoint = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
        "safeSearch": "none",
    }
    data = yt_api_get(endpoint, params)
    items = data.get("items", [])
    out = []
    for it in items:
        vid = (it.get("id", {}) or {}).get("videoId", "")
        sn = it.get("snippet", {}) or {}
        out.append({
            "videoId": vid,
            "title": sn.get("title", "") or "",
            "channelTitle": sn.get("channelTitle", "") or "",
            "publishedAt": sn.get("publishedAt", "") or "",
        })
    return [x for x in out if x.get("videoId")]

def fetch_video_stats(video_ids: list) -> dict:
    if not YOUTUBE_API_KEY or not video_ids:
        return {}
    endpoint = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "statistics", "id": ",".join(video_ids[:10]), "key": YOUTUBE_API_KEY}
    data = yt_api_get(endpoint, params)
    items = data.get("items", [])
    stats = {}
    for it in items:
        vid = it.get("id")
        stt = it.get("statistics", {}) or {}
        stats[vid] = {"viewCount": int(stt.get("viewCount", 0) or 0)}
    return stats

def iso_to_date(iso: str):
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except Exception:
        return None

def compute_competition(keyword: str) -> dict:
    results = youtube_search_top(keyword, max_results=10)
    if not results:
        return {"level": "UNKNOWN", "score": 0, "notes": ["YouTube API key OFF / সার্চ ডাটা পাওয়া যায়নি"], "top": []}

    ids = [r["videoId"] for r in results][:8]
    stats = fetch_video_stats(ids)

    kw = (keyword or "").strip().lower()
    kw_tokens = [t for t in re.split(r"\s+", kw) if t]
    if not kw_tokens:
        return {"level": "UNKNOWN", "score": 0, "notes": ["Main keyword ফাঁকা"], "top": results[:5]}

    title_hits, views, recent = 0, [], 0
    today = datetime.date.today()

    for r in results[:8]:
        title = (r.get("title") or "").lower()
        if all(t in title for t in kw_tokens[: min(2, len(kw_tokens))]):
            title_hits += 1
        v = stats.get(r["videoId"], {}).get("viewCount", 0)
        views.append(v)
        d = iso_to_date(r.get("publishedAt", ""))
        if d and (today - d).days <= 90:
            recent += 1

    avg_views = sum(views) / max(1, len(views))
    views_component = min(60, (math.log10(avg_views + 1) / 7.0) * 60)
    title_component = (title_hits / 8.0) * 25
    recent_component = (recent / 8.0) * 15
    score = int(round(views_component + title_component + recent_component))

    level = "HIGH" if score >= 70 else ("MED" if score >= 40 else "LOW")
    notes = [
        f"Top results avg views ≈ {int(avg_views):,}",
        f"Title keyword-match (approx) = {title_hits}/8",
        f"Recent uploads (≤90d) = {recent}/8",
        "HIGH হলে long-tail rank tags + country/language modifier ব্যবহার করাই best."
    ]
    return {"level": level, "score": score, "notes": notes, "top": results[:5]}

def call_gemini(prompt: str) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY missing")
    client = genai.Client(api_key=GEMINI_API_KEY)
    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    text = (resp.text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON found in Gemini response.")
    return json.loads(m.group(0))

def calc_checklist_score(best_title: str, desc: str, tags: list, rank_tags: list, hashtags: list, main_kw: str):
    # VidIQ-friendly checklist heuristic (ours)
    kw = (main_kw or "").strip().lower()
    title_ok = bool(kw) and kw in (best_title or "").lower()

    first2 = "\n".join((desc or "").splitlines()[:2]).lower()
    first2_ok = bool(kw) and kw in first2

    title_len = len(best_title or "")
    title_len_ok = 55 <= title_len <= 70

    desc_words = len(re.findall(r"\w+", desc or ""))
    desc_ok = 180 <= desc_words <= 380

    tag_count = len(tags or [])
    tags_ok = tag_count >= 30

    rt_count = len(rank_tags or [])
    rt_ok = 5 <= rt_count <= 8

    ht_count = len(hashtags or [])
    ht_ok = 5 <= ht_count <= 10

    combo = ((best_title or "") + " " + (desc or "")).lower()
    kw_repeats = combo.count(kw) if kw else 0
    no_stuff_ok = (kw_repeats <= 12) if kw else True

    breakdown = {
        "keyword_in_title": 15 if title_ok else 0,
        "keyword_in_first_2_lines": 15 if first2_ok else 0,
        "title_length_ok": 10 if title_len_ok else 0,
        "description_length_ok": 10 if desc_ok else 0,
        "tags_count_ok": 15 if tags_ok else 0,
        "rank_tags_5_8_ok": 15 if rt_ok else 0,
        "hashtags_5_10_ok": 10 if ht_ok else 0,
        "no_keyword_stuffing": 10 if no_stuff_ok else 0,
    }
    overall = sum(breakdown.values())

    fixes = []
    if not title_ok: fixes.append("Main keyword টাইটেলে naturally বসাও।")
    if not first2_ok: fixes.append("Description-এর প্রথম 2 লাইনে main keyword বসাও।")
    if not title_len_ok: fixes.append("Title length 55–70 chars রাখো।")
    if not desc_ok: fixes.append("Description 180–350 words এর মধ্যে রাখো।")
    if not tags_ok: fixes.append("Tags 30+ করো (broad + long-tail mix)।")
    if not rt_ok: fixes.append("Rank tags ঠিক 5–8টা long-tail phrase দাও।")
    if not ht_ok: fixes.append("Hashtags 5–10 এর মধ্যে রাখো।")
    if not no_stuff_ok: fixes.append("Keyword stuffing কমাও—natural রাখো।")

    return breakdown, overall, fixes

def build_prompt(video_url, meta, transcript, keyword, out_lang, out_country, comp_level, comp_score, comp_titles):
    # Language instruction
    if (out_lang or "").lower() == "auto":
        lang_instruction = (
            "Auto-detect the most appropriate language from the video metadata/transcript, "
            "then use that language for ALL output."
        )
    else:
        lang_instruction = f"Use {out_lang} for ALL output text."

    return f"""
You are a professional YouTube SEO expert and copywriter.
Return STRICT JSON only (no markdown, no extra text).

INPUT:
- video_url: {video_url}
- existing_title: {meta.get("title","")}
- existing_description: {meta.get("description","")[:1200]}
- channel: {meta.get("channelTitle","")}
- transcript_excerpt: {transcript[:5000]}
- main_keyword: {keyword}
- target_country: {out_country}
- serp_competition_level: {comp_level}
- serp_competition_score_0_100: {comp_score}
- serp_top_titles: {comp_titles}

OUTPUT JSON:
{{
  "best_title": "...",
  "title_options": ["...","...","...","...","...","...","...","...","...","..."],
  "viral_titles": ["...","...","...","...","...","...","...","...","...","..."],
  "thumbnail_text": ["...","...","...","...","..."],
  "description": "...",
  "tags": ["..."],
  "rank_tags": ["..."],
  "hashtags": ["#..."],
  "pinned_comment": "...",
  "chapters": ["00:00 ...", "00:30 ..."],
  "low_competition_keywords": ["...","...","...","...","...","...","...","...","...","..."]
}}

RULES (optimize for VidIQ-style checks):
- best_title length 55–70 characters; main_keyword MUST be in best_title naturally.
- title_options: 10 options (SEO focused).
- viral_titles: 10 options (high CTR style; still relevant; not misleading).
- thumbnail_text: 5 short texts (2–5 words).
- Description: 180–350 words; first 2 lines MUST contain main_keyword; include:
  - 3 bullet points
  - 1 CTA line
  - 3 link placeholders
- tags: 35–60 items, mix broad + long-tail + intent phrases.
- rank_tags: EXACTLY 5–8 long-tail phrases (3–7 words), designed to rank.
  Add modifiers like: year, "explained", "full", "step by step", plus country modifier when useful.
- hashtags: 5–10 max.
- low_competition_keywords: 10 suggestions that are more specific/long-tail than main keyword.
- Adapt based on competition:
  - HIGH: more long-tail + specific intent + country modifier
  - MED/LOW: balanced broad + long-tail
- {lang_instruction}
"""

# ---------------- UI ----------------
with st.sidebar:
    st.subheader("🌍 World Options (Search & Select)")
    st.caption("Dropdown খুলে টাইপ করলেই search হবে ✅")

    lang_mode = st.selectbox("Language Mode", ["Auto Detect", "Manual Select"], index=0)

    if lang_mode == "Manual Select":
        out_lang = st.selectbox("Output Language", LANGUAGES, index=LANGUAGES.index("English") if "English" in LANGUAGES else 0)
        custom_lang = st.text_input("Custom language (optional) — e.g., 'Spanish (Mexico)'", value="")
        final_lang = custom_lang.strip() if custom_lang.strip() else out_lang
        if final_lang.lower() == "auto":
            final_lang = "English"
    else:
        final_lang = "Auto"

    out_country = st.selectbox("Target Country", COUNTRIES, index=0)
    custom_country = st.text_input("Custom country (optional) — e.g., 'Italy'", value="")
    final_country = custom_country.strip() if custom_country.strip() else out_country

    use_transcript = st.toggle("Use transcript if available", value=True)
    st.caption("Tip: Client country/language দিলে Rank Tags আরও strong হয়।")

video_url = st.text_input("Paste YouTube Video Link", value="")
keyword = st.text_input("Main Keyword (client keyword)", value="")

run = st.button("Generate Pro SEO Pack 🚀", type="primary")

if run:
    if not video_url.strip():
        st.error("ভিডিও লিংক দাও।")
        st.stop()
    if not keyword.strip():
        st.error("Main keyword দাও।")
        st.stop()

    vid = extract_video_id(video_url)
    if not vid:
        st.error("ভিডিও ID বের করতে পারলাম না—লিংকটা ঠিক আছে তো?")
        st.stop()

    with st.spinner("Fetching metadata / transcript / SERP competition..."):
        meta = fetch_youtube_metadata(vid)
        transcript = fetch_transcript(vid) if use_transcript else ""
        comp = compute_competition(keyword.strip())

    st.subheader("📊 SERP Competition (YouTube Search)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Level", comp.get("level"))
    c2.metric("Score (0–100)", comp.get("score"))
    c3.metric("YouTube API", "ON" if YOUTUBE_API_KEY else "OFF")

    with st.expander("Why this competition?"):
        for n in comp.get("notes", []):
            st.write("• " + n)
        for x in comp.get("top", []):
            st.write("- " + x.get("title", ""))

    with st.spinner("Generating SEO pack with Gemini..."):
        prompt = build_prompt(
            video_url,
            meta,
            transcript,
            keyword.strip(),
            final_lang or "Auto",
            final_country or "Global",
            comp.get("level"),
            comp.get("score"),
            [x.get("title", "") for x in comp.get("top", [])]
        )
        out = call_gemini(prompt)

    # Extract
    best_title = out.get("best_title", "")
    desc = out.get("description", "")
    tags = out.get("tags", []) or []
    rank_tags = out.get("rank_tags", []) or []
    hashtags = out.get("hashtags", []) or []
    title_options = out.get("title_options", []) or []
    viral_titles = out.get("viral_titles", []) or []
    thumbnail_text = out.get("thumbnail_text", []) or []
    low_kw = out.get("low_competition_keywords", []) or []
    chapters = out.get("chapters", []) or []
    pinned_comment = out.get("pinned_comment", "")

    breakdown, overall, fixes = calc_checklist_score(best_title, desc, tags, rank_tags, hashtags, keyword.strip())

    # ---------------- Output ----------------
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("✅ Best Title")
        st.write(best_title)

        st.subheader("🎯 SEO Title Options (10)")
        for t in title_options[:10]:
            st.write("• " + t)

        st.subheader("🔥 Viral Titles (10)")
        for t in viral_titles[:10]:
            st.write("• " + t)

        st.subheader("🖼 Thumbnail Text (5)")
        for t in thumbnail_text[:5]:
            st.write("• " + t)

        st.subheader("🔥 Rank Tags (EXACT 5–8)")
        st.code("\n".join(rank_tags))

        st.subheader("🏷️ Hashtags")
        st.code(" ".join(hashtags))

        st.subheader("📌 Pinned Comment")
        st.write(pinned_comment)

    with col2:
        st.subheader("📝 Description")
        st.code(desc)

        st.subheader("🔖 Tags (copy-paste)")
        st.code(", ".join(tags))

        st.subheader("🕒 Chapters")
        st.code("\n".join(chapters) if chapters else "")

        st.subheader("🔍 Low-Competition Keywords (10)")
        for k in low_kw[:10]:
            st.write("• " + k)

        st.subheader("✅ VidIQ-friendly Checklist Score (0–100)")
        st.json(breakdown)
        st.metric("Overall Score", overall)

        st.subheader("🛠️ Fix Suggestions (to push score up)")
        for s in fixes[:10]:
            st.write("• " + s)

    st.success("Done! কপি-পেস্ট করে ইউটিউবে বসাও।")
