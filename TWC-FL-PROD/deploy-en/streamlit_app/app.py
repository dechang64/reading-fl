"""
TWC-FL Platform — Three-Way Catalyst Federated Learning Collaboration Platform
Streamlit Cloud Deployment Entry
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import numpy as np
import pandas as pd

from twc_fl_en import (
    DataVault, FormulaRecord, DataQualityReport,
    KnowledgeHub, FAQEntry, LiteratureRef,
    BayesianOptimizer, CandidateFormula, OptimizationResult,
    FLEngine, FLClient, FLConfig, AggregationResult,
    AuditChain, AuditEntry,
)

st.set_page_config(
    page_title="TWC-FL Platform",
    page_icon="🔬",
    layout="wide",
)

# ── Session State Init ──
if "vault" not in st.session_state:
    st.session_state.vault = DataVault(":memory:")
    # Pre-load demo data
    demos = [
        ({"Pt": 1.5, "Pd": 2.0, "Rh": 0.1}, {"CO_conv": 95.0, "HC_conv": 93.0, "NOx_conv": 90.0, "T50": 215, "T90": 245}),
        ({"Pt": 1.0, "Pd": 3.0, "Rh": 0.05}, {"CO_conv": 92.0, "HC_conv": 90.0, "NOx_conv": 88.0, "T50": 230, "T90": 260}),
        ({"Pt": 2.0, "Pd": 1.5, "Rh": 0.2}, {"CO_conv": 96.0, "HC_conv": 94.0, "NOx_conv": 91.0, "T50": 205, "T90": 235}),
        ({"Pt": 1.8, "Pd": 1.8, "Rh": 0.15}, {"CO_conv": 94.5, "HC_conv": 92.5, "NOx_conv": 89.5, "T50": 210, "T90": 240}),
        ({"Pt": 0.8, "Pd": 2.5, "Rh": 0.08}, {"CO_conv": 91.0, "HC_conv": 88.5, "NOx_conv": 86.0, "T50": 240, "T90": 270}),
    ]
    for comp, perf in demos:
        st.session_state.vault.add_formula(comp, perf)

if "optimizer" not in st.session_state:
    st.session_state.optimizer = BayesianOptimizer()
    demos_obs = [
        ({"Pt": 1.5, "Pd": 2.0, "Rh": 0.1}, {"NOx_conv": 90.0}),
        ({"Pt": 1.0, "Pd": 3.0, "Rh": 0.05}, {"NOx_conv": 88.0}),
        ({"Pt": 2.0, "Pd": 1.5, "Rh": 0.2}, {"NOx_conv": 92.0}),
        ({"Pt": 1.8, "Pd": 1.8, "Rh": 0.15}, {"NOx_conv": 91.0}),
        ({"Pt": 0.8, "Pd": 2.5, "Rh": 0.08}, {"NOx_conv": 87.0}),
    ]
    for comp, perf in demos_obs:
        st.session_state.optimizer.add_single_observation(comp, perf)

if "hub" not in st.session_state:
    st.session_state.hub = KnowledgeHub()

if "audit" not in st.session_state:
    st.session_state.audit = AuditChain()

# ── Sidebar ──
with st.sidebar:
    st.title("🔬 TWC-FL Platform")
    st.caption("Three-Way Catalyst Federated Learning Collaboration Platform")
    st.divider()
    st.metric("Formula Database", f"{len(st.session_state.vault.records)} records")
    st.metric("Knowledge FAQ", f"{len(st.session_state.hub.faqs)} entries")
    st.metric("Audit Chain", f"{len(st.session_state.audit.entries)} records")
    st.divider()
    st.caption("v1.1.0 | Pure NumPy | Streamlit Cloud")

# ── Main Tabs ──
tab_overview, tab_vault, tab_knowledge, tab_optimizer, tab_fl, tab_audit = st.tabs([
    "📊 Overview", "💾 Data Vault", "📚 Knowledge", "🎯 Bayesian", "🌐 FL Engine", "🔗 Audit Chain"
])

# ═══════════════════════════════════════════════════════════════
# Tab 1: Overview
# ═══════════════════════════════════════════════════════════════
with tab_overview:
    st.header("📊 Platform Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("💾 Data Vault (DataVault)")
        st.markdown("""
        - **P0** Formula data import (CSV/Excel/JSON)
        - **P0** Formula anonymization (for FL participation)
        - **P1** Data quality report (outliers/missing/distribution)
        - **P1** Formula similarity search
        """)
    with col2:
        st.subheader("🎯 Bayesian Optimization + 🌐 Federated Learning")
        st.markdown("""
        - **Bayesian Optimizer**: GP surrogate model + EI acquisition function
        - **FL Engine**: FedAvg aggregation + Differential Privacy
        - Pure NumPy implementation, no PyTorch dependency
        - Streamlit Cloud compatible
        """)
    with col3:
        st.subheader("📚 Knowledge Hub + 🔗 Audit Chain")
        st.markdown("""
        - **KnowledgeHub**: 20+ TWC industry FAQs
        - **Literature**: Pd-Rh catalysis, OSC materials, AI optimization
        - **AuditChain**: Blockchain-style audit, SHA-256 attestation
        - Full traceability for data exchanges
        """)

    st.divider()
    st.subheader("🏗️ System Architecture")
    st.code("""
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  DataVault  │───▶│  Bayesian    │───▶│  FL Engine  │
│  (Formula)  │    │  Optimizer   │    │  (FL)  │
└─────────────┘    └──────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ KnowledgeHub│    │  AuditChain  │    │  Dashboard  │
│  (Knowledge)    │    │  (Audit)    │    │  (Viz)    │
└─────────────┘    └──────────────┘    └─────────────┘
    """, language=None)

# ═══════════════════════════════════════════════════════════════
# Tab 2: DataVault
# ═══════════════════════════════════════════════════════════════
with tab_vault:
    st.header("💾 Data Vault")

    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["Add Formula", "Quality Report", "Similarity Search", "Anonymization"])

    with sub_tab1:
        st.subheader("Add New Formula")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Precious Metal Loadings**")
            pt = st.number_input("Pt (g/L)", 0.0, 10.0, 1.5, 0.1, key="pt")
            pd_ = st.number_input("Pd (g/L)", 0.0, 10.0, 2.0, 0.1, key="pd")
            rh = st.number_input("Rh (g/L)", 0.0, 5.0, 0.1, 0.01, key="rh")
        with col_b:
            st.markdown("**Performance Metrics**")
            co = st.number_input("CO_conv (%)", 0.0, 100.0, 95.0, 0.5, key="co")
            hc = st.number_input("HC_conv (%)", 0.0, 100.0, 93.0, 0.5, key="hc")
            nox = st.number_input("NOx_conv (%)", 0.0, 100.0, 90.0, 0.5, key="nox")
        if st.button("Add Formula", type="primary"):
            st.session_state.vault.add_formula(
                {"Pt": pt, "Pd": pd_, "Rh": rh},
                {"CO_conv": co, "HC_conv": hc, "NOx_conv": nox},
            )
            st.session_state.audit.append("formula_add", "user", {"Pt": pt, "Pd": pd_, "Rh": rh})
            st.success(f"Formula added! Total: {len(st.session_state.vault.records)} records")
            st.rerun()

        st.divider()
        st.subheader("Current Formula Data")
        if st.session_state.vault.records:
            df = st.session_state.vault.to_dataframe()
            st.dataframe(df, use_container_width=True)

    with sub_tab2:
        st.subheader("Data Quality Report")
        report = st.session_state.vault.quality_report()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Records", report.total_records)
        c2.metric("Compliance Rate", f"{report.compliance_rate:.1f}%")
        c3.metric("Outliers", report.outlier_count)
        if report.warnings:
            st.warning("⚠️ " + "\n⚠️ ".join(report.warnings))
        if report.distribution_stats:
            st.subheader("Distribution Statistics")
            stats_df = pd.DataFrame(report.distribution_stats).T
            st.dataframe(stats_df, use_container_width=True)

    with sub_tab3:
        st.subheader("Formula similarity search")
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            q_pt = st.number_input("Query Pt", 0.0, 10.0, 1.5, 0.1, key="q_pt")
            q_pd = st.number_input("Query Pd", 0.0, 10.0, 2.0, 0.1, key="q_pd")
        with col_q2:
            q_rh = st.number_input("Query Rh", 0.0, 5.0, 0.1, 0.01, key="q_rh")
            q_topk = st.number_input("Top-K", 1, 10, 3, key="q_topk")
        if st.button("Search Similar"):
            results = st.session_state.vault.search_similar(
                {"Pt": q_pt, "Pd": q_pd, "Rh": q_rh}, top_k=int(q_topk)
            )
            if results:
                for i, (rec, score) in enumerate(results):
                    st.markdown(f"**#{i+1}** similarity={score:.4f} | {rec.composition} | {rec.performance}")
            else:
                st.info("No matching results")

    with sub_tab4:
        st.subheader("Data Anonymization (for FL Participation)")
        st.caption("Add Gaussian noise to protect formula privacy, keep performance metrics as prediction targets")
        seed = st.number_input("Random Seed", 0, 9999, 42, key="anon_seed")
        noise = st.slider("Noise Scale", 0.0, 2.0, 0.5, 0.1)
        if st.button("Generate Anonymized Data"):
            anon_df = st.session_state.vault.anonymize(seed=int(seed), noise_scale=noise)
            st.dataframe(anon_df, use_container_width=True)
            st.session_state.audit.append("anonymize", "user", {"seed": seed, "noise": noise})
            st.success("Anonymized data generated (downloadable for FL training)")
            csv = anon_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "anonymized_formulas.csv", "text/csv")

# ═══════════════════════════════════════════════════════════════
# Tab 3: KnowledgeHub
# ═══════════════════════════════════════════════════════════════
with tab_knowledge:
    st.header("📚 TWC Domain Knowledge Hub")

    sub_k1, sub_k2, sub_k3 = st.tabs(["FAQ Search", "Literature", "All FAQs"])

    with sub_k1:
        query = st.text_input("Ask a question", placeholder="e.g. How to reduce Rh loading?", key="faq_q")
        if query:
            results = st.session_state.hub.search(query, top_k=5)
            for faq, score in results:
                with st.expander(f"**{faq.question}** (relevance: {score:.3f})"):
                    st.markdown(faq.answer.replace("\\n", "\n"))
                    if faq.references:
                        st.caption("References: " + ", ".join(faq.references))
                    if faq.tags:
                        st.caption("Tags: " + ", ".join(faq.tags))

    with sub_k2:
        topic = st.text_input("Research Topic", placeholder="e.g. Pd Rh catalyst", key="lit_topic")
        if topic:
            refs = st.session_state.hub.recommend_literature(topic)
            if refs:
                for ref in refs:
                    with st.expander(f"**{ref.title}** ({ref.year})"):
                        st.markdown(f"**Authors**: {ref.authors}")
                        st.markdown(f"**Source**: {ref.source}")
                        if ref.doi:
                            st.markdown(f"**DOI**: {ref.doi}")
                        if ref.key_findings:
                            st.markdown("**Key Findings**:")
                            for finding in ref.key_findings:
                                st.markdown(f"- {finding}")
            else:
                st.info("No related literature found")

    with sub_k3:
        cats = st.session_state.hub.get_categories()
        selected_cat = st.selectbox("Filter by Category", ["All"] + cats, key="faq_cat")
        faqs = st.session_state.hub.get_all_faqs()
        if selected_cat != "All":
            faqs = [f for f in faqs if f.category == selected_cat]
        for faq in faqs:
            with st.expander(faq.question):
                st.markdown(faq.answer.replace("\\n", "\n"))

# ═══════════════════════════════════════════════════════════════
# Tab 4: BayesianOptimizer
# ═══════════════════════════════════════════════════════════════
with tab_optimizer:
    st.header("🎯 Bayesian Formula Optimization")
    st.caption("Gaussian Process surrogate model + Expected Improvement acquisition function")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Optimization Settings")
        target = st.selectbox("Optimization Target", ["NOx_conv", "CO_conv", "HC_conv", "T50"], key="opt_target")
        mode = st.selectbox("Direction", ["maximize", "minimize"], key="opt_mode")
        n_cand = st.slider("Candidates", 1, 10, 5, key="opt_n")
    with c2:
        st.subheader("Current Model Status")
        opt = st.session_state.optimizer
        st.metric("Observations", opt.num_observations if hasattr(opt, "num_observations") else len(opt.observations))

    if st.button("Recommend Candidates", type="primary"):
        with st.spinner("Running Bayesian optimization..."):
            res = st.session_state.optimizer.recommend_candidates(target, mode, n_cand)
            st.session_state.audit.append("optimize", "user", {"target": target, "mode": mode, "n": n_cand})

            c1, c2, c3 = st.columns(3)
            c1.metric("Model Confidence", f"{res.model_confidence:.2f}")
            c2.metric("Current Best", f"{list(res.current_best.values())[0]:.2f}" if res.current_best else "N/A")
            c3.metric("Improvement Potential", f"{res.improvement_potential:.2f}")

            st.subheader("Recommend Candidates")
            for i, cand in enumerate(res.candidates):
                with st.expander(f"**Candidate #{i+1}** | EI={cand.acquisition_score:.4f}"):
                    cols = st.columns(len(cand.composition))
                    for j, (elem, val) in enumerate(cand.composition.items()):
                        with cols[j]:
                            st.metric(elem, f"{val:.3f}")
                    st.markdown("**Predicted Performance**:")
                    for metric, val in cand.predicted_performance.items():
                        st.markdown(f"- {metric}: {val:.2f} ± {cand.uncertainty.get(metric, 0):.2f}")

    st.divider()
    st.subheader("Submit Experiment Feedback")
    st.caption("Feed experiment results back to update the surrogate model")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        fb_pt = st.number_input("Pt", 0.0, 10.0, 1.5, 0.1, key="fb_pt")
        fb_pd = st.number_input("Pd", 0.0, 10.0, 2.0, 0.1, key="fb_pd")
    with fc2:
        fb_rh = st.number_input("Rh", 0.0, 5.0, 0.1, 0.01, key="fb_rh")
    with fc3:
        fb_val = st.number_input(f"{target} Measured", 0.0, 100.0, 90.0, 0.5, key="fb_val")
    if st.button("Submit Result"):
        st.session_state.optimizer.add_single_observation(
            {"Pt": fb_pt, "Pd": fb_pd, "Rh": fb_rh},
            {target: fb_val},
        )
        st.success("Experiment result submitted, model updated!")
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# Tab 5: FL Engine
# ═══════════════════════════════════════════════════════════════
with tab_fl:
    st.header("🌐 Federated Learning Engine")
    st.caption("FedAvg Aggregation + Differential Privacy | Pure NumPy Simulation")

    if "fl_engine" not in st.session_state:
        st.session_state.fl_engine = FLEngine(FLConfig(dp_epsilon=10.0))
        st.session_state.fl_engine.add_client(FLClient("c1", "Enterprise A", num_samples=200))
        st.session_state.fl_engine.add_client(FLClient("c2", "Enterprise B", num_samples=150))
        st.session_state.fl_engine.add_client(FLClient("c3", "Enterprise C", num_samples=180))

    sub_fl1, sub_fl2 = st.tabs(["FL Simulation", "Client Management"])

    with sub_fl1:
        c1, c2, c3 = st.columns(3)
        with c1:
            rounds = st.slider("Training Rounds", 1, 20, 10, key="fl_rounds")
        with c2:
            dp_eps = st.number_input("DP ε (Privacy Budget)", 0.0, 100.0, 10.0, 1.0, key="fl_dp")
        with c3:
            lr = st.number_input("Learning Rate", 0.001, 0.1, 0.01, 0.005, format="%.3f", key="fl_lr")

        if st.button("Start FL Training", type="primary"):
            cfg = FLConfig(dp_epsilon=dp_eps, learning_rate=lr)
            eng = FLEngine(cfg)
            for c in st.session_state.fl_engine.clients:
                eng.add_client(c)
            st.session_state.fl_engine = eng

            with st.spinner("FL training in progress..."):
                history = eng.run_simulation(rounds)
                st.session_state.audit.append("fl_train", "system", {"rounds": rounds, "dp": dp_eps})

            # Plot convergence
            st.subheader("Convergence Curve")
            loss_data = pd.DataFrame([
                {"Round": r.round_id, "Global Loss": r.global_loss, "Clients": r.participating_clients}
                for r in history
            ])
            st.line_chart(loss_data, x="Round", y="Global Loss")

            # Summary
            summary = eng.get_convergence_summary()
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", summary["status"])
            c2.metric("Loss Change", f"{summary['improvement_pct']:.1f}%")
            c3.metric("Final Loss", f"{history[-1].global_loss:.4f}")

            # Per-round details
            with st.expander("Per-Round Details"):
                st.dataframe(loss_data, use_container_width=True)

    with sub_fl2:
        st.subheader("Clients")
        eng = st.session_state.fl_engine
        for client in eng.clients:
            with st.expander(f"**{client.client_name}** ({client.client_id})"):
                c1, c2 = st.columns(2)
                c1.metric("Samples", client.num_samples)
                c2.metric("Quality Report", f"{client.data_quality:.1f}")
                st.caption(f"Specialty: {client.specialty} | Local Epochs: {client.local_epochs}")

# ═══════════════════════════════════════════════════════════════
# Tab 6: AuditChain
# ═══════════════════════════════════════════════════════════════
with tab_audit:
    st.header("🔗 Blockchain Audit Chain")
    st.caption("SHA-256 hash chain | Data attestation | Tamper detection")

    c1, c2, c3 = st.columns(3)
    chain = st.session_state.audit
    c1.metric("Total Entries", len(chain.entries))
    valid = chain.verify_chain()
    c2.metric("Chain Integrity", "✅ Intact" if valid else "❌ Tampered")
    summary = chain.get_summary()
    c3.metric("Action Types", summary.get("action_types", 0))

    st.divider()

    sub_a1, sub_a2 = st.tabs(["Audit Log", "Chain Verification"])

    with sub_a1:
        if chain.entries:
            df = chain.to_dataframe()
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Export Audit Log", csv, "audit_chain.csv", "text/csv")
        else:
            st.info("No audit records yet")

    with sub_a2:
        st.subheader("Chain Integrity Verification")
        if st.button("Verify Audit Chain"):
            valid = chain.verify_chain()
            if valid:
                st.success("✅ Audit chain is intact, all records are untampered!")
            else:
                st.error("❌ Audit chain has been tampered with!")

        st.subheader("JSON Export")
        json_str = chain.export_json()
        st.code(json_str[:2000] + ("..." if len(json_str) > 2000 else ""), language="json")
