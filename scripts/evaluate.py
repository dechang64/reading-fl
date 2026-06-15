"""
Reading-FL Evaluation Script

Evaluate trained model on held-out data.

Usage:
    python scripts/evaluate.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.config import Config
from core.server import FLServer
from core.client import FLClient
from data.dataset import DataGenerator
from data.transforms import TextEncoder


def evaluate():
    np.random.seed(42)
    config = Config()

    # Generate data
    generator = DataGenerator(config.data)
    all_data = generator.generate_all()

    # Encode
    all_texts = []
    for data in all_data.values():
        for r in data["reflections"]:
            all_texts.append(r.excerpt_text)
            all_texts.append(r.reflection_text)

    encoder = TextEncoder(max_features=config.model.max_features)
    encoder.fit(all_texts)
    datasets = generator.generate_fl_datasets(all_data, encoder)
    input_dim = config.model.max_features * 2

    # Setup and train
    server = FLServer(config.fl, config.model, input_dim)
    for campus_id, dataset in datasets.items():
        campus_type = all_data[campus_id]["campus_type"]
        client = FLClient(campus_id, campus_type, config.model, input_dim)
        client.load_data(dataset)
        server.register_client(client)

    server.run_training()

    # Per-client evaluation
    print("\nPer-Campus Evaluation:")
    print(f"{'Campus':>12} | {'Type':>6} | {'Emotion Acc':>12} | {'Quality MAE':>12}")
    print(f"{'─'*12}─┼─{'─'*6}─┼─{'─'*12}─┼─{'─'*12}")

    for cid, client in server.clients.items():
        acc = client.evaluate_emotion()
        mae = client.evaluate_quality()
        print(f"{cid:>12} | {client.campus_type:>6} | {acc:>11.1%} | {mae:>12.3f}")


if __name__ == "__main__":
    evaluate()
