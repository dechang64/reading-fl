"""Reading-FL 反脆弱异常处理 — 心灵语气 fallback

设计: 把 streamlit 的 st.error/st.warning/st.info 全部包成统一接口
- 错误时: 🪔 灯暂时暗了 (心灵语气)
- 加载时: ⏳ 段友正在翻书...
- 警告时: ⚠️ 灯闪了一下
- 成功时: ✅ 好
"""
import streamlit as st
import functools
import traceback


def gentle_error(e: Exception, where: str = "", user_msg: str = None):
    """统一错误展示 — 心灵语气 + 详细错误写到 caption"""
    icon = "🪔"
    title = user_msg or "灯暂时暗了一下, 我们再点点看"
    with st.container():
        st.error(f"{icon} {title}")
        if where:
            st.caption(f"📍 {where}")
        # 详细错误仅开发者可见
        with st.expander("🔧 技术细节 (开发用)", expanded=False):
            st.code(traceback.format_exc())


def gentle_warning(msg: str):
    """统一警告 — 心灵语气"""
    st.warning(f"🪔 {msg}")


def gentle_info(msg: str):
    """统一提示 — 心灵语气"""
    st.info(f"🪔 {msg}")


def gentle_success(msg: str):
    """统一成功 — 心灵语气"""
    st.success(f"🪔 {msg}")


def gentle_spinner(msg: str = "段友正在翻书, 等一下下..."):
    """统一 spinner — 心灵语气"""
    return st.spinner(f"🪔 {msg}")


def safe_run(fn, fallback_msg: str = "这件事我暂时做不到, 你先试试别的"):
    """装饰器: 任何函数出错都显示 fallback, 不让 streamlit crash"""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            gentle_error(e, where=fn.__name__, user_msg=fallback_msg)
            return None
    return wrapper
