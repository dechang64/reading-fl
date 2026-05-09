"""
Reading-FL Client

Local training on a single campus's data.
Only backbone weights are uploaded to the server.
"""

import numpy as np
from typing import Dict, List

from core.config import ModelConfig, FLConfig
from models.reading_model import ReadingFLModel


class FLClient:
    """
    Federated Learning Client representing one campus.

    Each client:
    1. Holds local data (reflections from that campus)
    2. Trains a ReadingFLModel locally (backbone + 3 heads)
    3. Uploads only backbone weights to the server
    4. Receives aggregated backbone weights from the server
    """

    def __init__(
        self,
        campus_id: str,
        campus_type: str,
        model_config: ModelConfig,
        fl_config: FLConfig,
        input_dim: int,
    ):
        self.campus_id = campus_id
        self.campus_type = campus_type
        self.model_config = model_config
        self.fl_config = fl_config

        # Local model — pass config directly
        self.model = ReadingFLModel(input_dim=input_dim, config=model_config)

        # Local dataset reference
        self.dataset = None
        self.n_samples: int = 0

        # Training metrics
        self.metrics: Dict[str, float] = {}

    def load_dataset(self, dataset):
        """Load a ReflectionDataset."""
        self.dataset = dataset
        self.n_samples = len(dataset)

    def train(self) -> Dict[str, float]:
        """
        Local training for one FL round.

        Returns:
            Training metrics (losses per task).
        """
        if self.dataset is None or self.n_samples == 0:
            return {"loss": 0.0}

        batch_size = self.fl_config.batch_size
        epochs = self.fl_config.local_epochs
        lr = self.fl_config.learning_rate
        n = self.n_samples

        total_losses = {"emotion": 0, "quality": 0, "matching": 0, "total": 0}
        n_batches = 0

        for epoch in range(epochs):
            # Iterate over all batches in each epoch
            n_steps = max(1, n // batch_size)
            for step in range(n_steps):
                batch = self.dataset.get_random_batch(batch_size)
                # Concatenate excerpt + reflection tokens as model input
                x = np.concatenate([batch["input_ids"], batch["reflection_ids"]], axis=1)
                y_emo = batch["emotion_labels"]
                y_qual = batch["quality_scores"]

                losses = self.model.train_step(
                    x, y_emo, y_qual, None,
                    backbone_lr=lr * 0.5,
                    head_lr=lr,
                )

                for k in total_losses:
                    total_losses[k] += losses.get(k, 0)
                n_batches += 1

        # Average losses
        self.metrics = {k: v / max(1, n_batches) for k, v in total_losses.items()}

        # Compute task-specific metrics
        self.metrics["emotion_acc"] = self._compute_emotion_accuracy()
        self.metrics["quality_mae"] = self._compute_quality_mae()

        return self.metrics

    def _compute_emotion_accuracy(self) -> float:
        """Compute emotion classification accuracy on local data."""
        if self.dataset is None:
            return 0.0
        batch = self.dataset.get_batch(list(range(len(self.dataset))))
        x = np.concatenate([batch["input_ids"], batch["reflection_ids"]], axis=1)
        preds = self.model.predict(x)
        accuracy = np.mean(preds["emotion"] == batch["emotion_labels"])
        return round(float(accuracy), 4)

    def _compute_quality_mae(self) -> float:
        """Compute quality prediction MAE on local data."""
        if self.dataset is None:
            return 0.0
        batch = self.dataset.get_batch(list(range(len(self.dataset))))
        x = np.concatenate([batch["input_ids"], batch["reflection_ids"]], axis=1)
        preds = self.model.predict(x)
        mae = np.mean(np.abs(preds["quality"].flatten() - batch["quality_scores"]))
        return round(float(mae), 4)

    def get_backbone_weights(self) -> List[np.ndarray]:
        """Extract backbone weights for upload to server."""
        return self.model.get_backbone_weights()

    def set_backbone_weights(self, weights: List[np.ndarray]):
        """Receive aggregated backbone weights from server."""
        self.model.set_backbone_weights(weights)

    def get_task_metrics(self) -> Dict[str, float]:
        """Get task-specific metrics for Task-Aware Aggregation."""
        return {
            "emotion": self.metrics.get("emotion_acc", 0),
            "quality": 1.0 - min(1.0, self.metrics.get("quality_mae", 1.0)),
            "matching": self.metrics.get("matching_loss", 0),
        }

    def __repr__(self) -> str:
        return (
            f"FLClient(campus={self.campus_id}, type={self.campus_type}, "
            f"samples={self.n_samples})"
        )
