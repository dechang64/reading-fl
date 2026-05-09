"""疗愈音乐 — MiniMax music-2.6-free 生成

功能：
- 选择场景和情绪风格
- AI 生成中国传统乐器疗愈音乐
- 在线播放 + 下载
"""

import streamlit as st
from core.minimax_music import generate_music, MUSIC_AVAILABLE
from core.config import MUSIC_PLACES, MUSIC_MOODS
import os

st.set_page_config(page_title="疗愈音乐 · 大观园树洞", page_icon="🎵", layout="centered")

# ── 返回 ──
if st.button("← 回到大观园", use_container_width=True):
    st.switch_page("app.py")

st.markdown("""
<div class="card-dark" style="text-align:center; padding: 1.5rem;">
    <div style="font-size: 2.5rem;">🎵</div>
    <h2 style="margin: 0.5rem 0;">疗愈音乐</h2>
    <p style="font-size: 0.85rem; color: #d4c5a9;">AI 为你生成专属疗愈音乐</p>
</div>
""", unsafe_allow_html=True)

# ── 音乐功能不可用提示 ──
if not MUSIC_AVAILABLE:
    st.markdown("""
<div class="card" style="text-align:center;">
    <p style="color: #8b7355;">🎵 音乐生成需要 MiniMax API Key（可选功能）</p>
    <p style="font-size: 0.8rem; color: #b8860b;">在 Streamlit Secrets 中配置 MINIMAX_API_KEY 即可启用</p>
    <p style="font-size: 0.75rem; color: #8b7355; margin-top: 0.5rem;">AI 对话功能不受影响，随时可以去倾诉 🎋</p>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ── 选择参数 ──
col1, col2 = st.columns(2)
with col1:
    place = st.selectbox("场景", MUSIC_PLACES, index=0)
with col2:
    mood = st.selectbox("情绪", MUSIC_MOODS, index=0)

duration = st.slider("时长（秒）", 30, 120, 60, step=10)

# ── 自定义描述 ──
custom_prompt = st.text_input(
    "自定义描述（可选）",
    placeholder="如：雨打芭蕉、月下独酌...",
)

# ── 生成 ──
if st.button("🎵 生成疗愈音乐", type="primary", use_container_width=True):
    prompt = custom_prompt or f"{place}的{mood}氛围"
    with st.spinner("🎵 AI 正在为你创作音乐..."):
        audio_path = generate_music(
            prompt=prompt,
            place=place,
            mood=mood,
            duration=duration,
        )

    if audio_path and os.path.exists(audio_path):
        st.session_state.current_audio = audio_path
        st.session_state.audio_place = place
        st.session_state.audio_mood = mood
        st.rerun()
    else:
        st.error("音乐生成失败，请稍后再试")

# ── 播放器 ──
if "current_audio" in st.session_state:
    audio_path = st.session_state.current_audio
    if os.path.exists(audio_path):
        st.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🎶</div>
    <h3>{st.session_state.audio_place} · {st.session_state.audio_mood}</h3>
    <p style="font-size: 0.8rem; color: #8b7355;">AI 专属生成</p>
</div>
""", unsafe_allow_html=True)

        with open(audio_path, "rb") as f:
            st.audio(f.read(), format="audio/mp3")

        with open(audio_path, "rb") as f:
            audio_data = f.read()
        st.download_button(
            "📥 下载音乐",
            data=audio_data,
            file_name=f"大观园_{st.session_state.audio_place}_{st.session_state.audio_mood}.mp3",
            mime="audio/mp3",
            use_container_width=True,
        )
