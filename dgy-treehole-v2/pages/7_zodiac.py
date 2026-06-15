"""星座指引 + 星盘分析 — 完整版

12星座×4元素 + 6星体简化天文计算 + 元素→角色匹配
界面完全对齐原版 index.html 的星座/星盘页面。
"""

import streamlit as st
from core.zodiac_data import (
    ZODIAC, ELEMENTS, ELEM_CHARS, PLANET_DESC, CITIES,
    calc_birth_chart,
)
from core.config import SCENE_MAP

st.set_page_config(page_title="星座星盘 · 大观园树洞", page_icon="⭐", layout="centered")
from core.styles import inject_css; inject_css()

# ── 返回 ──
if st.button("← 回到大观园", use_container_width=True):
    st.switch_page("app.py")

# ── 初始化 ──
if "zodiac_result" not in st.session_state:
    st.session_state.zodiac_result = None
if "chart_result" not in st.session_state:
    st.session_state.chart_result = None

# ── Tab ──
tab_zodiac, tab_chart = st.tabs(["⭐ 星座指引", "🔮 星盘分析"])

# ═══════════════════════════════════════════════════════════
#  星座指引
# ═══════════════════════════════════════════════════════════
with tab_zodiac:
    if st.session_state.zodiac_result is None:
        # Hero（对齐原版）
        st.markdown("""
<div style="background:linear-gradient(135deg,#2c1810,#4a2c1a 50%,#3d1f0e);
            padding:2rem 1.5rem;color:#f5f0e8;text-align:center;border-radius:0 0 16px 16px;
            position:relative;overflow:hidden;">
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(184,134,11,0.12),transparent 60%);pointer-events:none;"></div>
    <h1 style="font-size:1.4rem;position:relative;">⭐ 星座指引</h1>
    <p style="opacity:0.7;font-size:0.85rem;position:relative;">选择你的星座，找到属于你的院落</p>
</div>
""", unsafe_allow_html=True)

        # 按元素分组（对齐原版 initZodiac）
        elem_groups = {"火象": [], "土象": [], "风象": [], "水象": []}
        for z in ZODIAC:
            elem_groups[z["elem"] + "象"].append(z)

        elem_colors = {"火象": "#e74c3c", "土象": "#8B7355", "风象": "#3498db", "水象": "#2980b9"}

        for elem_name, zodiacs in elem_groups.items():
            color = elem_colors[elem_name]
            st.markdown(f'<div class="elem-label" style="color:{color}">{elem_name}</div>', unsafe_allow_html=True)

            # 3列网格（对齐原版 .zodiac-grid）
            for row_start in range(0, len(zodiacs), 3):
                cols = st.columns(3)
                for j, z in enumerate(zodiacs[row_start:row_start+3]):
                    with cols[j]:
                        icon = z["sign"].split(" ")[0]
                        name = z["sign"].split(" ")[1]
                        if st.button(
                            f"{icon} {name}\n{z['date']} · {z['trait']}",
                            key=f"zodiac_{z['sign']}",
                            use_container_width=True,
                        ):
                            st.session_state.zodiac_result = z
                            st.rerun()

        # 底部按钮（对齐原版）
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔮 星盘分析", use_container_width=True):
                st.session_state.chart_result = None
                st.rerun()
        with col2:
            if st.button("🧠 MBTI测试", use_container_width=True):
                st.switch_page("pages/5_mbti.py")

    else:
        # 星座结果页（对齐原版 showZodiacResult）
        z = st.session_state.zodiac_result
        elem = ELEMENTS.get(z["elem"], {})
        scene = SCENE_MAP.get(z["scene"], {})
        color = elem.get("color", "#8b7355")
        icon = z["sign"].split(" ")[0]
        name = z["sign"].split(" ")[1]

        st.markdown(f"""
<div style="background:linear-gradient(135deg,#2c1810,#4a2c1a 50%,#3d1f0e);
            padding:1.5rem;color:#f5f0e8;text-align:center;border-radius:0 0 16px 16px;">
    <h1 style="font-size:1.4rem;">⭐ 星座指引结果</h1>
</div>

<div style="padding:0.8rem;">
    <!-- 星座信息卡 -->
    <div style="text-align:center;padding:0.8rem;background:#fff;border-radius:12px;
                border:2px solid {color};margin-bottom:0.8rem;">
        <div style="font-size:1.8rem;">{icon}</div>
        <div style="font-size:0.85rem;color:#8b7355;">{name} · {z['date']}</div>
        <div style="font-size:0.75rem;color:#8b7355;margin-top:0.1rem;">{z['elem']}象 · {z['trait']}</div>
        <div style="font-size:0.72rem;color:{color};margin-top:0.2rem;">疗愈风格：{elem.get('style','')}</div>
    </div>

    <!-- 推荐场景（对齐原版 .result-scene） -->
    <div class="result-scene">
        <div class="icon">{scene.get('icon','🌸')}</div>
        <div>
            <div class="name">推荐：{z['scene']}</div>
            <div class="info">倾听者：{z['char']}</div>
        </div>
    </div>

    <!-- 适配理由（对齐原版 .result-reason） -->
    <div class="result-reason">{z['reason']}</div>

    <!-- 元素专属建议（对齐原版） -->
    <div style="background:#e8dfd0;border-radius:10px;padding:0.8rem;margin:0.8rem 0;">
        <div style="font-size:0.78rem;color:{color};font-weight:600;margin-bottom:0.3rem;">
            💡 {z['elem']}象专属建议</div>
        <div style="font-size:0.82rem;line-height:1.7;">{elem.get('advice','')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # 操作按钮
        if st.button(f"{scene.get('icon','🌸')} 进入{z['scene']}", type="primary", use_container_width=True):
            st.session_state.current_scene = z["scene"]
            st.session_state.chat_character = z["char"]
            st.session_state.chat_history = []
            st.switch_page("pages/1_chat.py")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔮 改做MBTI测试", use_container_width=True):
                st.switch_page("pages/5_mbti.py")
        with col2:
            if st.button("🔄 重新选择", use_container_width=True):
                st.session_state.zodiac_result = None
                st.rerun()

# ═══════════════════════════════════════════════════════════
#  星盘分析
# ═══════════════════════════════════════════════════════════
with tab_chart:
    if st.session_state.chart_result is None:
        # 输入表单（对齐原版 .birth-form）
        st.markdown("""
<div style="background:linear-gradient(135deg,#2c1810,#4a2c1a 50%,#3d1f0e);
            padding:2rem 1.5rem;color:#f5f0e8;text-align:center;border-radius:0 0 16px 16px;
            position:relative;overflow:hidden;">
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(184,134,11,0.12),transparent 60%);pointer-events:none;"></div>
    <h1 style="font-size:1.4rem;position:relative;">🔮 星盘分析</h1>
    <p style="opacity:0.7;font-size:0.85rem;position:relative;">输入出生信息，解锁你的专属星盘</p>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div style="padding:0.8rem;">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            birth_date = st.date_input("出生日期")
        with col2:
            birth_time = st.time_input("出生时间", value="12:00")

        city = st.selectbox("出生城市", list(CITIES.keys()), index=0)

        if st.button("🔮 解读我的星盘", type="primary", use_container_width=True):
            chart = calc_birth_chart(
                year=birth_date.year, month=birth_date.month, day=birth_date.day,
                hour=birth_time.hour, minute=birth_time.minute,
                city=city,
            )
            st.session_state.chart_result = chart
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # 星盘结果页（对齐原版 renderBirthChart）
        chart = st.session_state.chart_result
        dominant = chart["dominant"]
        dominant_elem = dominant[0]
        dominant_count = dominant[1]
        elem_info = ELEMENTS.get(dominant_elem, {})
        elem_char = ELEM_CHARS.get(dominant_elem, {})

        st.markdown("""
<div style="background:linear-gradient(135deg,#2c1810,#4a2c1a 50%,#3d1f0e);
            padding:1.5rem;color:#f5f0e8;text-align:center;border-radius:0 0 16px 16px;">
    <h1 style="font-size:1.4rem;">🔮 你的专属星盘</h1>
</div>
""", unsafe_allow_html=True)

        # 元素分布（对齐原版）
        elem_icons = {"火": "🔥", "土": "🏔️", "风": "💨", "水": "🌊"}
        elem_items = ""
        for e, c in chart["elements"].items():
            if c > 0:
                bg = "linear-gradient(135deg,#2c1810,#4a2c1a);color:#f5f0e8" if e == dominant_elem else "#fff;border:1px solid #e8dfd0"
                elem_items += f"""
<div style="background:{bg};border-radius:10px;padding:0.4rem;text-align:center;">
    <div style="font-size:1rem;">{elem_icons.get(e,'')}</div>
    <div style="font-size:0.7rem;margin-top:0.1rem;">{e}象 {c}</div>
</div>"""
        st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat({sum(1 for c in chart['elements'].values() if c > 0)},1fr);
            gap:0.4rem;padding:0.8rem;">
    {elem_items}
</div>
""", unsafe_allow_html=True)

        # 星体详情（对齐原版 .chart-planet）
        planet_keys = ["太阳", "月亮", "水星", "金星", "火星", "上升"]
        planet_icons = {"太阳": "☀️", "月亮": "🌙", "水星": "☿️", "金星": "💕", "火星": "🔥", "上升": "⬆️"}
        chart_key_map = {"太阳": "sun", "月亮": "moon", "水星": "mercury", "金星": "venus", "火星": "mars", "上升": "rising"}

        for key in planet_keys:
            chart_key = chart_key_map[key]
            p = chart.get(chart_key, {})
            if not p:
                continue
            pd = PLANET_DESC.get(key, {})
            sign_name = p.get("sign", "")
            desc_dict = pd.get("desc", {})
            desc_text = desc_dict.get(sign_name, "") if isinstance(desc_dict, dict) else ""

            st.markdown(f"""
<div class="chart-planet">
    <div class="p-icon">{planet_icons.get(key, '⭐')}</div>
    <div class="p-info">
        <div class="p-name">{pd.get('name', key)} · {sign_name}</div>
        <div class="p-sign">{pd.get('label', '')} · {p.get('elem', '')}象</div>
        <div class="p-desc">{desc_text}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # 总结（对齐原版 .chart-summary）
        st.markdown(f"""
<div class="chart-summary">
    <h3>你的星盘核心</h3>
    <p>你的{dominant_elem}象能量最强（{dominant_count}颗星体），{elem_info.get('style', '')}。</p>
    <p style="margin-top:0.3rem;">{elem_info.get('advice', '')}</p>
</div>
""", unsafe_allow_html=True)

        # 角色匹配（对齐原版 .chart-matches）
        if elem_char:
            scenes = elem_char.get("scene", "").split("/")
            chars = elem_char.get("char", "").split("/")
            theories = elem_char.get("theory", "").split("/")
            descs = elem_char.get("desc", "").split("/")
            icons = elem_char.get("icon", "").split("/")

            for idx in range(min(len(scenes), len(chars))):
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.6rem;padding:0.6rem;
            background:#fff;border-radius:10px;margin:0.4rem 0;border:1px solid #e8dfd0;">
    <div style="font-size:1.5rem;">{icons[idx] if idx < len(icons) else '🌸'}</div>
    <div style="flex:1;">
        <div style="font-size:0.85rem;font-weight:600;">{scenes[idx]} · {chars[idx]}</div>
        <div style="font-size:0.7rem;color:#8b7355;">{theories[idx] if idx < len(theories) else ''}</div>
        <div style="font-size:0.72rem;color:#2c1810;margin-top:0.1rem;">{descs[idx] if idx < len(descs) else ''}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # 操作按钮
        if elem_char:
            scenes = elem_char.get("scene", "").split("/")
            chars = elem_char.get("char", "").split("/")
            if scenes and chars:
                if st.button(f"💬 去找{chars[0]}聊聊", type="primary", use_container_width=True):
                    st.session_state.current_scene = scenes[0]
                    st.session_state.chat_character = chars[0]
                    st.session_state.chat_history = []
                    st.switch_page("pages/1_chat.py")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⭐ 改选星座", use_container_width=True):
                st.session_state.chart_result = None
                st.session_state.zodiac_result = None
                st.rerun()
        with col2:
            if st.button("🔄 重新解读", use_container_width=True):
                st.session_state.chart_result = None
                st.rerun()
