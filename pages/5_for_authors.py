"""回响 — 你的字, 读者的回响 (段级作者 dashboard)

设计:
- 模拟一个网文作者上传作品后的视角
- 看到 5 维度: 段级共鸣 / 段级情感 / 段级停留 / 跨章节热度 / AI 模拟改稿
- 全部 mock 数据,但视觉冲击力足够让网文作者"心动"
"""
import streamlit as st
import sys
import os
import random
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.points import init_points, add_points

st.set_page_config(page_title="回响 · 作者侧", page_icon="🫀", layout="centered", initial_sidebar_state="auto")

# 共用暗色 CSS (与 app.py 风格一致)
st.markdown("""
<style>
:root { --bg: #0d0d0f; --card: rgba(255,255,255,0.04); --text: #e8e4dc; --text-muted: #8b8680;
        --accent: #d4a574; --ember: #c4694a; --border: rgba(212,165,116,0.15);
        --border-hover: rgba(212,165,116,0.35); }
.stApp { background: linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%); }
.main .block-container { max-width: 720px; padding-top: 1.5rem; }
h1, h2, h3 { color: var(--text) !important; font-weight: 500 !important; }
h1 { font-size: 1.6rem !important; }
h3 { font-size: 0.85rem !important; color: var(--text-muted) !important;
     text-transform: uppercase; letter-spacing: 0.18em; }
p, .stMarkdown { color: var(--text) !important; line-height: 1.7; }
.stCaption { color: var(--text-muted) !important; }
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background-color: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-size: 16px !important;
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="secondary"] {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important;
}

/* 段级热度条 */
.heat-bar {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0.5rem 0;
    font-size: 0.82rem;
}
.heat-label { width: 4.5rem; color: var(--text-muted); flex-shrink: 0; }
.heat-bar-track {
    flex: 1;
    height: 8px;
    background: var(--card);
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid var(--border);
}
.heat-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent) 0%, var(--ember) 100%);
    border-radius: 4px;
}
.heat-value { color: var(--accent); width: 3.5rem; text-align: right; font-weight: 500; }

/* 段级停留 */
.duration-stay {
    background: rgba(212,165,116,0.08);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.2rem 0.5rem;
    font-size: 0.78rem;
    color: var(--accent);
    font-weight: 500;
}
.duration-skip {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px;
    padding: 0.2rem 0.5rem;
    font-size: 0.78rem;
    color: var(--text-muted);
}

/* 感悟气泡 */
.reflection-bubble {
    background: linear-gradient(135deg, rgba(212,165,116,0.10) 0%, rgba(196,105,74,0.06) 100%);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 0.6rem 0.8rem;
    margin: 0.4rem 0;
    color: var(--text);
    font-size: 0.88rem;
    line-height: 1.5;
}
.reflection-author {
    color: var(--text-muted);
    font-size: 0.75rem;
    margin-top: 0.3rem;
}

/* 情感画像 */
.emotion-tag {
    display: inline-block;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.2rem 0.6rem;
    margin: 0.15rem;
    font-size: 0.78rem;
    color: var(--text);
}
.emotion-tag.hot {
    background: linear-gradient(135deg, rgba(212,165,116,0.20) 0%, rgba(196,105,74,0.15) 100%);
    border-color: var(--accent);
    color: var(--accent);
}

/* 模拟器 */
.simulator-box {
    background: var(--card);
    border: 1px dashed var(--border);
    border-radius: 8px;
    padding: 0.8rem;
    margin: 0.5rem 0;
}

/* 跨章热度条 */
.chapter-heat {
    display: flex;
    gap: 0.15rem;
    align-items: end;
    height: 60px;
    margin: 0.8rem 0;
}
.chapter-bar {
    flex: 1;
    background: linear-gradient(180deg, var(--accent) 0%, var(--ember) 100%);
    border-radius: 2px 2px 0 0;
    opacity: 0.85;
    position: relative;
    cursor: pointer;
    transition: opacity 0.2s;
}
.chapter-bar:hover { opacity: 1; }
.chapter-bar[data-hot="true"] {
    background: linear-gradient(180deg, #ff6b4a 0%, #c4694a 100%);
    box-shadow: 0 0 8px rgba(196,105,74,0.6);
}

.author-pain-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    margin: 0.4rem 0;
    color: var(--text);
    font-size: 0.88rem;
}
.author-pain-num {
    color: var(--ember);
    font-weight: 600;
    margin-right: 0.4rem;
}
</style>
""", unsafe_allow_html=True)


# 兼容老 webview:深 fallback CSS
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;\n}\nsection[data-testid="stSidebar"] * {\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] h1,\nsection[data-testid="stSidebar"] h2,\nsection[data-testid="stSidebar"] h3,\nsection[data-testid="stSidebar"] p,\nsection[data-testid="stSidebar"] span,\nsection[data-testid="stSidebar"] a,\nsection[data-testid="stSidebar"] .stCaption {\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p,\n.main h1, .main h2, .main h3, .main h4,\n.main .stMarkdown, .main .stText, .main .stCaption {\n    color: #e8e4dc !important;\n}\n</style>', unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")
st.markdown("# 🌊 回响")
st.caption("给网文作者的「读者心跳」仪表盘 — 不再凭感觉写")

# ═══════════════════════════════════════════════════════════
#  作者痛点共鸣 (转化入口)
# ═══════════════════════════════════════════════════════════
st.markdown("### 网文作者的 5 个孤独")
st.html("""
<div class="author-pain-card"><span class="author-pain-num">1.</span>写完 50 万字,只有 30 个评论,不知道哪里打动了人</div>
<div class="author-pain-card"><span class="author-pain-num">2.</span>段级反馈 = 0 — 平台只给"1000 人收藏",不给"300 人在第 3 章哭了"</div>
<div class="author-pain-card"><span class="author-pain-num">3.</span>写到 30 万字想弃,没人知道你在写什么</div>
<div class="author-pain-card"><span class="author-pain-num">4.</span>不知道下一章往哪写 — 没有"读者情感走向"数据</div>
<div class="author-pain-card"><span class="author-pain-num">5.</span>找不到"赛博朋克 + 中年危机"的写作搭子</div>
""")

st.markdown("---")
st.caption("**回响** 是 Reading-FL 给创作者的 dashboard — 你的字, 读者的回响: 哪段让谁停, 谁哭, 谁想跟你聊。")

# ═══════════════════════════════════════════════════════════
#  模拟作品选择
# ═══════════════════════════════════════════════════════════
st.markdown("### 选一本你的作品(模拟)")

WORK_OPTIONS = {
    "代码乡愁 (杨家小蠍)": {
        "genre": "赛博朋克 + 怀旧",
        "chapters": 30,
        "total_words": 320000,
        "fake_reader_count": 1247,
    },
    "长安的雪 (示例)": {
        "genre": "历史言情",
        "chapters": 50,
        "total_words": 580000,
        "fake_reader_count": 892,
    },
    "白月光诊所 (示例)": {
        "genre": "现代都市 + 玄学",
        "chapters": 24,
        "total_words": 280000,
        "fake_reader_count": 2104,
    },
}

work = st.selectbox(
    "作品(模拟用真实案例:杨家小蠹的《代码乡愁》)",
    options=list(WORK_OPTIONS.keys()),
    label_visibility="collapsed",
)
info = WORK_OPTIONS[work]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("章节", info["chapters"])
with col2:
    st.metric("总字数", f"{info['total_words']//10000}万")
with col3:
    st.metric("读过读者", f"{info['fake_reader_count']:,}")
with col4:
    st.metric("段级摘录", f"{info['fake_reader_count']*2:,}", delta="含跨书社")

st.markdown("---")

# ═══════════════════════════════════════════════════════════
#  1. 段级共鸣 — 热度地图
# ═══════════════════════════════════════════════════════════
st.markdown("### 🌊 段级心跳")
st.caption("每一章 / 每一段 — 读者停下来的密度")

# 30 章热度
chapter_heats = [
    32, 28, 35, 41, 38, 42, 56, 48, 53, 49,  # 1-10
    67, 72, 68, 75, 64, 58, 71, 79, 82, 88,  # 11-20
    91, 95, 97, 89, 76, 68, 54, 42, 38, 35,  # 21-30
]
peak_idx = chapter_heats.index(max(chapter_heats))

bars_html = "".join(
    f'<div class="chapter-bar" style="height:{h}%;" data-hot="{"true" if i == peak_idx else "false"}" title="第 {i+1} 章 · {h} 段停"></div>'
    for i, h in enumerate(chapter_heats)
)
st.html(f"""
<div class="chapter-heat">
{bars_html}
</div>
<div style="text-align:center; font-size:0.78rem; color: var(--text-muted);">
第 1 章 &nbsp;&nbsp;&nbsp;&nbsp; 第 10 章 &nbsp;&nbsp;&nbsp;&nbsp; 第 20 章 &nbsp;&nbsp;&nbsp;&nbsp; 第 30 章<br>
<span style="color: var(--ember);">🔥 峰值:第 {peak_idx+1} 章(98 分,全书最高)</span>
</div>
""")

st.markdown("### 🔥 段级 Top 5")
top_segments = [
    ("第 3 章 第 7 段", "代码注释 / 失亲 / 回忆", 127, 89, 98),
    ("第 12 章 第 4 段", "初恋 / 错过 / 情感", 89, 56, 87),
    ("第 23 章 第 2 段", "母爱 / 遗憾 / 触动", 78, 62, 85),
    ("第 7 章 第 11 段", "友情 / 沉默 / 成长", 65, 41, 72),
    ("第 18 章 第 9 段", "理想 / 现实 / 妥协", 58, 39, 68),
]
for seg_idx, (seg, theme, stops, feels, score) in enumerate(top_segments):
    pct = (score / 100) * 100
    st.html(f"""
    <div class="heat-bar">
        <span class="heat-label">📍 {seg}</span>
        <div class="heat-bar-track"><div class="heat-bar-fill" style="width:{pct}%;"></div></div>
        <span class="heat-value">{score} 分</span>
    </div>
    <div style="font-size: 0.78rem; color: var(--text-muted); margin: 0 0 0.5rem 4.5rem;">
        # {theme} · ⏸ {stops} 停 · ✍️ {feels} 写感悟
    </div>
    """)

# ═══════════════════════════════════════════════════════════
#  2. 段级停留 + 跳过
# ═══════════════════════════════════════════════════════════
st.markdown("### ⏱ 段级停留(第 3 章 — 你的高光章节)")
st.caption("读者在哪段慢停?在哪段跳过?—— 你的第 3 章像过山车")

chapter3 = [
    ("第 1 段", 2.1, "stay"),
    ("第 2 段", 1.8, "stay"),
    ("第 3 段", 0.4, "skip"),
    ("第 4 段", 1.5, "stay"),
    ("第 5 段", 0.2, "skip"),
    ("第 6 段", 2.3, "stay"),
    ("第 7 段", 3.2, "hot"),  # 杨家小蠹的母题!
    ("第 8 段", 1.7, "stay"),
]
for label, dur, kind in chapter3:
    if kind == "hot":
        tag = f'<span class="duration-stay">⏸ {dur} 分钟</span>'
        note = '<span style="color: var(--ember);">🔥 慢停 — 深读</span>'
    elif kind == "skip":
        tag = f'<span class="duration-skip">⏸ {dur} 分钟</span>'
        note = '<span style="color: var(--text-muted);">跳过</span>'
    else:
        tag = f'<span class="duration-stay">⏸ {dur} 分钟</span>'
        note = ''
    st.html(f"""
    <div class="heat-bar">
        <span class="heat-label">{label}</span>
        {tag}
        {note}
    </div>
    """)

st.html("""
<div class="simulator-box">
    <div style="color: var(--accent); font-weight: 500; margin-bottom: 0.3rem;">💡 段友(AI)建议:</div>
    第 3、5 段读者跳过 — 可能太长 / 跑题了,建议改写或并入第 4 段。<br>
    第 7 段慢停 3.2 分钟 — <b>写得好,出书的话建议单独抽出来</b>。
</div>
""")

# ═══════════════════════════════════════════════════════════
#  3. 段级情感直方图
# ═══════════════════════════════════════════════════════════
st.markdown("### 💫 段级情感直方图")
st.caption("每段触发了什么情感?(基于读者感悟的 LLM 解析)")

# 8 段 × 6 种情感
emotion_data = [
    # 中性 平静 感动 思考 困惑 失亲
    [3, 5, 2, 3, 1, 1],  # 段 1
    [2, 4, 3, 4, 1, 1],  # 段 2
    [1, 1, 1, 1, 1, 1],  # 段 3 (跳过)
    [2, 3, 5, 4, 1, 2],  # 段 4
    [1, 1, 1, 1, 1, 1],  # 段 5 (跳过)
    [2, 3, 2, 2, 1, 1],  # 段 6
    [1, 2, 6, 7, 1, 9],  # 段 7 — 情感枢纽!
    [2, 3, 2, 2, 1, 1],  # 段 8
]
emotion_names = ["中性", "平静", "感动", "思考", "困惑", "失亲"]
emotion_colors = ["#8b8680", "#a0a0a0", "#d4a574", "#c4694a", "#666", "#ff6b4a"]

# 渲染情感直方图
chart_html = '<div style="display: flex; gap: 0.3rem; align-items: end; height: 120px; margin: 0.8rem 0;">'
for seg_idx, seg_emotions in enumerate(emotion_data):
    chart_html += '<div style="flex: 1; display: flex; flex-direction: column; gap: 1px; height: 100%; justify-content: end;">'
    for emo_idx, val in enumerate(seg_emotions):
        if val > 0:
            height_pct = (val / 10) * 100
            chart_html += f'<div style="height:{height_pct}%; background: {emotion_colors[emo_idx]}; border-radius: 1px;" title="{emotion_names[emo_idx]}: {val}"></div>'
    chart_html += '</div>'
chart_html += '</div>'

chart_html += '<div style="display: flex; gap: 0.3rem; margin-top: 0.3rem;">'
for i in range(8):
    chart_html += f'<div style="flex: 1; text-align: center; font-size: 0.7rem; color: var(--text-muted);">段 {i+1}</div>'
chart_html += '</div>'

chart_html += '<div style="margin-top: 0.8rem; display: flex; flex-wrap: wrap; gap: 0.4rem;">'
for i, (name, color) in enumerate(zip(emotion_names, emotion_colors)):
    chart_html += f'<span class="emotion-tag" style="border-color: {color};"><span style="display:inline-block; width:8px; height:8px; background:{color}; border-radius:50%; margin-right:0.3rem;"></span>{name}</span>'
chart_html += '</div>'

st.html(chart_html)

st.html("""
<div class="simulator-box">
    <div style="color: var(--accent); font-weight: 500; margin-bottom: 0.3rem;">💡 段友分析:</div>
    第 7 段是<b>全书情感枢纽</b> — 90% 的「失亲」情感集中在这一段。<br>
    删了,整本书塌了。
</div>
""")

# ═══════════════════════════════════════════════════════════
#  4. 精选感悟(读者已授权)
# ═══════════════════════════════════════════════════════════
st.markdown("### 💬 精选感悟(读者已授权)")
st.caption("127 人在第 3 章第 7 段停下来,其中 89 人写了感悟。**这 4 条是你授权可见的**")

curated = [
    ("看到这行注释的时候,我在地铁上哭了。", "北京 · 28 岁 · 产品经理"),
    ("我也想给我妈写一行代码。", "上海 · 32 岁 · 后端工程师"),
    ("三十年了,他妈妈还在这行代码里活着。", "广州 · 24 岁 · 学生"),
    ("我打电话给我妈了。", "深圳 · 30 岁 · 设计师"),
]
for quote, author in curated:
    st.html(f"""
    <div class="reflection-bubble">
        "{quote}"
        <div class="reflection-author">— {author}</div>
    </div>
    """)

# ═══════════════════════════════════════════════════════════
#  5. 跨书情感画像
# ═══════════════════════════════════════════════════════════
st.markdown("### 🧠 跨书情感画像")
st.caption("摘了第 3 章第 7 段的读者,还在其他什么书里被同一情感击中?")

cross_book = [
    ("《活着》", 67, "失亲"),
    ("《百年孤独》", 58, "失亲"),
    ("《背影》", 51, "父爱"),
    ("《小王子》", 47, "成长"),
    ("《追风筝的人》", 43, "友情+失亲"),
]
bars = ""
for book, pct, theme in cross_book:
    bars += f'<span class="emotion-tag hot">{book} · {pct}% · #{theme}</span> '
st.html(f'<div style="margin: 0.5rem 0;">{bars}</div>')

st.html("""
<div class="simulator-box">
    <div style="color: var(--accent); font-weight: 500; margin-bottom: 0.3rem;">💡 段友分析:</div>
    摘了第 3 段的读者,<b>67% 也在其他书里摘过「失亲」段落</b>。<br>
    他们不是随便划线的人,他们是<b>经历过失去的人</b>。<br>
    你的这段话,击中的不是"读者",是"那些在深夜想起某个人的普通人"。
</div>
""")

# ═══════════════════════════════════════════════════════════
#  6. AI 模拟改稿
# ═══════════════════════════════════════════════════════════
st.markdown("### 🪄 AI 模拟改稿器")
st.caption("如果...情感会怎么变?")

col1, col2 = st.columns(2)
with col1:
    edit_choice = st.selectbox(
        "我想改第 7 段...",
        options=[
            "保留(不动)",
            "🔪 删掉(测试是否塌方)",
            "💪 加强情感(放大失亲主题)",
            "🔄 重写(改用日记体)",
            "📏 缩短(从 320 字压到 150 字)",
        ],
    )
with col2:
    if st.button("🪄 模拟改稿效果", use_container_width=True):
        st.session_state["_simulate_result"] = edit_choice

if "_simulate_result" in st.session_state:
    choice = st.session_state["_simulate_result"]
    if choice == "🔪 删掉(测试是否塌方)":
        st.html("""
        <div class="simulator-box">
            <div style="color: var(--ember); font-weight: 600; margin-bottom: 0.3rem;">⚠️ 模拟结果</div>
            <b>全书情感枢纽消失</b>。预计:
            <ul style="margin: 0.3rem 0;">
                <li>第 4 章高潮读起来会<b>变平淡</b>(没有铺垫)</li>
                <li>第 12 章「初恋错过」共鸣度可能下降 <b>20-30%</b></li>
                <li>整体读者流失率 <b>+15%</b>(到第 8 章弃读)</li>
            </ul>
            <div style="color: var(--accent);">建议:不删。如果嫌长,试试缩短。</div>
        </div>
        """)
    elif "缩短" in choice:
        st.html("""
        <div class="simulator-box">
            <div style="color: var(--accent); font-weight: 600; margin-bottom: 0.3rem;">✅ 模拟结果</div>
            缩短到 150 字后:
            <ul style="margin: 0.3rem 0;">
                <li>段级共鸣数 <b>基本不变</b>(核心意象保留)</li>
                <li>读者停留时间 <b>从 3.2 分 → 1.8 分</b>(正常)</li>
                <li><b>节奏变快</b>,更适合连载</li>
            </ul>
            <div style="color: var(--accent);">建议:可缩短,先试 200 字版本。</div>
        </div>
        """)
    elif "加强" in choice:
        st.html("""
        <div class="simulator-box">
            <div style="color: var(--ember); font-weight: 600; margin-bottom: 0.3rem;">⚠️ 模拟结果</div>
            加强后(加重失亲主题):
            <ul style="margin: 0.3rem 0;">
                <li>段级共鸣 <b>+30-50%</b></li>
                <li>但 <b>情感阈值过高</b> — 后续章节读者会"情感疲劳"</li>
                <li>全书中段(第 12-20 章)可能变平淡</li>
            </ul>
            <div style="color: var(--accent);">建议:不加强。把「失亲」分布到第 7、12、23 三段更好。</div>
        </div>
        """)
    else:
        st.html("""
        <div class="simulator-box">
            <div style="color: var(--accent); font-weight: 600; margin-bottom: 0.3rem;">ℹ️ 模拟结果</div>
            当前结构最优。保持。
        </div>
        """)

# ═══════════════════════════════════════════════════════════
#  CTA: 给作者自己用 / 加精
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 你想做什么?")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⭐ 加精第 7 段", use_container_width=True):
        add_points("segment_author_pinned", 50)
        st.success("已加精!读者将看到你的回应 + 你 +50 积分")
        st.balloons()
with col2:
    if st.button("📝 给第 7 段写回信", use_container_width=True):
        st.info("🪔 灯会学着你的语气, 帮你起草回信")
with col3:
    if st.button("📢 推送本章节", use_container_width=True):
        st.info("🪔 推给那些 67% 跟你一样经历过的人")

# 底部
st.markdown("---")
st.html("""
<div style="text-align:center; color: var(--text-muted); font-size: 0.8rem;">
回响 · Reading-FL · 你写的字, 读者的回响<br>
🔒 读者身份不暴露 · 看到的都是聚合数据 · FL 隐私保证
</div>
""")
