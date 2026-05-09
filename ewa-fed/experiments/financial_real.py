"""
EWA-Fed Real Experiment: Financial Sentiment Classification
============================================================
Uses Twitter Financial News Sentiment dataset (HuggingFace).
Real TF-IDF features + MLP classifier trained in FL setting.
Extracts REAL softmax entropy per client per round.

Dataset: zeroshot/twitter-financial-news-sentiment
  - 9543 train, 2388 validation
  - 3 classes: Bearish (0), Bullish (1), Neutral (2)
  - Imbalanced: 1442 / 6178 / 1923

Non-IID setup:
  - Expert client: specializes in Bearish (rare class)
  - Majority clients: mostly Bullish + Neutral
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from collections import OrderedDict
import json
import time

from ewa.primitives import VisualPrimitive, PrimitiveBatch, PrimitiveType
from ewa.aggregator import EntropyWeightedAggregator, AggregationStrategy
from ewa.conformity import ConformityDetector


# ── Config ──
N_CLIENTS = 5
N_ROUNDS = 15
LOCAL_EPOCHS = 2
LR = 0.003
BATCH_SIZE = 64
HIDDEN_DIM = 64
SEED = 42
TFIDF_MAX_FEATURES = 5000
SVD_DIM = 128          # More dimensions for better representation
USE_SENTENCE_TRANSFORMER = True  # Use pretrained embeddings instead of TF-IDF
TEST_RATIO = 0.2
LR = 0.002
N_ROUNDS = 20
LOCAL_EPOCHS = 3

# Non-IID: expert (client 0) specializes in Bearish (rare, hard class)
CLIENT_DISTRIBUTIONS = {
    0: {"Bearish": 0.80, "Bullish": 0.05, "Neutral": 0.15},  # expert: 80% Bearish
    1: {"Bearish": 0.05, "Bullish": 0.35, "Neutral": 0.60},
    2: {"Bearish": 0.05, "Bullish": 0.30, "Neutral": 0.65},
    3: {"Bearish": 0.05, "Bullish": 0.30, "Neutral": 0.65},
    4: {"Bearish": 0.05, "Bullish": 0.30, "Neutral": 0.65},
}

CLASS_NAMES = ["Bearish", "Bullish", "Neutral"]
EXPERT_ID = "expert"
EXPERT_SPECIALTY = "Bearish"


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


def evaluate(model, X, y, batch_size=128, device="cpu"):
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
    for c in class_total:
        per_class[c] = class_correct[c] / class_total[c] if class_total[c] > 0 else 0.0

    return correct / total if total > 0 else 0.0, per_class


def run_experiment():
    device = "cpu"
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    print("=" * 80)
    print("EWA-Fed REAL Experiment: Financial Sentiment (Twitter)")
    print("=" * 80)

    # ── Load dataset ──
    from datasets import load_dataset
    print("\nLoading Twitter Financial News Sentiment dataset...")
    ds = load_dataset("zeroshot/twitter-financial-news-sentiment")
    texts = [item["text"] for item in ds["train"]]
    labels = np.array([item["label"] for item in ds["train"]], dtype=np.int64)

    # Map labels: 0=Bearish, 1=Bullish, 2=Neutral
    print(f"Dataset: {len(texts)} samples")
    from collections import Counter
    label_counts = Counter(labels)
    for lbl, cnt in sorted(label_counts.items()):
        print(f"  {CLASS_NAMES[lbl]}: {cnt} ({cnt/len(labels)*100:.1f}%)")

    # ── Feature extraction ──
    if USE_SENTENCE_TRANSFORMER:
        print(f"\nEncoding with sentence-transformers (all-MiniLM-L6-v2)...")
        from sentence_transformers import SentenceTransformer
        st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        features = st_model.encode(texts, show_progress_bar=True, batch_size=256).astype(np.float32)
        print(f"Features: {features.shape}")
    else:
        print(f"\nTF-IDF (max_features={TFIDF_MAX_FEATURES}) + SVD (dim={SVD_DIM})...")
        vectorizer = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES, stop_words='english',
                                      max_df=0.95, min_df=2)
        X_tfidf = vectorizer.fit_transform(texts)
        svd = TruncatedSVD(n_components=SVD_DIM, random_state=SEED)
        features = svd.fit_transform(X_tfidf).astype(np.float32)
        print(f"Features: {features.shape}, SVD explained variance: {svd.explained_variance_ratio_.sum():.4f}")

    # ── Non-IID split ──
    client_data = split_non_iid(features, labels, CLASS_NAMES, CLIENT_DISTRIBUTIONS, SEED)
    print(f"\nNon-IID split across {N_CLIENTS} clients:")
    for cid, (X, y) in client_data.items():
        dist = {CLASS_NAMES[c]: int(np.sum(y == c)) for c in range(len(CLASS_NAMES))}
        label = "EXPERT" if cid == 0 else f"Fund {cid}"
        print(f"  Client {cid} ({label}): {len(X)} samples — {dist}")

    # ── Train/test split per client ──
    train_data = {}
    for cid, (X, y) in client_data.items():
        n = len(X)
        n_test = max(int(n * TEST_RATIO), 1)
        indices = np.random.RandomState(SEED + cid).permutation(n)
        train_data[cid] = (X[indices[n_test:]], y[indices[n_test:]])

    # Global test set (stratified)
    all_test_X, all_test_y = [], []
    for cid, (X, y) in client_data.items():
        n = len(X)
        n_test = max(int(n * TEST_RATIO), 1)
        indices = np.random.RandomState(SEED + cid).permutation(n)
        all_test_X.append(X[indices[:n_test]])
        all_test_y.append(y[indices[:n_test]])
    test_X = np.concatenate(all_test_X)
    test_y = np.concatenate(all_test_y)

    n_train = sum(len(X) for X, _ in train_data.values())
    print(f"\nTrain: {n_train}, Global Test: {len(test_X)}")

    # ── Init model ──
    input_dim = features.shape[1]
    global_model = TextClassifier(input_dim, len(CLASS_NAMES), HIDDEN_DIM).to(device)

    # ── EWA setup ──
    ewa_agg = EntropyWeightedAggregator(strategy=AggregationStrategy.ENTROPY_WEIGHTED)
    fedavg_agg = EntropyWeightedAggregator(strategy=AggregationStrategy.EQUAL_WEIGHT)
    conformity_detector = ConformityDetector()

    # ── Training loop ──
    print(f"\n{'─'*80}")
    print(f"Running {N_ROUNDS} rounds of FL training...")
    print(f"{'─'*80}")

    round_results = []
    accs = []
    ewa_ws = []
    fedavg_ws = []

    for rnd in range(1, N_ROUNDS + 1):
        t0 = time.time()
        client_params_list = []
        client_weights = []
        client_batches = []

        for cid in range(N_CLIENTS):
            X_train, y_train = train_data[cid]
            if len(X_train) < 2:
                continue

            # Local training
            client_model = TextClassifier(input_dim, len(CLASS_NAMES), HIDDEN_DIM).to(device)
            set_params(client_model, get_params(global_model))

            # Compute class weights for imbalanced data
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
            client_id = EXPERT_ID if cid == 0 else f"fund_{cid}"
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

        # Extract expert weight share (aggregator already returns percentage)
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
            "per_class_acc": {CLASS_NAMES[k]: round(v, 4) for k, v in per_class.items()},
            "expert_ws_ewa": round(expert_ws_ewa, 2) if expert_ws_ewa else None,
            "expert_ws_fedavg": round(expert_ws_fedavg, 2) if expert_ws_fedavg else None,
            "avg_entropy": round(avg_h, 4),
            "elapsed": round(elapsed, 2),
        }
        round_results.append(rr)

        if rnd <= 3 or rnd % 5 == 0 or rnd == N_ROUNDS:
            ws_e = f"{expert_ws_ewa:.1f}%" if expert_ws_ewa else "N/A"
            ws_f = f"{expert_ws_fedavg:.1f}%" if expert_ws_fedavg else "N/A"
            print(f"  R{rnd:2d}: acc={test_acc:.4f}  EWA_ws={ws_e}  FedAvg_ws={ws_f}  H={avg_h:.4f}")

    # ── Summary ──
    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")

    print(f"\nTest Accuracy: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    print(f"Final Test Accuracy: {accs[-1]:.4f}")

    final_pca = round_results[-1]["per_class_acc"]
    print(f"\nPer-Class Accuracy (final round):")
    for cls, acc_val in final_pca.items():
        print(f"  {cls}: {acc_val}")

    if ewa_ws and fedavg_ws:
        delta = np.mean(ewa_ws) - np.mean(fedavg_ws)
        rel = (delta / np.mean(fedavg_ws) * 100) if np.mean(fedavg_ws) > 0 else 0
        print(f"\nExpert Weight Share on '{EXPERT_SPECIALTY}':")
        print(f"  EWA:       {np.mean(ewa_ws):.1f}% ± {np.std(ewa_ws):.1f}%")
        print(f"  FedAvg:    {np.mean(fedavg_ws):.1f}% ± {np.std(fedavg_ws):.1f}%")
        print(f"  Δ (EWA - FedAvg): +{delta:.1f}pp ({rel:.1f}% relative)")

    report = conformity_detector.get_report()
    print(f"\nConformity Trend: {report['trend']['status']}")
    print(f"Total Alerts: {len(report['alerts'])}")

    # ── Save ──
    output = {
        "experiment": "financial_sentiment_real",
        "dataset": "zeroshot/twitter-financial-news-sentiment",
        "n_samples": len(texts),
        "feature_extraction": f"TF-IDF({TFIDF_MAX_FEATURES}) + SVD({SVD_DIM})",
        "n_clients": N_CLIENTS,
        "n_rounds": N_ROUNDS,
        "n_classes": len(CLASS_NAMES),
        "class_names": CLASS_NAMES,
        "class_distribution_raw": {CLASS_NAMES[k]: int(v) for k, v in sorted(label_counts.items())},
        "client_distributions": CLIENT_DISTRIBUTIONS,
        "summary": {
            "mean_test_acc": float(np.mean(accs)),
            "std_test_acc": float(np.std(accs)),
            "final_test_acc": float(accs[-1]),
            "final_per_class_acc": final_pca,
            "ewa_expert_ws_mean": float(np.mean(ewa_ws)) if ewa_ws else None,
            "ewa_expert_ws_std": float(np.std(ewa_ws)) if ewa_ws else None,
            "fedavg_expert_ws_mean": float(np.mean(fedavg_ws)) if fedavg_ws else None,
            "fedavg_expert_ws_std": float(np.std(fedavg_ws)) if fedavg_ws else None,
            "delta_pp": round(float(np.mean(ewa_ws) - np.mean(fedavg_ws)), 1) if ewa_ws and fedavg_ws else None,
            "delta_relative_pct": round(float((np.mean(ewa_ws) - np.mean(fedavg_ws)) / np.mean(fedavg_ws) * 100), 1) if ewa_ws and fedavg_ws and np.mean(fedavg_ws) > 0 else None,
            "conformity_trend": report["trend"]["status"],
            "total_alerts": len(report["alerts"]),
        },
        "rounds": round_results,
    }

    out_path = "/home/z/my-project/download/ewa_results/financial_sentiment_real.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")

    # LaTeX
    if ewa_ws and fedavg_ws:
        latex = r"""\begin{table}[h]
\centering
\caption{Real FL Experiment: Financial Sentiment (Twitter, TF-IDF+SVD)}
\label{tab:financial_real}
\begin{tabular}{lcc}
\toprule
Metric & EWA & FedAvg \\
\midrule
Expert Weight Share (\texttt{Bearish}) & %.1f\%% $\pm$ %.1f & %.1f\%% $\pm$ %.1f \\
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
        latex_path = "/home/z/my-project/download/ewa_results/table_financial_real.tex"
        with open(latex_path, "w") as f:
            f.write(latex)
        print(f"LaTeX: {latex_path}")

    return output


if __name__ == "__main__":
    run_experiment()
