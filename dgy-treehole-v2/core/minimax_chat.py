"""GLM 聊天客户端 — 智谱AI OpenAI 兼容格式

API: POST https://open.bigmodel.cn/api/paas/v4/chat/completions
Model: glm-4-flash（免费，速度快，适合对话场景）
"""

import requests
from core.config import GLM_API_KEY, GLM_BASE_URL, CHAT_MODEL, MOCK_MODE
from core.characters import get_character


def chat(messages: list[dict], character: str = "贾宝玉",
         temperature: float = 0.7, max_tokens: int = 300) -> str:
    """
    发送聊天请求到 GLM API

    Args:
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        character: 角色名（用于获取 system prompt）
        temperature: 生成温度
        max_tokens: 最大生成 token 数

    Returns:
        AI 回复文本
    """
    if MOCK_MODE:
        return _mock_response(character, messages)

    char_info = get_character(character)
    system_prompt = char_info["system_prompt"]

    # 确保 system prompt 在最前面
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        if msg["role"] != "system":
            api_messages.append({"role": msg["role"], "content": msg["content"]})

    headers = {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": CHAT_MODEL,
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(
            f"{GLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "（网络超时，请稍后再试。）"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return "（请求太频繁了，请稍等片刻再试。）"
        return f"（服务暂时不可用，错误：{e.response.status_code}）"
    except Exception:
        return "（出了点小问题，请稍后再试。）"


def _mock_response(character: str, messages: list[dict]) -> str:
    """Mock 模式：基于关键词的简单回复（用于无 API Key 时）"""
    char_info = get_character(character)
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    last_msg = user_msgs[-1] if user_msgs else ""

    # 简单情绪检测
    sad_words = ["难过", "伤心", "哭", "悲伤", "心痛", "难受", "委屈", "不开心"]
    anxious_words = ["焦虑", "紧张", "害怕", "担心", "压力", "崩溃"]
    angry_words = ["生气", "愤怒", "讨厌", "恨", "烦", "气"]
    lost_words = ["迷茫", "不知道", "方向", "意义", "为什么"]
    tired_words = ["累", "疲惫", "撑不住", "加班", "熬夜"]

    is_sad = any(w in last_msg for w in sad_words)
    is_anxious = any(w in last_msg for w in anxious_words)
    is_angry = any(w in last_msg for w in angry_words)
    is_lost = any(w in last_msg for w in lost_words)
    is_tired = any(w in last_msg for w in tired_words)

    if is_sad:
        return f"我听到了。你的难过是真实的，不需要假装没事。\n\n{char_info['personality'][:30]}……你愿意多说一些吗？"
    elif is_anxious:
        return "深呼吸。你现在感受到的焦虑，是你的身体在告诉你——这件事对你很重要。\n\n不用急着解决，先让自己安定下来。"
    elif is_angry:
        return "你的愤怒是合理的。不公平的事情确实让人难以接受。\n\n你愿意告诉我发生了什么吗？我在听。"
    elif is_lost:
        return '迷茫的时候，不需要立刻找到方向。有时候，承认"我不知道"本身就需要勇气。\n\n你最近在纠结什么？'
    elif is_tired:
        return "你已经很努力了。累的时候，允许自己停下来休息，这不是软弱。\n\n你有多久没有好好休息了？"
    else:
        return "嗯，我在听。你说的每一句话，我都认真对待。\n\n你还有什么想说的吗？"
