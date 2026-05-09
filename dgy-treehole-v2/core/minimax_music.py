"""MiniMax 音乐生成客户端（可选，需单独配置 MINIMAX_API_KEY）

API: POST https://api.minimaxi.com/v1/music_generation
Model: music-2.6-free
Response: JSON, data.audio 为 hex 编码音频数据

注意：音乐生成是可选功能，不配置 MINIMAX_API_KEY 时该页面显示提示。
聊天功能使用 GLM API，两者独立。
"""

import requests
import tempfile
import os
from core.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MUSIC_MODEL

# 音乐功能是否可用（独立于聊天 MOCK_MODE）
MUSIC_AVAILABLE = bool(MINIMAX_API_KEY)


def generate_music(
    prompt: str,
    place: str = "潇湘馆",
    mood: str = "宁静",
    duration: int = 60,
    is_instrumental: bool = True,
) -> str | None:
    """
    生成疗愈音乐

    Args:
        prompt: 音乐描述
        place: 场景名（用于生成提示词）
        mood: 情绪风格
        duration: 时长（秒）
        is_instrumental: 是否纯音乐

    Returns:
        音频文件路径，失败返回 None
    """
    if not MUSIC_AVAILABLE:
        return None

    full_prompt = f"中国传统乐器演奏的{mood}氛围音乐，{prompt}，{place}场景，空灵悠远，适合冥想放松"

    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MUSIC_MODEL,
        "prompt": full_prompt,
        "duration": duration,
        "is_instrumental": is_instrumental,
        "output_format": "hex",
    }

    try:
        resp = requests.post(
            f"{MINIMAX_BASE_URL}/v1/music_generation",
            headers=headers,
            json=payload,
            timeout=120,  # 音乐生成较慢
        )
        resp.raise_for_status()
        data = resp.json()

        # 解码 hex 音频数据
        hex_audio = data.get("data", {}).get("audio", "")
        if not hex_audio:
            return None

        audio_bytes = bytes.fromhex(hex_audio)

        # 保存为临时文件
        tmp = tempfile.NamedTemporaryFile(
            suffix=".mp3", prefix=f"treehole_{place}_{mood}_", delete=False
        )
        tmp.write(audio_bytes)
        tmp.close()
        return tmp.name

    except requests.exceptions.Timeout:
        return None
    except Exception:
        return None
