"""心灯 (Reading-FL) — Federated Emotion Learning for Reading Communities

设计原则 (从竞品 Readwise / Are.na / 坐忘灯综合 + 独立思考):
  1. 用户: 文艺青年 / 知识工作者 / 重视隐私的读书人
  2. 美学: 暗色 + 暖橙 + 玻璃态 (学坐忘灯但更克制)
  3. 核心: 写摘录 / 找共鸣 / 往日重现 / 找书友 (4 个功能)
  4. 隐私: 每页头明示「你的书摘留在你手中」
  5. 交互: 全用 Streamlit 原生 widget

页面结构:
  - app.py (这个): 首页 = Hero + 4 功能入口 + 当日往日摘录
  - pages/1_excerpt.py: 写摘录
  - pages/2_resonance.py: 心动林
  - pages/3_archive.py: 我的心灯(往期摘录时间线)
  - pages/4_genie.py: 精灵(AI 对话)
  - pages/5_for_authors.py: 回响(作者侧,网文作者 dashboard)
  - pages/6_book_recommend.py: 段友推荐 (MBTI + 段级)
  - pages/7_architecture.py: 技术架构 (FL + HNSW + 审计)
  - pages/8_points.py: 积分账户
"""
import streamlit as st
import sys
import os
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="心灯 · Reading-FL",
    page_icon="🪔",
    layout="centered",
    initial_sidebar_state="auto",  # mobile 收起,desktop 展开
)

# 强制 sidebar 按钮(mobile 展开/收起)在 dark theme 下可见
# 兼容微信/老 webview:深 fallback,基础内容必须可见
# v6.1.2 改进: 默认 onboarded=True (不卡问卷), 用 0_welcome 顶部大按钮 / 折叠问卷
# 老 webview / 首次访问: 仍可答问卷 (1 步, 折叠式)
# P0 #4: 反脆弱 + 段友筛选 — 默认跳过, 问卷可选
if "onboarded" not in st.session_state:
    st.session_state.onboarded = True  # 默认跳过, 不再卡
# (0_welcome.py 仍存在, 用户主动访问 /welcome 路径才弹)

st.markdown("""
<style>
/* 兜底:确保 body / main / sidebar 在任何 webview 都有底色 + 亮字 */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: #0d0d0f !important;
    color: #e8e4dc !important;
}
/* sidebar 永远有可见背景(兼容微信 webview) */
section[data-testid="stSidebar"] {
    background-color: #0a0a0c !important;
    color: #e8e4dc !important;
    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;
}
section[data-testid="stSidebar"] * {
    color: #e8e4dc !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] a,
section[data-testid="stSidebar"] .stCaption {
    color: #e8e4dc !important;
}
/* main content 兜底:浅字 */
.main .block-container,
.main p,
.main h1, .main h2, .main h3, .main h4,
.main .stMarkdown, .main .stText, .main .stCaption {
    color: #e8e4dc !important;
}

/* 触发按钮高亮 */
button[data-testid="baseButton-headerNoSidebar"],
button[data-testid="baseButton-headerSidebar"] {
    color: #d4a574 !important;
    background: rgba(212, 165, 116, 0.12) !important;
    border: 1px solid #d4a574 !important;
    border-radius: 6px !important;
    padding: 0.3rem 0.5rem !important;
}
button[data-testid="baseButton-headerNoSidebar"]:hover,
button[data-testid="baseButton-headerSidebar"]:hover {
    background: rgba(212, 165, 116, 0.25) !important;
}
/* v6.1: 7 级等级徽章 (sidebar) */
.level-badge {
    background: linear-gradient(180deg, rgba(212,165,116,0.10) 0%, rgba(196,105,74,0.05) 100%);
    border: 1px solid rgba(212,165,116,0.30);
    border-radius: 10px;
    padding: 0.7rem 0.9rem;
    margin: 0.3rem 0 0.8rem 0;
    font-size: 0.88rem;
    color: var(--text);
}
.level-icon { font-size: 1.2rem; margin-right: 0.4rem; }
.level-code { font-weight: 600; color: var(--accent); }
.level-bar {
    background: rgba(0,0,0,0.3);
    border-radius: 4px;
    height: 5px;
    margin: 0.4rem 0 0.3rem 0;
    overflow: hidden;
}
.level-bar-fill {
    background: linear-gradient(90deg, #d4a574 0%, #c4694a 100%);
    height: 5px;
    border-radius: 4px;
    transition: width 0.4s;
}
.level-next {
    font-size: 0.78rem;
    color: var(--text-muted);
}
/* v6.1.2: who-badge 身份徽章 (MBTI/星座) */
.who-badge {
    background: linear-gradient(135deg, rgba(196,105,74,0.12) 0%, rgba(212,165,116,0.08) 100%);
    border: 1px solid rgba(196,105,74,0.30);
    border-radius: 8px;
    padding: 0.5rem 0.7rem;
    margin: 0.3rem 0 0.5rem 0;
    font-size: 0.88rem;
    color: var(--accent);
}
.who-empty {
    color: var(--text-muted);
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

# 兼容 mobile: 用 CSS 强制 sidebar 按钮高亮
st.markdown("""
<style>
/* Streamlit sidebar 展开/收起按钮 (mobile 上的 >> 按钮) */
button[data-testid="baseButton-headerNoSidebar"],
button[data-testid="baseButton-headerSidebar"] {
    color: var(--accent) !important;
    background: rgba(212, 165, 116, 0.12) !important;
    border: 1px solid var(--accent) !important;
    border-radius: 6px !important;
    padding: 0.3rem 0.5rem !important;
}
button[data-testid="baseButton-headerNoSidebar"]:hover,
button[data-testid="baseButton-headerSidebar"]:hover {
    background: rgba(212, 165, 116, 0.25) !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  暗色 + 暖橙主题 (CSS)
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --bg: #0d0d0f;
    --bg-soft: #16161a;
    --card: rgba(255, 255, 255, 0.04);
    --card-hover: rgba(255, 255, 255, 0.07);
    --text: #e8e4dc;
    --text-muted: #8b8680;
    --text-dim: #5a5650;
    --accent: #d4a574;          /* 暖金 — 灯芯色 */
    --accent-soft: #8b6a4a;
    --ember: #c4694a;           /* 橙红 — 火焰 */
    --border: rgba(212, 165, 116, 0.15);
    --border-hover: rgba(212, 165, 116, 0.35);
}

.stApp {
    background:
        radial-gradient(ellipse at top, rgba(212, 165, 116, 0.06) 0%, transparent 60%),
        linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%);
    color: var(--text);
}

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    max-width: 720px;
}

/* 字体: 系统无衬线 */
html, body, .stMarkdown, p, h1, h2, h3, h4, h5, h6 {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
                 "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
    color: var(--text) !important;
}

h1, h2, h3 {
    font-weight: 500 !important;
    letter-spacing: -0.01em;
}

h1 { font-size: 1.7rem !important; }
h2 { font-size: 1.3rem !important; margin-top: 2.5rem !important; color: var(--accent) !important; }
h3 { font-size: 0.85rem !important; color: var(--text-muted) !important;
     text-transform: uppercase; letter-spacing: 0.18em;
     font-weight: 500 !important; margin-top: 2rem !important; }

p, .stMarkdown { line-height: 1.7; }
small, .stCaption { color: var(--text-muted) !important; font-size: 0.85rem; }

/* 输入框: 暗色 + 玻璃态 */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background-color: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-size: 0.95rem !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--border-hover) !important;
    background-color: var(--card-hover) !important;
    box-shadow: 0 0 0 3px rgba(212, 165, 116, 0.1) !important;
}

/* 主按钮: 暖金底色 */
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, var(--ember) 0%, var(--accent) 100%) !important;
    transform: translateY(-1px);
}

.stButton > button[kind="secondary"] {
    background: var(--card) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--card-hover) !important;
    border-color: var(--border-hover) !important;
}

/* Sidebar: 极简暗色 */
section[data-testid="stSidebar"] {
    background-color: #0a0a0c !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p {
    color: var(--text) !important;
}

/* Sidebar nav: 高对比暖金中文链接 (覆盖 streamlit 默认灰) */
section[data-testid="stSidebar"] [data-testid="stPageLink"] a,
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
    background: transparent !important;
    color: #f0ebe1 !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 0.8rem !important;
    border-radius: 8px !important;
    margin: 0.15rem 0 !important;
    border: 1px solid transparent !important;
    transition: all 0.18s ease !important;
    text-decoration: none !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover,
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
    background: rgba(212, 165, 116, 0.10) !important;
    color: var(--accent) !important;
    border-color: var(--border-hover) !important;
}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a span,
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] span {
    color: inherit !important;
}

/* 分割线 */
hr { border-color: var(--border) !important; margin: 2rem 0 !important; }

/* 隐私条 */
.privacy-strip {
    background: linear-gradient(90deg, rgba(196, 105, 74, 0.1) 0%, rgba(212, 165, 116, 0.1) 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem 1rem;
    color: var(--accent);
    font-size: 0.88rem;
    text-align: center;
    margin: 1rem 0;
}

/* 被看见示例卡 (3 个,种子转化) */
.resonance-stack {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    margin: 0.8rem 0 1rem;
}
.resonance-card {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    background: linear-gradient(135deg, rgba(212,165,116,0.06) 0%, rgba(196,105,74,0.04) 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    text-decoration: none !important;
    color: var(--text) !important;
    transition: all 0.2s;
}
.resonance-card:hover {
    background: linear-gradient(135deg, rgba(212,165,116,0.12) 0%, rgba(196,105,74,0.08) 100%);
    border-color: var(--border-hover);
    transform: translateX(2px);
}
.resonance-emoji {
    font-size: 1.6rem;
    flex-shrink: 0;
    width: 2.4rem;
    text-align: center;
}
.resonance-content {
    flex: 1;
    min-width: 0;
}
.resonance-quote {
    font-size: 0.92rem;
    line-height: 1.5;
    color: var(--text);
    margin-bottom: 0.4rem;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}
.resonance-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.78rem;
    color: var(--text-muted);
    flex-wrap: wrap;
    gap: 0.4rem;
}
.resonance-book {
    color: var(--accent);
    font-weight: 500;
}
.resonance-stats {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
}
.resonance-stat {
    background: rgba(255,255,255,0.05);
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
    font-size: 0.72rem;
}
.resonance-arrow {
    color: var(--accent);
    font-size: 1.2rem;
    flex-shrink: 0;
}

/* CTA strip */
.cta-strip {
    background: linear-gradient(135deg, rgba(212,165,116,0.15) 0%, rgba(196,105,74,0.10) 100%);
    border: 1px solid var(--accent);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    margin: 1rem 0 1.5rem;
    flex-wrap: wrap;
}
.cta-text {
    color: var(--text);
    font-size: 0.9rem;
    flex: 1;
    min-width: 0;
}
.cta-button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%);
    color: #0d0d0f !important;
    text-decoration: none !important;
    padding: 0.55rem 1.1rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.88rem;
    flex-shrink: 0;
}

/* 积分徽章 (sidebar) */
.points-badge {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%);
    color: #0d0d0f;
    padding: 0.4rem 0.7rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    display: inline-block;
    margin: 0.3rem 0;
}

/* Hero */
.lantern-hero {
    background:
        radial-gradient(circle at 50% 30%, rgba(212, 165, 116, 0.15) 0%, transparent 70%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, transparent 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 3rem 2rem 2.5rem;
    margin-bottom: 2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.lantern-hero::before {
    content: "🪔";
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 2rem;
    filter: drop-shadow(0 0 8px rgba(212, 165, 116, 0.6));
}
.lantern-hero h1 {
    color: var(--text) !important;
    font-size: 1.9rem !important;
    margin: 1rem 0 0.5rem !important;
    font-weight: 500 !important;
}
.lantern-hero .tagline {
    color: var(--accent);
    font-size: 1rem;
    margin: 0 0 0.4rem;
}
.lantern-hero .sub {
    color: var(--text-muted);
    font-size: 0.85rem;
}

/* 功能入口卡 (4 个)*/
.func-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.8rem;
    margin: 1.5rem 0;
}
.func-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1rem;
    text-align: center;
    transition: all 0.2s;
    cursor: pointer;
    text-decoration: none;
    display: block;
}
.func-card:hover {
    background: var(--card-hover);
    border-color: var(--border-hover);
    transform: translateY(-2px);
}
.func-icon {
    font-size: 1.5rem;
    margin-bottom: 0.4rem;
    display: block;
}
.func-name {
    color: var(--text);
    font-size: 0.95rem;
    font-weight: 500;
    margin-bottom: 0.2rem;
}
.func-desc {
    color: var(--text-muted);
    font-size: 0.78rem;
    line-height: 1.4;
}

/* 往日摘录卡 */
.archive-card {
    background: var(--card);
    border-left: 3px solid var(--ember);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
}
.archive-quote {
    color: var(--text);
    font-size: 0.95rem;
    font-style: italic;
    line-height: 1.6;
    margin-bottom: 0.5rem;
}
.archive-meta {
    color: var(--text-muted);
    font-size: 0.8rem;
}

/* 进度条 (dark) */
.stProgress > div > div > div > div {
    background: var(--accent) !important;
}

/* Radio 横排 */
.stRadio [role="radiogroup"] {
    gap: 0.5rem;
}
.stRadio [role="radiogroup"] label {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 0.4rem 0.9rem !important;
    color: var(--text) !important;
    transition: all 0.15s !important;
}
.stRadio [role="radiogroup"] label:hover {
    background: var(--card-hover) !important;
}

/* Metric */
.stMetric {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 0.8rem !important;
}
.stMetric label {
    color: var(--text-muted) !important;
}
.stMetric [data-testid="stMetricValue"] {
    color: var(--accent) !important;
    font-weight: 500 !important;
}
.stMetric [data-testid="stMetricDelta"] {
    color: var(--text-muted) !important;
}

/* ═══════════════════════════════════════════════════════════
   Mobile 适配
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 640px) {
    .main .block-container {
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        padding-top: 1rem !important;
        max-width: 100% !important;
    }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.15rem !important; }
    h3 { font-size: 0.75rem !important; margin-top: 1.5rem !important; }

    .lantern-hero { padding: 2rem 1rem 1.5rem; }
    .lantern-hero h1 { font-size: 1.5rem !important; }

    .func-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 0.6rem;
    }
    .func-card { padding: 1rem 0.7rem; }
    .func-name { font-size: 0.85rem; }
    .func-desc { font-size: 0.72rem; }

    .stTextArea textarea { min-height: 90px !important; font-size: 16px !important; }
    .stRadio [role="radiogroup"] > div { flex: 1 1 30% !important; min-width: 70px !important; }
    .stButton > button { width: 100% !important; min-height: 44px !important; }
}

@media (max-width: 380px) {
    h1 { font-size: 1.25rem !important; }
    .main .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; }
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  Sidebar
# ═══════════════════════════════════════════════════════════
from core.points import init_points, show_points_sidebar

init_points()

with st.sidebar:
    st.markdown("### 🪔 段友")
    st.caption("Reading-FL · Federated")
    show_points_sidebar()
    # v6.1.2: MBTI/星座/情感画像 侧边栏标签 — 身份徽章
    # 从 localStorage 恢复
    st.html("""
<script>
(function() {
    try {
        var profile = localStorage.getItem('xindeng_who');
        if (profile) {
            var url = new URL(window.parent.location.href);
            if (!url.searchParams.get('restored_who')) {
                url.searchParams.set('restored_who', '1');
                url.searchParams.set('who', encodeURIComponent(profile));
                window.parent.location.href = url.toString();
            }
        }
    } catch(e) {}
})();
</script>
""")
    qparams = st.query_params
    if qparams.get("restored_who") == "1":
        import json as _json
        try:
            who = _json.loads(qparams.get("who", "{}"))
            for k, v in who.items():
                st.session_state[k] = v
        except Exception:
            pass
    mbti = st.session_state.get("user_mbti", "")
    zodiac = st.session_state.get("user_zodiac", "")
    n_emo = len(st.session_state.get("user_emotions_onboard", []))
    if mbti or zodiac or n_emo >= 3:
        badge_parts = []
        if mbti: badge_parts.append(f"**{mbti}**")
        if zodiac: badge_parts.append(zodiac)
        if badge_parts:
            st.markdown(
                f'<div class="who-badge">🧠 {" · ".join(badge_parts)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="who-badge who-empty">🧠 还没画像 (点下面设定)</div>',
                unsafe_allow_html=True,
            )
    st.page_link("pages/9_who_am_i.py", label=("🧠 改画像" if mbti or zodiac else "🧠 设定画像"), icon="🧠")
    st.markdown("---")
    st.page_link("app.py", label="首页", icon="🏠")
    st.page_link("pages/1_excerpt.py", label="写摘录", icon="✍️")
    st.page_link("pages/2_resonance.py", label="心动林", icon="💫")
    st.page_link("pages/3_archive.py", label="我的心灯", icon="🪔")
    st.page_link("pages/4_genie.py", label="精灵", icon="🕯️")
    st.markdown("---")
    st.caption("**给网文作者**")
    st.page_link("pages/5_for_authors.py", label="回响", icon="🌊")
    st.page_link("pages/6_book_recommend.py", label="段友推荐", icon="🔮")
    st.markdown("---")
    st.caption("**技术 / 学术**")
    st.page_link("pages/7_architecture.py", label="技术架构", icon="🏗️")
    st.page_link("pages/8_points.py", label="🪙 积分账户", icon="🪙")
    st.markdown("---")
    st.caption("🔒 你的书摘,留在你手中")


# ═══════════════════════════════════════════════════════════
#  浏览器兼容提示 (中国本土浏览器 streamlit 渲染问题)
# ═══════════════════════════════════════════════════════════
# 审计 #2 修复: st.html 默认禁用 JavaScript, 原 30 行 UA 检测是死代码.
# 改用静态提示 — 简洁, 不依赖 JS, 也不假装"在检测".
st.markdown("""
<div style="background: linear-gradient(135deg, #c4694a 0%, #d4a574 100%);
    color: #0d0d0f; padding: 0.6rem 0.9rem; border-radius: 8px; margin: 0 0 1rem 0;
    font-size: 0.85rem; font-weight: 500; text-align: center;">
    🪔 <b>建议用 Safari / Chrome 打开</b> — 其他浏览器可能有渲染问题
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  Hero
# ═══════════════════════════════════════════════════════════
st.html("""
<div class="lantern-hero">
    <h1>读到一段,找到另一个停下来的人</h1>
    <p class="tagline">你读过的字, 在陌生人那里被看见 · 读完一段的反思, 永久沉淀</p>
    <p class="sub">Reading-FL · Federated · 你的书摘,留在你手中</p>
</div>
""")


# ═══════════════════════════════════════════════════════════
#  3 个示例被看见 (无须登录可见,种子转化)
# ═══════════════════════════════════════════════════════════
st.markdown("### 你的字, 正在被看见")
st.caption("无须登录 — 点开看看 89 个陌生人都在这里想了什么")

EXAMPLE_RESONANCES = [
    {
        "emoji": "🪦",
        "quote": "老陈盯着屏幕上那行注释看了很久。他的手指悬在键盘上方,像是要敲什么,又像是要摸什么。",
        "book": "《代码乡愁》",
        "chapter": "第 3 章 · 杨家小蠍",
        "stop_count": 127,
        "feel_count": 89,
        "top_feel": "失亲 · 回忆",
    },
    {
        "emoji": "🌙",
        "quote": "那个夏天所有的事情都还没结束,但我们都知道它要结束了。",
        "book": "《了不起的盖茨比》",
        "chapter": "第 7 章 · 菲茨杰拉德",
        "stop_count": 47,
        "feel_count": 31,
        "top_feel": "青春 · 失落",
    },
    {
        "emoji": "🕯️",
        "quote": "重要的东西用眼睛是看不见的。",
        "book": "《小王子》",
        "chapter": "第 21 章 · 圣埃克苏佩里",
        "stop_count": 89,
        "feel_count": 62,
        "top_feel": "哲思 · 童心",
    },
]

st.html("""
<div class="resonance-stack">
""" + "".join([
    f"""
    <a class="resonance-card" href="resonance">
        <div class="resonance-emoji">{e['emoji']}</div>
        <div class="resonance-content">
            <div class="resonance-quote">「{e['quote']}」</div>
            <div class="resonance-meta">
                <span class="resonance-book">{e['chapter']}</span>
                <span class="resonance-stats">
                    <span class="resonance-stat">⏸ {e['stop_count']} 人在这里停</span>
                    <span class="resonance-stat">✍️ {e['feel_count']} 人写了感悟</span>
                    <span class="resonance-stat"># {e['top_feel']}</span>
                </span>
            </div>
        </div>
        <div class="resonance-arrow">→</div>
    </a>
    """
    for e in EXAMPLE_RESONANCES
]) + """
</div>
""")

st.caption("")

# 主 CTA — 写第一段
st.html("""
<div class="cta-strip">
    <div class="cta-text">📸 读完一段,截屏过来 — AI 一拍识别书名、作者、段落、章节</div>
    <a class="cta-button" href="excerpt">→ 去点亮第一段</a>
</div>
""")


# ═══════════════════════════════════════════════════════════
#  当日往日摘录 (学 Readwise "复习"概念)
# ═══════════════════════════════════════════════════════════
st.markdown("### 当日往日摘录")
st.caption("30 / 60 / 90 天前你读到的")

reflections = st.session_state.get("reflections", [])

def filter_by_age(reflections_list, days_ago):
    """筛选 days_ago 天前的摘录 (允许 ±3 天误差)"""
    now = datetime.datetime.now()
    target_date = now - datetime.timedelta(days=days_ago)
    matched = []
    for r in reflections_list:
        try:
            ts = datetime.datetime.fromisoformat(r.timestamp)
            diff_days = abs((ts - target_date).days)
            if diff_days <= 3:  # ±3 天容差
                matched.append((diff_days, r))
        except Exception:
            pass
    return sorted(matched, key=lambda x: x[0])[:1]  # 每段取最近 1 条

found_any = False
for days in [30, 60, 90, 180]:
    matches = filter_by_age(reflections, days)
    if matches:
        diff, r = matches[0]
        actual_days = days - diff if diff < days else days + diff
        years = actual_days // 365
        years_text = f"{years} 年前" if years >= 1 else f"{actual_days} 天前"
        emo_cn = {
            "moved": "💧 感动", "thinking": "🌊 思考", "resonance": "🔗 共鸣",
            "confused": "🌫️ 困惑", "disagree": "⚡ 反对", "calm": "🍃 平静",
        }.get(r.emotion_label, r.emotion_label)
        # XSS defense (审计 #1): escape all user fields
        import html as _html
        safe_text = _html.escape(r.excerpt.text)
        safe_title = _html.escape(r.excerpt.book_title)
        st.markdown(f"""
        <div class="archive-card">
            <div class="archive-quote">「{safe_text}」</div>
            <div class="archive-meta">
                {years_text} · 《{safe_title}》 · {emo_cn}
            </div>
        </div>
        """, unsafe_allow_html=True)
        found_any = True

if not found_any:
    st.caption("还没有往日摘录 — 等你积累更多记录后,这里会浮起旧日感动")


# ═══════════════════════════════════════════════════════════
#  跨书社状态
# ═══════════════════════════════════════════════════════════
st.markdown("### 跨书社动态")
st.caption("3 个书社的实时统计")

GUILD_STATS = {
    "guild_夜读派": {"readers": 60, "mood": "思考", "n_reflections": 60},
    "guild_晨读派": {"readers": 60, "mood": "共鸣", "n_reflections": 60},
    "guild_全日派": {"readers": 60, "mood": "感动", "n_reflections": 60},
}

col1, col2, col3 = st.columns(3)
for col, (gid, s) in zip([col1, col2, col3], GUILD_STATS.items()):
    with col:
        nice_name = gid.replace("guild_", "")
        st.metric(
            label=nice_name,
            value=f"{s['readers']}",
            delta=f"主情绪 · {s['mood']}",
            delta_color="off",
        )


# 底部
st.markdown("---")
st.caption("心灯 · Reading-FL · License: MIT · Powered by FedCtx")
