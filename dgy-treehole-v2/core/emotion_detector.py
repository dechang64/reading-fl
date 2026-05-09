"""情绪检测器 — 从用户文本中提取情绪标签

用于：
1. 聊天时实时标注用户情绪
2. 树洞释放时记录情绪统计
3. 联邦学习聚合的本地特征
"""

import re
from core.config import EMOTIONS

# 情绪关键词映射（优先级从高到低）
EMOTION_PATTERNS = {
    "悲伤": re.compile(
        r"难过|伤心|哭|悲伤|心痛|难受|委屈|不开心|低落|抑郁|绝望|"
        r"流泪|想哭|痛|失去|离开|分手|去世|走了|不在了|再也|"
        r"遗憾|后悔|自责|内疚|想念|思念|怀念|舍不得|心碎|泪|"
        r"想死|不想活|活着没意思|自杀|自残|割腕|跳楼|结束生命|"
        r"死了算了|活不下去|生不如死|解脱"
    ),
    "焦虑": re.compile(
        r"焦虑|紧张|害怕|恐惧|担心|不安|压力|崩溃|扛不住|喘不过|"
        r"失眠|睡不着|心慌|心跳|发抖|慌|万一|怎么办|考试|面试|"
        r"deadline|截止|来不及|赶不上|怕|慌张|忐忑"
    ),
    "愤怒": re.compile(
        r"生气|愤怒|讨厌|恨|不公平|凭什么|烦|恶心|混蛋|气死|"
        r"无语|忍不了|受够了|欺负|利用|背叛|骗|撒谎|虚伪|"
        r"不公|怒|火大|暴躁|烦死"
    ),
    "迷茫": re.compile(
        r"迷茫|不知道|方向|意义|活着|为什么|空虚|无聊|没意思|"
        r"目标|未来|选择|纠结|犹豫|到底|应该|该不该|值不值得|"
        r"困惑|不知所措|何去何从"
    ),
    "疲惫": re.compile(
        r"累|疲惫|倦怠|撑不住|撑不下去|好累|太累|筋疲力|透支|"
        r"加班|熬夜|起不来|没精神|不想动|摆烂|躺平|倦了|麻木|"
        r"耗尽|心力交瘁|精疲力竭"
    ),
    "孤独": re.compile(
        r"孤独|一个人|没人|寂寞|被抛弃|不被理解|没人在乎|孤单|"
        r"没朋友|合不来|融入不了|被排挤|被忽视|透明|没人理|"
        r"独处|形单影只"
    ),
    "平静": re.compile(
        r"还好|没事|平静|淡然|释怀|放下|算了|无所谓|习惯了|"
        r"接受|坦然|安宁|安静|还好吧|一般般|凑合"
    ),
    "感恩": re.compile(
        r"感谢|谢谢|感恩|幸运|珍惜|幸福|满足|温暖|感动|"
        r"好人|善良|帮助|支持|陪伴|在乎|关心|爱"
    ),
    "期待": re.compile(
        r"期待|希望|加油|努力|向前|未来可期|相信|机会|"
        r"尝试|改变|进步|成长|学习|新|开始|出发"
    ),
}

# 情绪强度权重（用于联邦学习聚合）
EMOTION_WEIGHTS = {
    "悲伤": 1.5, "焦虑": 1.3, "愤怒": 1.4,
    "迷茫": 1.0, "疲惫": 1.2, "孤独": 1.3,
    "平静": 0.5, "感恩": 0.3, "期待": 0.4,
}


def detect_emotion(text: str) -> str:
    """从文本中检测主要情绪，返回情绪标签"""
    if not text or not text.strip():
        return "平静"

    scores = {}
    for emotion, pattern in EMOTION_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            scores[emotion] = len(matches) * EMOTION_WEIGHTS.get(emotion, 1.0)

    if not scores:
        return "平静"

    return max(scores, key=scores.get)


def detect_emotions_multi(text: str) -> dict[str, float]:
    """检测文本中的多种情绪，返回 {情绪: 得分} 字典"""
    if not text or not text.strip():
        return {"平静": 1.0}

    scores = {}
    for emotion, pattern in EMOTION_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            scores[emotion] = len(matches) * EMOTION_WEIGHTS.get(emotion, 1.0)

    if not scores:
        return {"平静": 1.0}

    # 归一化
    total = sum(scores.values())
    return {k: round(v / total, 3) for k, v in scores.items()}


def compute_session_emotion_profile(messages: list[dict]) -> dict[str, float]:
    """
    计算一次会话的情绪画像（用于联邦学习本地统计）

    Args:
        messages: [{"role": "user", "text": "..."}, ...]

    Returns:
        {"悲伤": 0.3, "焦虑": 0.2, ...} 归一化后的情绪分布
    """
    user_messages = [m.get("text") or m.get("content", "") for m in messages if m.get("role") == "user"]
    if not user_messages:
        return {}

    aggregated = {}
    for msg in user_messages:
        emotions = detect_emotions_multi(msg)
        for emotion, score in emotions.items():
            aggregated[emotion] = aggregated.get(emotion, 0) + score

    # 归一化
    total = sum(aggregated.values())
    if total == 0:
        return {}
    return {k: round(v / total, 3) for k, v in aggregated.items()}
