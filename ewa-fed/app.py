"""
EWA-Fed: Entropy-Weighted Aggregation for Federated Learning
=============================================================
Paper Reproduction Dashboard

Two modes:
  - 🧪 Simulated Demo: Run lightweight NumPy simulations on Streamlit Cloud
  - 📊 Real Results: View pre-computed results from real PyTorch experiments

Streamlit Cloud compatible. Pure NumPy + Plotly. No PyTorch.
"""

import streamlit as st
import numpy as np
import json
import time
import sys
import os
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(__file__))

from ewa.experiments import (
    ALL_EXPERIMENTS, run_experiment, ExperimentConfig,
)
from ewa.aggregator import AggregationStrategy

# ── Page Config ──
st.set_page_config(
    page_title="EWA-Fed | Paper Reproduction",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .hero h1 { margin: 0 0 0.5rem 0; font-size: 2rem; }
    .hero p { margin: 0; opacity: 0.85; font-size: 1.1rem; }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; color: #1e40af; }
    .metric-card .label { font-size: 0.85rem; color: #64748b; margin-top: 0.3rem; }
    .tag { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
    .tag-nlp { background: #dbeafe; color: #1e40af; }
    .tag-cv { background: #dcfce7; color: #166534; }
    .tag-real { background: #fef3c7; color: #92400e; }
    .tag-sim { background: #e0e7ff; color: #3730a3; }
    table { font-size: 0.9rem; }
    th { background: #1e3a5f !important; color: white !important; }
    .finding-box {
        padding: 1rem;
        background: #f0fdf4;
        border-radius: 8px;
        border: 1px solid #bbf7d0;
        margin: 1rem 0;
    }

</style>
""", unsafe_allow_html=True)

# ── Load real results ──
_RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sample_results.json")
_real_results = {}
try:
    with open(_RESULTS_PATH) as f:
        _real_results = json.load(f)
except FileNotFoundError:
    pass

_REAL_TASK_META = {
    "organoid_cv": {
        "display": "Medical CV — Organoid Stage Classification",
        "tag": "CV",
        "dataset": "Organoid-FL (600 samples)",
        "feature": "DINOv2 + PCA 16d",
        "specialty": "late_stage",
    },
    "financial_nlp": {
        "display": "Financial NLP — Twitter Sentiment",
        "tag": "NLP",
        "dataset": "Twitter Financial News (9,543 samples)",
        "feature": "all-MiniLM-L6-v2 (384d)",
        "specialty": "Bearish",
    },
    "medical_nlp": {
        "display": "Medical NLP — PubMed QA",
        "tag": "NLP",
        "dataset": "PubMed QA (1,000 samples)",
        "feature": "all-MiniLM-L6-v2 (384d)",
        "specialty": "no",
    },
}

# ── Sidebar ──
with st.sidebar:
    mode = st.radio("## 🎛️ Mode", ["🧪 Simulated Demo", "📊 Real Results"], index=0)

    if mode == "🧪 Simulated Demo":
        st.markdown("### ⚙️ Configuration")
        n_rounds = st.slider("FL Rounds", 5, 50, 10, key="n_rounds")
        n_samples = st.slider("Samples per Client per Round", 5, 50, 20, key="n_samples")
        seed = st.number_input("Random Seed", value=42, step=1)

        st.markdown("---")
        st.markdown("### 📋 Experiment Tasks")
        selected_tasks = {}
        for key, factory in ALL_EXPERIMENTS.items():
            cfg = factory()
            tag = '<span class="tag tag-nlp">NLP</span>' if cfg.modality == "nlp" else '<span class="tag tag-cv">CV</span>'
            selected_tasks[key] = st.checkbox(
                f"{cfg.task_name} {tag}", value=True, key=f"sim_{key}"
            )

        st.markdown("---")
        st.markdown("""
        <span class="tag tag-sim">SIMULATED</span>

        Simulated entropy values demonstrate the EWA framework mechanism. For real results with actual datasets and model training, switch to **Real Results** mode.
        """, unsafe_allow_html=True)

    else:
        st.markdown("### 📋 Experiment Selection")
        real_keys = list(_real_results.keys())
        selected_real = {}
        for key in real_keys:
            meta = _REAL_TASK_META.get(key, {})
            tag_cls = "tag-cv" if meta.get("tag") == "CV" else "tag-nlp"
            tag_html = f'<span class="tag {tag_cls}">{meta.get("tag", "?")}</span>'
            selected_real[key] = st.checkbox(
                f"{meta.get('display', key)} {tag_html}", value=True, key=f"real_{key}"
            )

        st.markdown("---")
        st.markdown("""
        <span class="tag tag-real">REAL DATA</span>

        All results use **real datasets**, **real PyTorch model training**, and **real softmax entropy extraction** — no simulation.
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 📖 About")
    st.markdown("""
    **EWA-Fed** detects conformity effects in Federated Learning by analyzing entropy-weighted class prototypes.

    - 🔬 3 real-world experiments
    - 🧪 3 simulated demos
    - 🔒 Privacy-preserving (primitives only)
    - ☁️ Streamlit Cloud compatible
    """)

# ── Hero ──
st.markdown("""
<div class="hero">
    <h1>📊 EWA-Fed: Paper Reproduction Dashboard</h1>
    <p>Entropy-Weighted Aggregation for Federated Learning — Detecting Conformity Effects via Class Prototypes</p>
</div>
""", unsafe_allow_html=True)

# ── Architecture Overview ──
with st.expander("🏗️ Architecture Overview", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### Two-Layer Architecture

        **Layer 1 — Training (unchanged)**
        - Standard FedAvg aggregation
        - Model parameters updated normally

        **Layer 2 — Monitoring (EWA)**
        - Clients upload structured primitives (not raw data)
        - Server groups by class → computes prototypes
        - Detects conformity: is expert knowledge preserved?
        """)
    with col2:
        st.markdown("""
        ### Key Metrics

        | Metric | Meaning |
        |--------|---------|
        | Expert Weight Share | % of entropy-weighted contribution from expert |
        | Conformity Score | 0 = healthy, 1 = total suppression |
        | High Conformity Ratio | % of classes with conformity > 0.5 |

        ### Privacy Guarantee
        Only structured primitives are transmitted:
        - Class label (string)
        - Coordinates (normalized integers)
        - Entropy (scalar float)
        - No raw images, text, or gradients
        """)


# ══════════════════════════════════════════════════════════════
# MODE 1: SIMULATED DEMO
# ══════════════════════════════════════════════════════════════
if mode == "🧪 Simulated Demo":
    st.markdown("## 🧪 Simulated Experiments")

    tasks_to_run = [k for k, v in selected_tasks.items() if v]
    if not tasks_to_run:
        st.warning("Select at least one experiment task.")
        st.stop()

    if st.button("▶️ Run Selected Experiments", type="primary", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()
        results = {}

        for i, key in enumerate(tasks_to_run):
            factory = ALL_EXPERIMENTS[key]
            cfg = factory()
            cfg.n_rounds = n_rounds
            cfg.seed = seed
            for c in cfg.clients:
                c.n_samples_per_round = n_samples

            status.markdown(f"Running **{cfg.task_name}**...")
            result = run_experiment(cfg)
            results[key] = result
            progress.progress((i + 1) / len(tasks_to_run))

        status.markdown("✅ All experiments complete!")
        st.session_state["sim_results"] = results
        time.sleep(0.5)
        st.rerun()

    # ── Display Simulated Results ──
    if "sim_results" in st.session_state:
        results = st.session_state["sim_results"]

        # Summary cards
        st.markdown("## 📈 Results Summary")

        nlp_imps, cv_imps = [], []
        card_cols = st.columns(len(results))
        for i, (key, r) in enumerate(results.items()):
            s = r.summary["expert_specialty_weight"]
            imp = s["improvement"]
            if r.modality == "nlp":
                nlp_imps.append(imp)
            else:
                cv_imps.append(imp)

            with card_cols[i]:
                tag = "NLP" if r.modality == "nlp" else "CV"
                color = "#1e40af" if r.modality == "nlp" else "#166534"
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size:0.8rem;color:#64748b;margin-bottom:0.3rem">{r.task_name}</div>
                    <div class="value" style="color:{color}">+{imp:.1f}%</div>
                    <div class="label">Expert Weight Improvement</div>
                    <div style="margin-top:0.5rem;font-size:0.8rem">
                        EWA: <b>{s['ewa_mean']:.1f}%</b> → FedAvg: <b>{s['fedavg_mean']:.1f}%</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Cross-task table
        st.markdown("### Cross-Task Comparison")
        rows = []
        for key, r in results.items():
            s = r.summary["expert_specialty_weight"]
            rows.append({
                "Task": r.task_name,
                "Modality": r.modality.upper(),
                "EWA Expert Wt": f"{s['ewa_mean']:.1f}%",
                "FedAvg Expert Wt": f"{s['fedavg_mean']:.1f}%",
                "Δ": f"+{s['improvement']:.1f}%",
                "Rel. Improvement": f"{s['improvement_pct']:.1f}%",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Per-task detail
        st.markdown("## 📊 Per-Task Detail")
        task_tabs = st.tabs([results[k].task_name for k in results])

        # Helper: normalize round dict keys between simulated and real modes.
        def _safe_get(rd, key_sim, key_real, default=0.0):
            return rd.get(key_real, rd.get(key_sim, default))

        for tab, key in zip(task_tabs, results):
            r = results[key]
            s = r.summary["expert_specialty_weight"]
            with tab:
                col1, col2 = tab.columns(2)

                has_fedavg = any("expert_ws_fedavg" in rd for rd in r.rounds)

                with col1:
                    st.markdown("#### Expert Weight Share Over Rounds")
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=[rd["round"] for rd in r.rounds],
                        y=[_safe_get(rd, "expert_weight_share", "expert_ws_ewa") for rd in r.rounds],
                        mode="lines+markers", name="EWA",
                        line=dict(color="#1e40af", width=2),
                    ))
                    if has_fedavg:
                        fig.add_trace(go.Scatter(
                            x=[rd["round"] for rd in r.rounds],
                            y=[rd.get("expert_ws_fedavg", 0) for rd in r.rounds],
                            mode="lines+markers", name="FedAvg",
                            line=dict(color="#94a3b8", width=2, dash="dash"),
                        ))
                    fig.add_hline(y=50, line_dash="dot", line_color="#e2e8f0",
                                  annotation_text="50% threshold")
                    fig.update_layout(
                        template="plotly_white", height=350,
                        xaxis_title="FL Round", yaxis_title="Expert Weight Share (%)",
                        margin=dict(l=0, r=0, t=10, b=0),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"sim_ews_{key}")

                with col2:
                    st.markdown("#### Conformity Score Over Rounds")
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        x=[rd["round"] for rd in r.rounds],
                        y=[_safe_get(rd, "specialty_conformity", "conformity_score") for rd in r.rounds],
                        mode="lines+markers", name="Conformity",
                        line=dict(color="#dc2626", width=2),
                    ))
                    fig2.add_hline(y=0.5, line_dash="dot", line_color="#fca5a5",
                                   annotation_text="Alert threshold")
                    fig2.update_layout(
                        template="plotly_white", height=350,
                        xaxis_title="FL Round", yaxis_title="Conformity Score",
                        margin=dict(l=0, r=0, t=10, b=0),
                    )
                    st.plotly_chart(fig2, use_container_width=True, key=f"sim_conf_{key}")

                # Client details
                st.markdown("#### Client Configuration")
                cfg = ALL_EXPERIMENTS[key]()
                client_rows = []
                for c in cfg.clients:
                    dist_str = ", ".join([f"{k}: {v:.0%}" for k, v in c.class_distribution.items()])
                    client_rows.append({
                        "Client": c.label,
                        "Specialty": c.class_distribution.get(cfg.expert_specialty_class, 0) * 100,
                        "Confidence": f"{c.confidence_range[0]:.0%}–{c.confidence_range[1]:.0%}",
                        "Distribution": dist_str,
                    })
                st.dataframe(client_rows, use_container_width=True, hide_index=True, key=f"sim_clients_{key}")

        # Export
        st.markdown("## 💾 Export Results")
        col_a, col_b = st.columns(2)
        with col_a:
            json_str = json.dumps({
                k: {
                    "task_name": r.task_name,
                    "modality": r.modality,
                    "summary": r.summary,
                    "rounds": r.rounds,
                }
                for k, r in results.items()
            }, indent=2, ensure_ascii=False)
            st.download_button("Download JSON", json_str, "ewa_fed_sim_results.json", "application/json")
        with col_b:
            latex = r"\begin{table}[t]" + "\n"
            latex += r"\centering" + "\n"
            latex += r"\caption{EWA-Fed Simulated Results}" + "\n"
            latex += r"\begin{tabular}{llcccc}" + "\n"
            latex += r"\toprule" + "\n"
            latex += r"Task & Modality & EWA & FedAvg & $\Delta$ & Rel. \\" + "\n"
            latex += r"\midrule" + "\n"
            for key, r in results.items():
                s = r.summary["expert_specialty_weight"]
                latex += f"{r.task_name} & {r.modality.upper()} & {s['ewa_mean']:.1f}\\% & {s['fedavg_mean']:.1f}\\% & +{s['improvement']:.1f}\\% & {s['improvement_pct']:.1f}\\% \\\\\n"
            latex += r"\bottomrule" + "\n"
            latex += r"\end{tabular}" + "\n"
            latex += r"\end{table}"
            st.download_button("Download LaTeX", latex, "ewa_fed_sim_table.tex", "text/plain")


# ══════════════════════════════════════════════════════════════
# MODE 2: REAL RESULTS
# ══════════════════════════════════════════════════════════════
else:
    if not _real_results:
        st.error("Real results file not found. Place `sample_results.json` in `assets/` directory.")
        st.stop()

    real_keys = list(_real_results.keys())
    active_keys = [k for k in real_keys if selected_real.get(k)]
    if not active_keys:
        st.warning("Select at least one experiment.")
        st.stop()

    st.markdown("## 📈 Real Experiment Results")

    # Summary cards
    card_cols = st.columns(len(active_keys))
    for i, key in enumerate(active_keys):
        r = _real_results[key]
        s = r["summary"]
        meta = _REAL_TASK_META.get(key, {})
        delta = s.get("delta_pp", 0)
        color = "#166534" if meta.get("tag") == "CV" else "#1e40af"

        with card_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:0.8rem;color:#64748b;margin-bottom:0.3rem">{meta.get('display', key)}</div>
                <div class="value" style="color:{color}">+{delta:.1f}pp</div>
                <div class="label">Expert Weight Improvement</div>
                <div style="margin-top:0.5rem;font-size:0.8rem">
                    EWA: <b>{s['ewa_expert_ws_mean']:.1f}%</b> → FedAvg: <b>{s['fedavg_expert_ws_mean']:.1f}%</b>
                </div>
                <div style="margin-top:0.3rem;font-size:0.75rem;color:#64748b">
                    Accuracy: {s['final_test_acc']:.1%}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Cross-task comparison table
    st.markdown("### Cross-Task Comparison")

    rows = []
    for key in active_keys:
        r = _real_results[key]
        s = r["summary"]
        meta = _REAL_TASK_META.get(key, {})
        rows.append({
            "Task": meta.get("display", key),
            "Modality": meta.get("tag", "?"),
            "Dataset": meta.get("dataset", ""),
            "Feature": meta.get("feature", ""),
            "EWA Expert Wt": f"{s['ewa_expert_ws_mean']:.1f}% ± {s['ewa_expert_ws_std']:.1f}%",
            "FedAvg Expert Wt": f"{s['fedavg_expert_ws_mean']:.1f}% ± {s['fedavg_expert_ws_std']:.1f}%",
            "Δ (pp)": f"+{s.get('delta_pp', 0):.1f}",
            "Rel. Improvement": f"{s.get('delta_pct', s.get('delta_relative_pct', 0)):.1f}%",
            "Final Accuracy": f"{s['final_test_acc']:.1%}",
        })

    # Averages
    if len(active_keys) > 1:
        ewa_avg = np.mean([_real_results[k]["summary"]["ewa_expert_ws_mean"] for k in active_keys])
        fed_avg = np.mean([_real_results[k]["summary"]["fedavg_expert_ws_mean"] for k in active_keys])
        delta_avg = ewa_avg - fed_avg
        rows.append({
            "Task": "**Average**",
            "Modality": "",
            "Dataset": "",
            "Feature": "",
            "EWA Expert Wt": f"**{ewa_avg:.1f}%**",
            "FedAvg Expert Wt": f"**{fed_avg:.1f}%**",
            "Δ (pp)": f"**+{delta_avg:.1f}**",
            "Rel. Improvement": f"**{delta_avg/max(fed_avg,0.01)*100:.1f}%**",
            "Final Accuracy": "",
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Key finding
    if len(active_keys) >= 2:
        cv_keys = [k for k in active_keys if _REAL_TASK_META.get(k, {}).get("tag") == "CV"]
        nlp_keys = [k for k in active_keys if _REAL_TASK_META.get(k, {}).get("tag") == "NLP"]
        if cv_keys and nlp_keys:
            cv_delta = np.mean([_real_results[k]["summary"]["delta_pp"] for k in cv_keys])
            nlp_delta = np.mean([_real_results[k]["summary"]["delta_pp"] for k in nlp_keys])
            st.markdown(f"""
            <div class="finding-box">
            <b>Key Finding:</b> CV modality shows {'significantly' if cv_delta > nlp_delta + 10 else 'slightly'} stronger conformity protection than NLP
            (CV: +{cv_delta:.1f}pp vs NLP: +{nlp_delta:.1f}pp). Effect size correlates with task confidence — easier tasks with higher accuracy produce more pronounced EWA protection.
            </div>
            """, unsafe_allow_html=True)

    # Per-task detail
    st.markdown("## 📊 Per-Task Detail")
    task_tabs = st.tabs([_REAL_TASK_META.get(k, {}).get("display", k) for k in active_keys])

    for tab, key in zip(task_tabs, active_keys):
        r = _real_results[key]
        s = r["summary"]
        meta = _REAL_TASK_META.get(key, {})
        rounds = r["rounds"]

        with tab:
            # Dataset info
            st.markdown(f"""
            **Dataset:** {meta.get('dataset', '')}  |  **Feature:** {meta.get('feature', '')}  |  **Specialty Class:** `{meta.get('specialty', '')}`
            """)

            # Per-class accuracy
            if s.get("final_per_class_acc"):
                pca = s["final_per_class_acc"]
                pca_str = " | ".join([f"`{cls}`: {acc:.1%}" for cls, acc in pca.items()])
                st.markdown(f"**Per-Class Accuracy:** {pca_str}")

            col1, col2 = tab.columns(2)

            with col1:
                st.markdown("#### Expert Weight Share Over Rounds")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[rd["round"] for rd in rounds],
                    y=[rd.get("expert_ws_ewa", 0) for rd in rounds],
                    mode="lines+markers",
                    name="EWA (Entropy-Weighted)",
                    line=dict(color="#1e40af", width=2),
                ))
                fig.add_trace(go.Scatter(
                    x=[rd["round"] for rd in rounds],
                    y=[rd.get("expert_ws_fedavg", 0) for rd in rounds],
                    mode="lines+markers",
                    name="FedAvg (Equal-Weight)",
                    line=dict(color="#94a3b8", width=2, dash="dash"),
                ))
                fig.add_hline(y=50, line_dash="dot", line_color="#e2e8f0",
                              annotation_text="50% threshold")
                fig.update_layout(
                    template="plotly_white",
                    height=350,
                    xaxis_title="FL Round",
                    yaxis_title="Expert Weight Share (%)",
                    margin=dict(l=0, r=0, t=10, b=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True, key=f"real_ews_{key}")

            with col2:
                st.markdown("#### Average Entropy Over Rounds")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=[rd["round"] for rd in rounds],
                    y=[rd.get("avg_entropy", 0) for rd in rounds],
                    mode="lines+markers",
                    name="Mean Entropy",
                    line=dict(color="#7c3aed", width=2),
                ))
                # Use n_classes from summary or data, fallback to 3
                n_classes = r.get("n_classes", len(s.get("final_per_class_acc", {})))
                if n_classes < 2:
                    n_classes = 3
                max_entropy = np.log(n_classes)
                fig2.add_hline(y=max_entropy, line_dash="dot", line_color="#e2e8f0",
                               annotation_text=f"ln({n_classes})={max_entropy:.2f} (max)")
                fig2.update_layout(
                    template="plotly_white",
                    height=350,
                    xaxis_title="FL Round",
                    yaxis_title="Average Entropy (nats)",
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig2, use_container_width=True, key=f"real_entropy_{key}")

            # Test accuracy over rounds
            st.markdown("#### Test Accuracy Over Rounds")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=[rd["round"] for rd in rounds],
                y=[rd.get("test_acc", 0) for rd in rounds],
                mode="lines+markers",
                name="Test Accuracy",
                line=dict(color="#059669", width=2),
            ))
            fig3.update_layout(
                template="plotly_white",
                height=250,
                xaxis_title="FL Round",
                yaxis_title="Test Accuracy",
                yaxis_tickformat=".0%",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig3, use_container_width=True, key=f"real_acc_{key}")

            # Summary stats — use st.columns with markdown instead of st.metric
            # to avoid Streamlit version incompatibility with delta parameter
            st.markdown("#### Summary Statistics")
            ewa_mean = s.get("ewa_expert_ws_mean")
            ewa_std = s.get("ewa_expert_ws_std")
            fed_mean = s.get("fedavg_expert_ws_mean")
            fed_std = s.get("fedavg_expert_ws_std")
            delta_pp = s.get("delta_pp", 0)
            delta_pct = s.get("delta_pct", s.get("delta_relative_pct", 0))
            final_acc = s.get("final_test_acc")

            def _fmt(val, fmt_str, fallback="N/A"):
                return f"{val:{fmt_str}}" if val is not None else fallback

            stat_cols = st.columns(4)
            with stat_cols[0]:
                st.markdown(f"**EWA Expert Wt**\n\n# {_fmt(ewa_mean, '.1f')}%\n\n± {_fmt(ewa_std, '.1f')}%")
            with stat_cols[1]:
                st.markdown(f"**FedAvg Expert Wt**\n\n# {_fmt(fed_mean, '.1f')}%\n\n± {_fmt(fed_std, '.1f')}%")
            with stat_cols[2]:
                st.markdown(f"**Δ (EWA − FedAvg)**\n\n# +{_fmt(delta_pp, '.1f')}pp\n\n({_fmt(delta_pct, '.1f')}%)")
            with stat_cols[3]:
                st.markdown(f"**Final Accuracy**\n\n# {_fmt(final_acc, '.1%')}")

    # Export
    st.markdown("## 💾 Export Results")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        export_data = {k: _real_results[k] for k in active_keys}
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button("📥 Download JSON", json_str, "ewa_fed_real_results.json", "application/json")

    with col_b:
        latex = r"\begin{table}[t]" + "\n"
        latex += r"\centering" + "\n"
        latex += r"\caption{EWA-Fed Real Experiment Results}" + "\n"
        latex += r"\begin{tabular}{llcccc}" + "\n"
        latex += r"\toprule" + "\n"
        latex += r"Task & Modality & EWA & FedAvg & $\Delta$ & Rel. \\" + "\n"
        latex += r"\midrule" + "\n"
        for key in active_keys:
            r = _real_results[key]
            s = r["summary"]
            meta = _REAL_TASK_META.get(key, {})
            name = meta.get("display", key).split("—")[0].strip()
            tag = meta.get("tag", "?")
            delta = s.get("delta_pp", 0)
            rel = s.get("delta_pct", s.get("delta_relative_pct", 0))
            latex += f"{name} & {tag} & {s['ewa_expert_ws_mean']:.1f}\\% & {s['fedavg_expert_ws_mean']:.1f}\\% & +{delta:.1f} & {rel:.1f}\\% \\\\\n"
        latex += r"\bottomrule" + "\n"
        latex += r"\end{tabular}" + "\n"
        latex += r"\end{table}"
        st.download_button("📥 Download LaTeX", latex, "ewa_fed_table.tex", "text/plain")

    with col_c:
        csv_lines = ["Task,Modality,EWA_Expert_Wt,EWA_Std,FedAvg_Expert_Wt,FedAvg_Std,Delta_pp,Rel_Pct,Final_Acc"]
        for key in active_keys:
            r = _real_results[key]
            s = r["summary"]
            meta = _REAL_TASK_META.get(key, {})
            name = meta.get("display", key).split("—")[0].strip()
            tag = meta.get("tag", "?")
            delta = s.get("delta_pp", 0)
            rel = s.get("delta_pct", s.get("delta_relative_pct", 0))
            csv_lines.append(f"{name},{tag},{s['ewa_expert_ws_mean']},{s['ewa_expert_ws_std']},{s['fedavg_expert_ws_mean']},{s['fedavg_expert_ws_std']},{delta},{rel},{s['final_test_acc']}")
        csv_str = "\n".join(csv_lines)
        st.download_button("📥 Download CSV", csv_str, "ewa_fed_results.csv", "text/csv")
