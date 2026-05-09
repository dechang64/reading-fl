"""匿名共鸣 — 真实匿名社交

功能：
- 匿名发布心事（仅内容+情绪标签，无个人标识）
- 共鸣墙：浏览他人的匿名帖子
- 情绪匹配：找到与你情绪相似的人
- 共鸣（点赞）：让发布者知道有人懂
"""

import time
import streamlit as st
from core.db import create_post, get_posts, resonate_post
from core.emotion_detector import detect_emotion, compute_session_emotion_profile
from core.config import EMOTIONS, SCENES

st.set_page_config(page_title="匿名共鸣 · 大观园树洞", page_icon="🌸", layout="centered")

# ── 返回 ──
if st.button("← 回到大观园", use_container_width=True):
    st.switch_page("app.py")

# ── Tab 切换 ──
tab1, tab2, tab3 = st.tabs(["📝 发布", "🌸 共鸣墙", "💫 情绪匹配"])

# ═══════════════════════════════════════════════════════════
#  发布
# ═══════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
<div class="card" style="text-align:center;">
    <h3>📝 匿名发布</h3>
    <p style="font-size: 0.8rem; color: #8b7355;">你的身份完全匿名，只有内容会被看到</p>
</div>
""", unsafe_allow_html=True)

    post_content = st.text_area(
        "说出你想说的话...",
        height=100,
        placeholder="这里没有人认识你，你可以做真实的自己...",
        label_visibility="collapsed",
    )

    # 场景选择
    scene_options = ["不选择"] + [s["name"] for s in SCENES]
    selected_scene = st.selectbox("关联场景（可选）", scene_options, index=0)

    if post_content and st.button("🌸 匿名发布", type="primary", use_container_width=True):
        emotion = detect_emotion(post_content)
        scene = selected_scene if selected_scene != "不选择" else ""
        create_post(content=post_content, emotion=emotion, scene=scene)
        st.success("发布成功！你的心声已在共鸣墙上 🌸")
        st.rerun()

# ═══════════════════════════════════════════════════════════
#  共鸣墙
# ═══════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
<div class="card" style="text-align:center;">
    <h3>🌸 共鸣墙</h3>
    <p style="font-size: 0.8rem; color: #8b7355;">你不是一个人在感受</p>
</div>
""", unsafe_allow_html=True)

    # 情绪筛选
    filter_emotion = st.selectbox("按情绪筛选", ["全部"] + EMOTIONS, index=0)

    try:
        posts = get_posts(limit=30, emotion=None if filter_emotion == "全部" else filter_emotion)
    except Exception:
        posts = []

    if not posts:
        st.markdown("""
<div style="text-align:center; padding: 2rem; color: #8b7355;">
    <div style="font-size: 2rem;">🌙</div>
    <p>共鸣墙还很安静...</p>
    <p style="font-size: 0.8rem;">成为第一个分享的人吧</p>
</div>
""", unsafe_allow_html=True)
    else:
        for post in posts:
            time_str = _format_time(post["created_at"])
            scene_tag = f"<span class='tag'>{post['scene']}</span>" if post["scene"] else ""
            st.markdown(f"""
<div class="card fade-in">
    <p style="line-height: 1.8; margin-bottom: 0.5rem;">{post['content']}</p>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span class="tag">{post['emotion']}</span>
            {scene_tag}
            <span style="font-size: 0.7rem; color: #8b7355;">{time_str}</span>
        </div>
        <div>
            <span style="color: #b8860b; font-size: 0.85rem;">💗 {post['resonates']}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
            if st.button(f"💗 共鸣", key=f"resonate_{post['id']}", use_container_width=True):
                resonate_post(post["id"])
                st.rerun()

# ═══════════════════════════════════════════════════════════
#  情绪匹配
# ═══════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
<div class="card" style="text-align:center;">
    <h3>💫 情绪匹配</h3>
    <p style="font-size: 0.8rem; color: #8b7355;">找到与你情绪相似的人</p>
</div>
""", unsafe_allow_html=True)

    # 基于当前会话情绪匹配
    chat_history = st.session_state.get("chat_history", [])
    if chat_history:
        profile = compute_session_emotion_profile(chat_history)
        if profile:
            top_emotion = max(profile, key=profile.get)
            st.markdown(f"""
<div style="text-align:center; margin: 1rem 0;">
    <span class="tag" style="font-size: 1rem; padding: 0.3rem 1rem;">你的情绪：{top_emotion}</span>
</div>
""", unsafe_allow_html=True)

            try:
                matching_posts = get_posts(limit=10, emotion=top_emotion)
            except Exception:
                matching_posts = []
            if matching_posts:
                st.markdown(f"### 与你同样感到「{top_emotion}」的人")
                for post in matching_posts[:5]:
                    st.markdown(f"""
<div class="card">
    <p style="line-height: 1.8;">{post['content']}</p>
    <div style="font-size: 0.7rem; color: #8b7355; margin-top: 0.3rem;">
        💗 {post['resonates']} · {_format_time(post['created_at'])}
    </div>
</div>
""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
<div style="text-align:center; padding: 1rem; color: #8b7355;">
    暂时没有同样感到「{top_emotion}」的帖子<br>
    <span style="font-size: 0.8rem;">你可以成为第一个</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="text-align:center; padding: 2rem; color: #8b7355;">
    <div style="font-size: 2rem;">🔮</div>
    <p>先去和角色聊聊天吧</p>
    <p style="font-size: 0.8rem;">聊过之后，我就能帮你找到情绪相似的人</p>
</div>
""", unsafe_allow_html=True)
        if st.button("💬 去倾诉", use_container_width=True):
            st.switch_page("pages/1_倾诉对话.py")


def _format_time(timestamp: float) -> str:
    """格式化时间戳为友好文本"""
    if not timestamp:
        return ""
    diff = time.time() - timestamp
    if diff < 60:
        return "刚刚"
    elif diff < 3600:
        return f"{int(diff/60)}分钟前"
    elif diff < 86400:
        return f"{int(diff/3600)}小时前"
    else:
        return f"{int(diff/86400)}天前"
