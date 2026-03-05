import streamlit as st

st.title("YouTube SEO AI Tool")

video_link = st.text_input("Paste YouTube Video Link")

keyword = st.text_input("Main Keyword")

if st.button("Generate SEO"):
    st.write("SEO Title:")
    st.write("Best YouTube SEO Title Example")

    st.write("Description:")
    st.write("This is an example SEO description for your video.")

    st.write("Tags:")
    st.write("youtube seo, youtube tags, viral video, youtube growth")