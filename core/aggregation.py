"""
Reading-FL Aggregation Strategies

FedAvg and Task-Aware Aggregation for multi-head FL.
"""

import numpy as np
from typing import Dict, List, Tuple
from copy import deepcopy


class AggregationStrategy:
    """Base class for FL aggregation."""

    def aggregate(
        self,
        client_weights: List[List[np.ndarray]],
        client_data_sizes: List[int],
    ) -> List[np.ndarray]:
        raise NotImplementedError


class FedAvg(AggregationStrategy):
    """
    Federated Averaging.

    Simple weighted average of client model weights,
    weighted by the number of data points each client has.
    """

    def aggregate(
        self,
        client_weights: List[List[np.ndarray]],
        client_data_sizes: List[int],
    ) -> List[np.ndarray]:
        total = sum(client_data_sizes)
        aggregated = []

        for layer_idx in range(len(client_weights[0])):
            weighted_sum = np.zeros_like(client_weights[0][layer_idx])
            for weights, n in zip(client_weights, client_data_sizes):
                weighted_sum += (n / total) * weights[layer_idx]
            aggregated.append(weighted_sum)

        return aggregated


class TaskAwareAggregation(AggregationStrategy):
    """
    Task-Aware Aggregation.

    Instead of simple averaging, weights each client's contribution
    based on their performance on each task (emotion, quality, matching).

    Clients that perform better on a specific task get more weight
    for the backbone parameters relevant to that task.

    This is particularly useful when campuses have different strengths:
    - 理工科 campus might be better at analytical (思考) reflections
    - 文科 campus might be better at emotional (感动) reflections
    """

    def __init__(
        self,
        task_weights: Dict[str, float] = None,
        temperature: float = 1.0,
    ):
        self.task_weights = task_weights or {
            "emotion": 0.4,
            "quality": 0.3,
            "matching": 0.3,
        }
        self.temperature = temperature

    def aggregate(
        self,
        client_weights: List[List[np.ndarray]],
        client_data_sizes: List[int],
        client_metrics: List[Dict[str, float]] = None,
    ) -> List[np.ndarray]:
        """
        Aggregate with task-aware weighting.

        Args:
            client_weights: List of weight arrays from each client
            client_data_sizes: Number of samples per client
            client_metrics: Dict of task_name -> score for each client
        """
        if client_metrics is None:
            # Fall back to FedAvg
            return FedAvg().aggregate(client_weights, client_data_sizes)

        # Compute per-client importance scores
        client_scores = []
        for metrics in client_metrics:
            score = sum(
                self.task_weights.get(task, 0) * metrics.get(task, 0)
                for task in self.task_weights
            )
            # Softmax with temperature
            client_scores.append(score)

        # Normalize scores
        scores = np.array(client_scores)
        scores = np.exp((scores - scores.max()) / self.temperature)
        scores = scores / scores.sum()

        # Weighted aggregation
        aggregated = []
        for layer_idx in range(len(client_weights[0])):
            weighted_sum = np.zeros_like(client_weights[0][layer_idx])
            for weights, score in zip(client_weights, scores):
                weighted_sum += score * weights[layer_idx]
            aggregated.append(weighted_sum)

        return aggregated


def get_aggregator(strategy: str = "fedavg", **kwargs) -> AggregationStrategy:
    """Factory function for aggregation strategies."""
    if strategy == "fedavg":
        return FedAvg()
    elif strategy == "task_aware":
        return TaskAwareAggregation(**kwargs)
    else:
        raise ValueError(f"Unknown aggregation strategy: {strategy}")
