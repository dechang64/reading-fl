"""心灯周报 — User 触发生成, 看到 HTML 周报 + 199 元/年 会员墙

简化设计:
- 不用 CRON (streamlit cloud 不支持)
- 不用 Resend API (v6.5 接)
- 用户点按钮 → 立刻生成 + 渲染
- 199 元/年 会员 → 解锁"自动订阅 + 真发邮件"
"""
import streamlit as st
import sys
import os
import html as _html

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="心灯周报",
    page_icon="📩",
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
     text-transform: uppercase; letter-spacing: 0.18em; }
p, .stMarkdown { color: var(--text) !important; line-height: 1.7; }
.stCaption { color: var(--text-muted) !important; }
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--ember) 100%) !important;
    color: #0d0d0f !important; border: none !important; border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important; font-weight: 600 !important;
}
.stButton > button[kind="secondary"] {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.weekly-wrap {
    background: #f4ede0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    margin: 1.5rem 0;
}
.summary-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
}
.stat-row { display: flex; justify-content: space-between; padding: 0.5rem 0; }
.stat-label { color: var(--text-muted); font-size: 0.85rem; }
.stat-value { color: var(--text); font-weight: 600; }
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
    background: #0d0d0f !important; color: #e8e4dc !important;
}
.main .block-container, .main p, .main h1, .main h2, .main h3, .main h4,
.main .stMarkdown, .main .stText, .main .stCaption { color: #e8e4dc !important; }
</style>
""", unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")

st.markdown("# 📩 心灯周报")
st.caption("你读过的字, 每周一封信 — 199 元/年 会员, 自动订阅")

# ══════════════════════════════════════════════════════════════
#  1. 摘要
# ══════════════════════════════════════════════════════════════
from core.weekly import get_weekly_summary

summary = get_weekly_summary()

st.markdown('<div class="summary-card">', unsafe_allow_html=True)
st.html(f"""
<div class="stat-row">
    <div class="stat-label">📚 本周摘录数</div>
    <div class="stat-value">{summary['ref_count']} 段</div>
</div>
<div class="stat-row">
    <div class="stat-label">🪔 本周海报数</div>
    <div class="stat-value">{summary['poster_count']} 张</div>
</div>
<div class="stat-row">
    <div class="stat-label">📅 今年第几周</div>
    <div class="stat-value">#{summary['week']}</div>
</div>
""")

# 情绪分布
if summary["emotion_breakdown"]:
    emotion_cn = {
        "moved": "感动", "thinking": "思考", "resonance": "共鸣",
        "confused": "困惑", "disagree": "反对", "calm": "平静",
    }
    em_rows = ""
    for em, n in summary["emotion_breakdown"].items():
        em_rows += f'<div class="stat-row"><div class="stat-label">💗 {emotion_cn.get(em, em)}</div><div class="stat-value">{n} 次</div></div>'
    st.html(em_rows)

st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  2. 生成按钮
# ══════════════════════════════════════════════════════════════
if "weekly_html" not in st.session_state:
    st.session_state.weekly_html = None
    st.session_state.weekly_ai_comment = ""
    st.session_state.weekly_generated = False

if st.button("🪔 生成我的本周金句周报", use_container_width=True, type="primary"):
    from core.weekly import (
        render_weekly_html, _get_weekly_reflections, _get_weekly_posters,
        _generate_ai_comment, get_week_number,
    )
    from core.amax_chat import chat as amax_chat

    with st.spinner("🪔 心灯精灵正在为你整理..."):
        refs = _get_weekly_reflections()
        posters = _get_weekly_posters()

        # AI 评语 (1 次 AMAX 调用)
        ai_comment = _generate_ai_comment(refs, amax_chat)

        # 用户画像
        user_mbti = st.session_state.get("user_mbti", "—")
        user_zodiac = st.session_state.get("user_zodiac", "—")
        user_level = st.session_state.get("user_level_name", "L1 初见者")

        # 渲染
        html_content = render_weekly_html(
            reader_mbti=user_mbti,
            reader_zodiac=user_zodiac,
            reader_level=user_level,
            weekly_refs=refs,
            weekly_posters=posters,
            ai_comment=ai_comment,
            week_number=get_week_number(),
        )

        st.session_state.weekly_html = html_content
        st.session_state.weekly_ai_comment = ai_comment
        st.session_state.weekly_generated = True

    st.success("🪔 周报已生成 — 下方可截图保存或分享")
    st.rerun()

# ══════════════════════════════════════════════════════════════
#  3. 渲染周报
# ══════════════════════════════════════════════════════════════
if st.session_state.weekly_generated and st.session_state.weekly_html:
    st.markdown("---")
    st.markdown("### 📜 本周周报")
    st.caption("右键 → 截图保存 / 复制 HTML 邮件正文")

    # 包裹在白底容器
    st.html(f"""
    <div class="weekly-wrap">
    {st.session_state.weekly_html}
    </div>
    """)

    # AI 评语单独显示 (Text 模式, 方便复制)
    st.markdown("### 🪔 心灯精灵 这周想跟你说")
    st.markdown(f"*{st.session_state.weekly_ai_comment}*")

    # 复制按钮 (用 st.html 嵌入复制 JS)
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 复制 HTML 源码", use_container_width=True):
            st.html(f"""
            <script>
            navigator.clipboard.writeText({repr(st.session_state.weekly_html)});
            </script>
            """)
            st.caption("🪔 HTML 已复制到剪贴板 (用邮件客户端粘贴)")
    with col2:
        if st.button("🔄 重新生成", use_container_width=True):
            st.session_state.weekly_html = None
            st.session_state.weekly_generated = False
            st.rerun()

# ══════════════════════════════════════════════════════════════
#  4. 会员墙 (199 元/年 解锁自动订阅)
# ══════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🪔 199 元/年 会员 — 自动订阅")

is_member = st.session_state.get("is_paid_member", False)

if is_member:
    st.success("🪔 你是心灯会员 — 自动订阅已开启 (周一 9:00 发邮件)")
else:
    st.info(
        "💡 **199 元/年 会员**:\n\n"
        "- 📩 **自动每周一发邮件** (不用自己点按钮)\n"
        "- 🪔 **金句海报无限** (省 395 元/年)\n"
        "- 💾 **离线下载** (通勤路上, 飞机上都能读)\n"
        "- 🤖 **高级 AI 评语** (AMAX 调用升级)\n\n"
        "🪔 我在等一个仪式感的你, 不会催, 也不会打扰"
    )
    if st.button("🪔 成为心灯会员 ¥199/年", use_container_width=True, type="primary"):
        st.session_state.is_paid_member = True
        st.success("🪔 欢迎成为心灯会员 — 下周一 9:00 第一封周报自动发到你的邮箱 (开发中, v6.5 上线)")
        st.balloons()
        st.rerun()

# ══════════════════════════════════════════════════════════════
#  5. 底部链接
# ══════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🪔 下一步")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.page_link("pages/1_excerpt.py", label="✍️ 写摘录", icon="✍️")
with col_b:
    st.page_link("pages/2_resonance.py", label="🌳 心动林", icon="🌳")
with col_c:
    st.page_link("pages/10_poster.py", label="🪔 海报", icon="✨")
