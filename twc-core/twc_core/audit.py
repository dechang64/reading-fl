"""
twc_core.audit — SHA-256 Audit Chain
=====================================
Unified audit chain extracted from organoid-fl (AuditEngine) and TWC-FL-PROD (AuditChain).
Records FL operations with tamper-evident SHA-256 hashing.

Usage:
    from twc_core.audit import AuditEngine
    audit = AuditEngine("my-project")
    audit.append("round_start", {"round": 1, "clients": 5})
    audit.append("aggregation", {"strategy": "fedavg", "loss": 0.34})
    assert audit.verify_chain()
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AuditBlock:
    """A single block in the audit chain."""
    index: int
    timestamp: str
    operation: str
    details: dict
    prev_hash: str
    hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of block contents."""
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "details": self.details,
            "prev_hash": self.prev_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def verify(self) -> bool:
        """Verify block hash integrity."""
        return self.hash == self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class AuditEngine:
    """SHA-256 audit chain for FL operations.

    Provides tamper-evident logging of federated learning events.
    Compatible with Rust native audit chain via gRPC.

    Usage:
        audit = AuditEngine("organoid-fl")
        audit.append("training_round", {"round": 1, "loss": 0.45})
        audit.append("aggregation", {"strategy": "fedavg"})
        print(audit.get_stats())
    """

    def __init__(self, project_name: str = "twc"):
        self.project_name = project_name
        self.chain: list[AuditBlock] = []
        self._create_genesis()

    def _create_genesis(self):
        """Create genesis block."""
        genesis = AuditBlock(
            index=0,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            operation="genesis",
            details={"project": self.project_name},
            prev_hash="0" * 64,
        )
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    def append(self, operation: str, details: Optional[dict] = None) -> AuditBlock:
        """Append a new block to the chain.

        Args:
            operation: Operation type (e.g., "training_round", "aggregation").
            details: Optional metadata dict.

        Returns:
            The newly created AuditBlock.
        """
        block = AuditBlock(
            index=len(self.chain),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            operation=operation,
            details=details or {},
            prev_hash=self.chain[-1].hash,
        )
        block.hash = block.compute_hash()
        self.chain.append(block)
        return block

    def verify_chain(self) -> bool:
        """Verify entire chain integrity.

        Returns:
            True if all blocks are valid and properly linked.
        """
        for i in range(1, len(self.chain)):
            if self.chain[i].prev_hash != self.chain[i - 1].hash:
                return False
            if not self.chain[i].verify():
                return False
        return True

    def recent(self, n: int = 10) -> list[AuditBlock]:
        """Get the most recent n blocks."""
        return self.chain[-n:]

    def query(self, operation: str) -> list[AuditBlock]:
        """Query blocks by operation type."""
        return [b for b in self.chain if b.operation == operation]

    def export_json(self) -> str:
        """Export chain as JSON string."""
        return json.dumps([b.to_dict() for b in self.chain], ensure_ascii=False, indent=2)

    def __len__(self) -> int:
        return len(self.chain)

    def __repr__(self) -> str:
        return f"AuditEngine(project={self.project_name!r}, blocks={len(self)})"

    def get_stats(self) -> dict:
        """Return audit chain statistics."""
        return {
            "chain_length": len(self),
            "chain_valid": self.verify_chain(),
            "latest_hash": self.chain[-1].hash[:16] + "..." if self.chain else "",
            "operations": {op: sum(1 for b in self.chain if b.operation == op)
                          for op in set(b.operation for b in self.chain)},
        }

    def to_dataframe(self):
        """Export chain as pandas DataFrame."""
        import pandas as pd
        rows = []
        for b in self.chain:
            rows.append({
                "Block": b.index,
                "Time": b.timestamp,
                "Operation": b.operation,
                "Details": json.dumps(b.details, ensure_ascii=False)[:80],
                "Hash": b.hash[:16] + "...",
                "Prev": b.prev_hash[:16] + "...",
            })
        return pd.DataFrame(rows)
