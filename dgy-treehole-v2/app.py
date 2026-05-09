"""大观园树洞 v2 — 主入口

红楼梦主题心理疗愈平台
Streamlit + MiniMax API + 联邦学习
"""

import streamlit as st
from core.config import SCENES, MOCK_MODE
from core.db import init_db

# ── 初始化数据库（建表，幂等）──
init_db()

# ── 页面配置 ──
st.set_page_config(
    page_title="大观园树洞",
    page_icon="🌸",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── 自定义 CSS（与原版 index.html 完全对齐）──
st.markdown("""<style>
/* 隐藏 Streamlit 默认元素 */
#MainMenu, footer, header {visibility: hidden}
.block-container {padding-top: 0.5rem; padding-bottom: 2rem; max-width: 520px}

/* 全局字体 */
.stApp {font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', serif}

/* 卡片样式 */
.card {
    background: #f5f0e8;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.8rem 0;
    border: 1px solid #e8dfd0;
}
.card-dark {
    background: #2c1810;
    color: #f5f0e8;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.8rem 0;
}

/* 场景卡片 */
.scene-card {
    background: linear-gradient(135deg, #f5f0e8, #e8dfd0);
    border-radius: 16px;
    padding: 1.5rem;
    margin: 0.5rem 0;
    border: 1px solid #d4c5a9;
    cursor: pointer;
    transition: all 0.3s;
}
.scene-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(44,24,16,0.12);
    border-color: #b8860b;
}

/* 聊天气泡 */
.chat-ai {
    background: #e8dfd0;
    border-radius: 16px 16px 16px 4px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    max-width: 85%;
}
.chat-user {
    background: #2c1810;
    color: #f5f0e8;
    border-radius: 16px 16px 4px 16px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    max-width: 85%;
    margin-left: auto;
}

/* 标签 */
.tag {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    background: rgba(184,134,11,0.1);
    color: #b8860b;
    border-radius: 99px;
    font-size: 0.8rem;
    margin: 0.15rem;
}

/* 模式指示器 */
.mock-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    background: rgba(192,57,43,0.1);
    color: #c0392b;
    border-radius: 99px;
    font-size: 0.7rem;
}

/* Hero 头部（对齐原版 .hero） */
.hero {
    background: linear-gradient(135deg, #2c1810, #4a2c1a 50%, #3d1f0e);
    padding: 2.5rem 1.5rem 2rem;
    color: #f5f0e8;
    text-align: center;
    position: relative;
    overflow: hidden;
    border-radius: 0 0 16px 16px;
}
.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 30% 50%, rgba(184,134,11,0.12), transparent 60%);
    pointer-events: none;
}
.hero h1 {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.4rem;
    position: relative;
}
.hero .sub {
    opacity: 0.7;
    font-size: 0.85rem;
    margin: 0.4rem 0 0.8rem;
    position: relative;
}
.hero .motto {
    font-size: 0.8rem;
    opacity: 0.5;
    font-style: italic;
    position: relative;
}

/* 安全徽章（对齐原版 .badge） */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.8rem;
    background: rgba(45,106,79,0.1);
    color: #2d6a4f;
    border-radius: 99px;
    font-size: 0.75rem;
}

/* 结果卡片（对齐原版 .result-type/.result-scene/.result-reason/.result-quote） */
.result-type {
    font-size: 2.5rem;
    font-weight: 800;
    color: #c0392b;
    text-align: center;
    letter-spacing: 0.3rem;
    margin: 0.5rem 0;
}
.result-desc {
    text-align: center;
    font-size: 0.9rem;
    color: #8b7355;
    margin-bottom: 0.8rem;
}
.result-scene {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.8rem;
    background: #fff;
    border-radius: 12px;
    border: 1px solid #e8dfd0;
    margin-bottom: 0.8rem;
}
.result-scene .icon {
    font-size: 2rem;
    width: 48px;
    text-align: center;
}
.result-scene .name {
    font-weight: 600;
    font-size: 0.95rem;
    color: #2c1810;
}
.result-scene .info {
    font-size: 0.8rem;
    color: #8b7355;
    margin-top: 0.1rem;
}
.result-reason {
    background: #f5f0e8;
    border-radius: 12px;
    padding: 0.8rem;
    margin: 0.8rem 0;
    font-size: 0.85rem;
    line-height: 1.7;
    color: #2c1810;
}
.result-quote {
    text-align: center;
    font-style: italic;
    color: #8b7355;
    font-size: 0.85rem;
    padding: 0.8rem;
    border-left: 3px solid #b8860b;
    margin: 0.8rem 0;
}

/* 星座按钮（对齐原版 .zodiac-btn） */
.zodiac-btn {
    background: #fff;
    border: 1px solid #e8dfd0;
    border-radius: 12px;
    padding: 0.6rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}
.zodiac-btn:hover {
    border-color: #b8860b;
    box-shadow: 0 4px 12px rgba(44,24,16,0.08);
}

/* 星盘卡片（对齐原版 .chart-planet） */
.chart-planet {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    background: #fff;
    border-radius: 10px;
    margin: 0.3rem 0;
    border: 1px solid #e8dfd0;
}
.chart-planet .p-icon {
    font-size: 1.3rem;
    width: 32px;
    text-align: center;
    flex-shrink: 0;
}
.chart-planet .p-info { flex: 1; }
.chart-planet .p-name { font-size: 0.78rem; font-weight: 600; }
.chart-planet .p-sign { font-size: 0.7rem; color: #8b7355; }
.chart-planet .p-desc { font-size: 0.72rem; color: #2c1810; margin-top: 0.1rem; line-height: 1.5; }

/* 星盘总结（对齐原版 .chart-summary） */
.chart-summary {
    background: linear-gradient(135deg, #2c1810, #4a2c1a);
    color: #f5f0e8;
    border-radius: 12px;
    padding: 1rem;
    margin: 0.8rem 0;
    text-align: center;
}

/* 元素标签（对齐原版 .elem-label） */
.elem-label {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.3rem 0;
    margin-top: 0.5rem;
}

/* 动画 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeIn 0.5s ease-out; }
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  Hero（对齐原版首页）
# ═══════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <h1>大观园树洞</h1>
    <p class="sub">在这里，你可以放下所有防备</p>
    <p class="motto">"满纸荒唐言，一把辛酸泪。"</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="text-align:center"><span class="badge">🔒 匿名安全 · 不留痕迹 · 随时离开</span></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  MBTI / 星座入口（对齐原版首页按钮）
# ═══════════════════════════════════════════════════════════
st.markdown("""
<div style="padding: 0.8rem;">
    <p style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.5rem;">✨ 找到属于你的院落</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("🔮 MBTI测试", type="primary", use_container_width=True):
        st.switch_page("pages/5_mbti.py")
with col2:
    if st.button("⭐ 星座指引", use_container_width=True):
        st.switch_page("pages/7_zodiac.py")

# ═══════════════════════════════════════════════════════════
#  导航（7个功能入口）
# ═══════════════════════════════════════════════════════════
nav_cols = st.columns(7)
nav_items = [
    ("💬", "倾诉"),
    ("🌳", "树洞"),
    ("🌸", "共鸣"),
    ("🎵", "音乐"),
    ("🔮", "MBTI"),
    ("⭐", "星座"),
    ("📊", "洞察"),
]
nav_pages = [
    "1_chat", "2_treehole", "3_resonance",
    "4_music", "5_mbti", "7_zodiac", "6_insight",
]
for i, (icon, label) in enumerate(nav_items):
    with nav_cols[i]:
        if st.button(f"{icon}\n{label}", key=f"nav_{i}", use_container_width=True):
            st.switch_page(f"pages/{nav_pages[i]}.py")

# ═══════════════════════════════════════════════════════════
#  6大场景（对齐原版，展示 mood + style）
# ═══════════════════════════════════════════════════════════
st.markdown("### 🏯 选择你的场景")

for i in range(0, len(SCENES), 2):
    cols = st.columns(2)
    for j, scene in enumerate(SCENES[i:i+2]):
        with cols[j]:
            st.markdown(f"""
<div class="scene-card">
    <div style="font-size: 1.8rem; margin-bottom: 0.3rem;">{scene['icon']}</div>
    <div style="font-weight: 600; font-size: 1rem; color: #2c1810;">{scene['name']}</div>
    <div style="font-size: 0.8rem; color: #8b7355; margin-top: 0.2rem;">{scene['desc']}</div>
    <div style="font-size: 0.75rem; color: #b8860b; margin-top: 0.2rem;">{scene['mood']} · {scene['style']}</div>
    <div style="margin-top: 0.5rem;">
        <span class="tag">倾听者：{scene['char']}</span>
        <span class="tag">{scene['theory']}</span>
    </div>
</div>
""", unsafe_allow_html=True)
            if st.button(f"进入{scene['name']} →", key=f"scene_{scene['name']}", use_container_width=True):
                st.session_state.current_scene = scene["name"]
                st.session_state.chat_character = scene["char"]
                st.session_state.chat_history = []
                st.switch_page("pages/1_chat.py")

# ── 底部信息 ──
st.markdown("""
<div style="text-align:center; padding: 1rem 0; color: #8b7355; font-size: 0.75rem;">
    🌸 在这里，你不需要假装坚强 🌸<br>
    <span style="color: #b8860b;">联邦学习保护你的隐私 · 你的话只属于你</span>
</div>
""", unsafe_allow_html=True)

if MOCK_MODE:
    st.markdown('<div style="text-align:center"><span class="mock-badge">🎭 演示模式（未配置 GLM_API_KEY）</span></div>', unsafe_allow_html=True)
