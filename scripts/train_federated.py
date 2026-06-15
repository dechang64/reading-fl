"""
Reading-FL Federated Training Script

Standalone training without the full demo pipeline.
Useful for experimenting with different FL configurations.

Usage:
    python scripts/train_federated.py --rounds 15 --aggregation task_aware
    python scripts/train_federated.py --quick
"""

import sys
import os
import argparse
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.config import Config
from core.server import FLServer
from core.client import FLClient
from data.dataset import DataGenerator
from data.transforms import TextEncoder


def train(args):
    np.random.seed(42)
    config = Config()

    if args.quick:
        config.fl.n_rounds = 3
        config.data.readers_per_campus = 30

    if args.rounds:
        config.fl.n_rounds = args.rounds
    if args.aggregation:
        config.fl.aggregation = args.aggregation

    # Generate data
    print("Generating data...")
    generator = DataGenerator(config.data)
    all_data = generator.generate_all()

    # Encode texts
    all_texts = []
    for data in all_data.values():
        for r in data["reflections"]:
            all_texts.append(r.excerpt_text)
            all_texts.append(r.reflection_text)

    encoder = TextEncoder(max_features=config.model.max_features)
    encoder.fit(all_texts)

    datasets = generator.generate_fl_datasets(all_data, encoder)
    input_dim = config.model.max_features * 2

    # Setup FL
    server = FLServer(config.fl, config.model, input_dim)
    for campus_id, dataset in datasets.items():
        campus_type = all_data[campus_id]["campus_type"]
        client = FLClient(campus_id, campus_type, config.model, input_dim)
        client.load_data(dataset)
        server.register_client(client)

    # Train
    history = server.run_training()

    # Results
    metrics = server.get_global_metrics()
    print(f"\nResults:")
    print(f"  Best Emotion Accuracy: {metrics['best_emotion_acc']:.1%}")
    print(f"  Final Quality MAE: {metrics['final_quality_mae']:.3f}")
    print(f"  Converged: {metrics['convergence']}")

    # Save results
    results = {
        "config": {
            "rounds": config.fl.n_rounds,
            "aggregation": config.fl.aggregation,
            "readers_per_campus": config.data.readers_per_campus,
        },
        "history": history,
        "metrics": metrics,
    }

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results",
        f"training_{int(time.time())}.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, help="Number of FL rounds")
    parser.add_argument("--aggregation", choices=["fedavg", "task_aware"])
    parser.add_argument("--quick", action="store_true")
    train(parser.parse_args())
