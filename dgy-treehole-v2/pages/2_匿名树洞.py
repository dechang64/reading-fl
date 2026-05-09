"""匿名树洞 — 释放心事，不留痕迹

设计原则：
- 释放即消失，内容不持久化
- 4种释放方式（风/湖/花/烟）
- 仅统计聚合数据用于联邦学习
"""

import streamlit as st
from core.config import RELEASE_METHODS
from core.emotion_detector import detect_emotion
from core.fl_engine import submit_local_stats
from core.db import record_treehole, get_treehole_stats
import uuid

st.set_page_config(page_title="匿名树洞 · 大观园树洞", page_icon="🌳", layout="centered")

# ── 初始化 session ──
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

# ── 返回 ──
if st.button("← 回到大观园", use_container_width=True):
    st.switch_page("app.py")

st.markdown("""
<div class="card-dark" style="text-align:center; padding: 1.5rem;">
    <div style="font-size: 2.5rem;">🌳</div>
    <h2 style="margin: 0.5rem 0;">匿名树洞</h2>
    <p style="font-size: 0.85rem; color: #d4c5a9;">说出你的心事，然后让它随风而去</p>
    <p style="font-size: 0.75rem; color: #8b7355; margin-top: 0.3rem;">🔒 你的话不会被存储，释放即消失</p>
    <p style="font-size: 0.7rem; color: #b8860b; margin-top: 0.2rem;">💡 想让别人看到？去「匿名共鸣」发布，那里是匿名的</p>
</div>
""", unsafe_allow_html=True)

# ── 输入 ──
treehole_text = st.text_area(
    "把你想说的话写在这里...",
    height=120,
    placeholder="这里只有你和风...",
    label_visibility="collapsed",
)

# ── 释放方式 ──
if treehole_text:
    st.markdown("### 选择释放方式")
    cols = st.columns(4)
    selected_method = None

    for i, (key, info) in enumerate(RELEASE_METHODS.items()):
        with cols[i]:
            if st.button(
                f"{info['icon']}\n{key}",
                key=f"release_{key}",
                use_container_width=True,
            ):
                selected_method = key

    # ── 释放动画 ──
    if selected_method:
        method_info = RELEASE_METHODS[selected_method]
        emotion = detect_emotion(treehole_text)

        # 记录树洞统计
        try:
            record_treehole(selected_method, emotion, len(treehole_text))
        except Exception:
            pass

        # 提交联邦学习统计（只提交情绪标签，不提交内容）
        try:
            submit_local_stats(
                st.session_state.session_id,
                {emotion: 1.0}
            )
        except Exception:
            pass

        # 释放动画
        animations = {
            "wind": """
<div style="text-align:center; padding: 2rem;" class="fade-in">
    <div style="font-size: 4rem;" class="float">🍃</div>
    <h3 style="color: #2d6a4f; margin-top: 1rem;">已随风飘散</h3>
    <p style="color: #8b7355;">风会带走它</p>
</div>""",
            "lake": """
<div style="text-align:center; padding: 2rem;" class="fade-in">
    <div style="font-size: 4rem;" class="float">💧</div>
    <h3 style="color: #2d6a4f; margin-top: 1rem;">已沉入湖底</h3>
    <p style="color: #8b7355;">湖水会记住它</p>
</div>""",
            "petal": """
<div style="text-align:center; padding: 2rem;" class="fade-in">
    <div style="font-size: 4rem;" class="float">🌸</div>
    <h3 style="color: #c0392b; margin-top: 1rem;">已化为花瓣</h3>
    <p style="color: #8b7355;">花瓣会替你开</p>
</div>""",
            "smoke": """
<div style="text-align:center; padding: 2rem;" class="fade-in">
    <div style="font-size: 4rem;" class="float">🕯️</div>
    <h3 style="color: #8b7355; margin-top: 1rem;">已燃为青烟</h3>
    <p style="color: #8b7355;">烟会替你说</p>
</div>""",
        }

        st.markdown(animations[selected_method], unsafe_allow_html=True)

        # 疗愈回复
        replies = [
            "说出来就好了。有些事情，不需要被记住，只需要被释放。",
            "你已经很勇敢了。把心事说出来，本身就是一种力量。",
            "风会带走它，但你留下的勇气会留下来。",
            "每一次释放，都是一次新生。",
            "你不需要独自承受。但此刻，你选择了面对，这很了不起。",
            "有些话不需要回应，只需要一个出口。你找到了。",
        ]
        import random
        st.markdown(f"""
<div class="card" style="text-align:center; margin-top: 1rem;">
    <p style="font-style:italic; color: #8b7355; line-height: 1.8;">
        "{random.choice(replies)}"
    </p>
</div>
""", unsafe_allow_html=True)

        if st.button("🏠 回到大观园", use_container_width=True):
            st.rerun()

# ── 树洞统计 ──
try:
    stats = get_treehole_stats()
except Exception:
    stats = {}
total_count = sum(v["count"] for v in stats.values()) if stats else 0
if total_count > 0:
    st.markdown("---")
    st.markdown(f"""
<div style="text-align:center; color: #8b7355; font-size: 0.8rem;">
    已有 <strong>{total_count}</strong> 位朋友在这里释放了心事<br>
    <span style="color: #b8860b;">联邦学习保护了每一位朋友的隐私</span>
</div>
""", unsafe_allow_html=True)
