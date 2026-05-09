"""联邦学习引擎 — 用户情绪数据联邦聚合

核心思路（EWA-Fed 模式）：
- 每个用户会话是一个"客户端"
- 本地计算情绪分布（不共享原始消息）
- 服务端聚合时用 entropy 加权：高置信度的会话权重更大
- 聚合结果用于优化角色的 system prompt 和情绪识别

隐私保证：
- 只传输聚合统计量（情绪分布向量），不传输原始文本
- 统计量不可逆推原始消息
"""

import math
import json
import time
from core.config import EMOTIONS
from core.db import (
    save_emotion_snapshot,
    get_recent_snapshots,
    save_fl_round,
    get_fl_rounds,
)


def compute_entropy(emotion_dist: dict[str, float]) -> float:
    """
    计算情绪分布的 Shannon 熵

    高熵 = 情绪分散（不确定性强）→ 降权
    低熵 = 情绪集中（确定性强）→ 升权
    """
    if not emotion_dist:
        return 0.0

    total = sum(emotion_dist.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for prob in emotion_dist.values():
        p = prob / total
        if p > 0:
            entropy -= p * math.log2(p)

    return entropy


def compute_confidence(emotion_dist: dict[str, float]) -> float:
    """
    计算置信度 = 1 - 归一化熵

    置信度范围 [0, 1]：
    - 1.0 = 完全确定（只有一种情绪）
    - 0.0 = 完全不确定（均匀分布）
    """
    n = len(emotion_dist)
    if n <= 1:
        return 1.0

    max_entropy = math.log2(n)
    entropy = compute_entropy(emotion_dist)
    return 1.0 - (entropy / max_entropy)


def submit_local_stats(session_id: str, emotion_dist: dict[str, float]):
    """
    提交本地情绪统计到联邦聚合器

    Args:
        session_id: 会话标识（匿名）
        emotion_dist: {"悲伤": 0.3, "焦虑": 0.2, ...}
    """
    entropy = compute_entropy(emotion_dist)
    confidence = compute_confidence(emotion_dist)

    save_emotion_snapshot(
        emotions=emotion_dist,
        message_count=len(emotion_dist),
    )


def federated_aggregate(min_clients: int = 3) -> dict | None:
    """
    执行一轮联邦聚合

    1. 收集最近的客户端情绪快照
    2. 用 EWA（Entropy-Weighted Aggregation）加权
    3. 生成全局情绪分布
    4. 记录聚合轮次

    Returns:
        {
            "round": int,
            "aggregated": {"悲伤": 0.25, ...},
            "client_count": int,
            "entropy_weights": {...},
            "timestamp": float
        }
        如果客户端不足返回 None
    """
    snapshots = get_recent_snapshots(limit=50)
    if len(snapshots) < min_clients:
        return None

    # EWA 加权聚合
    weighted_sum = {e: 0.0 for e in EMOTIONS}
    total_weight = 0.0
    entropy_weights = {}

    for snap in snapshots:
        emotions = snap["session_emotions"]
        confidence = compute_confidence(emotions)

        # 权重 = confidence（高置信度多说话）
        weight = max(confidence, 0.01)  # 避免零权重
        entropy_weights[str(snap["id"])] = round(weight, 4)

        for emotion, score in emotions.items():
            if emotion in weighted_sum:
                weighted_sum[emotion] += score * weight

        total_weight += weight

    # 归一化
    aggregated = {}
    if total_weight > 0:
        for emotion in EMOTIONS:
            aggregated[emotion] = round(weighted_sum[emotion] / total_weight, 4)

    # 获取最新轮次号
    existing_rounds = get_fl_rounds(limit=1)
    next_round = (existing_rounds[0]["round_num"] + 1) if existing_rounds else 1

    result = {
        "round": next_round,
        "aggregated": aggregated,
        "client_count": len(snapshots),
        "entropy_weights": entropy_weights,
        "timestamp": time.time(),
    }

    save_fl_round(
        round_num=next_round,
        aggregated=aggregated,
        client_count=len(snapshots),
        entropy_weights=entropy_weights,
    )

    return result


def get_global_emotion_trend() -> dict:
    """
    获取全局情绪趋势（用于仪表盘展示）

    Returns:
        {
            "current": {"悲伤": 0.25, ...},
            "rounds": [...],
            "total_clients": int,
            "total_rounds": int
        }
    """
    rounds = get_fl_rounds(limit=10)
    snapshots = get_recent_snapshots(limit=200)

    current = rounds[0]["aggregated_emotions"] if rounds else {}

    return {
        "current": current,
        "rounds": rounds,
        "total_clients": len(snapshots),
        "total_rounds": len(rounds),
    }
