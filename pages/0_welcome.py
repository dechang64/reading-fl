"""心灯 · 欢迎 — 5 秒决断

v6.1.2 改进 (用户反馈"每次都要填一堆"):
- 顶部 "🪔 立刻体验" 大按钮, 0 步进主页
- 下面折叠式 1 步问卷 (可选, 不强制)
- localStorage 持久化 (跨刷新不丢)
- 老 webview 降级: 1 步问卷内可答

防 spam 仍保留 (问卷里) + 1 道情感画像 (FL 训练用, 可选)
"""
import streamlit as st
import sys
import os
import json as _json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="欢迎 · 心灯",
    page_icon="🪔",
    layout="centered",
    initial_sidebar_state="auto",
)

# === 跳过条件 ===
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

# localStorage 持久化
st.html("""
<script>
(function() {
    try {
        var done = localStorage.getItem('xindeng_onboarded');
        if (done === '1') {
            var url = new URL(window.parent.location.href);
            if (!url.searchParams.get('restored')) {
                url.searchParams.set('restored', '1');
                var saved = localStorage.getItem('xindeng_profile');
                if (saved) url.searchParams.set('profile', encodeURIComponent(saved));
                window.parent.location.href = url.toString();
            }
        }
    } catch(e) {}
})();
</script>
""")

qparams = st.query_params
if qparams.get("restored") == "1":
    st.session_state.onboarded = True
    try:
        profile = _json.loads(qparams.get("profile", "{}"))
        for k, v in profile.items():
            st.session_state[k] = v
    except Exception:
        pass

if st.session_state.onboarded:
    st.success("🪔 欢迎回来")
    st.switch_page("app.py")

# === 顶部: 1 键立刻进 (用户最想要的) ===
st.markdown("""
<style>
.welcome-hero {
    background: linear-gradient(180deg, rgba(212,165,116,0.10) 0%, rgba(196,105,74,0.05) 100%);
    border: 1px solid rgba(212,165,116,0.30);
    border-radius: 12px;
    padding: 1.5rem 1rem;
    margin: 1rem 0;
    text-align: center;
}
.welcome-tag {
    display: inline-block;
    background: rgba(212,165,116,0.15);
    color: var(--accent);
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="welcome-hero">
  <div class="welcome-tag">🪔 心灯 · Reading-FL</div>
  <h1 style="margin: 0.5rem 0; font-size: 1.5rem;">读到一段, 找到另一个停下来的人</h1>
  <p style="color: var(--text-muted); font-size: 0.9rem; margin: 0.3rem 0 1rem 0;">
    你读过的字, 在陌生人那里被看见 · 读完一段的反思, 永久沉淀
  </p>
</div>
""", unsafe_allow_html=True)

# 0 步进 — 顶部大按钮
st.markdown("### 0 步进 →")
if st.button("🪔 立刻体验", type="primary", use_container_width=True, key="enter_now"):
    st.session_state.onboarded = True
    st.html("""
<script>
(function() { try { localStorage.setItem('xindeng_onboarded', '1'); localStorage.setItem('xindeng_profile', '{}'); } catch(e) {} })();
</script>
""")
    st.switch_page("app.py")

st.caption("或, 答 1 个问题让我更懂你 ↓")

# === 下面: 可选 1 步问卷 (折叠式, 不强制) ===
with st.expander("🪔 答 1 个问题 (可选 — 帮灯更懂你)", expanded=False):
    st.caption("10 秒。选 ≥3 个情感标签 + 勾真人, 我就能更好推荐段级被看见。")

    emotion_options = [
        "💧 感动", "🌊 思考", "🔗 共鸣", "🌫️ 困惑", "⚡ 反对", "🍃 平静",
        "🔥 愤怒", "😢 悲伤", "✨ 治愈", "🌱 成长", "🌀 迷茫", "💪 坚定",
    ]
    emotions = st.pills(
        "可以多选",
        options=emotion_options,
        selection_mode="multi",
        label_visibility="collapsed",
        key="welcome_emotions",
    )
    n_emo = len(emotions) if emotions else 0
    if n_emo > 0 and n_emo < 3:
        st.caption(f"🪔 再选 {3 - n_emo} 个")
    elif n_emo >= 3:
        st.caption(f"🪔 已选 {n_emo} 个 — 完美")

    anti_spam = st.checkbox("我是真人, 不是机器人", key="anti_spam")

    can_go = (n_emo >= 3 and anti_spam)
    if st.button(
        "🪔 让我进来",
        type="primary",
        disabled=not can_go,
        use_container_width=True,
        key="enter_with_survey",
    ):
        st.session_state.onboarded = True
        st.session_state.user_emotions = list(emotions or [])
        st.html(f"""
<script>
(function() {{
    try {{
        localStorage.setItem('xindeng_onboarded', '1');
        var profile = {{
            user_emotions: {repr(list(emotions or []))},
            user_pain: "", user_genre: "", user_purpose: ""
        }};
        localStorage.setItem('xindeng_profile', JSON.stringify(profile));
    }} catch(e) {{}}
}})();
""")
        st.switch_page("app.py")

    if not can_go:
        missing = []
        if n_emo < 3: missing.append(f"选 {max(0, 3 - n_emo)} 个情感")
        if not anti_spam: missing.append("勾真人")
        if missing:
            st.caption(f"🪔 还差: {', '.join(missing)}")
