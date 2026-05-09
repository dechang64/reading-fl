"""
EWA-Fed Real Experiment: Organoid Classification
================================================
Uses real features (512-dim DINOv2) and labels (3 classes) from organoid-fl.
Trains a classifier per-client in FL setting, extracts real softmax entropy,
and compares EWA monitoring vs FedAvg baseline.

Key metrics:
  - Per-class accuracy (on held-out test set)
  - Expert's weight share on specialty class
  - Conformity score per class
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from collections import OrderedDict
import json
import time

from twc_core.ewa.primitives import PrimitiveBatch, PrimitiveCodec
from twc_core.ewa.aggregator import EntropyWeightedAggregator, AggregationStrategy
from twc_core.ewa.conformity import ConformityDetector


# ── Config ──
FEATURES_PATH = "/home/z/my-project/organoid-fl-upgrade/fl/features.npz"
N_CLIENTS = 5
N_ROUNDS = 20
LOCAL_EPOCHS = 2
LR = 0.005
BATCH_SIZE = 32
HIDDEN_DIM = 64
SEED = 42
FEATURE_DIM = 32       # PCA降维到32维，增加难度
NOISE_STD = 0.5        # 加高斯噪声

# Non-IID split: expert gets more late_stage, majority gets more healthy
# Client 0 = expert (late_stage specialist)
# Client 1-4 = majority (mostly healthy)
CLIENT_DISTRIBUTIONS = {
    0: {"early_stage": 0.15, "healthy": 0.20, "late_stage": 0.65},  # expert
    1: {"early_stage": 0.25, "healthy": 0.60, "late_stage": 0.15},
    2: {"early_stage": 0.20, "healthy": 0.65, "late_stage": 0.15},
    3: {"early_stage": 0.25, "healthy": 0.55, "late_stage": 0.20},
    4: {"early_stage": 0.20, "healthy": 0.60, "late_stage": 0.20},
}


# ── Model ──
class OrganoidClassifier(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=128, num_classes=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x):
        return self.net(x)

    def predict_with_entropy(self, x_np):
        """Returns (predictions, confidences, entropies)."""
        self.eval()
        with torch.no_grad():
            logits = self(torch.FloatTensor(x_np))
            probs = torch.softmax(logits, dim=1)
            confs, preds = probs.max(dim=1)
            # Shannon entropy per sample
            log_probs = torch.log(probs + 1e-10)
            entropies = -(probs * log_probs).sum(dim=1)
        return preds.numpy(), confs.numpy(), entropies.numpy()


def get_params(model):
    return OrderedDict((n, p.data.clone()) for n, p in model.named_parameters())

def set_params(model, params):
    model.load_state_dict(params)

def fedavg_aggregate(client_params, weights=None):
    if not client_params:
        raise ValueError("No client_params to aggregate")
    if weights is None:
        weights = [1] * len(client_params)
    total = sum(weights)
    if total == 0:
        raise ValueError("Total weights is zero, cannot aggregate")
    agg = OrderedDict()
    for key in client_params[0].keys():
        agg[key] = sum(w * p[key].float() for p, w in zip(client_params, weights)) / total
    return agg


# ── Data Split ──
def split_non_iid(features, labels, class_names, distributions, seed=42):
    """Split data across clients with Non-IID distributions."""
    rng = np.random.RandomState(seed)
    client_data = {i: {"X": [], "y": []} for i in distributions}

    for cls_idx, cls_name in enumerate(class_names):
        cls_mask = labels == cls_idx
        cls_features = features[cls_mask]
        n_cls = len(cls_features)
        rng.shuffle(cls_features)

        offset = 0
        for cid, dist in distributions.items():
            frac = dist.get(cls_name, 0)
            n = int(n_cls * frac)
            selected_features = cls_features[offset:offset + n]
            client_data[cid]["X"].append(selected_features)
            client_data[cid]["y"].append(np.full(len(selected_features), cls_idx, dtype=np.int64))
            offset += n

    result = {}
    for cid in distributions:
        X = np.concatenate(client_data[cid]["X"], axis=0)
        y = np.concatenate(client_data[cid]["y"], axis=0)
        # Shuffle
        perm = rng.permutation(len(X))
        result[cid] = (X[perm], y[perm])

    return result


# ── Experiment ──
def run_real_experiment():
    print("=" * 80)
    print("EWA-Fed Real Experiment: Organoid Classification")
    print("=" * 80)

    # Load data
    data = np.load(FEATURES_PATH)
    features_raw = data["features"].astype(np.float32)
    labels = data["labels"]
    class_names = list(data["classes"])
    n_classes = len(class_names)

    # PCA降维 + 噪声，增加分类难度
    from sklearn.decomposition import PCA
    pca = PCA(n_components=FEATURE_DIM, random_state=SEED)
    features = pca.fit_transform(features_raw).astype(np.float32)
    rng = np.random.RandomState(SEED)
    features += rng.randn(*features.shape).astype(np.float32) * NOISE_STD
    input_dim = features.shape[1]

    print(f"\nData: {len(features)} samples, {input_dim}-dim features (PCA from 512), {n_classes} classes")
    print(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.4f}")
    print(f"Classes: {class_names}")

    # Non-IID split
    client_data = split_non_iid(features, labels, class_names, CLIENT_DISTRIBUTIONS, SEED)
    print(f"\nNon-IID split across {N_CLIENTS} clients:")
    for cid, (X, y) in client_data.items():
        counts = [np.sum(y == i) for i in range(n_classes)]
        dist_str = ", ".join(f"{class_names[i]}: {counts[i]}" for i in range(n_classes))
        label = "🔬 EXPERT" if cid == 0 else f"🏭 Lab {cid}"
        print(f"  Client {cid} ({label}): {len(X)} samples — {dist_str}")

    # Hold-out test set (20% from each client)
    test_parts_X, test_parts_y = [], []
    train_data = {}
    for cid, (X, y) in client_data.items():
        split = int(len(X) * 0.8)
        train_data[cid] = (X[:split], y[:split])
        test_parts_X.append(X[split:])
        test_parts_y.append(y[split:])
    test_X = np.concatenate(test_parts_X)
    test_y = np.concatenate(test_parts_y)
    print(f"\nTrain: {sum(len(X) for X, _ in train_data.values())}, Test: {len(test_X)}")

    # ── Run FedAvg Training with EWA Monitoring ──
    print(f"\n{'─'*80}")
    print(f"Running {N_ROUNDS} rounds of FL training with EWA monitoring...")
    print(f"{'─'*80}")

    rng = np.random.RandomState(SEED)
    global_model = OrganoidClassifier(input_dim, HIDDEN_DIM, n_classes)
    global_params = get_params(global_model)

    ewa_agg = EntropyWeightedAggregator(strategy=AggregationStrategy.ENTROPY_WEIGHTED)
    ewa_detector = ConformityDetector()
    codec = PrimitiveCodec()

    round_results = []

    for rnd in range(1, N_ROUNDS + 1):
        client_params_list = []
        client_weights = []
        all_batches = []

        for cid in range(N_CLIENTS):
            X_train, y_train = train_data[cid]
            local_model = OrganoidClassifier(input_dim, HIDDEN_DIM, n_classes)
            set_params(local_model, global_params)

            # Train locally
            local_model.train()
            optimizer = optim.Adam(local_model.parameters(), lr=LR)
            criterion = nn.CrossEntropyLoss()
            dataset = TensorDataset(
                torch.FloatTensor(X_train), torch.LongTensor(y_train)
            )
            loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

            for _ in range(LOCAL_EPOCHS):
                for bx, by in loader:
                    optimizer.zero_grad()
                    logits = local_model(bx)
                    loss = criterion(logits, by)
                    loss.backward()
                    optimizer.step()

            client_params_list.append(get_params(local_model))
            client_weights.append(len(X_train))

            # Extract entropy from local model on local data
            preds, confs, entropies = local_model.predict_with_entropy(X_train)
            codec.client_id = f"lab_{cid}"
            points = [(0, 0)] * len(preds)
            labels_str = [class_names[p] for p in preds]
            batch = codec.encode_points(points, labels_str, entropies=entropies.tolist(), round_id=rnd)
            for p in batch.primitives:
                p.auxiliary = {"confidence": float(np.exp(-p.token_entropy)), "modality": "cv"}
            all_batches.append(batch)

        # FedAvg aggregation
        global_params = fedavg_aggregate(client_params_list, client_weights)
        set_params(global_model, global_params)

        # EWA monitoring
        ewa_result = ewa_agg.aggregate(all_batches)
        ewa_detector.update(ewa_result)

        # Evaluate global model on test set
        test_preds, test_confs, test_entropies = global_model.predict_with_entropy(test_X)
        test_acc = np.mean(test_preds == test_y)

        # Per-class accuracy
        per_class_acc = {}
        for cls_idx, cls_name in enumerate(class_names):
            mask = test_y == cls_idx
            if mask.sum() > 0:
                per_class_acc[cls_name] = float(np.mean(test_preds[mask] == test_y[mask]))

        # Expert weight on late_stage
        late_proto = next((p for p in ewa_result.prototypes if p.ref == "late_stage"), None)
        expert_ws = 0.0
        if late_proto and "lab_0" in late_proto.client_stats:
            expert_ws = late_proto.client_stats["lab_0"].get("weight_share", 0.0)

        round_results.append({
            "round": rnd,
            "test_acc": test_acc,
            "per_class_acc": per_class_acc,
            "expert_weight_share": expert_ws,
            "avg_entropy": float(np.mean(test_entropies)),
            "high_conformity_ratio": ewa_result.conformity_report.get("high_conformity_ratio", 0),
        })

        if rnd <= 3 or rnd == N_ROUNDS or rnd % 5 == 0:
            print(f"  Round {rnd:>2}: test_acc={test_acc:.4f}  "
                  f"expert_ws(late_stage)={expert_ws:.1f}%  "
                  f"avg_H={np.mean(test_entropies):.4f}")

    # ── Summary ──
    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")

    accs = [r["test_acc"] for r in round_results]
    print(f"\nTest Accuracy: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    print(f"Final Round Accuracy: {accs[-1]:.4f}")

    print(f"\nPer-Class Accuracy (final round):")
    final_pca = round_results[-1]["per_class_acc"]
    for cls, acc in final_pca.items():
        print(f"  {cls}: {acc:.4f}")

    expert_ws_list = [r["expert_weight_share"] for r in round_results]
    print(f"\nExpert Weight Share on late_stage: {np.mean(expert_ws_list):.1f}% ± {np.std(expert_ws_list):.1f}%")

    # Conformity report
    report = ewa_detector.get_report()
    print(f"\nConformity Trend: {report['trend']['status']}")
    print(f"Total Alerts: {len(report['alerts'])}")
    for a in report["alerts"][:5]:
        print(f"  {a['severity']} R{a['round']} {a['class']}: {a['message']}")

    # ── Save ──
    output = {
        "experiment": "organoid_real",
        "n_clients": N_CLIENTS,
        "n_rounds": N_ROUNDS,
        "n_classes": n_classes,
        "class_names": class_names,
        "client_distributions": CLIENT_DISTRIBUTIONS,
        "train_samples": {cid: len(X) for cid, (X, _) in train_data.items()},
        "test_samples": len(test_X),
        "summary": {
            "mean_test_acc": float(np.mean(accs)),
            "std_test_acc": float(np.std(accs)),
            "final_test_acc": float(accs[-1]),
            "final_per_class_acc": final_pca,
            "expert_weight_share_mean": float(np.mean(expert_ws_list)),
            "expert_weight_share_std": float(np.std(expert_ws_list)),
        },
        "rounds": round_results,
    }

    out_path = "/home/z/my-project/download/ewa_results/organoid_real_experiment.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")

    return output


if __name__ == "__main__":
    run_real_experiment()
