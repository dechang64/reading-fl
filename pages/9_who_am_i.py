"""我是谁 — 16 MBTI × 12 星座 × 8 情感 画像

v6.1.2 改进:
- 16 MBTI (4 字母组合)
- 12 星座
- 8 情感 (跟 v6.1 PRD 一致)
- localStorage 持久化
- 选完 → 跳回主页, 侧边栏显示 "🧠 INFJ ♍"
"""
import streamlit as st
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="我是谁 · 心灯",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="auto",
)

# === 风格 (跟其他 pages 一致) ===
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
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important; border: none !important; border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important; font-weight: 600 !important;
}
.stButton > button:disabled {
    background: var(--card) !important; color: var(--text-muted) !important;
}
.option-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.4rem;
    margin: 0.5rem 0;
}
.option-chip {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.5rem 0.3rem;
    text-align: center;
    font-size: 0.82rem;
    color: var(--text);
    cursor: pointer;
}
.option-chip.active {
    background: linear-gradient(135deg, rgba(212,165,116,0.25) 0%, rgba(196,105,74,0.15) 100%);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 600;
}
@media (max-width: 640px) {
    .main .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    h1 { font-size: 1.4rem !important; }
    .stButton > button { width: 100% !important; min-height: 44px !important; }
    .option-chip { font-size: 0.72rem; padding: 0.3rem 0.2rem; }
}
</style>
""", unsafe_allow_html=True)

# === 老 webview fallback ===
st.markdown('<style>\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p, .main h1, .main h2, .main h3,\n.main .stMarkdown, .main .stText, .main .stCaption { color: #e8e4dc !important; }\n</style>', unsafe_allow_html=True)

# === 恢复 (从 localStorage 或 session_state) ===
st.html("""
<script>
(function() {
    try {
        var profile = localStorage.getItem('xindeng_who');
        if (profile) {
            var url = new URL(window.parent.location.href);
            if (!url.searchParams.get('restored')) {
                url.searchParams.set('restored', '1');
                url.searchParams.set('profile', encodeURIComponent(profile));
                window.parent.location.href = url.toString();
            }
        }
    } catch(e) {}
})();
</script>
""")
qparams = st.query_params
if qparams.get("restored") == "1":
    try:
        who = json.loads(qparams.get("profile", "{}"))
        for k, v in who.items():
            st.session_state[k] = v
    except Exception:
        pass

st.page_link("app.py", label="← 回到首页", icon="🏠")

st.markdown("# 🧠 我是谁")
st.caption("画像完整 → 段级推荐 / 心动林 / 精灵 都更懂你")

# === 当前画像 ===
mbti = st.session_state.get("user_mbti", "")
zodiac = st.session_state.get("user_zodiac", "")
emotions = st.session_state.get("user_emotions_onboard", [])

if mbti or zodiac or emotions:
    parts = []
    if mbti: parts.append(f"**MBTI**: {mbti}")
    if zodiac: parts.append(f"**星座**: {zodiac}")
    if emotions: parts.append(f"**情感** ({len(emotions)}): {' '.join(emotions)}")
    st.markdown("### 当前画像")
    for p in parts:
        st.markdown(f"- {p}")

# === MBTI 16 ===
st.markdown("### 1. 你的 MBTI (选 1 个)")
MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]
MBTI_COLS = 4
cols = st.columns(MBTI_COLS)
for i, m in enumerate(MBTI_TYPES):
    with cols[i % MBTI_COLS]:
        is_active = (mbti == m)
        if st.button(m, key=f"mbti_{m}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.user_mbti = m
            st.rerun()

# === 星座 12 ===
st.markdown("### 2. 你的星座 (选 1 个)")
ZODIACS = [
    "♑ 摩羯", "♒ 水瓶", "♓ 双鱼", "♈ 白羊", "♉ 金牛", "♊ 双子",
    "♋ 巨蟹", "♌ 狮子", "♍ 处女", "♎ 天秤", "♏ 天蝎", "♐ 射手",
]
zcols = st.columns(4)
for i, z in enumerate(ZODIACS):
    with zcols[i % 4]:
        is_active = (zodiac == z)
        if st.button(z, key=f"zod_{z}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.user_zodiac = z
            st.rerun()

# === 情感 ≥3 ===
st.markdown("### 3. 哪些词跟你最近的状态贴近? (≥3 个)")
EMOTION_OPTIONS = [
    "💧 感动", "🌊 思考", "🔗 共鸣", "🌫️ 困惑",
    "⚡ 反对", "🍃 平静", "🔥 愤怒", "😢 悲伤",
    "✨ 治愈", "🌱 成长", "🌀 迷茫", "💪 坚定",
]
sel = st.pills(
    "可以多选",
    options=EMOTION_OPTIONS,
    default=emotions if emotions else [],
    selection_mode="multi",
    label_visibility="collapsed",
    key="who_emotions",
)
n_emo = len(sel) if sel else 0
if n_emo > 0 and n_emo < 3:
    st.warning(f"🪔 再选 {3 - n_emo} 个")
elif n_emo >= 3:
    st.caption(f"🪔 已选 {n_emo} 个 — 完美")

# === 保存 ===
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🪔 保存画像", type="primary", use_container_width=True,
                 disabled=not (mbti and zodiac and n_emo >= 3)):
        st.session_state.user_emotions_onboard = list(sel or [])
        st.session_state.user_emotions = list(sel or [])
        # 持久化
        who = {
            "user_mbti": st.session_state.user_mbti,
            "user_zodiac": st.session_state.user_zodiac,
            "user_emotions_onboard": st.session_state.user_emotions_onboard,
            "user_emotions": st.session_state.user_emotions,
        }
        st.html(f"""
<script>
(function() {{
    try {{
        localStorage.setItem('xindeng_who', JSON.stringify({repr(who)}));
    }} catch(e) {{}}
}})();
</script>
""")
        st.success("🪔 画像保存了 — 侧边栏顶部会显示你的身份")
        st.balloons()
        st.switch_page("app.py")

with col2:
    if st.button("清空画像", use_container_width=True):
        for k in ["user_mbti", "user_zodiac", "user_emotions_onboard", "user_emotions"]:
            st.session_state.pop(k, None)
        st.html("""
<script>
(function() { try { localStorage.removeItem('xindeng_who'); } catch(e) {} })();
</script>
""")
        st.rerun()

if not (mbti and zodiac):
    st.caption("🪔 MBTI 和星座都必选, 情感 ≥3 个")
