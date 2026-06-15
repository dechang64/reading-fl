"""金句海报预览页 — User 写完摘录后可一键生成海报

流程:
1. 主页 (1_excerpt.py) 写完摘录 → "🪔 生成金句海报" 按钮
2. 跳到本页 (?ref_id=xxx)
3. 渲染海报 + 提供下载/分享

收费墙 (mock):
- 5 张/月免费
- 第 6 张 → 9.9 元/张 OR 199 元/年无限
"""
import streamlit as st
import sys
import os
import json
import html as _html
import uuid as _uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="金句海报 · 心灯",
    page_icon="🪔",
    layout="centered",
    initial_sidebar_state="auto",
)

# 暗色 CSS
st.markdown("""
<style>
:root { --bg: #0d0d0f; --card: rgba(255,255,255,0.04); --text: #e8e4dc; --text-muted: #8b8680;
        --accent: #d4a574; --ember: #c4694a; --border: rgba(212,165,116,0.15); }
.stApp { background: linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%); }
.main .block-container { max-width: 720px; padding-top: 1.5rem; }
h1, h2, h3 { color: var(--text) !important; font-weight: 500 !important; }
h1 { font-size: 1.7rem !important; }
h3 { font-size: 0.85rem !important; color: var(--text-muted) !important;
     text-transform: uppercase; letter-spacing: 0.18em;
     font-weight: 500 !important; margin-top: 1.5rem !important; }
p, .stMarkdown { color: var(--text) !important; line-height: 1.7; }
.stCaption { color: var(--text-muted) !important; }
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background-color: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important; border: none !important; border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important; font-weight: 600 !important;
}
.stButton > button[kind="secondary"] {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.poster-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
    text-align: center;
}
.poster-preview {
    max-width: 375px;
    margin: 0 auto;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    border-radius: 12px;
    overflow: hidden;
}
@media (max-width: 640px) {
    .main .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    h1 { font-size: 1.4rem !important; }
    .stButton > button { width: 100% !important; min-height: 44px !important; }
}
</style>
""", unsafe_allow_html=True)

# 老 webview fallback
st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: #0d0d0f !important;
    color: #e8e4dc !important;
}
.main .block-container,
.main p, .main h1, .main h2, .main h3, .main h4,
.main .stMarkdown, .main .stText, .main .stCaption {
    color: #e8e4dc !important;
}
</style>
""", unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")
st.page_link("pages/1_excerpt.py", label="← 回去写摘录", icon="✍️")

st.markdown("# 🪔 金句海报")
st.caption("把触动你的那段话, 做成可分享的海报")

# ══════════════════════════════════════════════════════════════
#  1. 从 session_state._latest_ref_id 读 ref (从 1_excerpt.py 跳过来)
#  注: st.page_link 不支持 query string, 1_excerpt.py 写完摘录后
#  存 st.session_state._latest_ref_id, 海报页读它
#  ══════════════════════════════════════════════════════════════
ref_data = None
latest_ref_id = st.session_state.get("_latest_ref_id", "")
if latest_ref_id:
    persisted = st.session_state.get("_xindeng_persisted_refs", [])
    for r in persisted:
        if r.get("authenticity_hash", "")[:8] == latest_ref_id[:8]:
            ref_data = r
            break

# 2. fallback: 旧路径 — query param
if not ref_data:
    try:
        ref_id = st.query_params.get("ref_id", "")
        if ref_id:
            persisted = st.session_state.get("_xindeng_persisted_refs", [])
            for r in persisted:
                if r.get("authenticity_hash", "")[:8] == ref_id[:8]:
                    ref_data = r
                    break
    except Exception:
        pass

# 2. 没 query param, 从 session_state.reflections 拿最后一条
if not ref_data and st.session_state.get("reflections"):
    last = st.session_state.reflections[-1]
    # 安全取字段
    ref_data = {
        "excerpt_text": getattr(last.excerpt, "text", ""),
        "book_title": getattr(last.excerpt, "book_title", ""),
        "author": getattr(last.excerpt, "author", ""),
        "reflection_text": getattr(last, "reflection_text", ""),
        "emotion_label": getattr(last, "emotion_label", "resonance"),
        "ts": getattr(last, "timestamp", ""),
    }

# 3. 还没有, 提示去写摘录
if not ref_data:
    st.info("🪔 还没有摘录 — 先去 1_excerpt.py 写一段, 再回来生成海报")
    st.stop()

# 3.5 兜底: ref_data 必须是 dict, 万一 None 漏过 st.stop, 这里也防 crash
if not isinstance(ref_data, dict):
    st.info("🪔 摘录数据读取失败, 请回到 1_excerpt.py 重新写一段")
    st.stop()

# 4. 取用户画像
import json as _json
who = {}
try:
    who_raw = st.query_params.get("who", "")
    if not who_raw:
        who_raw = ""
except Exception:
    who_raw = ""

# 从 session_state 或 localStorage 读
user_mbti = st.session_state.get("user_mbti", "—")
user_zodiac = st.session_state.get("user_zodiac", "—")
user_level = st.session_state.get("user_level_name", "L1 初见者")

# 情绪中英对照
emotion_map = {
    "moved": "感动", "thinking": "思考", "resonance": "共鸣",
    "confused": "困惑", "disagree": "反对", "calm": "平静",
}
emotion_cn = emotion_map.get(ref_data.get("emotion_label", "resonance"), "共鸣")

# ══════════════════════════════════════════════════════════════
#  5. 渲染海报
# ══════════════════════════════════════════════════════════════
from core.poster import render_poster_html, render_poster_preview_html, save_poster_to_file
import uuid

poster_id = _uuid.uuid4().hex[:8]

poster_html = render_poster_html(
    book_title=ref_data.get("book_title", "未命名"),
    author=ref_data.get("author", ""),
    chapter="",  # BookExcerpt 没存章节
    text=ref_data.get("excerpt_text", ""),
    reader_mbti=user_mbti,
    reader_zodiac=user_zodiac,
    reader_level=user_level,
    emotion=emotion_cn,
    poster_id=poster_id,
    is_ai_generated=st.session_state.get("_latest_is_ai", False),
)

# 预览 (缩小版)
preview_html = render_poster_preview_html(
    book_title=ref_data.get("book_title", "未命名"),
    author=ref_data.get("author", ""),
    chapter="",
    text=ref_data.get("excerpt_text", ""),
    reader_mbti=user_mbti,
    reader_zodiac=user_zodiac,
    reader_level=user_level,
    emotion=emotion_cn,
    poster_id=poster_id,
    is_ai_generated=st.session_state.get("_latest_is_ai", False),
)

st.markdown('<div class="poster-card">', unsafe_allow_html=True)
st.html(f'<div class="poster-preview">{preview_html}</div>')
st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  6. 月度配额 + 付费墙 (mock)
# ══════════════════════════════════════════════════════════════
if "monthly_poster_count" not in st.session_state:
    st.session_state.monthly_poster_count = 0

# 月度计数 (简单版, 不严格)
FREE_QUOTA = 5
used = st.session_state.monthly_poster_count
remaining = max(0, FREE_QUOTA - used)

if remaining > 0:
    st.markdown(f"### 🪔 本月还能生成 {remaining} 张 (免费)")
    can_generate = True
else:
    st.markdown("### 🪔 本月免费额度已用完")
    st.info(
        f"💡 **付费方案**:\n\n"
        f"- 单张 **9.9 元** (冲动消费, 适合偶尔)\n"
        f"- **199 元/年** 会员 (无限海报 + 离线下载 + 高级 AI)\n\n"
        f"🪔 我在等一个仪式感的你, 不会催, 也不会打扰"
    )
    can_generate = False

# ══════════════════════════════════════════════════════════════
#  7. 下载 / 分享 / 复制 HTML
# ══════════════════════════════════════════════════════════════
st.markdown("### 📤 分享出去")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📥 保存为图片", use_container_width=True, disabled=not can_generate):
        # 试着用 html2image 截图
        png_path = save_poster_to_file(poster_html, f"/tmp/poster_{poster_id}.png")
        if png_path:
            st.success(f"✅ 已保存到 {png_path}")
            with open(png_path, "rb") as f:
                st.download_button(
                    "⬇️ 下载 PNG",
                    f.read(),
                    file_name=f"xindeng_poster_{poster_id}.png",
                    mime="image/png",
                    use_container_width=True,
                )
            st.session_state.monthly_poster_count += 1
        else:
            st.warning("🪔 截图服务暂时不可用 (需要 Chrome), 你可以复制 HTML 自己截图")

with col2:
    if st.button("📋 复制 HTML", use_container_width=True):
        # 用 st.html 内嵌的 HTML, 用户可以右键 → 另存为 / 截图
        st.info("🪔 海报已生成 — 下方 HTML 容器内右键 → 另存为 / 截图")

with col3:
    if st.button("🔄 换一张", use_container_width=True):
        # 重新生成 poster_id
        st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════
#  8. 完整 HTML 渲染区 (用户可截图)
# ══════════════════════════════════════════════════════════════
st.markdown("### 🎨 完整海报 (可截图)")
st.caption("右键 → 截图 / 复制, 或长按手机 → 添加到相册")

# 包裹在白底容器, 让用户知道这是要"截图保存"
st.html(f"""
<div style="background: #f4ede0; padding: 2rem; border-radius: 12px; display: flex; justify-content: center;">
{poster_html}
</div>
""")

# ══════════════════════════════════════════════════════════════
#  9. 海报数据存档 (供心灯周报用)
# ══════════════════════════════════════════════════════════════
if "posters" not in st.session_state:
    st.session_state.posters = []

st.session_state.posters.append({
    "poster_id": poster_id,
    "book_title": ref_data.get("book_title", ""),
    "author": ref_data.get("author", ""),
    "text": ref_data.get("excerpt_text", ""),
    "emotion": emotion_cn,
    "ts": st.session_state.get("_xindeng_persisted_refs", [{}])[-1].get("timestamp", ""),
    "reader_mbti": user_mbti,
    "reader_zodiac": user_zodiac,
    "reader_level": user_level,
})

# localStorage 同步
try:
    import json as _json
    snap = st.session_state.posters[-1]
    st.html(f"""
<script>
(function() {{
    try {{
        var existing = JSON.parse(localStorage.getItem('xindeng_posters') || '[]');
        existing.push({repr(snap)});
        localStorage.setItem('xindeng_posters', JSON.stringify(existing));
    }} catch(e) {{}}
}})();
</script>
""")
except Exception:
    pass

# 底部链接
st.markdown("---")
st.markdown("### 🪔 下一步")
col_a, col_b = st.columns(2)
with col_a:
    st.page_link("pages/2_resonance.py", label="去心动林看看", icon="🌲")
with col_b:
    st.page_link("pages/3_archive.py", label="回我的摘录", icon="📚")
