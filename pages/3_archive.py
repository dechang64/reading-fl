"""我的心灯 — 你写过的字, 永远在这里"""
import streamlit as st
import sys
import os
import datetime
import json as _json
import html as _html
from collections import Counter, defaultdict
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="我的心灯 · 心灯", page_icon="📖", layout="centered", initial_sidebar_state="auto")

# v6.1.2 改进: 从 localStorage 恢复 reflections (跨刷新持久化)
st.html("""
<script>
(function() {
    try {
        var saved = localStorage.getItem('xindeng_reflections');
        if (saved) {
            // 用 query param 触发 streamlit 重新跑 + 读 localStorage
            var url = new URL(window.parent.location.href);
            if (!url.searchParams.get('restored_refs')) {
                url.searchParams.set('restored_refs', '1');
                url.searchParams.set('refs', encodeURIComponent(saved));
                window.parent.location.href = url.toString();
            }
        }
    } catch(e) {}
})();
</script>
""")

# 从 query param 恢复
qparams = st.query_params
if qparams.get("restored_refs") == "1":
    try:
        refs = _json.loads(qparams.get("refs", "[]"))
        if refs:
            # 重构成 session_state 兼容的列表 (用 dict 模拟 Reflection)
            if "_xindeng_restored_refs" not in st.session_state:
                st.session_state["_xindeng_restored_refs"] = refs
    except Exception:
        pass

# 优先用 session_state.reflections, 否则从 _xindeng_restored_refs 恢复
reflections_raw = st.session_state.get("reflections", [])
if not reflections_raw and st.session_state.get("_xindeng_restored_refs"):
    # 转换 dict → 类 Reflection 对象 (用 SimpleNamespace, top import)
    reflections_raw = []
    for r in st.session_state["_xindeng_restored_refs"]:
        ex = SimpleNamespace(
            text=r.get("excerpt_text", ""),
            book_title=r.get("book_title", ""),
            author=r.get("author", ""),
            domain=r.get("domain", "其他"),
        )
        ref = SimpleNamespace(
            excerpt=ex,
            reflection_text=r.get("reflection_text", ""),
            emotion_label=r.get("emotion_label", ""),
            reading_duration_sec=r.get("reading_duration_sec", 0),
            timestamp=r.get("timestamp", ""),
            authenticity_hash=r.get("authenticity_hash", ""),
            reflection_depth=r.get("reflection_depth", 0.5),
        )
        reflections_raw.append(ref)

st.markdown("""
<style>
:root { --bg: #0d0d0f; --card: rgba(255,255,255,0.04); --card-hover: rgba(255,255,255,0.07);
        --text: #e8e4dc; --text-muted: #8b8680; --text-dim: #5a5650;
        --accent: #d4a574; --ember: #c4694a; --border: rgba(212,165,116,0.15); }
.stApp { background: linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%); }
.main .block-container { max-width: 720px; padding-top: 1.5rem; }
h1, h2, h3 { color: var(--text) !important; font-weight: 500 !important; }
h1 { font-size: 1.7rem !important; }
h3 { font-size: 0.85rem !important; color: var(--text-muted) !important;
     text-transform: uppercase; letter-spacing: 0.18em; }
p, .stMarkdown { color: var(--text) !important; line-height: 1.7; }
.stCaption { color: var(--text-muted) !important; }
.stButton > button[kind="secondary"] {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.timeline-day {
    border-left: 1px solid var(--border);
    padding-left: 1.2rem;
    margin: 0.5rem 0 1.5rem 0.5rem;
    position: relative;
}
.timeline-day::before {
    content: "🪔";
    position: absolute;
    left: -0.5rem;
    background: var(--bg);
    padding-right: 0.3rem;
}
.timeline-date {
    color: var(--accent);
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
    font-weight: 500;
}
.excerpt-card {
    background: var(--card);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    border: 1px solid var(--border);
}
.excerpt-quote { color: var(--text); font-size: 0.92rem; font-style: italic; line-height: 1.55; }
.excerpt-meta { color: var(--text-muted); font-size: 0.75rem; margin-top: 0.3rem; }
.tag-pill {
    display: inline-block;
    background: rgba(212, 165, 116, 0.15);
    color: var(--accent);
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
    font-size: 0.7rem;
    margin-right: 0.3rem;
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

st.markdown("# 我的心灯")
st.caption("你的所有摘录 — 按时间倒序,带标签连接")

# v6.1.2: reflections_raw 已在外层从 localStorage 恢复
reflections = reflections_raw  # 已经在文件顶部恢复

if not reflections:
    st.caption("还没有记录。回到首页 [写摘录] 点亮你的第一段")
    if st.button("去写摘录"):
        st.switch_page("pages/1_excerpt.py")
else:
    # 顶部统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总摘录", len(reflections))
    with col2:
        st.metric("覆盖书", len(set(r.excerpt.book_title for r in reflections)))
    with col3:
        avg_depth = sum(r.reflection_depth for r in reflections) / len(reflections)
        st.metric("平均深度", f"{avg_depth:.0%}")
    with col4:
        # 主导情绪
        emo_counts = Counter(r.emotion_label for r in reflections)
        dominant = emo_counts.most_common(1)[0][0] if emo_counts else "-"
        emo_cn = {
            "moved": "💧 感动", "thinking": "🌊 思考", "resonance": "🔗 共鸣",
            "confused": "🌫️ 困惑", "disagree": "⚡ 反对", "calm": "🍃 平静",
        }
        st.metric("主情绪", emo_cn.get(dominant, dominant))

    # 标签云 (学 Are.na)
    tags_index = st.session_state.get("tags_index", {})
    if tags_index:
        st.markdown("### 你的标签")
        st.caption("点击标签,看相关摘录 (学 Are.na 的「连接」思想)")
        tag_cols = st.columns(min(len(tags_index), 4) or 1)
        for i, (tag, refs) in enumerate(tags_index.items()):
            with tag_cols[i % len(tag_cols)]:
                if st.button(f"#{tag} ({len(refs)})", key=f"tag_{tag}", use_container_width=True):
                    st.session_state[f"_tag_filter"] = tag

    # 过滤
    active_tag = st.session_state.get("_tag_filter")
    if active_tag:
        st.caption(f"正在筛选标签: #{active_tag}")
        # 简单过滤(基于 timestamp 匹配)
        if active_tag in tags_index:
            ts_set = set(tags_index[active_tag])
            reflections = [r for r in reflections if r.timestamp in ts_set]
        if st.button("清除筛选", type="secondary"):
            st.session_state.pop("_tag_filter", None)
            st.rerun()

    # 时间线
    st.markdown("### 时间线")

    # 按天分组
    by_day = defaultdict(list)
    for r in reflections:
        try:
            day = r.timestamp[:10]  # YYYY-MM-DD
            by_day[day].append(r)
        except Exception:
            by_day["未知"].append(r)

    # 倒序
    for day in sorted(by_day.keys(), reverse=True):
        items = sorted(by_day[day], key=lambda r: r.timestamp, reverse=True)
        try:
            day_obj = datetime.date.fromisoformat(day)
            today = datetime.date.today()
            days_ago = (today - day_obj).days
            if days_ago == 0:
                date_text = "今天"
            elif days_ago == 1:
                date_text = "昨天"
            elif days_ago < 7:
                date_text = f"{days_ago} 天前"
            elif days_ago < 30:
                date_text = f"{days_ago // 7} 周前"
            else:
                date_text = f"{days_ago // 30} 个月前"
        except Exception:
            date_text = day

        st.markdown(f'<div class="timeline-day"><div class="timeline-date">{date_text} · {day}</div>', unsafe_allow_html=True)

        for r in items:
            emo_cn = {
                "moved": "💧 感动", "thinking": "🌊 思考", "resonance": "🔗 共鸣",
                "confused": "🌫️ 困惑", "disagree": "⚡ 反对", "calm": "🍃 平静",
            }.get(r.emotion_label, r.emotion_label)

            # XSS defense (审计 #1): escape all user fields
            # 用 st.html 默认就渲染 HTML (DOMPurify sanitize), 比 st.markdown(unsafe_allow_html=True) 更安全
            safe_text = _html.escape(r.excerpt.text)
            safe_title = _html.escape(r.excerpt.book_title)
            safe_refl = _html.escape(r.reflection_text) if r.reflection_text != "(无文字,只标记)" else None
            st.html(f"""
            <div class="excerpt-card">
                <div class="excerpt-quote">「{safe_text}」</div>
                {f'<div style="color:var(--text-muted);font-size:0.85rem;margin-top:0.3rem;">{safe_refl}</div>' if safe_refl else ''}
                <div class="excerpt-meta">
                    《{safe_title}》 · {emo_cn} · 深度 {r.reflection_depth:.0%}
                </div>
            </div>
            """)

        st.html('</div>')
