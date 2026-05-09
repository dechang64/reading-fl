"""
Reading-FL Models

Shared backbone with three task-specific heads:
  - Emotion Head: 6-class classification
  - Quality Head: regression (0-1)
  - Matching Head: embedding for reader matching
"""

import numpy as np
from typing import Dict, List, Tuple


# ============================================================
# Activation functions
# ============================================================

def relu(x: np.ndarray) -> np.ndarray:
    """Element-wise ReLU activation."""
    return np.maximum(0, x)

def relu_derivative(x: np.ndarray) -> np.ndarray:
    """Derivative of ReLU: 1 where x > 0, else 0."""
    return (x > 0).astype(np.float32)

def softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / e_x.sum(axis=-1, keepdims=True)

def sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid activation."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def l2_normalize(x: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """L2 normalize along last axis."""
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / (norm + eps)


# ============================================================
# Dense Layer
# ============================================================

class DenseLayer:
    """A single fully-connected layer with Xavier initialization."""

    def __init__(self, in_dim: int, out_dim: int):
        # Xavier initialization
        scale = np.sqrt(2.0 / (in_dim + out_dim))
        self.W = (np.random.randn(in_dim, out_dim) * scale).astype(np.float32)
        self.b = np.zeros(out_dim, dtype=np.float32)
        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._input = x
        return x @ self.W + self.b

    def backward(self, grad: np.ndarray) -> np.ndarray:
        self.dW = self._input.T @ grad
        self.db = grad.sum(axis=0)
        return grad @ self.W.T

    def params(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        return [(self.W, self.dW), (self.b, self.db)]


# ============================================================
# Shared Backbone
# ============================================================

class SharedBackbone:
    """
    Shared text encoder backbone.

    Takes concatenated [excerpt_embedding, reflection_embedding] as input,
    outputs a shared representation used by all three heads.

    Architecture:
        Input (2 * max_features) → Dense(256) → ReLU → Dense(128)
    """

    def __init__(self, input_dim: int, hidden_dim: int = 256, output_dim: int = 128):
        self.layer1 = DenseLayer(input_dim, hidden_dim)
        self.layer2 = DenseLayer(hidden_dim, output_dim)
        self._cache = {}

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = relu(self.layer1.forward(x))
        z = self.layer2.forward(h)
        self._cache = {"h": h, "z": z}
        return z

    def backward(self, grad: np.ndarray) -> np.ndarray:
        grad_h = self.layer2.backward(grad)
        grad_h = grad_h * relu_derivative(self._cache["h"])
        grad_x = self.layer1.backward(grad_h)
        return grad_x

    def params(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        return self.layer1.params() + self.layer2.params()

    def get_weights(self) -> List[np.ndarray]:
        """Get weight matrices for FL aggregation."""
        return [self.layer1.W, self.layer1.b, self.layer2.W, self.layer2.b]

    def set_weights(self, weights: List[np.ndarray]):
        """Set weight matrices from FL aggregation."""
        self.layer1.W, self.layer1.b, self.layer2.W, self.layer2.b = weights


# ============================================================
# Emotion Head (6-class classification)
# ============================================================

class EmotionHead:
    """
    Classifies reader emotion into 6 categories:
    感动, 思考, 共鸣, 困惑, 反对, 平静

    Architecture:
        Backbone output (128) → Dense(64) → ReLU → Dense(6) → Softmax
    """

    def __init__(self, input_dim: int = 128, hidden_dim: int = 64, n_classes: int = 6):
        self.layer1 = DenseLayer(input_dim, hidden_dim)
        self.layer2 = DenseLayer(hidden_dim, n_classes)
        self._cache = {}

    def forward(self, backbone_output: np.ndarray) -> np.ndarray:
        h = relu(self.layer1.forward(backbone_output))
        logits = self.layer2.forward(h)
        probs = softmax(logits)
        self._cache = {"h": h, "logits": logits, "probs": probs}
        return probs

    def backward(self, y_true: np.ndarray, lr: float = 0.001) -> np.ndarray:
        """Backward pass with cross-entropy loss. Returns gradient for backbone."""
        probs = self._cache["probs"]
        n = len(y_true)

        # Gradient of cross-entropy + softmax
        grad_logits = probs.copy()
        grad_logits[np.arange(n), y_true] -= 1
        grad_logits /= n

        grad_h = self.layer2.backward(grad_logits)
        grad_h = grad_h * relu_derivative(self._cache["h"])
        grad_backbone = self.layer1.backward(grad_h)

        # Update local head weights
        self._update_params(lr)
        return grad_backbone

    def _update_params(self, lr: float):
        for W, dW in self.layer1.params():
            W -= lr * dW
        for W, dW in self.layer2.params():
            W -= lr * dW

    def params(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        return self.layer1.params() + self.layer2.params()

    def loss(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        """Cross-entropy loss."""
        n = len(y_true)
        log_probs = np.log(y_pred[np.arange(n), y_true] + 1e-10)
        return -log_probs.mean()

    def predict(self, backbone_output: np.ndarray) -> np.ndarray:
        probs = self.forward(backbone_output)
        return np.argmax(probs, axis=-1)


# ============================================================
# Quality Head (regression 0-1)
# ============================================================

class QualityHead:
    """
    Predicts content quality score (0-1).

    Quality is computed from:
    - Reflection depth (length, personal markers, questions)
    - Emotion intensity
    - Reading duration correlation

    Architecture:
        Backbone output (128) → Dense(64) → ReLU → Dense(1) → Sigmoid
    """

    def __init__(self, input_dim: int = 128, hidden_dim: int = 64):
        self.layer1 = DenseLayer(input_dim, hidden_dim)
        self.layer2 = DenseLayer(hidden_dim, 1)
        self._cache = {}

    def forward(self, backbone_output: np.ndarray) -> np.ndarray:
        h = relu(self.layer1.forward(backbone_output))
        z = self.layer2.forward(h)
        score = sigmoid(z).squeeze(-1)
        self._cache = {"h": h, "z": z, "score": score}
        return score

    def backward(self, y_true: np.ndarray, lr: float = 0.001) -> np.ndarray:
        """Backward pass with MSE loss. Returns gradient for backbone."""
        score = self._cache["score"]
        n = len(y_true)

        # MSE gradient: d(score - y)^2 / d(score) = 2(score - y) / n
        grad_score = 2 * (score - y_true) / n

        # Sigmoid derivative: s * (1 - s)
        grad_z = grad_score * score * (1 - score)
        grad_z = grad_z.reshape(-1, 1)

        grad_h = self.layer2.backward(grad_z)
        grad_h = grad_h * relu_derivative(self._cache["h"])
        grad_backbone = self.layer1.backward(grad_h)

        self._update_params(lr)
        return grad_backbone

    def _update_params(self, lr: float):
        for W, dW in self.layer1.params():
            W -= lr * dW
        for W, dW in self.layer2.params():
            W -= lr * dW

    def params(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        return self.layer1.params() + self.layer2.params()

    def loss(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        return np.mean((y_pred - y_true) ** 2)


# ============================================================
# Matching Head (embedding output)
# ============================================================

class MatchingHead:
    """
    Produces reader/excerpt embeddings for similarity matching.

    Uses a projection head + L2 normalization to map backbone output
    to a shared embedding space for HNSW-based matching.

    Architecture:
        Backbone output (128) → Dense(128) → ReLU → L2 Normalize
    """

    def __init__(self, input_dim: int = 128, output_dim: int = 128):
        self.layer = DenseLayer(input_dim, output_dim)
        self._pre_relu = None  # Cache for ReLU input

    def forward(self, backbone_output: np.ndarray) -> np.ndarray:
        z = self.layer.forward(backbone_output)
        self._pre_relu = z  # Cache before ReLU for backward
        h = relu(z)
        return l2_normalize(h)

    def backward(self, grad: np.ndarray, lr: float = 0.001) -> np.ndarray:
        """Backward pass through L2 normalize → ReLU → Dense."""
        # Gradient through L2 normalization: grad_norm = (grad - emb * (emb @ grad.T)) / norm
        # Since embeddings are already L2-normalized (norm ≈ 1), simplified:
        emb = l2_normalize(relu(self._pre_relu))
        grad_norm = grad - emb * np.sum(grad * emb, axis=-1, keepdims=True)

        # Gradient through ReLU
        grad_h = grad_norm * relu_derivative(self._pre_relu)

        # Gradient through Dense layer
        grad_backbone = self.layer.backward(grad_h)
        self._update_params(lr)
        return grad_backbone

    def _update_params(self, lr: float):
        for W, dW in self.layer.params():
            W -= lr * dW

    def params(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        return self.layer.params()

    def contrastive_loss(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        temperature: float = 0.1,
    ) -> Tuple[float, np.ndarray]:
        """
        Supervised contrastive loss.

        Pulls embeddings of same-reader reflections together,
        pushes different readers apart.
        """
        n = len(labels)
        if n < 2:
            return 0.0, np.zeros_like(embeddings)

        # Compute similarity matrix
        sim = embeddings @ embeddings.T / temperature

        # Mask: positive pairs = same reader
        label_mask = (labels[:, None] == labels[None, :]).astype(np.float32)
        np.fill_diagonal(label_mask, 0)  # Exclude self

        # For each sample, loss = -log(exp(sim+) / sum(exp(sim)))
        exp_sim = np.exp(sim - np.max(sim, axis=-1, keepdims=True))  # Numerical stability
        log_sum_exp = np.log(exp_sim.sum(axis=-1) + 1e-10)

        # Positive pairs
        pos_sim = (exp_sim * label_mask).sum(axis=-1)
        n_pos = label_mask.sum(axis=-1)
        n_pos = np.maximum(n_pos, 1)  # Avoid division by zero

        loss = -np.log(pos_sim / n_pos + 1e-10).mean()

        # Gradient of supervised contrastive loss w.r.t. embeddings
        # d_loss/d_emb_i = (1/n) * sum_j [softmax(sim_ij) * d_sim/d_emb_i - indicator(j in P(i)) * d_sim/d_emb_i / |P(i)|]
        # where d_sim/d_emb_i = (emb_j - emb_i) / temperature for j != i
        softmax_sim = exp_sim / (exp_sim.sum(axis=-1, keepdims=True) + 1e-10)

        # For each anchor i: grad_i = (1/n) * sum_j (softmax_ij - pos_ij/n_pos_i) * (emb_j - emb_i) / temperature
        grad = np.zeros_like(embeddings)
        for i in range(n):
            diff = embeddings - embeddings[i]  # (n, d)
            coeff = softmax_sim[i] - label_mask[i] / n_pos[i]  # (n,)
            grad[i] = (coeff[:, None] * diff).sum(axis=0) / (temperature * n)

        return loss, grad


# ============================================================
# Multi-Head Model (combines all)
# ============================================================

class ReadingFLModel:
    """
    Complete model: Shared Backbone + 3 Task Heads.

    FL strategy:
    - Backbone weights are shared across campuses (aggregated on server)
    - Head weights stay local (each campus has its own heads)
    """

    def __init__(self, input_dim: int, config=None):
        from core.config import ModelConfig
        if config is None:
            config = ModelConfig()

        # Map config fields (support both naming conventions)
        hidden = getattr(config, 'backbone_hidden', None) or config.hidden_dim
        output = getattr(config, 'backbone_output', None) or config.embed_dim
        emotion_h = getattr(config, 'emotion_hidden', None) or config.hidden_dim // 4
        n_emotions = getattr(config, 'n_emotions', None) or 6
        quality_h = getattr(config, 'quality_hidden', None) or config.hidden_dim // 4
        matching_d = getattr(config, 'matching_dim', None) or config.embed_dim

        self.backbone = SharedBackbone(
            input_dim=input_dim,
            hidden_dim=hidden,
            output_dim=output,
        )
        self.emotion_head = EmotionHead(
            input_dim=output,
            hidden_dim=emotion_h,
            n_classes=n_emotions,
        )
        self.quality_head = QualityHead(
            input_dim=output,
            hidden_dim=quality_h,
        )
        self.matching_head = MatchingHead(
            input_dim=output,
            output_dim=matching_d,
        )

    def forward(self, x: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Forward pass through all heads.

        Args:
            x: Concatenated [excerpt_emb, reflection_emb] of shape (batch, 2*max_features)

        Returns:
            Dict with emotion_probs, quality_score, matching_embedding
        """
        backbone_out = self.backbone.forward(x)
        return {
            "backbone": backbone_out,
            "emotion": self.emotion_head.forward(backbone_out),
            "quality": self.quality_head.forward(backbone_out),
            "matching": self.matching_head.forward(backbone_out),
        }

    def train_step(
        self,
        x: np.ndarray,
        y_emotion: np.ndarray,
        y_quality: np.ndarray,
        reader_ids: np.ndarray,
        backbone_lr: float = 0.0005,
        head_lr: float = 0.002,
    ) -> Dict[str, float]:
        """
        One training step with multi-task loss.

        Loss = w1 * emotion_ce + w2 * quality_mse + w3 * matching_contrastive
        """
        # Forward
        outputs = self.forward(x)

        # Compute losses
        emotion_loss = self.emotion_head.loss(outputs["emotion"], y_emotion)
        quality_loss = self.quality_head.loss(outputs["quality"], y_quality)

        if reader_ids is not None and len(reader_ids) > 1:
            matching_loss, matching_grad = self.matching_head.contrastive_loss(
                outputs["matching"], reader_ids
            )
        else:
            # No reader IDs — use embedding regularization instead
            matching_loss = 0.0
            matching_grad = np.zeros_like(outputs["matching"])

        total_loss = 0.4 * emotion_loss + 0.3 * quality_loss + 0.3 * matching_loss

        # Backward through each head
        grad_emotion = self.emotion_head.backward(y_emotion, lr=head_lr)
        grad_quality = self.quality_head.backward(y_quality, lr=head_lr)
        grad_matching = self.matching_head.backward(matching_grad, lr=head_lr)

        # Aggregate gradients for backbone
        grad_backbone = 0.4 * grad_emotion + 0.3 * grad_quality + 0.3 * grad_matching

        # Update backbone with lower LR
        self.backbone.backward(grad_backbone)
        for W, dW in self.backbone.params():
            W -= backbone_lr * dW

        return {
            "total_loss": total_loss,
            "emotion_loss": emotion_loss,
            "quality_loss": quality_loss,
            "matching_loss": matching_loss,
        }

    def predict(self, x: np.ndarray) -> Dict[str, np.ndarray]:
        """Inference mode."""
        outputs = self.forward(x)
        return {
            "emotion": np.argmax(outputs["emotion"], axis=-1),
            "emotion_probs": outputs["emotion"],
            "quality": outputs["quality"],
            "matching": outputs["matching"],
        }

    def get_backbone_weights(self) -> List[np.ndarray]:
        return self.backbone.get_weights()

    def set_backbone_weights(self, weights: List[np.ndarray]):
        self.backbone.set_weights(weights)
