"""精灵 — 跟你的心灯精灵聊聊 (心灵语气)"""
import streamlit as st
import sys
import os
import hashlib
import datetime
import html as _html
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="精灵 · 心灯", page_icon="🕯️", layout="centered", initial_sidebar_state="auto")

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
.stTextInput input, .stTextArea textarea {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important;
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important; border: none !important; border-radius: 8px !important;
}
.stButton > button[kind="secondary"] {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.privacy-strip {
    background: linear-gradient(90deg, rgba(196,105,74,0.1) 0%, rgba(212,165,116,0.1) 100%);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 0.7rem 1rem; color: var(--accent);
    font-size: 0.88rem; text-align: center; margin: 1rem 0;
}
.context-strip {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}
.genie-msg {
    background: linear-gradient(135deg, rgba(212,165,116,0.15) 0%, rgba(196,105,74,0.1) 100%);
    border: 1px solid var(--border);
    border-radius: 12px 12px 12px 4px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    color: var(--text);
    max-width: 80%;
}
.genie-msg::before {
    content: "🕯️ 精灵 · ";
    color: var(--accent);
    font-size: 0.8rem;
}
.user-msg {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px 12px 4px 12px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    color: var(--text);
    max-width: 80%;
    margin-left: auto;
}
@media (max-width: 640px) {
    .main .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    h1 { font-size: 1.4rem !important; }
    .stTextArea textarea { min-height: 80px !important; font-size: 16px !important; }
    .stButton > button { width: 100% !important; min-height: 44px !important; }
}
</style>
""", unsafe_allow_html=True)


# 兼容老 webview:深 fallback CSS
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;\n}\nsection[data-testid="stSidebar"] * {\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] h1,\nsection[data-testid="stSidebar"] h2,\nsection[data-testid="stSidebar"] h3,\nsection[data-testid="stSidebar"] p,\nsection[data-testid="stSidebar"] span,\nsection[data-testid="stSidebar"] a,\nsection[data-testid="stSidebar"] .stCaption {\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p,\n.main h1, .main h2, .main h3, .main h4,\n.main .stMarkdown, .main .stText, .main .stCaption {\n    color: #e8e4dc !important;\n}\n</style>', unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")

st.markdown("# 🕯️ 心灯精灵")
st.caption("你的 AI 读书搭子 — 根据画像调整风格")
st.markdown("""
<div class="privacy-strip">
    🔒 精灵只看你最近的本地画像 — 不会看你的书摘原文
</div>
""", unsafe_allow_html=True)

# 画像
reflections = st.session_state.get("reflections", [])
recent_books = list(dict.fromkeys(r.excerpt.book_title for r in reflections[-10:])) if reflections else []
recent_emos = [r.emotion_label for r in reflections[-10:]] if reflections else []

st.markdown("### 你的最近画像")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**最近读**")
    if recent_books:
        for b in recent_books[:5]:
            st.caption(f"《{b}》")
    else:
        st.caption("(无)")
with col2:
    st.markdown("**最近情绪**")
    if recent_emos:
        from collections import Counter as C  # noqa  嵌套: 不影响主流程
        emo_cn = {
            "moved": "感动", "thinking": "思考", "resonance": "共鸣",
            "confused": "困惑", "disagree": "反对", "calm": "平静",
        }
        counts = C(emo_cn.get(e, e) for e in recent_emos)
        for label, cnt in counts.most_common(3):
            st.caption(f"{label} · {cnt}")
    else:
        st.caption("(无)")

# 风格
def pick_style(emos):
    if not emos:
        return "安静陪伴型"
    dom = max(set(emos), key=emos.count)
    return {
        "moved": "情感共鸣型", "thinking": "思辨探索型", "resonance": "寻找回响型",
        "confused": "共同探索型", "disagree": "辩论陪练型", "calm": "安静倾听型",
    }.get(dom, "安静陪伴型")

style = pick_style(recent_emos)
st.markdown(f"**当前风格:** {style}")

# 对话
if "genie_history" not in st.session_state:
    st.session_state.genie_history = []

for msg in st.session_state.genie_history:
    safe_content = _html.escape(msg["content"])
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{safe_content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="genie-msg">{safe_content}</div>', unsafe_allow_html=True)

user_input = st.chat_input("跟精灵说点什么...")

if user_input:
    st.session_state.genie_history.append({"role": "user", "content": user_input})

    # 尝试 AMAX — 直接 import reading-fl 自带的 core.amax_chat
    # (不依赖 ../dgy-treehole 兄弟 repo,share.streamlit.io 才能跑)
    reply = None
    amax_error = None
    try:
        from core.amax_chat import chat as amax_chat, _is_mock
        if _is_mock():
            amax_error = "未配置 AMAX_API_KEY (在 .streamlit/secrets.toml 或 share.streamlit.io Secrets 添加)"
        else:
            sys_prompt = f"""你是读者的心灯精灵,像心里的灯一样。当前风格:{style}。
读者最近读:{', '.join(recent_books) if recent_books else '无'}。
读者最近情绪:{', '.join(recent_emos) if recent_emos else '无'}。

要求: 不超过 4 句。不说教,不评判。用第一人称「我」对话。引用读者最近读过的书(如果有)。"""
            messages = [{"role": "system", "content": sys_prompt}]
            for m in st.session_state.genie_history[-6:]:
                messages.append(m)
            r = amax_chat(messages=messages, character="心灯精灵",
                          personality_params={"tone": "warm"}, max_tokens=300)
            # amax_chat 失败时返回 "💭 *(...)*\n\n{mock}",我们把这种当成 fallback
            if r and not r.lstrip().startswith("💭"):
                reply = r
            elif r:
                amax_error = r.split("\n", 1)[0]  # 截第一行
    except Exception as e:
        amax_error = f"{type(e).__name__}: {e}"

    if amax_error:
        st.caption(f"🪔 {amax_error[:120]}")

    # 兜底 — 画像为空时**不**编造书名/情绪,诚实地回"我们从零开始"
    if not reply:
        if recent_books or recent_emos:
            # 有画像 → 真实引用
            emo_cn = {
                "moved": "感动", "thinking": "思考", "resonance": "共鸣",
                "confused": "困惑", "disagree": "反对", "calm": "平静",
            }
            recent_emo_cn = emo_cn.get(recent_emos[-1], "思考") if recent_emos else "思考"
            recent_book = recent_books[0] if recent_books else "一本书"
            reply = (
                f"你说:「{user_input}」\n\n"
                f"你最近在《{recent_book}》里读到了「{recent_emo_cn}」的命题。"
                f"愿意多说一些吗?"
            )
        else:
            # 画像为空 → 诚实地开启对话,不要编造
            reply = (
                f"你说:「{user_input}」\n\n"
                f"你还没有写过摘录(画像是空的)。先去【写摘录】点亮第一段,\n"
                f"我才能更懂你。现在 — 你最近在读什么?"
            )

    st.session_state.genie_history.append({"role": "assistant", "content": reply})
    st.rerun()
