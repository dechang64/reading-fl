"""
Reading-FL Server

Orchestrates federated training across campuses.
Aggregates backbone weights and distributes updates.
"""

import numpy as np
from typing import Dict, List, Optional
from copy import deepcopy

from core.config import FLConfig, ModelConfig
from core.client import FLClient
from core.aggregation import get_aggregator


class FLServer:
    """
    Federated Learning Server.

    Coordinates training across campus clients:
    1. Selects participating clients each round
    2. Collects backbone weights from clients
    3. Aggregates weights (FedAvg or Task-Aware)
    4. Distributes aggregated weights back to clients
    5. Tracks global metrics and convergence
    """

    def __init__(
        self,
        fl_config: FLConfig,
        model_config: ModelConfig,
        input_dim: int,
    ):
        self.config = fl_config
        self.model_config = model_config
        self.input_dim = input_dim

        # Aggregation strategy
        self.aggregator = get_aggregator(
            strategy=fl_config.aggregation,
            task_weights={"emotion": 0.4, "quality": 0.3, "matching": 0.3},
        )

        # Connected clients
        self.clients: Dict[str, FLClient] = {}

        # Global backbone weights (aggregated)
        self.global_backbone: Optional[List[np.ndarray]] = None

        # Training history
        self.history: List[Dict[str, float]] = []

    def register_client(self, client: FLClient):
        """Register a campus client."""
        self.clients[client.campus_id] = client

    def run_round(self, round_idx: int) -> Dict[str, float]:
        """Execute one FL round."""
        # Select participating clients
        n_participants = max(
            self.config.min_clients,
            len(self.clients) - 1  # Leave-one-out style
        )
        participant_ids = list(np.random.choice(
            list(self.clients.keys()),
            size=min(n_participants, len(self.clients)),
            replace=False,
        ))

        # Distribute global backbone to participants
        if self.global_backbone is not None:
            for cid in participant_ids:
                self.clients[cid].set_backbone_weights(
                    deepcopy(self.global_backbone)
                )

        # Local training
        client_metrics = {}
        client_weights = []
        client_sizes = []

        for cid in participant_ids:
            client = self.clients[cid]
            metrics = client.train()
            client_metrics[cid] = metrics
            client_weights.append(client.get_backbone_weights())
            client_sizes.append(client.n_samples)

        # Aggregate backbone weights
        if client_weights:
            metrics_list = [client_metrics[cid] for cid in participant_ids]
            self.global_backbone = self.aggregator.aggregate(
                client_weights, client_sizes, metrics_list
            )

        # Compute global metrics
        avg_emotion_acc = np.mean([
            m.get("emotion_acc", 0) for m in client_metrics.values()
        ])
        avg_quality_mae = np.mean([
            m.get("quality_mae", 1.0) for m in client_metrics.values()
        ])

        round_metrics = {
            "round": round_idx,
            "participants": participant_ids,
            "avg_emotion_acc": round(float(avg_emotion_acc), 4),
            "avg_quality_mae": round(float(avg_quality_mae), 4),
            **{
                f"{cid}_{k}": v
                for cid, m in client_metrics.items()
                for k, v in m.items()
            },
        }
        self.history.append(round_metrics)
        return round_metrics

    def run_training(self, n_rounds: Optional[int] = None) -> List[Dict]:
        """Run full FL training loop."""
        n_rounds = n_rounds or self.config.num_rounds

        print(f"{'='*60}")
        print(f"  Reading-FL: Federated Training")
        print(f"  Campuses: {list(self.clients.keys())}")
        print(f"  Rounds: {n_rounds} | Aggregation: {self.config.aggregation}")
        print(f"{'='*60}")

        for r in range(n_rounds):
            metrics = self.run_round(r)
            acc = metrics.get("avg_emotion_acc", 0)
            mae = metrics.get("avg_quality_mae", 1.0)
            print(
                f"  Round {r+1:2d}/{n_rounds} | "
                f"Emotion Acc: {acc:.1%} | "
                f"Quality MAE: {mae:.3f}"
            )

        print(f"{'='*60}\n")
        return self.history

    def get_global_metrics(self) -> Dict:
        """Get summary of global training metrics."""
        if not self.history:
            return {}

        return {
            "n_rounds": len(self.history),
            "final_emotion_acc": self.history[-1].get("avg_emotion_acc", 0),
            "final_quality_mae": self.history[-1].get("avg_quality_mae", 1.0),
            "best_emotion_acc": max(
                h.get("avg_emotion_acc", 0) for h in self.history
            ),
            "convergence": self._check_convergence(),
        }

    def _check_convergence(self) -> bool:
        """Check if training has converged (last 3 rounds stable)."""
        if len(self.history) < 3:
            return False
        recent = [h.get("avg_emotion_acc", 0) for h in self.history[-3:]]
        return max(recent) - min(recent) < 0.05

    def __repr__(self) -> str:
        return (
            f"FLServer(clients={len(self.clients)}, "
            f"rounds_completed={len(self.history)}, "
            f"aggregation={self.config.aggregation})"
        )
