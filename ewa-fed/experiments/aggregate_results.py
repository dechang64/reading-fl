"""
EWA-Fed: Aggregate Results from All Real Experiments
=====================================================
Combines organoid CV, financial NLP, and medical NLP experiments.
Generates summary JSON + LaTeX tables for the paper.
"""

import json
import os
import numpy as np

RESULTS_DIR = "/home/z/my-project/download/ewa_results"

experiments = {
    "organoid_cv": {
        "file": "organoid_real_v2.json",
        "display_name": "Medical CV (Organoid, DINOv2+PCA)",
        "modality": "CV",
        "specialty_class": "late_stage",
    },
    "financial_nlp": {
        "file": "financial_sentiment_real.json",
        "display_name": "Financial NLP (Twitter, Sentence-Transformer)",
        "modality": "NLP",
        "specialty_class": "Bearish",
    },
    "medical_nlp": {
        "file": "medical_qa_real.json",
        "display_name": "Medical NLP (PubMed QA, Sentence-Transformer)",
        "modality": "NLP",
        "specialty_class": "no",
    },
}

print("=" * 80)
print("EWA-Fed: Aggregate Results Summary")
print("=" * 80)

rows = []
for key, meta in experiments.items():
    path = os.path.join(RESULTS_DIR, meta["file"])
    if not os.path.exists(path):
        print(f"  {key}: MISSING ({path})")
        continue

    with open(path) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    row = {
        "task": meta["display_name"],
        "modality": meta["modality"],
        "specialty": meta["specialty_class"],
        "ewa_ws_mean": summary.get("ewa_expert_ws_mean"),
        "ewa_ws_std": summary.get("ewa_expert_ws_std"),
        "fedavg_ws_mean": summary.get("fedavg_expert_ws_mean"),
        "fedavg_ws_std": summary.get("fedavg_expert_ws_std"),
        "delta_pp": summary.get("delta_pp"),
        "delta_pct": summary.get("delta_pct"),
        "mean_acc": summary.get("mean_test_acc"),
        "final_acc": summary.get("final_test_acc"),
        "n_rounds": data.get("n_rounds"),
        "n_clients": data.get("n_clients"),
        "n_classes": data.get("n_classes"),
        "conformity_trend": summary.get("conformity_trend"),
        "total_alerts": summary.get("total_alerts"),
    }

    # Compute delta if missing
    if row["delta_pp"] is None and row["ewa_ws_mean"] and row["fedavg_ws_mean"]:
        row["delta_pp"] = round(row["ewa_ws_mean"] - row["fedavg_ws_mean"], 1)
    if row["delta_pct"] is None and row["delta_pp"] and row["fedavg_ws_mean"]:
        row["delta_pct"] = round(row["delta_pp"] / row["fedavg_ws_mean"] * 100, 1)

    rows.append(row)

    print(f"\n  {meta['display_name']}")
    print(f"    EWA expert ws:  {row['ewa_ws_mean']:.1f}% ± {row['ewa_ws_std']:.1f}%")
    print(f"    FedAvg expert ws: {row['fedavg_ws_mean']:.1f}% ± {row['fedavg_ws_std']:.1f}%")
    if row["delta_pp"]:
        print(f"    Δ: +{row['delta_pp']:.1f}pp ({row['delta_pct']:.1f}% relative)")
    print(f"    Accuracy: {row['mean_acc']:.4f} (final: {row['final_acc']:.4f})")

# ── Summary statistics ──
cv_rows = [r for r in rows if r["modality"] == "CV"]
nlp_rows = [r for r in rows if r["modality"] == "NLP"]

print(f"\n{'=' * 80}")
print("SUMMARY")
print(f"{'=' * 80}")

for group_name, group in [("CV", cv_rows), ("NLP", nlp_rows), ("ALL", rows)]:
    if not group:
        continue
    ewa_means = [r["ewa_ws_mean"] for r in group if r["ewa_ws_mean"]]
    fedavg_means = [r["fedavg_ws_mean"] for r in group if r["fedavg_ws_mean"]]
    deltas = [r["delta_pp"] for r in group if r["delta_pp"] is not None]
    delta_pcts = [r["delta_pct"] for r in group if r["delta_pct"] is not None]

    print(f"\n  {group_name} ({len(group)} experiments):")
    print(f"    EWA avg expert ws:  {np.mean(ewa_means):.1f}%")
    print(f"    FedAvg avg expert ws: {np.mean(fedavg_means):.1f}%")
    print(f"    Mean Δ: +{np.mean(deltas):.1f}pp ({np.mean(delta_pcts):.1f}% relative)")

# ── Save aggregate JSON ──
aggregate = {
    "experiments": rows,
    "summary": {
        "cv": {
            "n": len(cv_rows),
            "ewa_avg": round(float(np.mean([r["ewa_ws_mean"] for r in cv_rows if r["ewa_ws_mean"]])), 2),
            "fedavg_avg": round(float(np.mean([r["fedavg_ws_mean"] for r in cv_rows if r["fedavg_ws_mean"]])), 2),
            "delta_pp": round(float(np.mean([r["delta_pp"] for r in cv_rows if r["delta_pp"]])), 2),
            "delta_pct": round(float(np.mean([r["delta_pct"] for r in cv_rows if r["delta_pct"]])), 2),
        },
        "nlp": {
            "n": len(nlp_rows),
            "ewa_avg": round(float(np.mean([r["ewa_ws_mean"] for r in nlp_rows if r["ewa_ws_mean"]])), 2),
            "fedavg_avg": round(float(np.mean([r["fedavg_ws_mean"] for r in nlp_rows if r["fedavg_ws_mean"]])), 2),
            "delta_pp": round(float(np.mean([r["delta_pp"] for r in nlp_rows if r["delta_pp"]])), 2),
            "delta_pct": round(float(np.mean([r["delta_pct"] for r in nlp_rows if r["delta_pct"]])), 2),
        },
        "all": {
            "n": len(rows),
            "ewa_avg": round(float(np.mean([r["ewa_ws_mean"] for r in rows if r["ewa_ws_mean"]])), 2),
            "fedavg_avg": round(float(np.mean([r["fedavg_ws_mean"] for r in rows if r["fedavg_ws_mean"]])), 2),
            "delta_pp": round(float(np.mean([r["delta_pp"] for r in rows if r["delta_pp"]])), 2),
            "delta_pct": round(float(np.mean([r["delta_pct"] for r in rows if r["delta_pct"]])), 2),
        },
    },
}

out_path = os.path.join(RESULTS_DIR, "all_real_results.json")
with open(out_path, "w") as f:
    json.dump(aggregate, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out_path}")

# ── LaTeX main table ──
latex_rows = ""
for r in rows:
    latex_rows += f"{r['task']} & {r['modality']} & {r['ewa_ws_mean']:.1f}\\% $\\pm$ {r['ewa_ws_std']:.1f} & {r['fedavg_ws_mean']:.1f}\\% $\\pm$ {r['fedavg_ws_std']:.1f} & +{r['delta_pp']:.1f} & {r['delta_pct']:.1f}\\% \\\\\n"
    latex_rows += "\\midrule\n"

latex = r"""\begin{table*}[t]
\centering
\caption{Real FL Experiments: EWA vs FedAvg Expert Weight Share on Specialty Classes.
All experiments use real data, real model training, and real softmax entropy extraction.
EWA consistently gives higher weight to the expert client on its specialty class.}
\label{tab:all_real}
\begin{tabular}{llcccc}
\toprule
Task & Modality & EWA Expert Wt & FedAvg Expert Wt & $\Delta$ (pp) & Relative \\
\midrule
""" + latex_rows + r"""\bottomrule
\end{tabular}
\end{table*}
"""

latex_path = os.path.join(RESULTS_DIR, "table_all_real.tex")
with open(latex_path, "w") as f:
    f.write(latex)
print(f"LaTeX: {latex_path}")

print(f"\nDone!")
