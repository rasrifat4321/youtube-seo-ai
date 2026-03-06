import os
import re
import json
import requests
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

st.set_page_config(page_title="YouTube SEO AI Tool", layout="wide")

st.title("🌍 YouTube SEO AI Tool (World)")
st.write("Worldwide + Any Language | SEO Pack + Rank Tags + Competition")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ------------------------
# Extract Video ID
# ------------------------

def extract_video_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


# ------------------------
# YouTube Metadata
# ------------------------

def fetch_metadata(video_id):

    if not YOUTUBE_API_KEY:
        return {}

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet",
        "id": video_id,
        "key": YOUTUBE_API_KEY,
    }

    r = requests.get(url, params=params)

    data = r.json()

    if not data["items"]:
        return {}

    snippet = data["items"][0]["snippet"]

    return {
        "title": snippet["title"],
        "description": snippet["description"],
        "channel": snippet["channelTitle"],
    }


# ------------------------
# Transcript
# ------------------------

def get_transcript(video_id):

    try:

        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        text = " ".join([x["text"] for x in transcript])

        return text

    except:

        return ""


# ------------------------
# SERP Competition
# ------------------------

def serp_competition(keyword):

    if not YOUTUBE_API_KEY:
        return "UNKNOWN", 0

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": 10,
        "key": YOUTUBE_API_KEY,
    }

    r = requests.get(url, params=params)

    data = r.json()

    score = len(data.get("items", [])) * 7

    level = "LOW"

    if score > 60:
        level = "HIGH"
    elif score > 30:
        level = "MED"

    return level, score


# ------------------------
# Gemini AI
# ------------------------

def call_gemini(prompt):

    client = genai.Client(api_key=GEMINI_API_KEY)

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = resp.text

    m = re.search(r"\{.*\}", text, re.S)

    return json.loads(m.group(0))


# ------------------------
# Prompt Builder
# ------------------------

def build_prompt(meta, transcript, keyword):

    return f"""
You are a professional YouTube SEO expert.

Return JSON only.

INPUT

title: {meta.get("title","")}
description: {meta.get("description","")}
channel: {meta.get("channel","")}
transcript: {transcript[:2000]}
main_keyword: {keyword}

OUTPUT JSON

{{
"best_title":"",
"title_options":[],
"viral_titles":[],
"description":"",
"tags":[],
"rank_tags":[],
"hashtags":[]
}}

RULES

best_title 55-70 chars

rank_tags 5-8

tags 40+

hashtags 5-10

optimize for YouTube SEO
"""


# ------------------------
# UI
# ------------------------

url = st.text_input("Paste YouTube Video Link")

keyword = st.text_input("Main Keyword")

if st.button("Generate Pro SEO Pack 🚀"):

    video_id = extract_video_id(url)

    if not video_id:

        st.error("Invalid YouTube URL")

        st.stop()

    with st.spinner("Fetching data..."):

        meta = fetch_metadata(video_id)

        transcript = get_transcript(video_id)

        level, score = serp_competition(keyword)

    st.subheader("📊 SERP Competition")

    col1, col2 = st.columns(2)

    col1.metric("Level", level)

    col2.metric("Score", score)

    with st.spinner("Generating SEO Pack..."):

        prompt = build_prompt(meta, transcript, keyword)

        data = call_gemini(prompt)

    st.subheader("✅ Best Title")

    st.write(data["best_title"])

    st.subheader("🎯 Title Options")

    for t in data["title_options"]:
        st.write("•", t)

    st.subheader("🔥 Viral Titles")

    for t in data["viral_titles"]:
        st.write("•", t)

    st.subheader("📝 Description")

    st.write(data["description"])

    st.subheader("🏷 Tags")

    st.code(", ".join(data["tags"]))

    st.subheader("🔥 Rank Tags")

    st.code(", ".join(data["rank_tags"]))

    st.subheader("#️⃣ Hashtags")

    st.code(" ".join(data["hashtags"]))
