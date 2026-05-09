"""
Module F: Blockchain Audit Chain

Features:
    - P0 Data attestation: immutable audit records for every data exchange/model update
    - P0 Chain verification: verify integrity of the entire audit chain
    - P1 Audit query: filter records by time/action type/client
    - P1 Export: generate audit log reports

Pure Python implementation. No external dependencies.
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
    """Audit entry."""
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
        """Compute entry hash (SHA-256)."""
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
        """Verify entry hash integrity."""
        return self.entry_hash == self._compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class AuditChain:
    """Blockchain-style audit chain.

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
        """Add audit entry.

        Args:
            action: action type
            actor: executor (client_id or "system")
            details: action details

        Returns:
            Newly created AuditEntry
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
        """Verify integrity of the entire audit chain.

        Returns:
            True if chain is intact and untampered
        """
        for i, entry in enumerate(self.entries):
            # Verify hash
            if not entry.verify():
                return False
            # Verify linkage
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
        """Query audit records.

        Args:
            action: filter by action type
            actor: filter by actor
            limit: maximum results to return

        Returns:
            List of matching audit entries
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
        """Get audit chain summary."""
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
        """Export audit chain as JSON string."""
        return json.dumps(
            [e.to_dict() for e in self.entries],
            indent=2, ensure_ascii=False, default=str,
        )

    def to_dataframe(self):
        """Export as pandas DataFrame."""
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
