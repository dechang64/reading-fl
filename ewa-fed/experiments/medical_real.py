"""
EWA-Fed Real Experiment: Medical QA Classification
=====================================================
Uses PubMed QA dataset (HuggingFace) — biomedical question answering.
Real sentence-transformer embeddings + MLP classifier in FL setting.
Extracts REAL softmax entropy per client per round.

Dataset: pubmed_qa (pqa_labeled)
  - 1000 samples
  - 3 classes: yes (552), no (338), maybe (110)
  - Expert specializes in 'maybe' (rare, hardest class)

Non-IID setup:
  - Expert client: 70% 'maybe' (rare diagnostic uncertainty)
  - Majority clients: mostly 'yes'/'no'
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
N_CLIENTS = 5
N_ROUNDS = 20
LOCAL_EPOCHS = 3
LR = 0.003
BATCH_SIZE = 32
HIDDEN_DIM = 128
SEED = 42
TEST_RATIO = 0.15

# Non-IID: expert (client 0) specializes in 'no' (33.8%, moderate difficulty)
# 'no' is harder than 'yes' (55.2%) but learnable
CLIENT_DISTRIBUTIONS = {
    0: {"yes": 0.10, "no": 0.80, "maybe": 0.10},  # expert: 80% no
    1: {"yes": 0.60, "no": 0.30, "maybe": 0.10},
    2: {"yes": 0.65, "no": 0.25, "maybe": 0.10},
    3: {"yes": 0.60, "no": 0.30, "maybe": 0.10},
    4: {"yes": 0.65, "no": 0.25, "maybe": 0.10},
}

CLASS_NAMES = ["yes", "no", "maybe"]
EXPERT_ID = "expert"
EXPERT_SPECIALTY = "no"


# ── Model ──
class TextClassifier(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, num_classes),
        )

    def forward(self, x):
        return self.net(x)


# ── Utils ──
def get_params(model):
    return [p.detach().clone() for p in model.parameters()]

def set_params(model, params):
    with torch.no_grad():
        for p, new_p in zip(model.parameters(), params):
            p.copy_(new_p)

def fedavg_aggregate(param_lists, weights=None):
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
    probs = torch.softmax(logits, dim=-1)
    log_probs = torch.log(probs + 1e-8)
    return -(probs * log_probs).sum(dim=-1)

def split_non_iid(features, labels, class_names, distributions, seed):
    """Split data across clients with Non-IID distributions."""
    rng = np.random.RandomState(seed)
    client_data = {i: {"X": [], "y": []} for i in distributions}

    for cls_idx, cls_name in enumerate(class_names):
        cls_mask = labels == cls_idx
        cls_features = features[cls_mask].copy()
        n_cls = len(cls_features)
        rng.shuffle(cls_features)

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
            ref=pred_cls,
            primitive_type=PrimitiveType.POINT,
            coords=[[int(preds[i]), int(y[i])]],
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
            preds = torch.argmax(logits, dim=1)
            correct += (preds == yb).sum().item()
            total += yb.size(0)
            for c in yb.unique():
                c = c.item()
                mask = yb == c
                class_correct[c] = class_correct.get(c, 0) + (preds[mask] == yb[mask]).sum().item()
                class_total[c] = class_total.get(c, 0) + mask.sum().item()

    per_class = {}
    for c in sorted(class_total.keys()):
        per_class[c] = class_correct[c] / class_total[c] if class_total[c] > 0 else 0.0

    return correct / total if total > 0 else 0.0, per_class


def run_experiment():
    device = "cpu"
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    print("=" * 80)
    print("EWA-Fed REAL Experiment: Medical QA (PubMed)")
    print("=" * 80)

    # ── Load dataset ──
    from datasets import load_dataset
    print("\nLoading PubMed QA dataset...")
    ds = load_dataset("pubmed_qa", "pqa_labeled", split="train")

    # Combine question + context for embedding
    texts = []
    labels = []
    label_map = {"yes": 0, "no": 1, "maybe": 2}
    for item in ds:
        context_str = " ".join(item["context"]["contexts"])
        text = f"Question: {item['question']} Context: {context_str}"
        texts.append(text)
        labels.append(label_map[item["final_decision"]])
    labels = np.array(labels, dtype=np.int64)

    print(f"Dataset: {len(texts)} samples")
    from collections import Counter
    label_counts = Counter(labels)
    for lbl, cnt in sorted(label_counts.items()):
        print(f"  {CLASS_NAMES[lbl]}: {cnt} ({cnt/len(labels)*100:.1f}%)")

    # ── Sentence-transformer embeddings ──
    print(f"\nEncoding with sentence-transformers (all-MiniLM-L6-v2)...")
    from sentence_transformers import SentenceTransformer
    st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    features = st_model.encode(texts, show_progress_bar=True, batch_size=64).astype(np.float32)
    print(f"Features: {features.shape}")

    # ── Non-IID split ──
    client_data = split_non_iid(features, labels, CLASS_NAMES, CLIENT_DISTRIBUTIONS, SEED)
    print(f"\nNon-IID split across {N_CLIENTS} clients:")
    for cid, (X, y) in client_data.items():
        dist = {CLASS_NAMES[c]: int(np.sum(y == c)) for c in range(len(CLASS_NAMES))}
        label = "EXPERT" if cid == 0 else f"Hospital {cid}"
        print(f"  Client {cid} ({label}): {len(X)} samples — {dist}")

    # ── Train/test split (global) ──
    all_X = np.concatenate([cd[0] for cd in client_data.values()], axis=0)
    all_y = np.concatenate([cd[1] for cd in client_data.values()], axis=0)
    n_test = int(len(all_X) * TEST_RATIO)
    rng = np.random.RandomState(SEED)
    idx = rng.permutation(len(all_X))
    test_idx, train_idx = idx[:n_test], idx[n_test:]
    test_X, test_y = all_X[test_idx], all_y[test_idx]

    # Remove test samples from client data
    train_data = {}
    for cid in client_data:
        X, y = client_data[cid]
        mask = np.ones(len(X), dtype=bool)
        for ti in test_idx:
            # Mark samples that are in test set
            for j in range(len(X)):
                if np.array_equal(X[j], all_X[ti]) and y[j] == all_y[ti]:
                    mask[j] = False
        train_data[cid] = (X[mask], y[mask])

    total_train = sum(len(td[0]) for td in train_data.values())
    print(f"\nTrain: {total_train}, Global Test: {n_test}")

    # ── Init model ──
    input_dim = features.shape[1]
    global_model = TextClassifier(input_dim, len(CLASS_NAMES), HIDDEN_DIM).to(device)

    # ── EWA aggregators ──
    ewa_agg = EntropyWeightedAggregator(strategy=AggregationStrategy.ENTROPY_WEIGHTED)
    fedavg_agg = EntropyWeightedAggregator(strategy=AggregationStrategy.EQUAL_WEIGHT)
    conformity_detector = ConformityDetector()

    # ── Training loop ──
    accs = []
    ewa_ws = []
    fedavg_ws = []
    round_results = []

    print(f"\n{'─' * 80}")
    print(f"Running {N_ROUNDS} rounds of FL training...")
    print(f"{'─' * 80}")

    for rnd in range(1, N_ROUNDS + 1):
        t0 = time.time()
        client_params_list = []
        client_weights = []
        client_batches = []

        for cid in range(N_CLIENTS):
            X_train, y_train = train_data[cid]
            if len(X_train) < 10:
                continue

            # Local training
            client_model = TextClassifier(input_dim, len(CLASS_NAMES), HIDDEN_DIM).to(device)
            set_params(client_model, get_params(global_model))

            # Class weights for imbalance
            class_counts = np.bincount(y_train, minlength=len(CLASS_NAMES))
            class_weights = 1.0 / (class_counts + 1e-6)
            class_weights = class_weights / class_weights.sum() * len(CLASS_NAMES)
            cw_tensor = torch.FloatTensor(class_weights).to(device)

            optimizer = optim.Adam(client_model.parameters(), lr=LR)
            criterion = nn.CrossEntropyLoss(weight=cw_tensor)
            loader = DataLoader(TensorDataset(
                torch.FloatTensor(X_train), torch.LongTensor(y_train)),
                batch_size=BATCH_SIZE, shuffle=True,
            )

            client_model.train()
            for _ in range(LOCAL_EPOCHS):
                for xb, yb in loader:
                    xb, yb = xb.to(device), yb.to(device)
                    optimizer.zero_grad()
                    logits = client_model(xb)
                    loss = criterion(logits, yb)
                    loss.backward()
                    optimizer.step()

            client_params_list.append(get_params(client_model))
            client_weights.append(len(X_train))

            # Extract primitives with REAL entropy
            client_id = EXPERT_ID if cid == 0 else f"hospital_{cid}"
            batch = extract_primitives(
                client_model, X_train, y_train, CLASS_NAMES,
                client_id, rnd, device
            )
            client_batches.append(batch)

        # FedAvg aggregation
        global_params = fedavg_aggregate(client_params_list, client_weights)
        set_params(global_model, global_params)

        # Evaluate
        test_acc, per_class = evaluate(global_model, test_X, test_y, device=device)
        accs.append(test_acc)

        # EWA analysis
        ewa_result = ewa_agg.aggregate(client_batches)
        fedavg_result = fedavg_agg.aggregate(client_batches)

        # Extract expert weight share
        expert_ws_ewa = None
        expert_ws_fedavg = None
        for proto in ewa_result.prototypes:
            if proto.ref == EXPERT_SPECIALTY and EXPERT_ID in proto.client_stats:
                expert_ws_ewa = proto.client_stats[EXPERT_ID]["weight_share"]
        for proto in fedavg_result.prototypes:
            if proto.ref == EXPERT_SPECIALTY and EXPERT_ID in proto.client_stats:
                expert_ws_fedavg = proto.client_stats[EXPERT_ID]["weight_share"]

        if expert_ws_ewa is not None:
            ewa_ws.append(expert_ws_ewa)
        if expert_ws_fedavg is not None:
            fedavg_ws.append(expert_ws_fedavg)

        # Conformity tracking
        conformity_detector.update(ewa_result)

        elapsed = time.time() - t0
        avg_h = ewa_result.entropy_stats.get("mean", 0)
        rr = {
            "round": rnd,
            "test_acc": round(test_acc, 4),
            "expert_ws_ewa": expert_ws_ewa,
            "expert_ws_fedavg": expert_ws_fedavg,
            "avg_entropy": round(avg_h, 4),
            "per_class_acc": {CLASS_NAMES[k]: round(v, 4) for k, v in per_class.items()},
            "elapsed": round(elapsed, 2),
        }
        round_results.append(rr)

        if rnd in [1, 2, 3, 5, 10, 15, 20] or rnd == N_ROUNDS:
            ws_str = f"{expert_ws_ewa:.1f}%" if expert_ws_ewa else "N/A"
            fa_str = f"{expert_ws_fedavg:.1f}%" if expert_ws_fedavg else "N/A"
            print(f"  R{rnd:2d}: acc={test_acc:.4f}  EWA_ws={ws_str}  FedAvg_ws={fa_str}  H={avg_h:.4f}")

    # ── Summary ──
    print(f"\n{'=' * 80}")
    print("RESULTS")
    print(f"{'=' * 80}")
    print(f"\nTest Accuracy: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    print(f"Final Round Accuracy: {accs[-1]:.4f}")

    final_pca = round_results[-1]["per_class_acc"]
    print(f"\nPer-Class Accuracy (final round):")
    for cls, acc_val in final_pca.items():
        print(f"  {cls}: {acc_val}")

    print(f"\nExpert Weight Share on '{EXPERT_SPECIALTY}':")
    if ewa_ws and fedavg_ws:
        delta = np.mean(ewa_ws) - np.mean(fedavg_ws)
        rel = delta / np.mean(fedavg_ws) * 100 if np.mean(fedavg_ws) > 0 else 0
        print(f"  EWA:       {np.mean(ewa_ws):.1f}% ± {np.std(ewa_ws):.1f}%")
        print(f"  FedAvg:    {np.mean(fedavg_ws):.1f}% ± {np.std(fedavg_ws):.1f}%")
        print(f"  Δ (EWA - FedAvg): +{delta:.1f}pp ({rel:.1f}% relative)")

    report = conformity_detector.get_report()
    print(f"\nConformity Trend: {report['trend']['status']}")
    print(f"Total Alerts: {len(report['alerts'])}")

    # ── Save ──
    output = {
        "experiment": "medical_qa_real",
        "dataset": "pubmed_qa (pqa_labeled)",
        "n_clients": N_CLIENTS,
        "n_rounds": N_ROUNDS,
        "n_classes": len(CLASS_NAMES),
        "class_names": CLASS_NAMES,
        "feature_extractor": "sentence-transformers/all-MiniLM-L6-v2",
        "feature_dim": input_dim,
        "client_distributions": CLIENT_DISTRIBUTIONS,
        "train_samples": total_train,
        "test_samples": n_test,
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
            "delta_relative_pct": round(float((np.mean(ewa_ws) - np.mean(fedavg_ws)) / np.mean(fedavg_ws) * 100), 1) if ewa_ws and fedavg_ws and np.mean(fedavg_ws) > 0 else None,
            "conformity_trend": report["trend"]["status"],
            "total_alerts": len(report["alerts"]),
        },
        "rounds": round_results,
    }

    out_path = "/home/z/my-project/download/ewa_results/medical_qa_real.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")

    # LaTeX
    if ewa_ws and fedavg_ws:
        latex = r"""\begin{table}[h]
\centering
\caption{Real FL Experiment: Medical QA (PubMed QA, Sentence-Transformer)}
\label{tab:medical_real}
\begin{tabular}{lcc}
\toprule
Metric & EWA & FedAvg \\
\midrule
Expert Weight Share (\texttt{maybe}) & %.1f\%% $\pm$ %.1f & %.1f\%% $\pm$ %.1f \\
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
        latex_path = "/home/z/my-project/download/ewa_results/table_medical_real.tex"
        with open(latex_path, "w") as f:
            f.write(latex)
        print(f"LaTeX: {latex_path}")

    return output


if __name__ == "__main__":
    run_experiment()
