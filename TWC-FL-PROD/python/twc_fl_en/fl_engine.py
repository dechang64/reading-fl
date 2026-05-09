"""
Module E: Federated Learning Engine

Features:
    - P0 FL node management: add/remove participating enterprises
    - P0 FedAvg aggregation: weighted average of client model updates
    - P0 Model distribution: broadcast global model to all clients
    - P1 Differential privacy: gradient noise injection
    - P1 Convergence monitoring: training curves and metrics

Pure NumPy implementation. No PyTorch dependency. Streamlit Cloud compatible.
"""
from __future__ import annotations

import numpy as np
import json
import hashlib
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FLConfig:
    """Federated learning configuration."""
    num_rounds: int = 10
    local_epochs: int = 5
    learning_rate: float = 0.01
    dp_epsilon: float = 10.0  # DP budget (inf = no protection)
    dp_clip_norm: float = 1.0  # gradient clipping norm
    min_participants: int = 2  # minimum participating clients


@dataclass
class FLClient:
    """Federated learning client (represents one catalyst enterprise)."""
    client_id: str
    client_name: str
    num_samples: int = 500
    model_dim: int = 32
    local_epochs: int = 5
    learning_rate: float = 0.01
    # Simulated data characteristics
    specialty: str = "general"  # general / low_rh / high_osc / diesel
    data_quality: float = 1.0  # 0-1, simulated data quality


@dataclass
class ClientUpdate:
    """Client model update."""
    client_id: str
    round_id: int
    num_samples: int
    local_loss: float
    weights: List[np.ndarray] = field(default_factory=list, repr=False, compare=False)
    dp_noise_scale: float = 0.0


@dataclass
class AggregationResult:
    """FedAvg aggregation result."""
    round_id: int
    global_loss: float
    participating_clients: int
    total_samples: int
    client_losses: Dict[str, float] = field(default_factory=dict)
    convergence_delta: float = 0.0


class TWCModel:
    """TWC performance prediction model (simplified MLP, pure NumPy).

    Input: formula feature vector
    Output: performance prediction (CO/HC/NOx conversion, T50)
    """

    def __init__(self, input_dim: int = 10, hidden_dim: int = 32, output_dim: int = 3):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        # Xavier initialization
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, output_dim) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(output_dim)

    def forward(self, X: np.ndarray) -> np.ndarray:
        """Forward pass."""
        h = np.maximum(0, X @ self.W1 + self.b1)  # ReLU
        return h @ self.W2 + self.b2

    def get_weights(self) -> List[np.ndarray]:
        return [self.W1, self.b1, self.W2, self.b2]

    def set_weights(self, weights: List[np.ndarray]):
        self.W1, self.b1, self.W2, self.b2 = weights

    def compute_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        pred = self.forward(X)
        return float(np.mean((pred - y) ** 2))

    def train_step(self, X: np.ndarray, y: np.ndarray, lr: float = 0.01) -> float:
        """Single-step gradient descent with gradient clipping and numerical stability."""
        n = len(X)
        # Forward
        z1 = X @ self.W1 + self.b1
        h = np.maximum(0, z1)  # ReLU
        pred = h @ self.W2 + self.b2
        loss = float(np.mean((pred - y) ** 2))

        # Check NaN
        if np.isnan(loss) or np.isinf(loss):
            return loss

        # Backward
        dpred = 2 * (pred - y) / n
        dW2 = h.T @ dpred
        db2 = dpred.sum(axis=0)
        dh = (dpred @ self.W2.T) * (z1 > 0).astype(float)
        dW1 = X.T @ dh
        db1 = dh.sum(axis=0)

        # Gradient clipping (max norm = 5.0)
        clip_norm = 5.0
        for grad_name, grad in [("W1", dW1), ("b1", db1), ("W2", dW2), ("b2", db2)]:
            g_norm = np.linalg.norm(grad)
            if g_norm > clip_norm:
                grad *= clip_norm / g_norm

        # Update
        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2

        return loss


class FLEngine:
    """Federated learning engine.

    Usage:
        engine = FLEngine()
        engine.add_client(FLClient("client_1", "Weifu High-Tech", num_samples=800))
        engine.add_client(FLClient("client_2", "Sino-Platinum", num_samples=600))
        history = engine.run_simulation(num_rounds=10)
    """

    def __init__(self, config: Optional[FLConfig] = None):
        self.config = config or FLConfig()
        self.clients: List[FLClient] = []
        self.global_model: Optional[TWCModel] = None
        self.history: List[AggregationResult] = []
        self._client_data_cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self._y_mean: Optional[np.ndarray] = None
        self._y_std: Optional[np.ndarray] = None
        self._init_global_model()

    def _init_global_model(self):
        """Initialize global model."""
        self.global_model = TWCModel(input_dim=10, hidden_dim=32, output_dim=3)

    def add_client(self, client: FLClient):
        """Add FL client."""
        self.clients.append(client)

    def remove_client(self, client_id: str):
        """Remove a client."""
        self.clients = [c for c in self.clients if c.client_id != client_id]

    def get_client(self, client_id: str) -> Optional[FLClient]:
        for c in self.clients:
            if c.client_id == client_id:
                return c
        return None

    def run_simulation(self, num_rounds: Optional[int] = None) -> List[AggregationResult]:
        """Run FL training simulation.

        Returns:
            List of aggregation results per round
        """
        n_rounds = num_rounds or self.config.num_rounds
        self.history = []

        if len(self.clients) < self.config.min_participants:
            return self.history

        # Pre-generate all client data and compute global y normalization params
        all_y = []
        for client in self.clients:
            X, y = self._generate_client_data(client)
            all_y.append(y)
        all_y_concat = np.concatenate(all_y, axis=0)
        self._y_mean = all_y_concat.mean(axis=0)
        self._y_std = all_y_concat.std(axis=0) + 1e-8

        prev_loss = float("inf")

        for round_id in range(1, n_rounds + 1):
            # 1. Distribute global model
            updates = []
            client_losses = {}

            for client in self.clients:
                # 2. Local training
                local_model = TWCModel(
                    input_dim=self.global_model.input_dim,
                    hidden_dim=self.global_model.hidden_dim,
                    output_dim=self.global_model.output_dim,
                )
                local_model.set_weights(self.global_model.get_weights())

                # Generate simulated data (cached)
                X, y_raw = self._generate_client_data(client)
                y = (y_raw - self._y_mean) / self._y_std  # Z-score normalization

                # Local training
                loss = float("inf")
                for _ in range(client.local_epochs):
                    loss = local_model.train_step(X, y, client.learning_rate)

                # 3. Differential privacy (optional): add Gaussian noise to weights
                dp_noise = 0.0
                if self.config.dp_epsilon < float("inf"):
                    dp_noise = self._compute_dp_noise(client.num_samples)
                    noisy_weights = []
                    for w in local_model.get_weights():
                        noisy_w = w + np.random.normal(0, dp_noise, w.shape)
                        noisy_weights.append(noisy_w)
                    local_model.set_weights(noisy_weights)

                # 4. Collect update
                update = ClientUpdate(
                    client_id=client.client_id,
                    round_id=round_id,
                    num_samples=client.num_samples,
                    local_loss=loss,
                    weights=local_model.get_weights(),
                    dp_noise_scale=dp_noise,
                )
                updates.append(update)
                client_losses[client.client_id] = round(loss, 4)

            # 5. FedAvg aggregation
            agg = self._fedavg_aggregate(updates, round_id)
            agg.client_losses = client_losses
            agg.convergence_delta = round(prev_loss - agg.global_loss, 4)
            prev_loss = agg.global_loss
            self.history.append(agg)

        return self.history

    def _generate_client_data(self, client: FLClient) -> Tuple[np.ndarray, np.ndarray]:
        """Generate simulated training data for client (cached, reproducible)."""
        if client.client_id in self._client_data_cache:
            return self._client_data_cache[client.client_id]

        # Deterministic seed (based on client_id SHA-256)
        seed = int(hashlib.sha256(client.client_id.encode()).hexdigest(), 16) % (2**31)
        rng = np.random.RandomState(seed)
        n = client.num_samples
        X = rng.randn(n, self.global_model.input_dim) * client.data_quality

        # Simulate TWC performance targets
        y = np.zeros((n, self.global_model.output_dim))
        y[:, 0] = 95 + rng.randn(n) * 3  # CO_conv ~ 95%
        y[:, 1] = 94 + rng.randn(n) * 4  # HC_conv ~ 94%
        y[:, 2] = 91 + rng.randn(n) * 5  # NOx_conv ~ 91%

        # Adjust based on specialty
        if client.specialty == "low_rh":
            y[:, 2] -= 2  # NOx slightly lower
        elif client.specialty == "high_osc":
            y[:, 0] += 1  # CO slightly higher

        self._client_data_cache[client.client_id] = (X, y)
        return X, y

    def _fedavg_aggregate(self, updates: List[ClientUpdate], round_id: int) -> AggregationResult:
        """FedAvg weighted average aggregation."""
        total_samples = sum(u.num_samples for u in updates)
        if total_samples == 0:
            raise ValueError("Total samples is zero — cannot aggregate")

        agg_weights = []
        for layer_idx in range(len(updates[0].weights)):
            weighted_sum = sum(
                u.num_samples * u.weights[layer_idx] for u in updates
            )
            agg_weights.append(weighted_sum / total_samples)

        self.global_model.set_weights(agg_weights)

        # Compute global loss (normalized y, consistent with training)
        X_all, y_all = [], []
        for client in self.clients:
            X, y = self._generate_client_data(client)
            X_all.append(X)
            y_all.append(y)
        X_all = np.vstack(X_all)
        y_all = np.vstack(y_all)
        y_all_norm = (y_all - self._y_mean) / self._y_std
        global_loss = self.global_model.compute_loss(X_all, y_all_norm)

        return AggregationResult(
            round_id=round_id,
            global_loss=round(global_loss, 4),
            participating_clients=len(updates),
            total_samples=total_samples,
        )

    def _compute_dp_noise(self, num_samples: int) -> float:
        """Compute differential privacy noise standard deviation."""
        if self.config.dp_epsilon >= float("inf"):
            return 0.0
        # Gaussian mechanism: σ = clip_norm * sqrt(2*ln(1.25/δ)) / ε
        delta = 1e-5
        sigma = self.config.dp_clip_norm * np.sqrt(2 * np.log(1.25 / delta)) / self.config.dp_epsilon
        return sigma / np.sqrt(num_samples)

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
            "total_samples": sum(c.num_samples for c in self.clients),
        }
