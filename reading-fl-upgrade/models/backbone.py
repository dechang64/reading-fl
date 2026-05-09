"""
Shared Backbone — Text Encoder shared across all campuses.

FL聚合只发生在这一层。各校区的Head保持本地。
"""

import numpy as np


class TextBackbone:
    """
    Lightweight text encoder backbone.

    Architecture:
        Embedding → [TransformerBlock × N] → Pooled Output

    Pure NumPy implementation for zero-dependency deployment.
    """

    def __init__(
        self,
        vocab_size: int = 10000,
        embed_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 2,
        max_length: int = 256,
        dropout: float = 0.1,
    ):
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.max_length = max_length
        self.dropout = dropout

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Xavier initialization"""
        scale_e = np.sqrt(2.0 / (self.vocab_size + self.embed_dim))
        self.embedding = np.random.randn(self.vocab_size, self.embed_dim).astype(np.float32) * scale_e

        # Positional embedding (learned)
        self.pos_embedding = np.random.randn(self.max_length, self.embed_dim).astype(np.float32) * scale_e

        self.layers = []
        for _ in range(self.num_layers):
            layer = {
                "W_q": np.random.randn(self.embed_dim, self.hidden_dim).astype(np.float32) * np.sqrt(2.0 / (self.embed_dim + self.hidden_dim)),
                "W_k": np.random.randn(self.embed_dim, self.hidden_dim).astype(np.float32) * np.sqrt(2.0 / (self.embed_dim + self.hidden_dim)),
                "W_v": np.random.randn(self.embed_dim, self.hidden_dim).astype(np.float32) * np.sqrt(2.0 / (self.embed_dim + self.hidden_dim)),
                "W_o": np.random.randn(self.hidden_dim, self.embed_dim).astype(np.float32) * np.sqrt(2.0 / (self.hidden_dim + self.embed_dim)),
                "W_ff1": np.random.randn(self.embed_dim, self.hidden_dim).astype(np.float32) * np.sqrt(2.0 / (self.embed_dim + self.hidden_dim)),
                "b_ff1": np.zeros(self.hidden_dim, dtype=np.float32),
                "W_ff2": np.random.randn(self.hidden_dim, self.embed_dim).astype(np.float32) * np.sqrt(2.0 / (self.hidden_dim + self.embed_dim)),
                "b_ff2": np.zeros(self.embed_dim, dtype=np.float32),
                "ln1_w": np.ones(self.embed_dim, dtype=np.float32),
                "ln1_b": np.zeros(self.embed_dim, dtype=np.float32),
                "ln2_w": np.ones(self.embed_dim, dtype=np.float32),
                "ln2_b": np.zeros(self.embed_dim, dtype=np.float32),
            }
            self.layers.append(layer)

        # Output projection
        self.W_out = np.random.randn(self.embed_dim, self.embed_dim).astype(np.float32) * np.sqrt(2.0 / (self.embed_dim + self.embed_dim))
        self.b_out = np.zeros(self.embed_dim, dtype=np.float32)

    def forward(self, input_ids: np.ndarray, training: bool = True) -> np.ndarray:
        """
        Forward pass.

        Args:
            input_ids: (batch_size, seq_length) integer token IDs
            training: whether in training mode (dropout)

        Returns:
            (batch_size, embed_dim) pooled output
        """
        batch_size, seq_len = input_ids.shape

        # Embedding lookup
        x = self.embedding[input_ids]  # (batch, seq, embed_dim)

        # Add positional embedding
        seq_len = input_ids.shape[1]
        x = x + self.pos_embedding[:seq_len]  # (batch, seq, embed_dim)

        # Apply dropout to embeddings
        if training and self.dropout > 0:
            mask = (np.random.rand(*x.shape) > self.dropout).astype(np.float32)
            x = x * mask / (1 - self.dropout)

        # Transformer blocks
        for layer in self.layers:
            x = self._transformer_block(x, layer, training)

        # Pool: mean of non-padding tokens (token 0 is <CLS>)
        # Simple approach: use first token (CLS)
        pooled = x[:, 0, :]  # (batch, embed_dim)

        # Output projection
        output = pooled @ self.W_out + self.b_out

        return output

    def _transformer_block(self, x: np.ndarray, layer: dict, training: bool) -> np.ndarray:
        """Single transformer block with self-attention + FFN"""
        batch_size, seq_len, dim = x.shape

        # Self-attention
        Q = x @ layer["W_q"]  # (batch, seq, hidden)
        K = x @ layer["W_k"]
        V = x @ layer["W_v"]

        # Scaled dot-product attention
        scores = Q @ K.transpose(0, 2, 1) / np.sqrt(self.hidden_dim)
        # Causal mask (optional, for bidirectional set to False)
        # For simplicity, use full attention
        attn = self._softmax(scores, axis=-1)

        if training and self.dropout > 0:
            attn_mask = (np.random.rand(*attn.shape) > self.dropout).astype(np.float32)
            attn = attn * attn_mask / (1 - self.dropout)

        context = attn @ V  # (batch, seq, hidden)
        attn_out = context @ layer["W_o"]  # (batch, seq, embed_dim)

        # Residual + LayerNorm
        x = self._layer_norm(x + attn_out, layer["ln1_w"], layer["ln1_b"])

        # FFN
        ff = x @ layer["W_ff1"] + layer["b_ff1"]
        ff = np.maximum(0, ff)  # ReLU
        ff = ff @ layer["W_ff2"] + layer["b_ff2"]

        # Residual + LayerNorm
        x = self._layer_norm(x + ff, layer["ln2_w"], layer["ln2_b"])

        return x

    @staticmethod
    def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
        e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e_x / (e_x.sum(axis=axis, keepdims=True) + 1e-8)

    @staticmethod
    def _layer_norm(x: np.ndarray, w: np.ndarray, b: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        mean = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        return w * (x - mean) / np.sqrt(var + eps) + b

    def get_parameters(self) -> dict:
        """Get all trainable parameters"""
        params = {
            "embedding": self.embedding,
            "pos_embedding": self.pos_embedding,
            "W_out": self.W_out,
            "b_out": self.b_out,
        }
        for i, layer in enumerate(self.layers):
            for key, val in layer.items():
                params[f"layer_{i}_{key}"] = val
        return params

    def set_parameters(self, params: dict):
        """Set parameters (for FL aggregation)"""
        self.embedding = params["embedding"]
        self.pos_embedding = params["pos_embedding"]
        self.W_out = params["W_out"]
        self.b_out = params["b_out"]
        for i, layer in enumerate(self.layers):
            for key in layer:
                layer[key] = params[f"layer_{i}_{key}"]

    def get_gradients(self) -> dict:
        """Alias for get_parameters (used in FL)"""
        return self.get_parameters()

    def parameter_count(self) -> int:
        """Count total parameters"""
        total = 0
        for name, param in self.get_parameters().items():
            total += param.size
        return total
