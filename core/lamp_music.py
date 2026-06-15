"""心灯音乐生成 — MiniMax music-2.6 客户端

复用 dgy-treehole 的 MiniMax key, 但提示词针对 reading-fl 场景定制:
- 中国传统乐器 (古琴/笛/箫/琵琶)
- 段级情绪 (感动/思考/共鸣/困惑/反对/平静)
- 书名 + 章节 提示词
- 30s loop
- 缓存: hash(book+chapter+emotion) → 复用

API 文档: https://api.minimaxi.com/v1/music_generation
"""
import requests
import hashlib
import os
import base64
import streamlit as st


def _get_minimax_config() -> tuple[str, str]:
    """读 MiniMax 配置 (从 streamlit secrets 优先, env fallback)

    Returns:
        (api_key, base_url)
    """
    try:
        api_key = st.secrets.get("MINIMAX_API_KEY", "")
        base_url = st.secrets.get("MINIMAX_BASE_URL", "https://api.minimaxi.com")
    except Exception:
        api_key = os.environ.get("MINIMAX_API_KEY", "")
        base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com")
    return api_key, base_url


def _is_mock() -> bool:
    """是否 mock 模式 (无 key)"""
    api_key, _ = _get_minimax_config()
    return not api_key


def _mock_music(emotion: str, book: str, chapter: str) -> dict:
    """无 key 时的 mock — 返回空 URL + 提示"""
    return {
        "error": "未配置 MINIMAX_API_KEY",
        "hint": "在 .streamlit/secrets.toml 或 share.streamlit.io Secrets 加: MINIMAX_API_KEY = 'sk-cp-...'",
        "audio_url": None,
        "mock": True,
    }


def _build_prompt(emotion: str, book: str, chapter: str) -> str:
    """构建音乐提示词 (reading-fl 风格)"""
    book_part = f"《{book}》" if book else "任何文学"
    chapter_part = f"{chapter}的氛围" if chapter else "阅读时的氛围"
    return (
        f"中国传统乐器演奏的{emotion}氛围音乐, "
        f"{book_part}{chapter_part}, "
        f"空灵悠远, 30秒, 适合冥想"
    )


def get_cache_key(emotion: str, book: str, chapter: str) -> str:
    """计算缓存 key (同 emotion+book+chapter 复用音频)"""
    raw = f"{emotion}|{book}|{chapter}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def generate_lamp_music(
    emotion: str = "共鸣",
    book: str = "",
    chapter: str = "",
    duration: int = 30,
    use_cache: bool = True,
) -> dict:
    """生成心动林 30s 配乐

    Args:
        emotion: 6 维情绪 (感动/思考/共鸣/困惑/反对/平静)
        book: 书名 (e.g. "三体")
        chapter: 章节 (e.g. "第 47 章") 可选
        duration: 秒数 (固定 30)
        use_cache: 是否用 session_state 缓存

    Returns:
        {
            "audio_url": "https://..." | None,
            "audio_hex": "hex bytes" | None,  # 二进制, 前端可转 base64
            "cache_key": "...",
            "prompt": "...",
            "duration": 30,
            "emotion": "...",
            "book": "...",
            "chapter": "...",
            "mock": bool,
            "error": str | None,
        }
    """
    cache_key = get_cache_key(emotion, book, chapter)

    # 缓存检查 (session_state)
    if use_cache and "lamp_music_cache" in st.session_state:
        if cache_key in st.session_state.lamp_music_cache:
            cached = st.session_state.lamp_music_cache[cache_key]
            return {**cached, "cached": True}

    # mock 模式
    if _is_mock():
        return _mock_music(emotion, book, chapter)

    api_key, base_url = _get_minimax_config()
    prompt = _build_prompt(emotion, book, chapter)

    payload = {
        "model": "music-2.6",
        "prompt": prompt,
        "duration": duration,
        "is_instrumental": True,
        "output_format": "hex",  # 紧凑十六进制
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/v1/music_generation"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # MiniMax 返回结构: {"data": {"audio": "hex string", "audio_url": "..."}}
        audio_data = data.get("data", {})
        audio_hex = audio_data.get("audio")
        audio_url = audio_data.get("audio_url")

        if not audio_hex and not audio_url:
            return {
                "error": "MiniMax 返回空音频",
                "raw": data,
                "cache_key": cache_key,
                "prompt": prompt,
            }

        result = {
            "audio_url": audio_url,
            "audio_hex": audio_hex,
            "cache_key": cache_key,
            "prompt": prompt,
            "duration": duration,
            "emotion": emotion,
            "book": book,
            "chapter": chapter,
            "mock": False,
        }

        # 存缓存
        if use_cache:
            if "lamp_music_cache" not in st.session_state:
                st.session_state.lamp_music_cache = {}
            st.session_state.lamp_music_cache[cache_key] = result

        return result

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        return {
            "error": f"MiniMax HTTP {code}",
            "hint": "检查 MINIMAX_API_KEY, music-2.6 模型可能需要权限",
            "cache_key": cache_key,
            "prompt": prompt,
        }
    except Exception as e:
        return {
            "error": f"{type(e).__name__}: {e}",
            "cache_key": cache_key,
            "prompt": prompt,
        }


def audio_hex_to_data_url(audio_hex: str, mime: str = "audio/mpeg") -> str:
    """hex 字符串 → data URL (前端可直接 <audio src=...>)"""
    try:
        audio_bytes = bytes.fromhex(audio_hex)
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


# 6 维情绪的中英对照 (Reading-FL 风格)
EMOTION_CN = {
    "moved": "感动",
    "thinking": "思考",
    "resonance": "共鸣",
    "confused": "困惑",
    "disagree": "反对",
    "calm": "平静",
}
EMOTION_EN = {v: k for k, v in EMOTION_CN.items()}
