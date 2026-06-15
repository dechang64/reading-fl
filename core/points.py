"""Reading-FL 段级社区看见币 (积分) 系统

设计哲学: 看见币 = 段级社区公民权, 不是虚拟货币
- 段级讨论 / 作者 AI 替身对话 等稀缺权益用看见币兑换
- 主行为 (摘录) 奖励低, 网络效应行为 (被共鸣) 奖励高
- 防止通胀: 月度兑换池固定
- 7 级等级体系 (L1-L7, 跟看见读书会对齐)
"""
import streamlit as st
import datetime


# ═══════════════════════════════════════════════════════════════
#  7 级等级体系 (L1-L7, 跟看见读书会对齐: 初见/同行/微光/星芒/执灯/引路/共创)
# ═══════════════════════════════════════════════════════════════
LEVELS = [
    (0,     "L1", "初见者", "新用户入门",                "🔍"),
    (100,   "L2", "同行者", "活跃读者, 偶尔被看见",       "👣"),
    (300,   "L3", "微光者", "深度参与者, 段级被共鸣",     "✨"),
    (800,   "L4", "星芒者", "优质分享者, 可申请领读人",   "⭐"),
    (2000,  "L5", "执灯人", "正式领读人, 自主开雅集",     "🪔"),
    (5000,  "L6", "引路人", "资深主理人, 跨圈影响",       "🌟"),
    (12000, "L7", "共创者", "核心共建者, 平台合伙",       "👑"),
]


def get_level(points: int) -> dict:
    """根据积分返回当前等级"""
    cur = LEVELS[0]
    nxt = LEVELS[1] if len(LEVELS) > 1 else None
    for i, lv in enumerate(LEVELS):
        if points >= lv[0]:
            cur = lv
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    progress = 0.0
    if nxt:
        progress = (points - cur[0]) / (nxt[0] - cur[0])
        progress = max(0.0, min(1.0, progress))
    return {
        "code": cur[1], "name": cur[2], "tagline": cur[3], "icon": cur[4],
        "min_points": cur[0],
        "next_code": nxt[1] if nxt else None,
        "next_name": nxt[2] if nxt else None,
        "next_min": nxt[0] if nxt else None,
        "progress": progress,
    }


def show_level_badge(points: int) -> str:
    """生成等级徽章 HTML (sidebar 用)"""
    lv = get_level(points)
    progress_pct = int(lv["progress"] * 100)
    return f"""
<div class="level-badge">
  <span class="level-icon">{lv['icon']}</span>
  <span class="level-code">{lv['code']} {lv['name']}</span>
  <div class="level-bar"><div class="level-bar-fill" style="width:{progress_pct}%"></div></div>
  <span class="level-next">{lv['next_name'] or '满级'} · {points} 看见币</span>
</div>
"""


# ═══════════════════════════════════════════════════════════════
#  看见币奖励规则
# ═══════════════════════════════════════════════════════════════
REWARDS = {
    "excerpt": 5,                # 写一段摘录 (主行为,低)
    "excerpt_with_reflection": 12,  # 摘录 + 感悟 (>20字)
    "tags_3plus": 3,             # 3+ 标签额外奖励
    "segment_resonated": 20,     # 段级被 3+ 人共鸣(网络效应)
    "segment_author_pinned": 50, # 段级被作者加精/置顶 (作者侧)
    "cross_book_match": 30,      # 跨书情感命中(被推荐新书)
    "reflection_liked": 2,       # 感悟被人点赞
    "first_excerpt_today": 5,    # 今日首段额外
    "streak_7d": 100,            # 连续 7 天有摘录
    "invite_friend": 30,         # 邀请好友
    "mbti_test": 20,             # 完成 MBTI 测试
    "screenshot_used": 8,        # 用截屏识别(替代打字,鼓励)
}


# ═══════════════════════════════════════════════════════════════
#  积分兑换(月度配额)
# ═══════════════════════════════════════════════════════════════
EXCHANGE_CATALOG = {
    "segment_discuss_5x": {"name": "段级讨论 ×5", "cost": 30, "period": "monthly"},
    "author_genie_3x":    {"name": "作者 AI 替身 ×3", "cost": 50, "period": "monthly"},
    "book_recommend_vip": {"name": "VIP 推荐解锁(本月)", "cost": 80, "period": "monthly"},
    "segment_pin_1x":     {"name": "段级置顶 ×1", "cost": 60, "period": "weekly"},
    "lamp_discount_15":   {"name": "坐忘·灯 9.5 折码", "cost": 200, "period": "once"},
    "annual_cross_book":  {"name": "年度跨书情感图谱", "cost": 500, "period": "once"},
}


def init_points():
    """在 session_state 初始化积分账户"""
    if "points_total" not in st.session_state:
        st.session_state.points_total = 50  # 初始 50 积分(给新用户启动)
    if "points_history" not in st.session_state:
        st.session_state.points_history = []  # [(timestamp, reason, delta), ...]
    if "points_exchanged" not in st.session_state:
        st.session_state.points_exchanged = {}  # {key: timestamp}


def add_points(reason: str, amount: int | None = None):
    """加积分,reason 必须是 REWARDS 的 key"""
    init_points()
    if amount is None:
        amount = REWARDS.get(reason, 0)
    if amount == 0:
        return
    st.session_state.points_total += amount
    st.session_state.points_history.append({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "delta": amount,
    })
    # 保留最近 50 条
    st.session_state.points_history = st.session_state.points_history[-50:]


def spend_points(key: str) -> bool:
    """兑换某项,扣积分,返回是否成功"""
    init_points()
    item = EXCHANGE_CATALOG.get(key)
    if not item:
        return False
    if st.session_state.points_total < item["cost"]:
        return False
    # 检查周期配额
    if item["period"] != "once":
        last = st.session_state.points_exchanged.get(key)
        now = datetime.datetime.now()
        if last:
            try:
                last_dt = datetime.datetime.fromisoformat(last)
                if item["period"] == "monthly" and (now - last_dt).days < 30:
                    return False
                if item["period"] == "weekly" and (now - last_dt).days < 7:
                    return False
            except Exception:
                pass
    st.session_state.points_total -= item["cost"]
    st.session_state.points_exchanged[key] = datetime.datetime.now().isoformat(timespec="seconds")
    return True


def show_points_sidebar():
    """在 sidebar 顶部显示积分 + 7 级等级徽章"""
    init_points()
    with st.sidebar:
        st.markdown(
            show_level_badge(st.session_state.points_total),
            unsafe_allow_html=True,
        )


def show_points_page():
    """完整的看见币账户页 — 给 `pages/8_points.py` 用"""
    init_points()
    lv = get_level(st.session_state.points_total)
    st.markdown(f"# 🪔 看见币 · {lv['icon']} {lv['code']} {lv['name']}")
    st.caption(f"{lv['tagline']} · 你的字被看见, 才重要")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("看见币", st.session_state.points_total)
    with col2:
        today = sum(
            h["delta"] for h in st.session_state.points_history
            if h["ts"].startswith(__import__("datetime").datetime.now().strftime("%Y-%m-%d"))
        )
        st.metric("今日 +", today)
    with col3:
        st.metric("本月兑换", len([
            k for k, v in st.session_state.points_exchanged.items()
        ]))

    # 等级进度条
    lv = get_level(st.session_state.points_total)
    if lv["next_name"]:
        st.html(f"""
<div style="background: linear-gradient(90deg, rgba(212,165,116,0.15) 0%, rgba(196,105,74,0.10) 100%);
    padding: 0.6rem 0.9rem; border-radius: 8px; margin: 0.5rem 0 1rem 0;
    border: 1px solid rgba(212,165,116,0.25); font-size: 0.88rem;">
  🪔 <b>{lv['code']} {lv['name']}</b> · 再攒 <b>{lv['next_min'] - st.session_state.points_total}</b> 看见币 → <b>{lv['next_code']} {lv['next_name']}</b>
  <div style="background: rgba(0,0,0,0.3); border-radius: 4px; height: 6px; margin-top: 0.4rem;">
    <div style="background: linear-gradient(90deg, #d4a574 0%, #c4694a 100%);
        width: {int(lv['progress']*100)}%; height: 6px; border-radius: 4px; transition: width 0.3s;"></div>
  </div>
</div>
""")
    else:
        st.html(f"""
<div style="background: linear-gradient(90deg, #d4a574 0%, #c4694a 100%);
    color: #0d0d0f; padding: 0.6rem 0.9rem; border-radius: 8px; margin: 0.5rem 0 1rem 0;
    font-size: 0.88rem; font-weight: 600;">
  👑 恭喜! 你已是 <b>{lv['code']} {lv['name']}</b> — 满级
</div>
""")

    st.markdown("### 怎么赚积分?")
    st.html("""
    <div class="privacy-strip">
    <table style="width:100%; color: var(--text); font-size:0.88rem;">
      <tr><td>✍️ 写一段摘录</td><td style="text-align:right;">+5</td></tr>
      <tr><td>💭 摘录 + 感悟 (>20字)</td><td style="text-align:right;">+12</td></tr>
      <tr><td>🏷️ 3+ 标签</td><td style="text-align:right;">+3</td></tr>
      <tr><td>📸 用截屏识别(替代打字)</td><td style="text-align:right;">+8</td></tr>
      <tr><td>🔥 段级被 3+ 人共鸣</td><td style="text-align:right;"><b>+20</b></td></tr>
      <tr><td>⭐ 段级被作者加精</td><td style="text-align:right;"><b>+50</b></td></tr>
      <tr><td>💫 跨书情感命中</td><td style="text-align:right;"><b>+30</b></td></tr>
      <tr><td>🔥 连续 7 天</td><td style="text-align:right;"><b>+100</b></td></tr>
      <tr><td>🧠 完成 MBTI 测试</td><td style="text-align:right;">+20</td></tr>
      <tr><td>👥 邀请好友</td><td style="text-align:right;">+30</td></tr>
    </table>
    </div>
    """)

    st.markdown("### 积分换什么?")
    for key, item in EXCHANGE_CATALOG.items():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{item['name']}**")
            period_cn = {"monthly": "月度", "weekly": "周度", "once": "一次性"}.get(item["period"], item["period"])
            st.caption(f"{period_cn}配额")
        with col2:
            st.markdown(f"🪙 {item['cost']}")
        with col3:
            if st.button("兑换", key=f"exchange_{key}"):
                if spend_points(key):
                    st.success(f"✅ 兑换成功! {item['name']}")
                    st.rerun()
                else:
                    if st.session_state.points_total < item["cost"]:
                        st.error(f"🪔 你的看见币还差 {item['cost'] - st.session_state.points_total} 枚, 多写几段被看见")
                    else:
                        st.warning("🪔 本周期已换过, 下个周期再来")

    st.markdown("### 最近积分记录")
    if st.session_state.points_history:
        for h in reversed(st.session_state.points_history[-10:]):
            reason_cn = {
                "excerpt": "写摘录", "excerpt_with_reflection": "摘录+感悟",
                "tags_3plus": "3+ 标签", "segment_resonated": "段级被共鸣",
                "segment_author_pinned": "被作者加精", "cross_book_match": "跨书情感命中",
                "reflection_liked": "感悟被赞", "first_excerpt_today": "今日首段",
                "streak_7d": "连续 7 天", "invite_friend": "邀请好友",
                "mbti_test": "完成 MBTI", "screenshot_used": "截屏识别",
            }.get(h["reason"], h["reason"])
            st.caption(f"`{h['ts'][-8:]}` · {reason_cn} · +{h['delta']}")
    else:
        st.caption("还没有记录 — 去写第一段摘录!")
