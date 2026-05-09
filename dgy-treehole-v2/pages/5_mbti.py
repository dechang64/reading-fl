"""MBTI 红楼梦情境化测试 — 完整版

8题情境化测试，16种MBTI类型，每种映射到红楼梦角色+场景+疗法。
界面完全对齐原版 index.html 的 MBTI 页面。
"""

import streamlit as st
from core.mbti_data import (
    MBTI_QUESTIONS, MBTI_MAP, DIM_LABELS, DIM_DESCS, calc_mbti,
)
from core.config import SCENE_MAP

st.set_page_config(page_title="心灵指引 · 大观园树洞", page_icon="🔮", layout="centered")

# ── 返回 ──
if st.button("← 回到大观园", use_container_width=True):
    st.switch_page("app.py")

# ── 初始化 ──
if "mbti_answers" not in st.session_state:
    st.session_state.mbti_answers = {}
if "mbti_result" not in st.session_state:
    st.session_state.mbti_result = None

# ═══════════════════════════════════════════════════════════
#  答题阶段
# ═══════════════════════════════════════════════════════════
if st.session_state.mbti_result is None:
    answered = len(st.session_state.mbti_answers)

    # Hero（对齐原版 .hero）
    st.markdown("""
<div style="background:linear-gradient(135deg,#2c1810,#4a2c1a 50%,#3d1f0e);
            padding:2rem 1.5rem;color:#f5f0e8;text-align:center;border-radius:0 0 16px 16px;
            position:relative;overflow:hidden;">
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(184,134,11,0.12),transparent 60%);pointer-events:none;"></div>
    <h1 style="font-size:1.4rem;position:relative;">🔮 心灵指引</h1>
    <p style="opacity:0.7;font-size:0.85rem;position:relative;">8道红楼梦情境题，找到最适合你的倾听者</p>
</div>
""", unsafe_allow_html=True)

    # 进度条（对齐原版 .progress）
    st.markdown(f"""
<div style="padding:0.8rem;">
    <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#8b7355;margin-bottom:0.3rem;">
        <span>第 {answered}/8 题</span>
        <span>{answered * 12}%</span>
    </div>
    <div style="background:#e8dfd0;border-radius:99px;height:8px;overflow:hidden;">
        <div style="background:linear-gradient(90deg,#c0392b,#b8860b);height:100%;width:{answered * 12}%;border-radius:99px;transition:width 0.3s;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

    if answered >= 8:
        # 计算结果
        mbti = calc_mbti(st.session_state.mbti_answers)
        st.session_state.mbti_result = mbti
        st.rerun()

    # 当前题目
    q = MBTI_QUESTIONS[answered]
    st.markdown(f"""
<div class="card fade-in" style="text-align:center;">
    <div style="font-size:0.75rem;color:#b8860b;margin-bottom:0.3rem;">第 {answered + 1} 题</div>
    <div style="font-size:1rem;font-weight:600;color:#2c1810;line-height:1.6;">{q['q']}</div>
</div>
""", unsafe_allow_html=True)

    # 选项（对齐原版 .q-opt 样式）
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(q["a"], key=f"opt_a_{answered}", use_container_width=True):
            st.session_state.mbti_answers[answered] = q["at"]
            st.rerun()
    with col_b:
        if st.button(q["b"], key=f"opt_b_{answered}", use_container_width=True):
            st.session_state.mbti_answers[answered] = q["bt"]
            st.rerun()

# ═══════════════════════════════════════════════════════════
#  结果阶段（对齐原版 showMBTIResult）
# ═══════════════════════════════════════════════════════════
else:
    mbti = st.session_state.mbti_result
    info = MBTI_MAP.get(mbti, MBTI_MAP["INFP"])
    scene = SCENE_MAP.get(info["scene"], {})

    # Hero
    st.markdown("""
<div style="background:linear-gradient(135deg,#2c1810,#4a2c1a 50%,#3d1f0e);
            padding:1.5rem;color:#f5f0e8;text-align:center;border-radius:0 0 16px 16px;
            position:relative;overflow:hidden;">
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(184,134,11,0.12),transparent 60%);pointer-events:none;"></div>
    <h1 style="font-size:1.4rem;position:relative;">🔮 你的心灵指引</h1>
    <p style="opacity:0.7;font-size:0.85rem;position:relative;">大观园中，有一处院落等着你</p>
</div>
""", unsafe_allow_html=True)

    # MBTI 类型（对齐原版 .result-type）
    st.markdown(f"""
<div style="padding:0.8rem;">
    <div class="result-type">{mbti}</div>
    <div class="result-desc">{info['desc']}</div>

    <div class="result-scene">
        <div class="icon">{scene.get('icon', '🌸')}</div>
        <div>
            <div class="name">推荐：{info['scene']}</div>
            <div class="info">倾听者：{info['char']} · {info['theory']}</div>
        </div>
    </div>

    <div class="result-reason">
        <div style="font-size:0.78rem;color:#c0392b;font-weight:600;margin-bottom:0.3rem;">💡 为什么适合你</div>
        {info['reason']}
    </div>

    <div class="result-quote">"{info['quote']}"</div>
</div>
""", unsafe_allow_html=True)

    # 维度解析（4个维度卡片）
    st.markdown("### 维度解析")
    dim_items = ""
    for letter in mbti:
        dim_items += f"""
<div style="background:#fff;border-radius:8px;padding:0.4rem;text-align:center;
            border:1px solid #e8dfd0;">
    <div style="font-size:1.1rem;font-weight:700;color:#c0392b;">{letter}</div>
    <div style="font-size:0.65rem;color:#8b7355;margin-top:0.1rem;">{DIM_LABELS[letter]}</div>
    <div style="font-size:0.6rem;color:#2c1810;margin-top:0.2rem;">{DIM_DESCS[letter]}</div>
</div>"""
    st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.4rem;margin:0.8rem 0;">
    {dim_items}
</div>
""", unsafe_allow_html=True)

    # 操作按钮（对齐原版底部按钮组）
    if st.button(f"💬 进入{info['scene']}找{info['char']}聊聊", type="primary", use_container_width=True):
        st.session_state.current_scene = info["scene"]
        st.session_state.chat_character = info["char"]
        st.session_state.chat_history = []
        st.switch_page("pages/1_chat.py")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⭐ 改选星座", use_container_width=True):
            st.switch_page("pages/7_zodiac.py")
    with col2:
        if st.button("🔄 重新测试", use_container_width=True):
            st.session_state.mbti_answers = {}
            st.session_state.mbti_result = None
            st.rerun()
