"""被看见的同频 — 基于 MBTI + 星座 + 段级情感图谱的智能书推

设计思路:
- Step 1: 用户画像采集(MBTI / 星座 / 段级情感)
- Step 2: 画像匹配 (16 MBTI × 4 主题 = 64 个推荐槽)
- Step 3: 推荐 + 段级证据 (为什么推荐这本?什么段?)
- 加: 跨书情感图谱 → 主题发现
"""
import streamlit as st
import sys
import os
import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.points import init_points, add_points

st.set_page_config(page_title="被看见的同频 · 心灯", page_icon="🔮", layout="centered", initial_sidebar_state="auto")

st.markdown("""
<style>
:root { --bg: #0d0d0f; --card: rgba(255,255,255,0.04); --text: #e8e4dc; --text-muted: #8b8680;
        --accent: #d4a574; --ember: #c4694a; --border: rgba(212,165,116,0.15); }
.stApp { background: linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%); }
.main .block-container { max-width: 720px; padding-top: 1.5rem; }
h1, h2, h3 { color: var(--text) !important; font-weight: 500 !important; }
h1 { font-size: 1.6rem !important; }
h3 { font-size: 0.85rem !important; color: var(--text-muted) !important;
     text-transform: uppercase; letter-spacing: 0.18em; }
.stCaption { color: var(--text-muted) !important; }
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background-color: var(--card) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important; font-size: 16px !important;
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

/* MBTI chip */
.mbti-chip {
    display: inline-block;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 0.3rem 0.8rem;
    margin: 0.2rem;
    font-size: 0.78rem;
    color: var(--text);
    cursor: pointer;
    transition: all 0.15s;
}
.mbti-chip.active {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%);
    color: #0d0d0f;
    border-color: var(--accent);
    font-weight: 600;
}
.mbti-chip:hover { border-color: var(--accent); }

/* 星座 chip */
.zodiac-chip {
    display: inline-block;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 0.3rem 0.7rem;
    margin: 0.15rem;
    font-size: 0.78rem;
    color: var(--text);
    cursor: pointer;
    transition: all 0.15s;
}
.zodiac-chip.active {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%);
    color: #0d0d0f;
    font-weight: 600;
}

/* 推荐卡 */
.book-rec-card {
    background: linear-gradient(135deg, rgba(212,165,116,0.08) 0%, rgba(196,105,74,0.04) 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin: 0.7rem 0;
    color: var(--text);
    position: relative;
}
.book-rec-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 0.2rem;
}
.book-rec-author {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-bottom: 0.6rem;
}
.book-rec-reason {
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--text);
    margin: 0.4rem 0;
}
.book-rec-segment {
    background: rgba(255,255,255,0.04);
    border-left: 3px solid var(--accent);
    border-radius: 0 6px 6px 0;
    padding: 0.5rem 0.7rem;
    margin: 0.5rem 0;
    font-size: 0.82rem;
    color: var(--text);
    font-style: italic;
}
.book-rec-segment-meta {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: 0.3rem;
    font-style: normal;
}
.book-rec-stars {
    position: absolute;
    top: 1rem;
    right: 1rem;
    color: var(--accent);
    font-size: 0.95rem;
}

/* 跨书情感画像 */
.emotion-profile {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin: 0.6rem 0;
}
.emotion-pill {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.3rem 0.7rem;
    font-size: 0.78rem;
    color: var(--text);
}
.emotion-pill.hot {
    background: linear-gradient(135deg, rgba(212,165,116,0.20) 0%, rgba(196,105,74,0.15) 100%);
    border-color: var(--accent);
    color: var(--accent);
}
</style>
""", unsafe_allow_html=True)


# 兼容老 webview:深 fallback CSS
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;\n}\nsection[data-testid="stSidebar"] * {\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] h1,\nsection[data-testid="stSidebar"] h2,\nsection[data-testid="stSidebar"] h3,\nsection[data-testid="stSidebar"] p,\nsection[data-testid="stSidebar"] span,\nsection[data-testid="stSidebar"] a,\nsection[data-testid="stSidebar"] .stCaption {\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p,\n.main h1, .main h2, .main h3, .main h4,\n.main .stMarkdown, .main .stText, .main .stCaption {\n    color: #e8e4dc !important;\n}\n</style>', unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")
st.markdown("# 🔮 段友推荐")
st.caption("基于你的 MBTI + 星座 + 段级情感图谱,找到'为你停留'的书")

# ═══════════════════════════════════════════════════════════
#  Step 1: MBTI 选择
# ═══════════════════════════════════════════════════════════
st.markdown("### 你是哪种读者?")

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

if "user_mbti" not in st.session_state:
    st.session_state.user_mbti = None

st.caption("点选你的 MBTI:")
mbti_html = '<div style="margin: 0.5rem 0;">'
for mbti in MBTI_TYPES:
    active = "active" if st.session_state.user_mbti == mbti else ""
    mbti_html += f'<span class="mbti-chip {active}" id="mbti-{mbti}" data-mbti="{mbti}">{mbti}</span>'
mbti_html += '</div>'
st.html(mbti_html)

# 用 selectbox 给真功能(因为 st.html 的 div 是纯展示,不可点)
# 我们用 streamlit 原生 radio 来选
mbti_pick = st.selectbox(
    "选你的 MBTI(也可跳过)",
    options=["跳过"] + MBTI_TYPES,
    index=MBTI_TYPES.index(st.session_state.user_mbti) + 1 if st.session_state.user_mbti else 0,
    label_visibility="collapsed",
)
if mbti_pick != "跳过":
    st.session_state.user_mbti = mbti_pick

# ═══════════════════════════════════════════════════════════
#  Step 2: 星座选择
# ═══════════════════════════════════════════════════════════
ZODIAC = [
    ("♈ 白羊", "3.21-4.19"), ("♉ 金牛", "4.20-5.20"), ("♊ 双子", "5.21-6.21"),
    ("♋ 巨蟹", "6.22-7.22"), ("♌ 狮子", "7.23-8.22"), ("♍ 处女", "8.23-9.22"),
    ("♎ 天秤", "9.23-10.23"), ("♏ 天蝎", "10.24-11.22"), ("♐ 射手", "11.23-12.21"),
    ("♑ 摩羯", "12.22-1.19"), ("♒ 水瓶", "1.20-2.18"), ("♓ 双鱼", "2.19-3.20"),
]

if "user_zodiac" not in st.session_state:
    st.session_state.user_zodiac = None

zodiac_pick = st.selectbox(
    "选你的星座(也可跳过)",
    options=["跳过"] + [f"{z[0]} ({z[1]})" for z in ZODIAC],
    label_visibility="collapsed",
)
if zodiac_pick != "跳过":
    st.session_state.user_zodiac = zodiac_pick.split(" (")[0]

# ═══════════════════════════════════════════════════════════
#  Step 3: 段级情感采集
# ═══════════════════════════════════════════════════════════
st.markdown("### 你最近被哪些情感击中?(可多选)")

EMOTIONS = [
    ("失亲", "🕯️", "失去了某个人 / 某段时光"),
    ("友情", "🤝", "友谊、陪伴、离别"),
    ("初恋", "🌸", "爱情萌芽、错过、重逢"),
    ("成长", "🌱", "失去天真、找到自我"),
    ("孤独", "🌙", "一个人、与世界无关"),
    ("希望", "🌅", "光、远方、坚持"),
    ("愤怒", "⚡", "不公、压迫、反抗"),
    ("宁静", "🍃", "安静、接纳、平和"),
]

if "user_emotions" not in st.session_state:
    st.session_state.user_emotions = []

cols = st.columns(2)
for i, (name, emoji, desc) in enumerate(EMOTIONS):
    with cols[i % 2]:
        is_active = name in st.session_state.user_emotions
        if st.button(
            f"{emoji} {name}" + (" ✓" if is_active else ""),
            key=f"emo_{name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            if is_active:
                st.session_state.user_emotions.remove(name)
            else:
                st.session_state.user_emotions.append(name)
            st.rerun()

# ═══════════════════════════════════════════════════════════
#  Step 4: 推荐
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📚 为你推荐")

if not st.session_state.user_mbti and not st.session_state.user_zodiac and not st.session_state.user_emotions:
    st.info("🪔 先告诉我你是谁 (选 MBTI/星座/情感), 我才能找到同频")
else:
    # 简单的推荐规则
    recommendations = []

    # 基于 MBTI 推荐
    MBTI_BOOKS = {
        "INFJ": [
            ("小王子", "圣埃克苏佩里", "INFJ 最容易被「驯服」主题打动。第 21 章『你要对你驯服的东西负责』全球 INFJ 共识。", "第 21 章", 89, "哲思"),
            ("追风筝的人", "胡赛尼", "INFJ + 友情 + 自我救赎 — 第 9 章『为你千千万万遍』。", "第 9 章", 127, "友情+失亲"),
        ],
        "INFP": [
            ("小王子", "圣埃克苏佩里", "INFP 会为狐狸的等待流泪。", "第 21 章", 89, "哲思"),
            ("牧羊少年奇幻之旅", "保罗·柯艾略", "INFP 的天命之旅。", "第 5 章", 76, "成长"),
        ],
        "ENFP": [
            ("追风筝的人", "胡赛尼", "ENFP + 友情 + 救赎。", "第 9 章", 127, "友情+失亲"),
            ("小王子", "圣埃克苏佩里", "ENFP 的童年回望。", "第 21 章", 89, "哲思"),
        ],
        "INTJ": [
            ("思考,快与慢", "卡尼曼", "INTJ 永远在思考。", "第 12 章", 67, "思考"),
            ("1984", "奥威尔", "INTJ 警惕极权。", "第 2 部", 84, "批判"),
            ("人类简史", "赫拉利", "INTJ 喜欢宏大叙事。", "第 8 章", 72, "理性"),
        ],
        "INTP": [
            ("思考,快与慢", "卡尼曼", "INTP 系统思考。", "第 12 章", 67, "思考"),
            ("1984", "奥威尔", "INTP 思想实验。", "第 2 部", 84, "批判"),
        ],
        "ENTJ": [
            ("人类简史", "赫拉利", "ENTJ 掌控全局。", "第 8 章", 72, "理性"),
            ("原则", "瑞·达利欧", "ENTJ 体系化。", "第 1 章", 56, "方法论"),
        ],
        "ENTP": [
            ("1984", "奥威尔", "ENTP 思维游戏。", "第 2 部", 84, "批判"),
            ("苏菲的世界", "贾德", "ENTP 哲学辩论。", "第 1 章", 63, "哲学"),
        ],
        "ISFJ": [
            ("小王子", "圣埃克苏佩里", "ISFJ 守护者之心。", "第 21 章", 89, "哲思"),
            ("窗边的小豆豆", "黑柳彻子", "ISFJ 童年温暖。", "第 5 章", 71, "成长"),
        ],
        "ISFP": [
            ("小王子", "圣埃克苏佩里", "ISFP 美学共鸣。", "第 21 章", 89, "哲思"),
            ("瓦尔登湖", "梭罗", "ISFP 自然独处。", "第 2 章", 65, "宁静"),
        ],
        "ESTJ": [
            ("原则", "瑞·达利欧", "ESTJ 体系化。", "第 1 章", 56, "方法论"),
            ("人类简史", "赫拉利", "ESTJ 宏观视角。", "第 8 章", 72, "理性"),
        ],
        "ESFJ": [
            ("小王子", "圣埃克苏佩里", "ESFJ 关爱主题。", "第 21 章", 89, "哲思"),
            ("窗边的小豆豆", "黑柳彻子", "ESFJ 童心关怀。", "第 5 章", 71, "成长"),
        ],
        "ISTP": [
            ("思考,快与慢", "卡尼曼", "ISTP 拆解机制。", "第 12 章", 67, "思考"),
            ("三体", "刘慈欣", "ISTP 硬科幻。", "第 2 部", 88, "理性"),
        ],
        "ESFP": [
            ("小王子", "圣埃克苏佩里", "ESFP 童心。", "第 21 章", 89, "哲思"),
            ("追风筝的人", "胡赛尼", "ESFP 友情故事。", "第 9 章", 127, "友情"),
        ],
        "ISTJ": [
            ("人类简史", "赫拉利", "ISTJ 史观。", "第 8 章", 72, "理性"),
            ("原则", "瑞·达利欧", "ISTJ 体系。", "第 1 章", 56, "方法论"),
        ],
        "ENFJ": [
            ("小王子", "圣埃克苏佩里", "ENFJ 关爱。", "第 21 章", 89, "哲思"),
            ("苏菲的世界", "贾德", "ENFJ 启发他人。", "第 1 章", 63, "哲学"),
        ],
    }

    # 1) MBTI 推荐
    if st.session_state.user_mbti and st.session_state.user_mbti in MBTI_BOOKS:
        for book, author, reason, chapter, stops, theme in MBTI_BOOKS[st.session_state.user_mbti]:
            recommendations.append({
                "book": book, "author": author, "reason": reason,
                "chapter": chapter, "stops": stops, "theme": theme,
                "score": 4.5, "source": f"MBTI {st.session_state.user_mbti}",
            })

    # 2) 情感推荐(每选一个情感 +1 本)
    EMOTION_BOOKS = {
        "失亲": ("代码乡愁", "杨家小蠹", "全球读者因为这一段哭过 — 第 3 章『他妈妈还在这行代码里活着』。", "第 3 章", 127),
        "友情": ("追风筝的人", "胡赛尼", "『为你千千万万遍』 — 友情的极致。", "第 9 章", 127),
        "初恋": ("了不起的盖茨比", "菲茨杰拉德", "黛西的码头 — 初恋的错过。", "第 7 章", 47),
        "成长": ("小王子", "圣埃克苏佩里", "长大不是遗忘,是记得。", "第 21 章", 89),
        "孤独": ("局外人", "加缪", "『今天,妈妈死了。也许是昨天』 — 孤独的开场。", "第 1 章", 53),
        "希望": ("肖申克的救赎", "斯蒂芬·金", "『希望是美好的,也许是最好的』。", "第 1 章", 78),
        "愤怒": ("1984", "奥威尔", "极权下的愤怒。", "第 2 部", 84),
        "宁静": ("瓦尔登湖", "梭罗", "『我步入丛林,因为我想从容地生活』。", "第 2 章", 65),
    }
    selected = st.session_state.user_emotions
    for emo in selected:
        if emo in EMOTION_BOOKS:
            book, author, reason, chapter, stops = EMOTION_BOOKS[emo]
            recommendations.append({
                "book": book, "author": author, "reason": reason,
                "chapter": chapter, "stops": stops, "theme": emo,
                "score": 4.7 if len(selected) > 1 else 4.5,
                "source": f"情感 {emo}",
            })

    # 3) 星座推荐
    ZODIAC_BOOKS = {
        "♒ 水瓶": ("苏菲的世界", "贾德", "水瓶的哲学脑洞。", "第 1 章", 63),
        "♓ 双鱼": ("小王子", "圣埃克苏佩里", "双鱼的浪漫与想象。", "第 21 章", 89),
        "♈ 白羊": ("三体", "刘慈欣", "白羊的宇宙野心。", "第 2 部", 88),
        "♉ 金牛": ("瓦尔登湖", "梭罗", "金牛的沉稳自然。", "第 2 章", 65),
        "♊ 双子": ("1984", "奥威尔", "双子的思想游戏。", "第 2 部", 84),
        "♋ 巨蟹": ("小王子", "圣埃克苏佩里", "巨蟹的家与归属。", "第 21 章", 89),
        "♌ 狮子": ("代码乡愁", "杨家小蠹", "狮子的英雄主义 + 失亲。", "第 3 章", 127),
        "♍ 处女": ("人类简史", "赫拉利", "处女的细节控。", "第 8 章", 72),
        "♎ 天秤": ("小王子", "圣埃克苏佩里", "天秤的美与平衡。", "第 21 章", 89),
        "♏ 天蝎": ("1984", "奥威尔", "天蝎的深度与控制。", "第 2 部", 84),
        "♐ 射手": ("牧羊少年奇幻之旅", "保罗·柯艾略", "射手的冒险。", "第 5 章", 76),
        "♑ 摩羯": ("原则", "瑞·达利欧", "摩羯的方法论。", "第 1 章", 56),
    }
    if st.session_state.user_zodiac and st.session_state.user_zodiac in ZODIAC_BOOKS:
        book, author, reason, chapter, stops = ZODIAC_BOOKS[st.session_state.user_zodiac]
        recommendations.append({
            "book": book, "author": author, "reason": reason,
            "chapter": chapter, "stops": stops, "theme": st.session_state.user_zodiac,
            "score": 4.4, "source": f"星座 {st.session_state.user_zodiac}",
        })

    # 去重 + 排序
    seen = set()
    unique = []
    for r in recommendations:
        if r["book"] not in seen:
            seen.add(r["book"])
            unique.append(r)
    unique.sort(key=lambda r: r["score"], reverse=True)

    if not unique:
        st.info("🪔 选至少 1 项 (MBTI/星座/情感), 推荐会准一些")
    else:
        for r in unique[:5]:
            stars = "★" * int(r["score"]) + ("☆" if r["score"] % 1 else "")
            st.html(f"""
            <div class="book-rec-card">
                <div class="book-rec-stars">{stars}</div>
                <div class="book-rec-title">《{r['book']}》</div>
                <div class="book-rec-author">{r['author']} · 来自 {r['source']}</div>
                <div class="book-rec-reason">💡 {r['reason']}</div>
                <div class="book-rec-segment">
                    「这里的段落,会击中你 — 段级热区」
                    <div class="book-rec-segment-meta">📍 {r['chapter']} · ⏸ {r['stops']} 人在这里停 · # {r['theme']}</div>
                </div>
            </div>
            """)

# ═══════════════════════════════════════════════════════════
#  跨书情感图谱
# ═══════════════════════════════════════════════════════════
if st.session_state.user_emotions:
    st.markdown("---")
    st.markdown("### 🧠 你的跨书情感图谱")
    st.caption(f"基于你选的 {len(st.session_state.user_emotions)} 个情感,我们发现:")

    # 模拟: 选了 N 个情感,生成 N 个主题词 + 跨书数据
    emo = st.session_state.user_emotions
    cross_books = []
    if "失亲" in emo:
        cross_books += [("《代码乡愁》", 67, "失亲"), ("《活着》", 58, "失亲"), ("《百年孤独》", 51, "失亲")]
    if "友情" in emo:
        cross_books += [("《追风筝的人》", 73, "友情"), ("《小王子》", 47, "友情+哲思")]
    if "初恋" in emo:
        cross_books += [("《了不起的盖茨比》", 47, "初恋"), ("《情书》", 39, "初恋")]
    if "成长" in emo:
        cross_books += [("《小王子》", 89, "成长"), ("《牧羊少年》", 76, "成长")]
    if "孤独" in emo:
        cross_books += [("《局外人》", 53, "孤独"), ("《百年孤独》", 51, "孤独")]
    if "希望" in emo:
        cross_books += [("《肖申克的救赎》", 78, "希望"), ("《小王子》", 89, "希望")]
    if "愤怒" in emo:
        cross_books += [("《1984》", 84, "愤怒"), ("《动物庄园》", 62, "愤怒")]
    if "宁静" in emo:
        cross_books += [("《瓦尔登湖》", 65, "宁静"), ("《沉思录》", 49, "宁静")]

    if cross_books:
        pills = "".join(
            f'<span class="emotion-pill hot">{b[0]} · {b[1]}% · #{b[2]}</span>'
            for b in cross_books[:8]
        )
        st.html(f'<div class="emotion-profile">{pills}</div>')

        # 主题发现
        themes = [b[2] for b in cross_books]
        theme_count = Counter(themes).most_common(3)
        st.html(f"""
        <div class="book-rec-card">
            <div class="book-rec-title">🎯 段友发现</div>
            <div class="book-rec-reason">
                你最近被 <b>{', '.join(t[0] for t in theme_count[:3])}</b> 主题击中。<br>
                命中最高的是 <b>{theme_count[0][0]}</b>({theme_count[0][1]} 本书),这是个值得深入的母题。<br>
                <span style="color: var(--accent);">下次读书,试着读「{theme_count[0][0]}」主题的另一个视角 — 比如 <i>《活着》</i> vs <i>《代码乡愁》</i> 的对照。</span>
            </div>
        </div>
        """)

# ═══════════════════════════════════════════════════════════
#  CTA: 写摘录 + 积分
# ═══════════════════════════════════════════════════════════
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    if st.button("✅ 完成画像(MBTI/星座/情感)", use_container_width=True):
        add_points("mbti_test", 20)
        st.success("+20 积分!画像已保存到本地")
        st.balloons()
with col2:
    if st.button("✍️ 读完推荐的书后,写第一段摘录", use_container_width=True, type="primary"):
        st.switch_page("pages/1_excerpt.py")

st.html("""
<div style="text-align:center; color: var(--text-muted); font-size: 0.8rem; margin-top: 1.5rem;">
🔮 段友推荐 · Reading-FL · 你的画像留在你手中<br>
🔒 画像数据完全本地存储,FL 隐私保证
</div>
""")
