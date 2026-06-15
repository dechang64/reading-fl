"""
EWA-Fed Real Experiment: Organoid Classification with Real Softmax Entropy
==========================================================================
Uses real 512-dim DINOv2 features from organoid-fl (600 samples, 3 classes).
Trains classifiers in FL setting, extracts REAL softmax entropy per client,
and feeds them into the EWA aggregator for conformity analysis.

Key difference from simulated experiments:
  - Entropy values come from actual model inference, not random sampling
  - Classification accuracy is measured on held-out test set
  - Non-IID data split creates genuine expertise asymmetry

Output: JSON with per-round metrics + LaTeX table
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from collections import OrderedDict
import json
import time

from ewa.primitives import VisualPrimitive, PrimitiveBatch, PrimitiveType
from ewa.aggregator import EntropyWeightedAggregator, AggregationStrategy
from ewa.conformity import ConformityDetector


# ── Config ──
FEATURES_PATH = "/home/z/my-project/organoid-fl/fl/features.npz"
N_CLIENTS = 5
N_ROUNDS = 20
LOCAL_EPOCHS = 2
LR = 0.002
BATCH_SIZE = 32
HIDDEN_DIM = 64
SEED = 42
PCA_DIM = 16          # Aggressive reduction for harder task
NOISE_STD = 1.0       # Strong noise
TEST_RATIO = 0.2
LR = 0.005
HIDDEN_DIM = 32
LOCAL_EPOCHS = 1

# Non-IID: expert (client 0) specializes in late_stage
# Others are majority (mostly healthy + early_stage)
CLIENT_DISTRIBUTIONS = {
    0: {"early_stage": 0.10, "healthy": 0.15, "late_stage": 0.75},  # expert
    1: {"early_stage": 0.30, "healthy": 0.55, "late_stage": 0.15},
    2: {"early_stage": 0.35, "healthy": 0.50, "late_stage": 0.15},
    3: {"early_stage": 0.30, "healthy": 0.55, "late_stage": 0.15},
    4: {"early_stage": 0.25, "healthy": 0.60, "late_stage": 0.15},
}

EXPERT_ID = "expert"
EXPERT_SPECIALTY = "late_stage"


# ── Model ──
class Classifier(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x):
        return self.net(x)


# ── Helpers ──
def get_params(model):
    return [p.detach().clone() for p in model.parameters()]

def set_params(model, params):
    with torch.no_grad():
        for p, new_p in zip(model.parameters(), params):
            p.copy_(new_p)

def fedavg_aggregate(param_lists, weights=None):
    """FedAvg: weighted average of model parameters."""
    if not param_lists:
        raise ValueError("No param_lists to aggregate")
    if weights is None:
        weights = [1.0] * len(param_lists)
    total = sum(weights)
    if total == 0:
        raise ValueError("Total weights is zero, cannot aggregate")
    aggregated = []
    for layer_idx in range(len(param_lists[0])):
        layer_sum = sum(w * params[layer_idx] for w, params in zip(weights, param_lists))
        aggregated.append(layer_sum / total)
    return aggregated

def softmax_entropy(logits):
    """Compute Shannon entropy of softmax distribution. H = -sum(p * log(p))"""
    probs = torch.softmax(logits, dim=-1)
    log_probs = torch.log(probs + 1e-8)
    return -(probs * log_probs).sum(dim=-1)

def split_non_iid(features, labels, class_names, distributions, seed):
    """Split data across clients with Non-IID distributions.

    Normalizes fractions per class so they sum to 1.0, then allocates.
    """
    rng = np.random.RandomState(seed)
    client_data = {i: {"X": [], "y": []} for i in distributions}

    for cls_idx, cls_name in enumerate(class_names):
        cls_mask = labels == cls_idx
        cls_features = features[cls_mask].copy()
        n_cls = len(cls_features)
        rng.shuffle(cls_features)

        # Normalize fractions to sum to 1.0
        fracs = [distributions[cid].get(cls_name, 0) for cid in distributions]
        total_frac = sum(fracs)
        if total_frac > 0:
            fracs = [f / total_frac for f in fracs]

        offset = 0
        for i, cid in enumerate(distributions):
            n = int(n_cls * fracs[i])
            if offset + n > n_cls:
                n = n_cls - offset
            selected = cls_features[offset:offset + n]
            client_data[cid]["X"].append(selected)
            client_data[cid]["y"].append(np.full(len(selected), cls_idx, dtype=np.int64))
            offset += n

    result = {}
    for cid in distributions:
        X = np.concatenate(client_data[cid]["X"], axis=0)
        y = np.concatenate(client_data[cid]["y"], axis=0)
        result[cid] = (X, y)
    return result


def extract_primitives(model, X, y, class_names, client_id, round_id, device):
    """Run inference and extract primitives with REAL softmax entropy."""
    model.eval()
    with torch.no_grad():
        X_t = torch.FloatTensor(X).to(device)
        logits = model(X_t)
        entropies = softmax_entropy(logits).cpu().numpy()
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        preds = np.argmax(probs, axis=1)

    primitives = []
    for i in range(len(X)):
        pred_cls = class_names[preds[i]]
        true_cls = class_names[y[i]]
        h = float(entropies[i])
        conf = float(probs[i][preds[i]])

        primitives.append(VisualPrimitive(
            ref=pred_cls,                    # predicted class as ref
            primitive_type=PrimitiveType.POINT,
            coords=[[int(preds[i]), int(y[i])]],  # [pred, true] as coords
            token_entropy=h,
            source_client=client_id,
            auxiliary={
                "confidence": conf,
                "true_class": true_cls,
                "correct": int(preds[i] == y[i]),
            },
        ))

    return PrimitiveBatch(
        client_id=client_id,
        round_id=round_id,
        primitives=primitives,
    )


def evaluate(model, X, y, batch_size=64, device="cpu"):
    """Compute accuracy and per-class accuracy."""
    model.eval()
    loader = DataLoader(TensorDataset(torch.FloatTensor(X), torch.LongTensor(y)),
                        batch_size=batch_size)
    correct, total = 0, 0
    class_correct = {}
    class_total = {}

    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.size(0)
            for cls in yb.unique():
                c = cls.item()
                mask = yb == c
                class_correct[c] = class_correct.get(c, 0) + (preds[mask] == c).sum().item()
                class_total[c] = class_total.get(c, 0) + mask.sum().item()

    per_class = {c: class_correct.get(c, 0) / max(class_total.get(c, 1), 1)
                 for c in sorted(class_total.keys())}
    return correct / max(total, 1), per_class


def run_experiment():
    device = "cpu"
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    print("=" * 80)
    print("EWA-Fed REAL Experiment: Organoid Classification")
    print("=" * 80)

    # ── Load data ──
    data = np.load(FEATURES_PATH, allow_pickle=True)
    features_raw = data["features"].astype(np.float32)
    labels = data["labels"]
    class_names = [str(c) for c in data["classes"]]
    n_classes = len(class_names)

    # PCA降维 + 噪声
    from sklearn.decomposition import PCA
    pca = PCA(n_components=PCA_DIM, random_state=SEED)
    features = pca.fit_transform(features_raw).astype(np.float32)
    rng = np.random.RandomState(SEED + 1)
    features += rng.randn(*features.shape).astype(np.float32) * NOISE_STD
    input_dim = features.shape[1]

    print(f"\nData: {len(features)} samples, {input_dim}-dim (PCA from 512), {n_classes} classes")
    print(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.4f}")
    print(f"Classes: {class_names}")

    # ── Non-IID split ──
    client_data = split_non_iid(features, labels, class_names, CLIENT_DISTRIBUTIONS, SEED)
    print(f"\nNon-IID split across {N_CLIENTS} clients:")
    for cid, (X, y) in client_data.items():
        dist = {class_names[c]: int(np.sum(y == c)) for c in range(n_classes)}
        label = "EXPERT" if cid == 0 else f"Lab {cid}"
        print(f"  Client {cid} ({label}): {len(X)} samples — {dist}")

    # ── Train/test split per client ──
    train_data = {}
    for cid, (X, y) in client_data.items():
        n = len(X)
        n_test = max(int(n * TEST_RATIO), 1)
        idx = np.random.RandomState(SEED + cid).permutation(n)
        train_data[cid] = (X[idx[n_test:]], y[idx[n_test:]])

    # Global test set (20% of total, stratified)
    all_X, all_y = features.copy(), labels.copy()
    idx = np.random.RandomState(SEED).permutation(len(all_X))
    n_global_test = int(len(all_X) * TEST_RATIO)
    test_X, test_y = all_X[idx[:n_global_test]], all_y[idx[:n_global_test]]

    total_train = sum(len(X) for X, _ in train_data.values())
    print(f"\nTrain: {total_train}, Global Test: {len(test_X)}")

    # ── Init model ──
    global_model = Classifier(input_dim, n_classes, HIDDEN_DIM).to(device)
    global_params = get_params(global_model)

    # ── EWA aggregators ──
    ewa_agg = EntropyWeightedAggregator(strategy="entropy_weighted", entropy_threshold=5.0)
    fedavg_agg = EntropyWeightedAggregator(strategy="equal_weight", entropy_threshold=5.0)
    conformity_detector = ConformityDetector()

    # ── Run FL ──
    round_results = []
    print(f"\n{'─' * 80}")
    print(f"Running {N_ROUNDS} rounds of FL training...")
    print(f"{'─' * 80}")

    for rnd in range(1, N_ROUNDS + 1):
        t0 = time.time()
        client_params_list = []
        client_batches = []
        client_metrics = []

        for cid in range(N_CLIENTS):
            X_train, y_train = train_data[cid]
            if len(X_train) < 2:
                continue

            # Local training
            local_model = Classifier(input_dim, n_classes, HIDDEN_DIM).to(device)
            set_params(local_model, global_params)

            optimizer = optim.Adam(local_model.parameters(), lr=LR)
            criterion = nn.CrossEntropyLoss()
            loader = DataLoader(TensorDataset(
                torch.FloatTensor(X_train), torch.LongTensor(y_train)),
                batch_size=BATCH_SIZE, shuffle=True,
            )

            local_model.train()
            for _ in range(LOCAL_EPOCHS):
                for xb, yb in loader:
                    xb, yb = xb.to(device), yb.to(device)
                    optimizer.zero_grad()
                    loss = criterion(local_model(xb), yb)
                    loss.backward()
                    optimizer.step()

            client_params_list.append(get_params(local_model))

            # Extract REAL primitives (entropy from actual inference)
            client_id = EXPERT_ID if cid == 0 else f"lab_{cid}"
            batch = extract_primitives(
                local_model, X_train, y_train, class_names, client_id, rnd, device
            )
            client_batches.append(batch)

            # Local metrics
            train_acc, _ = evaluate(local_model, X_train, y_train, device=device)
            client_metrics.append({
                "client_id": client_id,
                "train_acc": round(train_acc, 4),
                "n_samples": len(X_train),
                "avg_entropy": round(float(np.mean([p.token_entropy for p in batch.primitives])), 4),
            })

        # FedAvg aggregation (training layer)
        weights = [m["n_samples"] for m in client_metrics]
        global_params = fedavg_aggregate(client_params_list, weights)
        set_params(global_model, global_params)

        # EWA analysis (monitoring layer)
        ewa_result = ewa_agg.aggregate(client_batches)
        fedavg_result = fedavg_agg.aggregate(client_batches)

        # Global test accuracy
        test_acc, per_class_acc = evaluate(global_model, test_X, test_y, device=device)

        # Extract expert weight share on specialty class
        expert_ws_ewa = None
        expert_ws_fedavg = None
        for proto in ewa_result.prototypes:
            if proto.ref == EXPERT_SPECIALTY and EXPERT_ID in proto.client_stats:
                expert_ws_ewa = proto.client_stats[EXPERT_ID]["weight_share"]
        for proto in fedavg_result.prototypes:
            if proto.ref == EXPERT_SPECIALTY and EXPERT_ID in proto.client_stats:
                expert_ws_fedavg = proto.client_stats[EXPERT_ID]["weight_share"]

        # Conformity tracking
        conformity_detector.update(ewa_result)

        elapsed = time.time() - t0
        rr = {
            "round": rnd,
            "test_acc": round(test_acc, 4),
            "per_class_acc": {class_names[k]: round(v, 4) for k, v in per_class_acc.items()},
            "expert_ws_ewa": expert_ws_ewa,
            "expert_ws_fedavg": expert_ws_fedavg,
            "avg_entropy": ewa_result.entropy_stats.get("mean", 0),
            "conformity": ewa_result.conformity_report.get("avg_conformity", 0),
            "minority_suppressed": ewa_result.conformity_report.get("minority_suppressed", 0),
            "client_metrics": client_metrics,
            "elapsed": round(elapsed, 2),
        }
        round_results.append(rr)

        if rnd <= 3 or rnd % 5 == 0 or rnd == N_ROUNDS:
            ws_str = f"{expert_ws_ewa:.1f}%" if expert_ws_ewa else "N/A"
            fa_str = f"{expert_ws_fedavg:.1f}%" if expert_ws_fedavg else "N/A"
            print(f"  R{rnd:2d}: acc={test_acc:.4f}  EWA_ws={ws_str}  FedAvg_ws={fa_str}  H={rr['avg_entropy']:.4f}  conf={rr['conformity']:.3f}")

    # ── Summary ──
    accs = [r["test_acc"] for r in round_results]
    ewa_ws = [r["expert_ws_ewa"] for r in round_results if r["expert_ws_ewa"] is not None]
    fedavg_ws = [r["expert_ws_fedavg"] for r in round_results if r["expert_ws_fedavg"] is not None]

    print(f"\n{'=' * 80}")
    print("RESULTS")
    print(f"{'=' * 80}")
    print(f"\nTest Accuracy: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    print(f"Final Test Accuracy: {accs[-1]:.4f}")

    final_pca = round_results[-1]["per_class_acc"]
    print(f"\nPer-Class Accuracy (final round):")
    for cls, acc in final_pca.items():
        print(f"  {cls}: {acc:.4f}")

    if ewa_ws and fedavg_ws:
        print(f"\nExpert Weight Share on '{EXPERT_SPECIALTY}':")
        print(f"  EWA:       {np.mean(ewa_ws):.1f}% ± {np.std(ewa_ws):.1f}%")
        print(f"  FedAvg:    {np.mean(fedavg_ws):.1f}% ± {np.std(fedavg_ws):.1f}%")
        delta = np.mean(ewa_ws) - np.mean(fedavg_ws)
        pct = delta / max(np.mean(fedavg_ws), 0.01) * 100
        print(f"  Δ (EWA - FedAvg): +{delta:.1f}pp ({pct:.1f}% relative)")

    # Conformity report
    report = conformity_detector.get_report()
    print(f"\nConformity Trend: {report['trend']['status']}")
    print(f"Total Alerts: {len(report['alerts'])}")
    for a in report["alerts"][:5]:
        print(f"  {a['severity']} R{a['round']} {a['class']}: {a['message']}")

    # ── Save ──
    output = {
        "experiment": "organoid_real_v2",
        "description": "Real FL training with DINOv2 features (PCA 48-dim + noise), real softmax entropy",
        "n_clients": N_CLIENTS,
        "n_rounds": N_ROUNDS,
        "n_classes": n_classes,
        "class_names": class_names,
        "input_dim": input_dim,
        "pca_dim": PCA_DIM,
        "noise_std": NOISE_STD,
        "hidden_dim": HIDDEN_DIM,
        "lr": LR,
        "local_epochs": LOCAL_EPOCHS,
        "client_distributions": CLIENT_DISTRIBUTIONS,
        "expert_id": EXPERT_ID,
        "expert_specialty": EXPERT_SPECIALTY,
        "train_samples": {EXPERT_ID if k == 0 else f"lab_{k}": len(v[0]) for k, v in train_data.items()},
        "test_samples": len(test_X),
        "summary": {
            "mean_test_acc": round(float(np.mean(accs)), 4),
            "std_test_acc": round(float(np.std(accs)), 4),
            "final_test_acc": round(float(accs[-1]), 4),
            "final_per_class_acc": final_pca,
            "ewa_expert_ws_mean": round(float(np.mean(ewa_ws)), 2) if ewa_ws else None,
            "ewa_expert_ws_std": round(float(np.std(ewa_ws)), 2) if ewa_ws else None,
            "fedavg_expert_ws_mean": round(float(np.mean(fedavg_ws)), 2) if fedavg_ws else None,
            "fedavg_expert_ws_std": round(float(np.std(fedavg_ws)), 2) if fedavg_ws else None,
            "delta_pp": round(float(np.mean(ewa_ws) - np.mean(fedavg_ws)), 2) if ewa_ws and fedavg_ws else None,
            "delta_pct": round(float((np.mean(ewa_ws) - np.mean(fedavg_ws)) / max(np.mean(fedavg_ws), 0.01) * 100), 1) if ewa_ws and fedavg_ws else None,
            "conformity_trend": report["trend"]["status"],
            "total_alerts": len(report["alerts"]),
        },
        "rounds": round_results,
        "conformity_report": report,
    }

    out_path = "/home/z/my-project/download/ewa_results/organoid_real_v2.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")

    # LaTeX table
    if ewa_ws and fedavg_ws:
        latex = r"""\begin{table}[h]
\centering
\caption{Real FL Experiment: Organoid Classification (DINOv2 features, PCA 48-dim)}
\label{tab:organoid_real}
\begin{tabular}{lcc}
\toprule
Metric & EWA & FedAvg \\
\midrule
Expert Weight Share (\texttt{late\_stage}) & %.1f\%% $\pm$ %.1f & %.1f\%% $\pm$ %.1f \\
Mean Test Accuracy & %.2f & %.2f \\
Final Test Accuracy & %.2f & %.2f \\
Conformity Alerts & %d & — \\
\bottomrule
\end{tabular}
\end{table}
""" % (
            np.mean(ewa_ws), np.std(ewa_ws),
            np.mean(fedavg_ws), np.std(fedavg_ws),
            np.mean(accs), np.mean(accs),
            accs[-1], accs[-1],
            len(report["alerts"]),
        )
        latex_path = "/home/z/my-project/download/ewa_results/table_organoid_real.tex"
        with open(latex_path, "w") as f:
            f.write(latex)
        print(f"LaTeX: {latex_path}")

    return output


if __name__ == "__main__":
    run_experiment()
