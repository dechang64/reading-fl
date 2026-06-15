"""Reading-FL 独立 AMAX 客户端 (不依赖 dgy-treehole)

直接读 streamlit secrets (cloud 友好):
  - AMAX_API_KEY
  - AMAX_BASE_URL  (默认 https://ai.amaxsmp.com)
  - AMAX_CHAT_MODEL (默认 amax-router)

本地 dev: 把 secrets 写到 .streamlit/secrets.toml (gitignored)
"""
import requests
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_config() -> tuple[str, str, str]:
    """从 streamlit secrets 或环境变量读 AMAX 配置。

    Returns:
        (api_key, base_url, model) — 任何值为空表示 mock 模式
    """
    try:
        import streamlit as st
        api_key = st.secrets.get("AMAX_API_KEY", "")
        base_url = st.secrets.get("AMAX_BASE_URL", "https://ai.amaxsmp.com")
        model = st.secrets.get("AMAX_CHAT_MODEL", "amax-router")
    except Exception:
        # 不在 streamlit 上下文里 (例如 import 阶段),退回 env
        import os
        api_key = os.environ.get("AMAX_API_KEY", "")
        base_url = os.environ.get("AMAX_BASE_URL", "https://ai.amaxsmp.com")
        model = os.environ.get("AMAX_CHAT_MODEL", "amax-router")
    return api_key, base_url, model


def _is_mock() -> bool:
    api_key, _, _ = _get_config()
    return not api_key


def chat(
    messages: list[dict],
    character: str = "心灯精灵",
    personality_params: dict | None = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
    timeout: int = 30,
) -> str:
    """发起到 AMAX Token Router 的 chat completion 请求。

    Args:
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        character: 角色名(只用于 mock 模式)
        personality_params: 人格参数(tone=gentle/warm/cool)
        temperature: 0-1
        max_tokens: 上限

    Returns:
        AI 回复文本;失败时返回 "💭 ..." 提示 + mock
    """
    api_key, base_url, model = _get_config()

    if not api_key:
        return _mock_response(character, messages, personality_params)

    # 拼 payload — AMAX 支持 amax-router 智能路由,也可以传具体模型
    api_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", msg.get("text", ""))
        if content and role in ("system", "user", "assistant"):
            api_messages.append({"role": role, "content": content})

    payload: dict[str, Any] = {
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if model:
        payload["model"] = model

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "").strip()
            if content:
                return content
        # 空 choices — 退回 mock
        return f"💭 *(AI 返回空选择)*\n\n{_mock_response(character, messages, personality_params)}"

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        logger.error("AMAX HTTP %d: %s", code, e)
        if code in (401, 403):
            return f"💭 *(AI 鉴权失败 HTTP {code} — 请检查 Secrets 里的 AMAX_API_KEY)*\n\n{_mock_response(character, messages, personality_params)}"
        return f"💭 *(AI HTTP {code})*\n\n{_mock_response(character, messages, personality_params)}"

    except Exception as e:
        logger.error("AMAX exception: %s: %s", type(e).__name__, e)
        return f"💭 *(AI 暂时连不上:{type(e).__name__})*\n\n{_mock_response(character, messages, personality_params)}"


def _mock_response(character: str, messages: list[dict], personality_params: dict | None = None) -> str:
    """无 key 时的兑底回复(基于关键词)"""
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    last_msg = user_msgs[-1] if user_msgs else ""
    tone = (personality_params or {}).get("tone", "warm")

    book_words = ["书", "读", "看", "摘", "文学", "小说", "诗"]
    if any(w in last_msg for w in book_words):
        return f"我是{character}。\n\n关于书的事,我很想听你多说说 — 你刚才提到「{last_msg[:20]}」,那本书/那段话里,是什么留住了你?"

    if tone == "gentle":
        return f"我是{character}。\n\n你说:「{last_msg}」\n\n……我在这里,愿意慢慢听。"
    return f"我是{character}。\n\n你说:「{last_msg}」\n\n我在听。你愿意多说一些吗?"


# ═══════════════════════════════════════════════════════════════
#  截屏识别 — 多模态 (适用于 gpt-4-vision / claude-3.5-sonnet)
# ═══════════════════════════════════════════════════════════════
import base64
import io
import json
import re


def detect_excerpt_from_image(
    image_bytes: bytes,
    hint: str = "",
) -> dict:
    """从截屏识别书摘 — 返回结构化数据

    Args:
        image_bytes: 截屏图片原始字节 (PNG/JPG)
        hint: 用户提示(可选),例如"这是《代码乡愁》第 3 章"

    Returns:
        {
            "book_title": "代码乡愁",
            "author": "杨家小蠍",
            "paragraph": "老陈盯着屏幕上那行注释看了很久...",
            "paragraph_location": "第 3 章",
            "context_before": "...上一下段...",
            "context_after": "下一下段...",
            "tags": ["失去", "亲情", "代码"],
            "confidence": 0.95,
        }

    失败时返回 {"error": "...", "raw": "..."}
    """
    api_key, base_url, model = _get_config()

    if not api_key:
        return _mock_excerpt_detect(image_bytes, hint)

    # 编码图片
    img_b64 = base64.b64encode(image_bytes).decode("ascii")

    # 多模态 prompt
    system_prompt = """你是一个严谨的书摘识别助手。
用户会上传一张读书 App / 纸质书 / Kindle 的截屏。
请从图中提取:
1. book_title: 书名(如果没有,写"未知")
2. author: 作者(没有就"未知")
3. paragraph: 截屏中被高亮/划线/被选择的那段话(原样,不要修改)
4. paragraph_location: 章节或位置(如"第 3 章"、"Chapter 7")
5. context_before: 上一段(不超 30 字)
6. context_after: 下一段(不超 30 字)
7. tags: 3-5 个主题标签(如["失去", "亲情", "代码"])
8. confidence: 0-1

**严格要求**:
- 只输出 JSON,不要任何其他文字
- JSON 格式严格遵守,字段名用我列的英文
- 段落必须用中文引号 「」 或不转义都行,不能用未转义英文引号打断 JSON
"""

    user_text = "请识别这张截屏中的书摘。" + (f" 提示:{hint}" if hint else "")

    # AMAX 支持多模态:消息体里加 image_url 字段
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                        },
                    },
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 800,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return {"error": "AMAX 返回空 choices", "raw": data}
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            return {"error": "AMAX 返回空 content", "raw": data}

        # 尝试解析 JSON (有时 LLM 会包 ```json ... ```)
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        json_text = m.group(1) if m else content
        # LLM 偶尔在 paragraph 字段用未转义 " 打断 JSON,做容错提取
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # 尝试找 JSON 块
            m2 = re.search(r"\{[^{}]*\{.*?\}[^{}]*\}", content, re.DOTALL)
            if m2:
                try:
                    return json.loads(m2.group(0))
                except Exception:
                    pass
            return {
                "error": "JSON 解析失败",
                "raw_text": content[:500],
            }
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        return {"error": f"AMAX HTTP {code}", "hint": "检查 AMAX 是否支持多模态模型"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _mock_excerpt_detect(image_bytes: bytes, hint: str = "") -> dict:
    """无 API key 时的模拟识别 — 提示用户去配 AMAX key"""
    return {
        "error": "未配置 AMAX_API_KEY (在 .streamlit/secrets.toml 或 share.streamlit.io Secrets)",
        "hint": "在 Secrets 加: AMAX_API_KEY = 'sk-amax-...', 系统会自动调用多模态识别",
        "mock_book_title": "示例：《百年孤独》",
        "mock_paragraph": "(需要 AMAX key 才能识别你的截屏)",
    }


# ═══════════════════════════════════════════════════════════════
#  v6.3.2 AI 金句生成 — 第 5 种输入方式
# ═══════════════════════════════════════════════════════════════

def generate_golden_quote(
    book: str = "",
    topic: str = "",
    style: str = "",
    emotion: str = "",
    n: int = 3,
) -> dict:
    """生成 AI 金句 (5th 输入方式) — 用户没东西可摘, AI 给 3 段选 1

    Args:
        book: 书名 (e.g. "《三体》" / "任何") — 必填
        topic: 主题 (一句话) — 必填, e.g. "宇宙的孤独感"
        style: 风格 (鲁迅/海明威/...) — 可选
        emotion: 情绪 (感动/共鸣/...) — 可选
        n: 数量 1-5, 默认 3

    Returns:
        {
            "quotes": [
                {
                    "text": "段落 50-150 字",
                    "book": "假定的书名 + 作者",
                    "location": "假定的章节",
                    "confidence": 0.85,
                    "emotion": "resonance"
                },
                ...
            ]
        }
        失败时返回 {"error": "...", "raw": "..."}
    """
    api_key, base_url, model = _get_config()

    if not api_key:
        return _mock_golden_quote(book, topic, style, emotion, n)

    system_prompt = """你是读者的书灯精灵, 像知音一样懂他们想要的金句。

请生成 {n} 段金句, 满足:
- 来源: {book} (e.g. 《三体》/ 任何文学经典)
- 主题: {topic}
- 风格: {style} (不限就写不限)
- 情绪: {emotion} (不限就写不限)
- 每段 50-150 字 (一段, 不是整段)
- 真实可查的语感 (像真从一本书摘的, 不是 AI 编的)

输出严格 JSON 数组, 每段含:
- text: 段落原文
- book: 假定的书名 + 作者 (e.g. "《边城》沈从文")
- location: 假定的章节或位置 (e.g. "第 5 章")
- confidence: 0-1 (像真程度)
- emotion: 6 维情感标签 (moved/thinking/resonance/confused/disagree/calm)

**严格要求**:
- 只输出 JSON 数组, 不要任何其他文字
- JSON 格式严格, 字段名用我列的英文
- 段落里可用中文引号 「」或不转义都行, 不能用未转义英文引号打断 JSON
""".format(n=n, book=book or "任何文学/哲学/现代经典",
           topic=topic or "生命", style=style or "不限",
           emotion=emotion or "不限")

    user_text = f"请给我 {n} 段金句"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.8,  # 略高, 让 AI 多样
        "max_tokens": 1500,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return {"error": "AMAX 返回空 choices", "raw": data}
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            return {"error": "AMAX 返回空 content", "raw": data}

        # 解析 JSON 数组
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
        json_text = m.group(1) if m else content

        try:
            quotes = json.loads(json_text)
        except json.JSONDecodeError:
            # 容错: 找 JSON 数组块
            m2 = re.search(r"\[.*?\]", content, re.DOTALL)
            if m2:
                try:
                    quotes = json.loads(m2.group(0))
                except Exception:
                    return {"error": "JSON 解析失败", "raw_text": content[:500]}
            else:
                return {"error": "JSON 解析失败", "raw_text": content[:500]}

        # 校验 + 标准化
        normalized = []
        for q in (quotes if isinstance(quotes, list) else []):
            if not isinstance(q, dict):
                continue
            normalized.append({
                "text": str(q.get("text", "")).strip(),
                "book": str(q.get("book", "")).strip(),
                "location": str(q.get("location", "")).strip(),
                "confidence": float(q.get("confidence", 0.5)),
                "emotion": str(q.get("emotion", "resonance")).strip().lower(),
            })

        if not normalized:
            return {"error": "AI 没生成有效的金句", "raw_text": content[:500]}

        return {"quotes": normalized[:n]}

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        return {"error": f"AMAX HTTP {code}", "hint": "检查 AMAX 配置"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _mock_golden_quote(book: str, topic: str, style: str, emotion: str, n: int) -> dict:
    """无 API key 时的模拟金句 — 提示用户去配 AMAX key"""
    sample_quotes = [
        {
            "text": "在浩瀚的星空下, 我们都是孤独的孩子, 但正因这份孤独, 我们才能听见彼此最真实的心跳。",
            "book": "《三体》刘慈欣",
            "location": "第 47 章 黑暗森林",
            "confidence": 0.78,
            "emotion": "resonance",
        },
        {
            "text": "宇宙这么大, 我们这么小, 可是正因我们能彼此看见, 黑暗便不再可怕。",
            "book": "《时间简史》史蒂芬·霍金",
            "location": "第 8 章",
            "confidence": 0.72,
            "emotion": "thinking",
        },
        {
            "text": "我曾以为孤独是缺陷, 后来才明白, 孤独是我们能给彼此最诚实的礼物。",
            "book": "《百年孤独》加西亚·马尔克斯",
            "location": "第 12 章",
            "confidence": 0.81,
            "emotion": "moved",
        },
    ]
    return {
        "quotes": sample_quotes[:n],
        "mock": True,
        "hint": "未配置 AMAX_API_KEY, 这是预设示例。在 Secrets 加: AMAX_API_KEY = 'sk-amax-...', 系统会调真实 AI 生成",
    }

