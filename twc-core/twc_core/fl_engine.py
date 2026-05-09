"""
twc_core.fl_engine — Federated Learning Engine
==============================================
Unified FL engine extracted from TWC-FL-PROD (FLEngine) with NumPy-only implementation.
Supports FedAvg aggregation, differential privacy, and convergence monitoring.

Usage:
    from twc_core.fl_engine import FLEngine, FLConfig
    config = FLConfig(num_rounds=10, local_epochs=5)
    engine = FLEngine(config)
    engine.add_client("lab_a", num_samples=100)
    engine.add_client("lab_b", num_samples=80)
    result = engine.run_simulation()
"""
from __future__ import annotations

import numpy as np
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class FLConfig:
    """Federated learning configuration."""
    num_rounds: int = 10
    local_epochs: int = 5
    learning_rate: float = 0.01
    dp_epsilon: float = float("inf")  # DP budget (inf = no protection)
    dp_clip_norm: float = 1.0
    min_participants: int = 2


@dataclass
class FLClient:
    """Represents one FL participant."""
    client_id: str
    client_name: str = ""
    num_samples: int = 100
    data: Optional[np.ndarray] = None
    labels: Optional[np.ndarray] = None
    weights: Optional[np.ndarray] = None


@dataclass
class ClientUpdate:
    """Result of one client's local training."""
    client_id: str
    num_samples: int
    weights: np.ndarray
    loss: float
    entropy: float = 0.0  # Optional: model uncertainty signal


@dataclass
class AggregationResult:
    """Result of one FL round."""
    round_id: int
    global_loss: float
    client_losses: Dict[str, float] = field(default_factory=dict)
    client_entropies: Dict[str, float] = field(default_factory=dict)
    weights_used: Dict[str, float] = field(default_factory=dict)


class FLEngine:
    """Federated Learning Engine with FedAvg and optional DP.

    Pure NumPy implementation. No PyTorch dependency.

    Usage:
        engine = FLEngine(FLConfig(num_rounds=20))
        engine.add_client("hospital_a", num_samples=500)
        engine.add_client("hospital_b", num_samples=300)
        for result in engine.run_simulation():
            print(f"Round {result.round_id}: loss={result.global_loss:.4f}")
    """

    def __init__(self, config: Optional[FLConfig] = None):
        self.config = config or FLConfig()
        self.clients: Dict[str, FLClient] = {}
        self.global_weights: Optional[np.ndarray] = None
        self.history: List[AggregationResult] = []
        self._client_data_cache: Dict[str, tuple] = {}

    def add_client(self, client_id: str, client_name: str = "",
                   num_samples: int = 100, data: Optional[np.ndarray] = None,
                   labels: Optional[np.ndarray] = None) -> FLClient:
        """Add a participating client."""
        client = FLClient(
            client_id=client_id,
            client_name=client_name or client_id,
            num_samples=num_samples,
            data=data,
            labels=labels,
        )
        self.clients[client_id] = client
        return client

    def remove_client(self, client_id: str):
        """Remove a client."""
        self.clients.pop(client_id, None)
        self._client_data_cache.pop(client_id, None)

    def get_client(self, client_id: str) -> Optional[FLClient]:
        """Get client by ID."""
        return self.clients.get(client_id)

    def _generate_client_data(self, client: FLClient, input_dim: int, output_dim: int,
                              seed: int = 42) -> tuple:
        """Generate or retrieve cached synthetic data for a client."""
        cache_key = f"{client.client_id}_{input_dim}_{output_dim}"
        if cache_key in self._client_data_cache:
            return self._client_data_cache[cache_key]

        seed = int(hashlib.sha256(client.client_id.encode()).hexdigest()[:8], 16) % (2**31)
        rng = np.random.RandomState(seed)
        X = rng.randn(client.num_samples, input_dim)
        W_true = rng.randn(input_dim, output_dim)
        y = X @ W_true + rng.randn(client.num_samples, output_dim) * 0.1

        self._client_data_cache[cache_key] = (X, y, W_true)
        return X, y, W_true

    def _fedavg_aggregate(self, updates: List[ClientUpdate]) -> np.ndarray:
        """FedAvg: weighted average of client updates by sample count."""
        total_samples = sum(u.num_samples for u in updates)
        if total_samples == 0:
            return self.global_weights

        aggregated = np.zeros_like(updates[0].weights)
        for update in updates:
            weight = update.num_samples / total_samples
            aggregated += weight * update.weights
        return aggregated

    def _compute_dp_noise(self, num_samples: int) -> float:
        """Compute differential privacy noise standard deviation."""
        if self.config.dp_epsilon >= float("inf"):
            return 0.0
        delta = 1e-5
        sigma = self.config.dp_clip_norm * np.sqrt(2 * np.log(1.25 / delta)) / self.config.dp_epsilon
        return sigma / np.sqrt(num_samples)

    def run_simulation(self, input_dim: int = 10, output_dim: int = 2) -> List[AggregationResult]:
        """Run federated training simulation.

        Args:
            input_dim: Feature dimension for synthetic data.
            output_dim: Output dimension.

        Yields:
            AggregationResult for each round.
        """
        if len(self.clients) < self.config.min_participants:
            raise ValueError(f"Need at least {self.config.min_participants} clients")

        # Initialize global model
        self.global_weights = np.zeros((input_dim, output_dim))

        for round_id in range(1, self.config.num_rounds + 1):
            updates = []
            client_losses = {}
            client_entropies = {}
            weights_used = {}

            for cid, client in self.clients.items():
                X, y, _ = self._generate_client_data(client, input_dim, output_dim)

                # Local training (gradient descent)
                local_weights = self.global_weights.copy()
                for _ in range(self.config.local_epochs):
                    pred = X @ local_weights
                    error = pred - y
                    grad = X.T @ error / max(len(X), 1)
                    local_weights -= self.config.learning_rate * grad

                # Compute loss
                final_pred = X @ local_weights
                loss = float(np.mean((final_pred - y) ** 2))

                # Compute entropy (softmax over predictions)
                probs = np.exp(final_pred - np.max(final_pred, axis=-1, keepdims=True))
                probs = probs / np.sum(probs, axis=-1, keepdims=True)
                entropy = float(-np.mean(np.sum(probs * np.log(probs + 1e-10), axis=-1)))

                # DP noise
                noise_std = self._compute_dp_noise(client.num_samples)
                if noise_std > 0:
                    local_weights += np.random.randn(*local_weights.shape) * noise_std

                updates.append(ClientUpdate(
                    client_id=cid,
                    num_samples=client.num_samples,
                    weights=local_weights,
                    loss=loss,
                    entropy=entropy,
                ))
                client_losses[cid] = round(loss, 4)
                client_entropies[cid] = round(entropy, 4)
                weights_used[cid] = client.num_samples

            # Aggregate
            self.global_weights = self._fedavg_aggregate(updates)

            # Global loss
            global_loss = np.mean([u.loss for u in updates])

            result = AggregationResult(
                round_id=round_id,
                global_loss=round(global_loss, 4),
                client_losses=client_losses,
                client_entropies=client_entropies,
                weights_used=weights_used,
            )
            self.history.append(result)
            yield result

    def get_convergence_summary(self) -> Dict[str, Any]:
        """Get convergence summary."""
        if not self.history:
            return {"status": "no_data"}

        losses = [h.global_loss for h in self.history]
        return {
            "status": "converged" if len(losses) >= 2 and losses[-1] < losses[0] else "training",
            "initial_loss": round(losses[0], 4),
            "final_loss": round(losses[-1], 4),
            "improvement": round(losses[0] - losses[-1], 4),
            "improvement_pct": round((losses[0] - losses[-1]) / losses[0] * 100, 1) if losses[0] > 0 else 0,
            "total_rounds": len(losses),
            "total_clients": len(self.clients),
            "total_samples": sum(c.num_samples for c in self.clients.values()),
        }
