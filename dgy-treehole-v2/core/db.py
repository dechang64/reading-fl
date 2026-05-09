"""SQLite 数据库层 — 匿名社交、情绪统计、树洞记录

设计原则：
- 所有用户数据匿名，不存储任何个人标识
- 树洞内容不持久化（释放即消失），仅统计聚合数据
- 社交帖子匿名存储，仅保留内容+情绪标签+时间戳
- 情绪统计用于联邦学习聚合
"""

import sqlite3
import json
import time
import threading
import html
from contextlib import contextmanager
from core.config import DB_PATH, EMOTIONS

_lock = threading.Lock()
_conn = None  # 单例连接（内存数据库必须共享同一个连接）

def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        if DB_PATH != ":memory:":
            _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn

@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    # 内存数据库不关闭连接，保持单例

def init_db():
    """建表（幂等）"""
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                emotion TEXT NOT NULL,
                scene TEXT DEFAULT '',
                resonates INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_posts_emotion ON posts(emotion);
            CREATE INDEX IF NOT EXISTS idx_posts_scene ON posts(scene);
            CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);

            CREATE TABLE IF NOT EXISTS treehole_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                emotion TEXT NOT NULL,
                word_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_th_stats_created ON treehole_stats(created_at);

            CREATE TABLE IF NOT EXISTS emotion_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_emotions TEXT NOT NULL,
                scene TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_emotion_snap_created ON emotion_snapshots(created_at);

            CREATE TABLE IF NOT EXISTS fl_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_num INTEGER NOT NULL,
                aggregated_emotions TEXT NOT NULL,
                client_count INTEGER DEFAULT 0,
                entropy_weights TEXT DEFAULT '{}',
                created_at REAL NOT NULL
            );
        """)


# 模块加载时自动建表（内存数据库必须在使用前初始化）
init_db()


# ═══════════════════════════════════════════════════════════
#  匿名社交
# ═══════════════════════════════════════════════════════════

def create_post(content: str, emotion: str, scene: str = "") -> int:
    with _lock:
        with get_db() as db:
            cur = db.execute(
                "INSERT INTO posts (content, emotion, scene, created_at) VALUES (?, ?, ?, ?)",
                (html.escape(content[:500]), emotion, scene, time.time())
            )
            return cur.lastrowid

def get_posts(limit: int = 50, emotion: str = "", scene: str = "") -> list[dict]:
    with get_db() as db:
        q = "SELECT * FROM posts"
        params = []
        conditions = []
        if emotion:
            conditions.append("emotion = ?")
            params.append(emotion)
        if scene:
            conditions.append("scene = ?")
            params.append(scene)
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = db.execute(q, params).fetchall()
        return [dict(r) for r in rows]

def resonate_post(post_id: int) -> bool:
    with _lock:
        with get_db() as db:
            cur = db.execute(
                "UPDATE posts SET resonates = resonates + 1 WHERE id = ?", (post_id,)
            )
            return cur.rowcount > 0

def get_emotion_distribution(days: int = 7) -> dict[str, int]:
    """获取最近N天的情绪分布"""
    with get_db() as db:
        cutoff = time.time() - days * 86400
        rows = db.execute(
            "SELECT emotion, COUNT(*) as cnt FROM posts WHERE created_at > ? GROUP BY emotion",
            (cutoff,)
        ).fetchall()
        return {r["emotion"]: r["cnt"] for r in rows}


# ═══════════════════════════════════════════════════════════
#  树洞统计（不存储内容，仅统计）
# ═══════════════════════════════════════════════════════════

def record_treehole(method: str, emotion: str, word_count: int = 0):
    with _lock:
        with get_db() as db:
            db.execute(
                "INSERT INTO treehole_stats (method, emotion, word_count, created_at) VALUES (?, ?, ?, ?)",
                (method, emotion, word_count, time.time())
            )

def get_treehole_stats(days: int = 7) -> dict:
    with get_db() as db:
        cutoff = time.time() - days * 86400
        rows = db.execute(
            "SELECT method, COUNT(*) as cnt, SUM(word_count) as total_words "
            "FROM treehole_stats WHERE created_at > ? GROUP BY method",
            (cutoff,)
        ).fetchall()
        return {r["method"]: {"count": r["cnt"], "total_words": r["total_words"] or 0} for r in rows}


# ═══════════════════════════════════════════════════════════
#  情绪快照（用于联邦学习）
# ═══════════════════════════════════════════════════════════

def save_emotion_snapshot(emotions: dict, scene: str = "", message_count: int = 0):
    """保存一次会话的情绪统计快照（不存储原始消息）"""
    with _lock:
        with get_db() as db:
            db.execute(
                "INSERT INTO emotion_snapshots (session_emotions, scene, message_count, created_at) VALUES (?, ?, ?, ?)",
                (json.dumps(emotions, ensure_ascii=False), scene, message_count, time.time())
            )

def get_recent_snapshots(limit: int = 100) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM emotion_snapshots ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["session_emotions"] = json.loads(d["session_emotions"])
            result.append(d)
        return result


# ═══════════════════════════════════════════════════════════
#  联邦学习轮次记录
# ═══════════════════════════════════════════════════════════

def save_fl_round(round_num: int, aggregated: dict, client_count: int, entropy_weights: dict):
    with _lock:
        with get_db() as db:
            db.execute(
                "INSERT INTO fl_rounds (round_num, aggregated_emotions, client_count, entropy_weights, created_at) VALUES (?, ?, ?, ?, ?)",
                (round_num, json.dumps(aggregated, ensure_ascii=False), client_count,
                 json.dumps(entropy_weights, ensure_ascii=False), time.time())
            )

def get_fl_rounds(limit: int = 20) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM fl_rounds ORDER BY round_num DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["aggregated_emotions"] = json.loads(d["aggregated_emotions"])
            d["entropy_weights"] = json.loads(d["entropy_weights"])
            result.append(d)
        return result
