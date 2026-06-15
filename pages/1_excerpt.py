"""写摘录 — 一句话, 永久被看见

4 种输入方式 (心灯产品哲学: 录入越低门槛, 越多人能开始):
1. ✍️ 打字 (核心)
2. 📷 拍照 (纸书 / 朋友圈 / Kindle)
3. 🖼 上传图 (电脑 / 微信截图)
4. 🎙 语音 (边走边说, 老人小孩都能用)
+ 截屏识别 (单独保留, AMAX 多模态)
"""
import streamlit as st
import sys
import os
import hashlib
import datetime
import html as _html
import uuid as _uuid
import json as _json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="写摘录 · 心灯",
    page_icon="✍️",
    layout="centered",
    initial_sidebar_state="auto",
)

# 共用暗色 CSS
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
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(212, 165, 116, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(212, 165, 116, 0.1) !important;
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
.stRadio [role="radiogroup"] label {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 0.4rem 0.9rem !important;
    color: var(--text) !important;
}
/* 4 tab 模式按钮 (替代 st.tabs, 移动友好) */
.input-mode-tabs {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    margin: 0.5rem 0 1rem 0;
}
.input-mode-tab {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 0.4rem;
    text-align: center;
    font-size: 0.82rem;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
}
.input-mode-tab.active {
    background: linear-gradient(135deg, rgba(212,165,116,0.20) 0%, rgba(196,105,74,0.15) 100%);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 600;
}
.input-mode-tab .icon { font-size: 1.4rem; display: block; margin-bottom: 0.2rem; }
.archive-card {
    background: var(--card);
    border-left: 3px solid var(--ember);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
}
.archive-quote { color: var(--text); font-size: 0.95rem; font-style: italic; line-height: 1.6; margin-bottom: 0.5rem; }
.archive-meta { color: var(--text-muted); font-size: 0.8rem; }
@media (max-width: 640px) {
    .main .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    h1 { font-size: 1.4rem !important; }
    .stTextArea textarea { min-height: 90px !important; font-size: 16px !important; }
    .stRadio [role="radiogroup"] > div { flex: 1 1 30% !important; min-width: 70px !important; }
    .stButton > button { width: 100% !important; min-height: 44px !important; }
    .input-mode-tab { font-size: 0.7rem; padding: 0.4rem 0.2rem; }
    .input-mode-tab .icon { font-size: 1.1rem; }
}
</style>
""", unsafe_allow_html=True)


# 兼容老 webview:深 fallback CSS
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;\n}\nsection[data-testid="stSidebar"] * {\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] h1,\nsection[data-testid="stSidebar"] h2,\nsection[data-testid="stSidebar"] h3,\nsection[data-testid="stSidebar"] p,\nsection[data-testid="stSidebar"] span,\nsection[data-testid="stSidebar"] a,\nsection[data-testid="stSidebar"] .stCaption {\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p,\n.main h1, .main h2, .main h3, .main h4,\n.main .stMarkdown, .main .stText, .main .stCaption {\n    color: #e8e4dc !important;\n}\n</style>', unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")

st.markdown("# ✍️ 写摘录")
st.caption("你今天被什么打动了? 我帮你存下来")

# ══════════════════════════════════════════════════════════════
#  4 种输入方式 — tab 模式
# ══════════════════════════════════════════════════════════════
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "✍️ 打字"

# 4 tab 切换
st.markdown('<div class="input-mode-tabs">', unsafe_allow_html=True)
col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1:
    if st.button("✍️\n\n**打字**", key="tab_type", use_container_width=True, help="手动输入"):
        st.session_state.input_mode = "✍️ 打字"
        st.rerun()
with col_t2:
    if st.button("📷\n\n**拍照**", key="tab_camera", use_container_width=True, help="纸书 / Kindle"):
        st.session_state.input_mode = "📷 拍照"
        st.rerun()
with col_t3:
    if st.button("🖼\n\n**上传图**", key="tab_upload", use_container_width=True, help="电脑 / 微信截图"):
        st.session_state.input_mode = "🖼 上传图"
        st.rerun()
with col_t4:
    if st.button("🎙\n\n**语音**", key="tab_audio", use_container_width=True, help="边走边说"):
        st.session_state.input_mode = "🎙 语音"
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# v6.3.2 第 5 种: AI 金句 (单独一行, 全宽, 区别于 4 tab)
if st.button("🤖  **AI 金句** — 不知道读什么? 让 AI 给你 3 段选 1", key="tab_ai", use_container_width=True, help="v6.3.2 新"):
    st.session_state.input_mode = "🤖 AI 金句"
    st.rerun()

# 当前模式
current_mode = st.session_state.input_mode
st.caption(f"🪔 当前模式: **{current_mode}** — 切到其他模式不会丢你已经写的内容")

# 暂存"已识别结果", 跨 tab 共享
if "_image_prefill" not in st.session_state:
    st.session_state["_image_prefill"] = None
if "_latest_is_ai" not in st.session_state:
    st.session_state["_latest_is_ai"] = False

# 4 个 tab 内容区
if current_mode == "📷 拍照":
    st.markdown("### 📷 拍一张")
    st.caption("对准纸书 / Kindle / 朋友圈截图, 按下相机按钮")
    cam_photo = st.camera_input("拍下打动你的那一段", label_visibility="collapsed")
    cam_hint = st.text_input(
        "提示(可选) — 例如:这是《代码乡愁》第 3 章",
        key="camera_hint",
        label_visibility="collapsed",
        placeholder="提示(可选) — 例如:这是《代码乡愁》第 3 章",
    )
    if cam_photo is not None and st.button("🔍 识别", key="cam_recog", use_container_width=True):
        from core.amax_chat import detect_excerpt_from_image
        with st.spinner("段友正在翻书, 等一下下..."):
            result = detect_excerpt_from_image(cam_photo.read(), hint=cam_hint)
        if "error" in result:
            st.warning(f"🪔 灯暂时暗了一下: {result['error'][:80]}")
            if "mock_paragraph" in result:
                st.info(f"🪔 我暂时只能示范: {result.get('mock_book_title','')} — {result['mock_paragraph'][:80]}")
        else:
            st.success(f"✅ 识别成功 (置信度 {result.get('confidence', 0):.0%})")
            st.session_state["_image_prefill"] = {
                "book": result.get('book_title', '📝 我自己的书'),
                "author": result.get('author', ''),
                "excerpt": result.get('paragraph', ''),
                "tags": ' '.join(result.get('tags', [])),
                "location": result.get('paragraph_location', ''),
            }
            st.rerun()

elif current_mode == "🖼 上传图":
    st.markdown("### 🖼 上传一张图")
    st.caption("微信截图 / 微博截图 / 电脑本地截图 都行")
    up_img = st.file_uploader(
        "拖入或选择图片",
        type=["png", "jpg", "jpeg", "webp"],
        key="upload_img",
        label_visibility="collapsed",
    )
    up_hint = st.text_input(
        "提示(可选) — 例如:这是《代码乡愁》第 3 章",
        key="upload_hint",
        label_visibility="collapsed",
        placeholder="提示(可选) — 例如:这是《代码乡愁》第 3 章",
    )
    if up_img is not None and st.button("🔍 识别", key="up_recog", use_container_width=True):
        from core.amax_chat import detect_excerpt_from_image
        with st.spinner("段友正在翻书, 等一下下..."):
            result = detect_excerpt_from_image(up_img.read(), hint=up_hint)
        if "error" in result:
            st.warning(f"🪔 灯暂时暗了一下: {result['error'][:80]}")
            if "mock_paragraph" in result:
                st.info(f"🪔 我暂时只能示范: {result.get('mock_book_title','')} — {result['mock_paragraph'][:80]}")
        else:
            st.success(f"✅ 识别成功 (置信度 {result.get('confidence', 0):.0%})")
            st.session_state["_image_prefill"] = {
                "book": result.get('book_title', '📝 我自己的书'),
                "author": result.get('author', ''),
                "excerpt": result.get('paragraph', ''),
                "tags": ' '.join(result.get('tags', [])),
                "location": result.get('paragraph_location', ''),
            }
            st.rerun()

elif current_mode == "🎙 语音":
    st.markdown("### 🎙 录一段")
    st.caption("按下麦克风说一段, AI 转成文字")
    voice = st.audio_input("录下你今天想记住的", label_visibility="collapsed")
    if voice is not None and st.button("🔍 转文字", key="voice_recog", use_container_width=True):
        with st.spinner("段友正在听你说话..."):
            try:
                # AMAX 暂未支持语音, 给个 mock
                st.info("🪔 AI 转录功能开发中, 我先帮你存了一段占位文字 — 你可以手动改")
                st.session_state["_image_prefill"] = {
                    "book": "📝 我自己的书",
                    "author": "",
                    "excerpt": "[🎙 语音转文字 — 请手动修改] 这一刻...",
                    "tags": "",
                    "location": "",
                }
                st.rerun()
            except Exception as e:
                st.warning(f"🪔 灯暂时暗了一下 (语音转文字失败: {str(e)[:60]})")

else:  # ✍️ 打字
    st.markdown("### ✍️ 手动输入")
    st.caption("不想拍? 直接贴/写")

# v6.3.2 第 5 种输入方式: AI 金句
if current_mode == "🤖 AI 金句":
    st.markdown("### 🤖 AI 金句")
    st.caption("不记得哪一段? 没关系, AI 帮你找 3 段 — 你选 1 段就够")

    # 输入表单
    col_a, col_b = st.columns(2)
    with col_a:
        ai_book = st.text_input(
            "📖 书 (可选)",
            value=st.session_state.get("ai_book", ""),
            placeholder="《三体》/ 任何",
            key="ai_book_input",
        )
    with col_b:
        ai_topic = st.text_input(
            "💭 主题 (必填)",
            value=st.session_state.get("ai_topic", ""),
            placeholder="宇宙的孤独感",
            key="ai_topic_input",
        )

    col_c, col_d = st.columns(2)
    with col_c:
        ai_style = st.selectbox(
            "🎨 风格 (可选)",
            options=["不限", "鲁迅", "海明威", "马尔克斯", "村上春树", "张爱玲", "李白", "苏轼"],
            index=0,
            key="ai_style_sel",
            label_visibility="collapsed",
        )
    with col_d:
        ai_emotion = st.selectbox(
            "💗 情绪 (可选)",
            options=["不限", "感动", "思考", "共鸣", "困惑", "反对", "平静"],
            index=0,
            key="ai_emotion_sel",
            label_visibility="collapsed",
        )

    ai_n = st.slider("要几段?", 1, 5, 3, key="ai_n_slider")

    if st.button("🪔 给我金句", key="ai_gen", use_container_width=True, type="primary"):
        if not ai_topic:
            st.warning("🪔 告诉我一句你想读的主题, 我去帮你找")
        else:
            from core.amax_chat import generate_golden_quote
            with st.spinner("🪔 心灯精灵正在替你翻书..."):
                result = generate_golden_quote(
                    book=ai_book,
                    topic=ai_topic,
                    style=ai_style,
                    emotion=ai_emotion,
                    n=ai_n,
                )
            if "error" in result and "quotes" not in result:
                st.warning(f"🪔 灯暂时暗了一下: {result.get('error', '未知错误')[:80]}")
            else:
                quotes = result.get("quotes", [])
                st.session_state["_ai_quotes"] = quotes
                st.session_state["_ai_book"] = ai_book or "任何"
                st.session_state["_ai_topic"] = ai_topic
                st.session_state["_ai_style"] = ai_style
                st.session_state["_ai_emotion"] = ai_emotion
                if result.get("mock"):
                    st.caption("🪔 灯暂时没接 AI, 这是预设的示例 (配 AMAX_API_KEY 后会用真 AI)")
                else:
                    st.success(f"🪔 找到 {len(quotes)} 段 — 选 1 段写进摘录")
                st.rerun()

    # 显示已生成的金句, 每段一个"写入摘录"按钮
    if st.session_state.get("_ai_quotes"):
        st.markdown("---")
        st.markdown("### 📚 我找到的")
        st.caption("标了 [AI 生成] 的是 AI 写的, 不是真摘录, 别拿去发表哦")

        for i, q in enumerate(st.session_state["_ai_quotes"]):
            safe_text = _html.escape(q.get("text", ""))
            safe_book = _html.escape(q.get("book", ""))
            safe_loc = _html.escape(q.get("location", ""))
            confidence = q.get("confidence", 0.5)
            q_emotion = q.get("emotion", "resonance")
            emotion_cn = {
                "moved": "感动", "thinking": "思考", "resonance": "共鸣",
                "confused": "困惑", "disagree": "反对", "calm": "平静",
            }.get(q_emotion, "共鸣")

            st.html(f"""
            <div style="background: rgba(212,165,116,0.08); border-left: 3px solid #d4a574;
                        border-radius: 8px; padding: 1rem 1.2rem; margin: 0.8rem 0;">
                <div style="color: #e8e4dc; font-size: 0.95rem; line-height: 1.6; font-style: italic; margin-bottom: 0.6rem;">
                    「{safe_text}」
                </div>
                <div style="color: #8b8680; font-size: 0.78rem;">
                    🤖 [AI 生成] · {safe_book} · {safe_loc} · 🪔 {emotion_cn} · 像真度 {confidence:.0%}
                </div>
            </div>
            """)

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button(f"✍️ 选这段", key=f"ai_pick_{i}", use_container_width=True):
                    # 预填到下面的"书"和"摘录"字段
                    st.session_state["book"] = q.get("book", "📝 我自己的书")
                    st.session_state["author"] = ""
                    st.session_state["excerpt"] = q.get("text", "")
                    st.session_state["tags"] = st.session_state.get("_ai_topic", "")
                    st.session_state["emotion"] = emotion_cn
                    # v6.3.1 修: 标记这段是 AI 生成的, 海报页加 AI 水印
                    st.session_state["_latest_is_ai"] = True
                    # 跳回打字 tab
                    st.session_state.input_mode = "✍️ 打字"
                    st.success(f"🪔 已选第 {i+1} 段 — 切到打字 tab, 你可以微调再发布")
                    st.rerun()
            with col2:
                if st.button(f"⏭ 跳过", key=f"ai_skip_{i}", use_container_width=True):
                    pass
            with col3:
                st.caption("")

        # 重置按钮
        st.markdown("---")
        if st.button("🔄 重新生成", key="ai_regen", use_container_width=False):
            st.session_state.pop("_ai_quotes", None)
            st.rerun()

# 应用图片预填 (3 种图片模式都共用)
if st.session_state.get("_image_prefill"):
    pre = st.session_state.pop("_image_prefill")
    st.session_state["book"] = pre.get("book", "📝 我自己的书")
    st.session_state["author"] = pre.get("author", "")
    st.session_state["excerpt"] = pre.get("excerpt", "")
    st.session_state["tags"] = pre.get("tags", "")

st.markdown("---")
st.caption("下面手动微调, 然后发布 ↓")

BOOKS = {
    "百年孤独": ("加西亚·马尔克斯", "文学"),
    "人类简史": ("尤瓦尔·赫拉利", "历史"),
    "小王子": ("圣埃克苏佩里", "哲学"),
    "三体": ("刘慈欣", "科幻"),
    "被讨厌的勇气": ("岸见一郎 / 古贺史健", "心理"),
    "瓦尔登湖": ("梭罗", "自然"),
    "刀锋": ("毛姆", "文学"),
    "沉思录": ("马可·奥勒留", "哲学"),
}

# 选书
col1, col2 = st.columns([2, 1])
with col1:
    book_choice = st.selectbox(
        "书",
        options=list(BOOKS.keys()) + ["📝 我自己的书"],
        index=(list(BOOKS.keys()) + ["📝 我自己的书"]).index(
            st.session_state.get("book", "百年孤独")
        ) if st.session_state.get("book", "百年孤独") in (list(BOOKS.keys()) + ["📝 我自己的书"]) else 0,
        label_visibility="collapsed",
    )
with col2:
    if book_choice == "📝 我自己的书":
        custom_book = st.text_input("书名", value=st.session_state.get("book", ""), placeholder="你的书", label_visibility="collapsed")
    else:
        st.text_input(
            "作者",
            value=BOOKS[book_choice][0],
            disabled=True,
            label_visibility="collapsed",
        )

# 摘录
excerpt = st.text_area(
    "摘录",
    value=st.session_state.get("excerpt", ""),
    placeholder="把触动你的那段话贴进来...",
    height=100,
    label_visibility="collapsed",
)

# 感悟
reflection = st.text_area(
    "你的感悟 (可选)",
    value=st.session_state.get("reflection", ""),
    placeholder="我想到... / 这让我...",
    height=70,
    label_visibility="collapsed",
)

# 情绪 (学坐忘灯 + Are.na 简洁版)
emotion = st.radio(
    "情绪",
    options=["感动", "思考", "共鸣", "困惑", "反对", "平静"],
    horizontal=True,
    label_visibility="collapsed",
)

# 标签 (学 Are.na:自由连接,不强制分类)
tags = st.text_input(
    "标签 (逗号分隔,可选)",
    value=st.session_state.get("tags", ""),
    placeholder="比如: 孤独, 童年, 时间",
    label_visibility="collapsed",
)

if st.button("🪔 点亮这段", use_container_width=False):
    if not excerpt:
        st.warning("🪔 写一句话再发, 我等着")
    else:
        try:
            from data.reflection import BookExcerpt, Reflection

            if "reader_id" not in st.session_state:
                st.session_state.reader_id = hashlib.sha256(
                    f"reader_{datetime.datetime.now().isoformat()}".encode()
                ).hexdigest()[:12]

            if book_choice == "📝 我自己的书":
                book_title = custom_book or "未命名"
                book_author = "未知"
                book_domain = "其他"
            else:
                book_title = book_choice
                book_author, book_domain = BOOKS[book_choice]

            # XSS defense: escape user fields (import 已在文件顶部)
            ex = Reflection(
                reader_id=st.session_state.reader_id,
                campus_id=st.session_state.get("campus_id", "campus_A"),
                excerpt=BookExcerpt(
                    book_id=str(_uuid.uuid4())[:12],   # 自动生成 book_id
                    text=excerpt,
                    book_title=book_title,
                    author=book_author,
                    paragraph_id=str(_uuid.uuid4())[:8],  # 自动生成 paragraph_id
                    domain=book_domain,
                ),
                reflection_text=reflection or "(无文字,只标记)",
                emotion_label={"感动": "moved", "思考": "thinking", "共鸣": "resonance",
                               "困惑": "confused", "反对": "disagree", "平静": "calm"}[emotion],
                reading_duration_sec=float(min(3600, 30 + len(excerpt) * 0.5)),
            )
            # tags 和 reflection_depth 是 v6.1 demo 用的, 原 Reflection 不接受, 这里
            # 直接存到 session_state 供后续 心动林 / 我的心灯 / 段级匹配 用
            if "extra_reflections" not in st.session_state:
                st.session_state.extra_reflections = []
            st.session_state.extra_reflections.append({
                "tags": [t.strip() for t in tags.split(",") if t.strip()],
                "reflection_depth": min(1.0, 0.4 + (len(reflection or "") / 200.0) + (len(tags.split(",")) * 0.05)),
                "book_title": book_title,
                "author": book_author,
                "excerpt": excerpt,
                "reflection": reflection,
                "emotion": emotion,
                "ts": datetime.datetime.now().isoformat(),
            })

            if "reflections" not in st.session_state:
                st.session_state.reflections = []
            st.session_state.reflections.append(ex)

            from core.points import add_points
            add_points("excerpt_with_reflection")

            st.success("🪔 这段被点亮了 — 去「我的心灯」看看, 也欢迎去「心动林」看看谁也在这一刻停下来")
            st.balloons()

            # v6.3 联动: 一键生成金句海报
            # 注: st.page_link 不支持 query string, 改用 session_state 传 ref_id
            ref_id_for_poster = ex.authenticity_hash[:8] if ex.authenticity_hash else ""
            st.session_state["_latest_ref_id"] = ref_id_for_poster
            # 标记这段是不是 AI 生成 (海报页读这个标志加水印)
            # _latest_is_ai 是 AI 金句 tab 选段时设的, 点亮后**保留**标志
            # (海报页加 AI 水印); 下次再写摘录时**清掉**默认 False
            st.markdown("---")
            st.markdown("### 🪔 这段, 值得被更多人看见")
            st.caption("做成一张可分享的海报 — 朋友圈 1 个, 心灯 5 个")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.page_link(
                    "pages/10_poster.py",
                    label="🪔 生成金句海报",
                    icon="✨",
                )
            with col_p2:
                st.page_link(
                    "pages/2_resonance.py",
                    label="🌲 去心动林",
                    icon="🌲",
                )

            # 持久化: 存当前 ref 的快照 + 增量到 localStorage
            try:
                existing = st.session_state.get("_xindeng_persisted_refs", [])
                snap = {
                    "excerpt_text": ex.excerpt.text,
                    "book_title": ex.excerpt.book_title,
                    "author": ex.excerpt.author,
                    "domain": ex.excerpt.domain,
                    "reflection_text": ex.reflection_text,
                    "emotion_label": ex.emotion_label,
                    "reading_duration_sec": ex.reading_duration_sec,
                    "timestamp": ex.timestamp,
                    "authenticity_hash": ex.authenticity_hash,
                    "reflection_depth": ex.reflection_depth,  # property
                }
                existing.append(snap)
                st.session_state["_xindeng_persisted_refs"] = existing
                st.html(f"""
<script>
(function() {{
    try {{
        var refs = {repr([r for r in existing])};
        localStorage.setItem('xindeng_reflections', JSON.stringify(refs));
    }} catch(e) {{}}
}})();
</script>
""")
            except Exception as e:
                st.caption(f"💡 灯正在记下, 但本地暂存跳过 (不影响云): {str(e)[:50]}")
        except Exception as e:
            st.error(f"🪔 灯闪了一下 (保存失败: {str(e)[:80]})")

# 历史
st.markdown("---")
st.caption("你今天写过 →")
if st.session_state.get("reflections"):
    for r in reversed(st.session_state.reflections[-3:]):
        import html as _html
        safe_text = _html.escape(r.excerpt.text)
        safe_title = _html.escape(r.excerpt.book_title)
        st.markdown(f"""
        <div class="archive-card">
            <div class="archive-quote">「{safe_text[:80]}{'...' if len(safe_text) > 80 else ''}」</div>
            <div class="archive-meta">《{safe_title}》 · {r.emotion_label}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.caption("还没写过 — 试试上面 4 种方式")
