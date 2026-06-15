"""情绪洞察 — 联邦学习仪表盘

展示：
- 当前会话的情绪画像
- 全局情绪趋势（联邦聚合结果）
- FL 轮次历史
- 隐私保护说明
"""

import streamlit as st
from core.fl_engine import get_global_emotion_trend, compute_entropy, compute_confidence
from core.emotion_detector import compute_session_emotion_profile
from core.config import EMOTIONS, MOCK_MODE

st.set_page_config(page_title="情绪洞察 · 大观园树洞", page_icon="📊", layout="centered")
from core.styles import inject_css; inject_css()

# ── 返回 ──
if st.button("← 回到大观园", use_container_width=True):
    st.switch_page("app.py")

st.markdown("""
<div class="card-dark" style="text-align:center; padding: 1.5rem;">
    <div style="font-size: 2.5rem;">📊</div>
    <h2 style="margin: 0.5rem 0;">情绪洞察</h2>
    <p style="font-size: 0.85rem; color: #d4c5a9;">联邦学习保护下的情绪趋势</p>
</div>
""", unsafe_allow_html=True)

# ── 隐私说明 ──
st.markdown("""
<div class="card" style="border-left: 3px solid #2d6a4f;">
    <strong>🔒 隐私保护说明</strong><br>
    <span style="font-size: 0.85rem; color: #8b7355;">
    你的聊天内容不会被存储或传输。系统只提取情绪统计量（如"悲伤30%、焦虑20%"），
    通过联邦学习聚合后用于优化服务。统计量无法逆推原始对话内容。
    </span>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  当前会话情绪画像
# ═══════════════════════════════════════════════════════════
st.markdown("### 🧘 你的情绪画像")

chat_history = st.session_state.get("chat_history", [])
if chat_history:
    profile = compute_session_emotion_profile(chat_history)
    if profile:
        entropy = compute_entropy(profile)
        confidence = compute_confidence(profile)

        # 情绪分布条
        st.markdown(f"""
<div class="card">
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
        <span>置信度</span>
        <span style="color: #b8860b;"><strong>{confidence:.0%}</strong></span>
    </div>
    <div style="background: #e8dfd0; border-radius: 99px; height: 8px; overflow: hidden;">
        <div style="background: #2d6a4f; height: 100%; width: {confidence*100}%; border-radius: 99px;"></div>
    </div>
    <div style="font-size: 0.75rem; color: #8b7355; margin-top: 0.3rem;">
        熵值: {entropy:.2f} bits · {"情绪集中" if confidence > 0.7 else "情绪分散"}
    </div>
</div>
""", unsafe_allow_html=True)

        # 情绪分布
        sorted_emotions = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        for emotion, score in sorted_emotions:
            if score > 0.01:
                st.markdown(f"""
<div style="margin: 0.3rem 0;">
    <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
        <span>{emotion}</span>
        <span>{score:.1%}</span>
    </div>
    <div style="background: #e8dfd0; border-radius: 99px; height: 6px; overflow: hidden;">
        <div style="background: #b8860b; height: 100%; width: {score*100}%; border-radius: 99px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="text-align:center; padding: 1rem; color: #8b7355;">
    还没有足够的对话数据来生成情绪画像<br>
    <span style="font-size: 0.8rem;">去和角色聊几句吧</span>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div style="text-align:center; padding: 1rem; color: #8b7355;">
    还没有对话记录<br>
    <span style="font-size: 0.8rem;">去和角色聊几句吧</span>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  全局情绪趋势（联邦聚合）
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🌐 全局情绪趋势（联邦聚合）")

try:
    trend = get_global_emotion_trend()
except Exception:
    trend = {"current": {}, "rounds": [], "total_clients": 0, "total_rounds": 0}

st.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="display: flex; justify-content: space-around;">
        <div>
            <div style="font-size: 1.5rem; font-weight: 600; color: #b8860b;">{trend['total_clients']}</div>
            <div style="font-size: 0.75rem; color: #8b7355;">参与会话</div>
        </div>
        <div>
            <div style="font-size: 1.5rem; font-weight: 600; color: #2d6a4f;">{trend['total_rounds']}</div>
            <div style="font-size: 0.75rem; color: #8b7355;">聚合轮次</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if trend["current"]:
    st.markdown("#### 当前全局情绪分布")
    sorted_global = sorted(trend["current"].items(), key=lambda x: x[1], reverse=True)
    for emotion, score in sorted_global:
        if score > 0.005:
            st.markdown(f"""
<div style="margin: 0.3rem 0;">
    <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
        <span>{emotion}</span>
        <span>{score:.1%}</span>
    </div>
    <div style="background: #e8dfd0; border-radius: 99px; height: 6px; overflow: hidden;">
        <div style="background: #c0392b; height: 100%; width: {score*100}%; border-radius: 99px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── FL 轮次历史 ──
if trend["rounds"]:
    st.markdown("#### 聚合历史")
    for round_data in trend["rounds"][:5]:
        top_emotion = max(
            round_data["aggregated_emotions"].items(),
            key=lambda x: x[1]
        ) if round_data["aggregated_emotions"] else ("—", 0)
        st.markdown(f"""
<div class="card" style="padding: 0.6rem 1rem;">
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
        <span>轮次 #{round_data['round_num']}</span>
        <span style="color: #8b7355;">{round_data['client_count']} 个会话</span>
    </div>
    <div style="font-size: 0.75rem; color: #b8860b; margin-top: 0.2rem;">
        主导情绪：{top_emotion[0]} ({top_emotion[1]:.1%})
    </div>
</div>
""", unsafe_allow_html=True)

# ── EWA-Fed 说明 ──
st.markdown("---")
st.markdown("""
<div class="card" style="border-left: 3px solid #b8860b;">
    <strong>🧠 EWA-Fed 聚合算法</strong><br>
    <span style="font-size: 0.85rem; color: #8b7355;">
    采用 Entropy-Weighted Aggregation（熵加权聚合）：<br>
    • 情绪集中的会话获得更高权重（更"确定"的声音）<br>
    • 情绪分散的会话获得较低权重（更"不确定"的声音）<br>
    • 有效抑制从众效应，让少数但确定的声音被听到
    </span>
</div>
""", unsafe_allow_html=True)
