"""会员体系 — 月度配额 + 199 元/年 会员 (mock)

v6.3 起步: 纯 mock, 不接支付
- 月度配额 (5 张免费)
- 单张 9.9 元
- 199 元/年 会员 (无限)

未来 v6.4 接 Stripe / 微信支付
"""
import streamlit as st
import datetime
from typing import Optional


def get_monthly_poster_count() -> int:
    """本月已生成海报数 (简单 session_state 计数, 不跨刷新)"""
    return st.session_state.get("monthly_poster_count", 0)


def get_free_quota_remaining() -> int:
    """剩余免费配额"""
    FREE_QUOTA = 5
    return max(0, FREE_QUOTA - get_monthly_poster_count())


def is_paid_member() -> bool:
    """是否付费会员 (mock)"""
    return st.session_state.get("is_paid_member", False)


def can_generate_poster() -> bool:
    """是否还能生成海报 (免费额度 OR 会员)"""
    if is_paid_member():
        return True
    return get_free_quota_remaining() > 0


def consume_poster_quota() -> bool:
    """消耗 1 张配额, 返回是否成功"""
    if is_paid_member():
        return True
    if get_free_quota_remaining() > 0:
        st.session_state.monthly_poster_count = get_monthly_poster_count() + 1
        return True
    return False


def get_pricing() -> dict:
    """定价信息"""
    return {
        "single_price": 9.9,            # 元/张
        "annual_price": 199.0,          # 元/年
        "annual_savings": 5 * 12 * 9.9 - 199,  # 年会员 vs 月度 5 张
        "free_quota_per_month": 5,      # 免费张数
    }


def show_paywall_gentle() -> None:
    """显示付费墙 (心灵语气版本, 不强推)"""
    pricing = get_pricing()
    st.markdown("### 🪔 本月免费额度已用完")
    st.info(
        f"💡 **付费方案**:\n\n"
        f"- 单张 **{pricing['single_price']:.1f} 元** (冲动消费, 适合偶尔)\n"
        f"- **{pricing['annual_price']:.0f} 元/年** 会员 "
        f"(无限海报 + 离线下载 + 高级 AI, 省 ¥{pricing['annual_savings']:.0f}/年)\n\n"
        f"🪔 我在等一个仪式感的你, 不会催, 也不会打扰"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"💳 单张 ¥{pricing['single_price']:.1f}", use_container_width=True):
            # mock 付费 — 直接给配额
            st.session_state.monthly_poster_count = max(0, get_monthly_poster_count() - 1)
            st.success("🪔 已解锁 1 张 — 谢谢支持")
            st.rerun()
    with col2:
        if st.button(f"🪔 会员 ¥{pricing['annual_price']:.0f}/年", use_container_width=True, type="primary"):
            # mock 会员 — 永久解锁
            st.session_state.is_paid_member = True
            st.session_state.member_since = datetime.datetime.now().isoformat()
            st.success("🪔 欢迎成为心灯会员 — 海报无限, 离线下载, 高级 AI 全部解锁")
            st.balloons()
            st.rerun()
