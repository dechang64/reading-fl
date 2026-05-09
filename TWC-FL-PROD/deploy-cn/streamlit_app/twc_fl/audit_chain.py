"""
模块F：区块链审计链（Audit Chain）

功能：
    - P0 数据存证：每次数据交换/模型更新生成不可篡改的审计记录
    - P0 链验证：验证整条审计链的完整性
    - P1 审计查询：按时间/类型/客户端筛选审计记录
    - P1 导出报告：生成审计日志报告

纯Python实现，无外部依赖。
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AuditEntry:
    """审计条目。"""
    entry_id: str
    timestamp: str
    action: str  # data_import / fl_round / model_distribute / anonymize / compliance_check
    actor: str  # client_id or "system"
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = "0" * 64
    entry_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """计算条目哈希（SHA-256）。"""
        content = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def verify(self) -> bool:
        """验证条目哈希是否正确。"""
        return self.entry_hash == self._compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class AuditChain:
    """区块链式审计链。

    Usage:
        chain = AuditChain()
        chain.append("data_import", "client_1", {"num_records": 50})
        chain.append("fl_round", "system", {"round_id": 1, "participants": 3})
        is_valid = chain.verify_chain()
    """

    def __init__(self):
        self.entries: List[AuditEntry] = []
        self._counter = 0

    def append(self, action: str, actor: str,
               details: Optional[Dict[str, Any]] = None) -> AuditEntry:
        """添加审计条目。

        Args:
            action: 操作类型
            actor: 执行者（client_id 或 "system"）
            details: 操作详情

        Returns:
            新创建的 AuditEntry
        """
        self._counter += 1
        previous_hash = self.entries[-1].entry_hash if self.entries else "0" * 64

        entry = AuditEntry(
            entry_id=f"AUD-{self._counter:06d}",
            timestamp=datetime.now().isoformat(),
            action=action,
            actor=actor,
            details=details or {},
            previous_hash=previous_hash,
        )
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """验证整条审计链的完整性。

        Returns:
            True 如果链完整且未被篡改
        """
        for i, entry in enumerate(self.entries):
            # 验证哈希
            if not entry.verify():
                return False
            # 验证链接
            if i == 0:
                if entry.previous_hash != "0" * 64:
                    return False
            else:
                if entry.previous_hash != self.entries[i - 1].entry_hash:
                    return False
        return True

    def query(self, action: Optional[str] = None,
              actor: Optional[str] = None,
              limit: int = 50) -> List[AuditEntry]:
        """查询审计记录。

        Args:
            action: 按操作类型筛选
            actor: 按执行者筛选
            limit: 最大返回数量

        Returns:
            匹配的审计条目列表
        """
        results = []
        for entry in reversed(self.entries):
            if action and entry.action != action:
                continue
            if actor and entry.actor != actor:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def get_summary(self) -> Dict[str, Any]:
        """获取审计链摘要。"""
        action_counts: Dict[str, int] = {}
        actor_counts: Dict[str, int] = {}
        for entry in self.entries:
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
            actor_counts[entry.actor] = actor_counts.get(entry.actor, 0) + 1

        return {
            "total_entries": len(self.entries),
            "is_valid": self.verify_chain(),
            "action_counts": action_counts,
            "actor_counts": actor_counts,
            "first_timestamp": self.entries[0].timestamp if self.entries else None,
            "last_timestamp": self.entries[-1].timestamp if self.entries else None,
        }

    def export_json(self) -> str:
        """导出审计链为 JSON 字符串。"""
        return json.dumps(
            [e.to_dict() for e in self.entries],
            indent=2, ensure_ascii=False, default=str,
        )

    def to_dataframe(self):
        """导出为 pandas DataFrame。"""
        import pandas as pd
        if not self.entries:
            return pd.DataFrame()
        rows = []
        for e in self.entries:
            row = {
                "entry_id": e.entry_id,
                "timestamp": e.timestamp,
                "action": e.action,
                "actor": e.actor,
                "previous_hash": e.previous_hash[:16] + "...",
                "hash": e.entry_hash[:16] + "...",
            }
            row.update({f"detail_{k}": v for k, v in e.details.items()})
            rows.append(row)
        return pd.DataFrame(rows)
