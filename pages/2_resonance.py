"""心动林 — 你的字, 在陌生人那里被看见"""
import streamlit as st
import sys
import os
import html as _html

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="心动林 · 心灯", page_icon="💫", layout="centered", initial_sidebar_state="auto")

st.markdown("""
<style>
:root { --bg: #0d0d0f; --card: rgba(255,255,255,0.04); --text: #e8e4dc; --text-muted: #8b8680;
        --accent: #d4a574; --ember: #c4694a; --border: rgba(212,165,116,0.15); }
.stApp { background: linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%); }
.main .block-container { max-width: 720px; padding-top: 1.5rem; }
h1, h2, h3 { color: var(--text) !important; font-weight: 500 !important; }
h1 { font-size: 1.7rem !important; }
h3 { font-size: 0.85rem !important; color: var(--text-muted) !important;
     text-transform: uppercase; letter-spacing: 0.18em; }
p, .stMarkdown { color: var(--text) !important; line-height: 1.7; }
.stCaption { color: var(--text-muted) !important; }
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important; border: none !important; border-radius: 8px !important;
}
.stButton > button[kind="secondary"] {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.resonance-row {
    border-bottom: 1px solid var(--border);
    padding: 1rem 0;
}
.resonance-row:last-child { border-bottom: none; }
.resonance-quote { color: var(--text); font-size: 0.95rem; line-height: 1.6; margin-bottom: 0.4rem; }
.resonance-meta { color: var(--text-muted); font-size: 0.8rem; }
.privacy-strip {
    background: linear-gradient(90deg, rgba(196,105,74,0.1) 0%, rgba(212,165,116,0.1) 100%);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 0.7rem 1rem; color: var(--accent);
    font-size: 0.88rem; text-align: center; margin: 1rem 0;
}
@media (max-width: 640px) {
    .main .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    h1 { font-size: 1.4rem !important; }
}
</style>
""", unsafe_allow_html=True)


# 兼容老 webview:深 fallback CSS
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;\n}\nsection[data-testid="stSidebar"] * {\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] h1,\nsection[data-testid="stSidebar"] h2,\nsection[data-testid="stSidebar"] h3,\nsection[data-testid="stSidebar"] p,\nsection[data-testid="stSidebar"] span,\nsection[data-testid="stSidebar"] a,\nsection[data-testid="stSidebar"] .stCaption {\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p,\n.main h1, .main h2, .main h3, .main h4,\n.main .stMarkdown, .main .stText, .main .stCaption {\n    color: #e8e4dc !important;\n}\n</style>', unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")

st.markdown("# 🌳 心动林")
st.caption("跨 3 个书社的匿名共振 — 原文不上传,只共享模型结果")
st.markdown("""
<div class="privacy-strip">
    🔒 这些摘录来自 3 个书社 60 个匿名读者。原始感悟从未离开书社,只有模型参数和聚合结果跨书社流动。
</div>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_resonance():
    # 审计 #3 修复: 弃用 subprocess.run (share.streamlit.io 沙箱可能拦截),
    # 改用直接 import demo.run_demo(quick=True), 函数返回结构化被看见数据.
    from scripts.demo import run_demo
    rows = run_demo(quick=True) or []
    rows.sort(key=lambda x: -x["score"])
    return rows


with st.spinner("段友正在翻书, 等一下下..."):
    rows = get_resonance()

# 排序 + 筛选
col1, col2, col3 = st.columns(3)
with col1:
    sort_by = st.selectbox("排序", ["被看见度", "跨书社数", "读者数"], label_visibility="collapsed")
with col2:
    min_score = st.slider("最低被看见度", 0.0, 1.0, 0.4, 0.05)
with col3:
    min_guilds = st.selectbox("最少跨书社", [1, 2, 3], index=0)

filtered = [
    r for r in rows
    if r["score"] >= min_score and int(str(r["n_guilds"]).replace("?", "0")) >= min_guilds
]

if sort_by == "被看见度":
    filtered.sort(key=lambda x: -x["score"])
elif sort_by == "跨书社数":
    filtered.sort(key=lambda x: -int(str(x["n_guilds"]).replace("?", "0")))
elif sort_by == "读者数":
    filtered.sort(key=lambda x: -int(str(x["n_readers"]).replace("?", "0")))

st.caption(f"共 {len(filtered)} 条 / 总 {len(rows)} 条")

for r in filtered:
    safe_text = _html.escape(r['text'])
    st.markdown(f"""
    <div class="resonance-row">
        <div class="resonance-quote">「{safe_text}」</div>
        <div class="resonance-meta">
            🔥 {r['score']:.2f} · 👥 {r['n_readers']} 读者 · 🏛️ {r['n_guilds']} 书社
        </div>
    </div>
    """, unsafe_allow_html=True)

    # v6.3.3 心动林 30s 配乐 (MiniMax music-2.6)
    col_text, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("🎵 听 30s", key=f"music_{r.get('id', r['text'][:8])}", help="MiniMax 配乐"):
            from core.lamp_music import generate_lamp_music, audio_hex_to_data_url
            with st.spinner("🪔 心灯正在为你拨弦..."):
                result = generate_lamp_music(
                    emotion="共鸣",  # 默认 (后续按真实情绪)
                    book=r.get('book_title', ''),
                    chapter=r.get('chapter', ''),
                )
            if result.get("audio_hex"):
                # 渲染 audio 播放器
                data_url = audio_hex_to_data_url(result["audio_hex"])
                if data_url:
                    st.html(f"""
                    <audio controls autoplay style="width: 100%; margin-top: 0.5rem;">
                        <source src="{data_url}" type="audio/mpeg">
                    </audio>
                    """)
                    st.caption(f"🪔 30s 配乐 — 《{result.get('book','')}》 {result.get('chapter','')}")
                else:
                    st.warning("🪔 音频转换失败")
            elif result.get("audio_url"):
                st.html(f"""
                <audio controls autoplay style="width: 100%; margin-top: 0.5rem;">
                    <source src="{result['audio_url']}" type="audio/mpeg">
                </audio>
                """)
            elif result.get("error"):
                st.caption(f"🪔 配乐暂时没开 ({result['error'][:50]})")
            elif result.get("mock"):
                st.caption("🪔 配乐功能开发中, 配 MINIMAX_API_KEY 后可用")
