"""
TWC-FL Platform — 三元催化器联邦学习协作平台
Streamlit Cloud 部署入口
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import numpy as np
import pandas as pd

from twc_fl import (
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
    # 预置示例数据
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
    st.caption("三元催化器联邦学习协作平台")
    st.divider()
    st.metric("配方数据库", f"{len(st.session_state.vault.records)} 条记录")
    st.metric("知识库 FAQ", f"{len(st.session_state.hub.faqs)} 条")
    st.metric("审计链", f"{len(st.session_state.audit.entries)} 条记录")
    st.divider()
    st.caption("v1.1.0 | Pure NumPy | Streamlit Cloud")

# ── Main Tabs ──
tab_overview, tab_vault, tab_knowledge, tab_optimizer, tab_fl, tab_audit = st.tabs([
    "📊 概览", "💾 配方数据管理", "📚 知识库", "🎯 贝叶斯优化", "🌐 联邦学习", "🔗 审计链"
])

# ═══════════════════════════════════════════════════════════════
# Tab 1: Overview
# ═══════════════════════════════════════════════════════════════
with tab_overview:
    st.header("📊 平台概览")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("💾 配方数据管理 (DataVault)")
        st.markdown("""
        - **P0** 配方数据导入（CSV/Excel/JSON）
        - **P0** 配方数据脱敏（FL 参与用）
        - **P1** 数据质量报告（异常值/缺失/分布）
        - **P1** 配方相似度检索
        """)
    with col2:
        st.subheader("🎯 贝叶斯优化 + 🌐 联邦学习")
        st.markdown("""
        - **Bayesian Optimizer**: GP 代理模型 + EI 采集函数
        - **FL Engine**: FedAvg 聚合 + 差分隐私
        - 纯 NumPy 实现，无 PyTorch 依赖
        - Streamlit Cloud 兼容
        """)
    with col3:
        st.subheader("📚 知识库 + 🔗 审计链")
        st.markdown("""
        - **KnowledgeHub**: 20+ TWC 行业 FAQ
        - **文献推荐**: Pd-Rh 催化、OSC 材料、AI 优化
        - **AuditChain**: 区块链式审计，SHA-256 存证
        - 数据交换全程可追溯
        """)

    st.divider()
    st.subheader("🏗️ 系统架构")
    st.code("""
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  DataVault  │───▶│  Bayesian    │───▶│  FL Engine  │
│  (配方数据)  │    │  Optimizer   │    │  (联邦学习)  │
└─────────────┘    └──────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ KnowledgeHub│    │  AuditChain  │    │  Dashboard  │
│  (知识库)    │    │  (审计链)    │    │  (可视化)    │
└─────────────┘    └──────────────┘    └─────────────┘
    """, language=None)

# ═══════════════════════════════════════════════════════════════
# Tab 2: DataVault
# ═══════════════════════════════════════════════════════════════
with tab_vault:
    st.header("💾 配方数据管理")

    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["添加配方", "数据质量", "相似度检索", "数据脱敏"])

    with sub_tab1:
        st.subheader("添加新配方")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**贵金属载量**")
            pt = st.number_input("Pt (g/L)", 0.0, 10.0, 1.5, 0.1, key="pt")
            pd_ = st.number_input("Pd (g/L)", 0.0, 10.0, 2.0, 0.1, key="pd")
            rh = st.number_input("Rh (g/L)", 0.0, 5.0, 0.1, 0.01, key="rh")
        with col_b:
            st.markdown("**性能指标**")
            co = st.number_input("CO_conv (%)", 0.0, 100.0, 95.0, 0.5, key="co")
            hc = st.number_input("HC_conv (%)", 0.0, 100.0, 93.0, 0.5, key="hc")
            nox = st.number_input("NOx_conv (%)", 0.0, 100.0, 90.0, 0.5, key="nox")
        if st.button("添加配方", type="primary"):
            st.session_state.vault.add_formula(
                {"Pt": pt, "Pd": pd_, "Rh": rh},
                {"CO_conv": co, "HC_conv": hc, "NOx_conv": nox},
            )
            st.session_state.audit.append("formula_add", "user", {"Pt": pt, "Pd": pd_, "Rh": rh})
            st.success(f"配方已添加！当前共 {len(st.session_state.vault.records)} 条记录")
            st.rerun()

        st.divider()
        st.subheader("当前配方数据")
        if st.session_state.vault.records:
            df = st.session_state.vault.to_dataframe()
            st.dataframe(df, use_container_width=True)

    with sub_tab2:
        st.subheader("数据质量报告")
        report = st.session_state.vault.quality_report()
        c1, c2, c3 = st.columns(3)
        c1.metric("总记录数", report.total_records)
        c2.metric("合规率", f"{report.compliance_rate:.1f}%")
        c3.metric("异常值", report.outlier_count)
        if report.warnings:
            st.warning("⚠️ " + "\n⚠️ ".join(report.warnings))
        if report.distribution_stats:
            st.subheader("分布统计")
            stats_df = pd.DataFrame(report.distribution_stats).T
            st.dataframe(stats_df, use_container_width=True)

    with sub_tab3:
        st.subheader("配方相似度检索")
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            q_pt = st.number_input("查询 Pt", 0.0, 10.0, 1.5, 0.1, key="q_pt")
            q_pd = st.number_input("查询 Pd", 0.0, 10.0, 2.0, 0.1, key="q_pd")
        with col_q2:
            q_rh = st.number_input("查询 Rh", 0.0, 5.0, 0.1, 0.01, key="q_rh")
            q_topk = st.number_input("Top-K", 1, 10, 3, key="q_topk")
        if st.button("搜索相似配方"):
            results = st.session_state.vault.search_similar(
                {"Pt": q_pt, "Pd": q_pd, "Rh": q_rh}, top_k=int(q_topk)
            )
            if results:
                for i, (rec, score) in enumerate(results):
                    st.markdown(f"**#{i+1}** 相似度={score:.4f} | {rec.composition} | {rec.performance}")
            else:
                st.info("无匹配结果")

    with sub_tab4:
        st.subheader("数据脱敏（FL 参与用）")
        st.caption("添加高斯噪声保护配方数据隐私，仅保留性能指标作为预测目标")
        seed = st.number_input("随机种子", 0, 9999, 42, key="anon_seed")
        noise = st.slider("噪声比例", 0.0, 2.0, 0.5, 0.1)
        if st.button("生成脱敏数据"):
            anon_df = st.session_state.vault.anonymize(seed=int(seed), noise_scale=noise)
            st.dataframe(anon_df, use_container_width=True)
            st.session_state.audit.append("anonymize", "user", {"seed": seed, "noise": noise})
            st.success("脱敏数据已生成（可下载用于 FL 训练）")
            csv = anon_df.to_csv(index=False).encode("utf-8")
            st.download_button("下载 CSV", csv, "anonymized_formulas.csv", "text/csv")

# ═══════════════════════════════════════════════════════════════
# Tab 3: KnowledgeHub
# ═══════════════════════════════════════════════════════════════
with tab_knowledge:
    st.header("📚 TWC 领域知识库")

    sub_k1, sub_k2, sub_k3 = st.tabs(["FAQ 查询", "文献推荐", "全部 FAQ"])

    with sub_k1:
        query = st.text_input("输入问题", placeholder="例如：如何降低Rh载量？", key="faq_q")
        if query:
            results = st.session_state.hub.search(query, top_k=5)
            for faq, score in results:
                with st.expander(f"**{faq.question}** (相关度: {score:.3f})"):
                    st.markdown(faq.answer.replace("\\n", "\n"))
                    if faq.references:
                        st.caption("参考文献: " + ", ".join(faq.references))
                    if faq.tags:
                        st.caption("标签: " + ", ".join(faq.tags))

    with sub_k2:
        topic = st.text_input("研究主题", placeholder="例如：Pd Rh catalyst", key="lit_topic")
        if topic:
            refs = st.session_state.hub.recommend_literature(topic)
            if refs:
                for ref in refs:
                    with st.expander(f"**{ref.title}** ({ref.year})"):
                        st.markdown(f"**作者**: {ref.authors}")
                        st.markdown(f"**来源**: {ref.source}")
                        if ref.doi:
                            st.markdown(f"**DOI**: {ref.doi}")
                        if ref.key_findings:
                            st.markdown("**关键发现**:")
                            for finding in ref.key_findings:
                                st.markdown(f"- {finding}")
            else:
                st.info("未找到相关文献")

    with sub_k3:
        cats = st.session_state.hub.get_categories()
        selected_cat = st.selectbox("按分类筛选", ["全部"] + cats, key="faq_cat")
        faqs = st.session_state.hub.get_all_faqs()
        if selected_cat != "全部":
            faqs = [f for f in faqs if f.category == selected_cat]
        for faq in faqs:
            with st.expander(faq.question):
                st.markdown(faq.answer.replace("\\n", "\n"))

# ═══════════════════════════════════════════════════════════════
# Tab 4: BayesianOptimizer
# ═══════════════════════════════════════════════════════════════
with tab_optimizer:
    st.header("🎯 贝叶斯配方优化")
    st.caption("基于高斯过程代理模型 + Expected Improvement 采集函数")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("优化设置")
        target = st.selectbox("优化目标", ["NOx_conv", "CO_conv", "HC_conv", "T50"], key="opt_target")
        mode = st.selectbox("优化方向", ["maximize", "minimize"], key="opt_mode")
        n_cand = st.slider("推荐候选数", 1, 10, 5, key="opt_n")
    with c2:
        st.subheader("当前模型状态")
        opt = st.session_state.optimizer
        st.metric("历史观测数", opt.num_observations if hasattr(opt, "num_observations") else len(opt.observations))

    if st.button("推荐候选配方", type="primary"):
        with st.spinner("正在运行贝叶斯优化..."):
            res = st.session_state.optimizer.recommend_candidates(target, mode, n_cand)
            st.session_state.audit.append("optimize", "user", {"target": target, "mode": mode, "n": n_cand})

            c1, c2, c3 = st.columns(3)
            c1.metric("模型置信度", f"{res.model_confidence:.2f}")
            c2.metric("当前最优", f"{list(res.current_best.values())[0]:.2f}" if res.current_best else "N/A")
            c3.metric("提升潜力", f"{res.improvement_potential:.2f}")

            st.subheader("推荐候选配方")
            for i, cand in enumerate(res.candidates):
                with st.expander(f"**候选 #{i+1}** | EI={cand.acquisition_score:.4f}"):
                    cols = st.columns(len(cand.composition))
                    for j, (elem, val) in enumerate(cand.composition.items()):
                        with cols[j]:
                            st.metric(elem, f"{val:.3f}")
                    st.markdown("**预测性能**:")
                    for metric, val in cand.predicted_performance.items():
                        st.markdown(f"- {metric}: {val:.2f} ± {cand.uncertainty.get(metric, 0):.2f}")

    st.divider()
    st.subheader("添加实验反馈")
    st.caption("将实验结果回填到优化器，更新代理模型")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        fb_pt = st.number_input("Pt", 0.0, 10.0, 1.5, 0.1, key="fb_pt")
        fb_pd = st.number_input("Pd", 0.0, 10.0, 2.0, 0.1, key="fb_pd")
    with fc2:
        fb_rh = st.number_input("Rh", 0.0, 5.0, 0.1, 0.01, key="fb_rh")
    with fc3:
        fb_val = st.number_input(f"{target} 实测值", 0.0, 100.0, 90.0, 0.5, key="fb_val")
    if st.button("提交实验结果"):
        st.session_state.optimizer.add_single_observation(
            {"Pt": fb_pt, "Pd": fb_pd, "Rh": fb_rh},
            {target: fb_val},
        )
        st.success("实验结果已提交，模型已更新！")
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# Tab 5: FL Engine
# ═══════════════════════════════════════════════════════════════
with tab_fl:
    st.header("🌐 联邦学习引擎")
    st.caption("FedAvg 聚合 + 差分隐私 | 纯 NumPy 模拟")

    if "fl_engine" not in st.session_state:
        st.session_state.fl_engine = FLEngine(FLConfig(dp_epsilon=10.0))
        st.session_state.fl_engine.add_client(FLClient("c1", "企业A", num_samples=200))
        st.session_state.fl_engine.add_client(FLClient("c2", "企业B", num_samples=150))
        st.session_state.fl_engine.add_client(FLClient("c3", "企业C", num_samples=180))

    sub_fl1, sub_fl2 = st.tabs(["FL 模拟", "客户端管理"])

    with sub_fl1:
        c1, c2, c3 = st.columns(3)
        with c1:
            rounds = st.slider("训练轮数", 1, 20, 10, key="fl_rounds")
        with c2:
            dp_eps = st.number_input("DP ε (隐私预算)", 0.0, 100.0, 10.0, 1.0, key="fl_dp")
        with c3:
            lr = st.number_input("学习率", 0.001, 0.1, 0.01, 0.005, format="%.3f", key="fl_lr")

        if st.button("开始 FL 训练", type="primary"):
            cfg = FLConfig(dp_epsilon=dp_eps, learning_rate=lr)
            eng = FLEngine(cfg)
            for c in st.session_state.fl_engine.clients:
                eng.add_client(c)
            st.session_state.fl_engine = eng

            with st.spinner("FL 训练中..."):
                history = eng.run_simulation(rounds)
                st.session_state.audit.append("fl_train", "system", {"rounds": rounds, "dp": dp_eps})

            # Plot convergence
            st.subheader("收敛曲线")
            loss_data = pd.DataFrame([
                {"轮次": r.round_id, "全局Loss": r.global_loss, "参与客户端": r.participating_clients}
                for r in history
            ])
            st.line_chart(loss_data, x="轮次", y="全局Loss")

            # Summary
            summary = eng.get_convergence_summary()
            c1, c2, c3 = st.columns(3)
            c1.metric("状态", summary["status"])
            c2.metric("Loss 变化", f"{summary['improvement_pct']:.1f}%")
            c3.metric("最终 Loss", f"{history[-1].global_loss:.4f}")

            # Per-round details
            with st.expander("每轮详情"):
                st.dataframe(loss_data, use_container_width=True)

    with sub_fl2:
        st.subheader("参与客户端")
        eng = st.session_state.fl_engine
        for client in eng.clients:
            with st.expander(f"**{client.client_name}** ({client.client_id})"):
                c1, c2 = st.columns(2)
                c1.metric("样本数", client.num_samples)
                c2.metric("数据质量", f"{client.data_quality:.1f}")
                st.caption(f"专业方向: {client.specialty} | 本地轮数: {client.local_epochs}")

# ═══════════════════════════════════════════════════════════════
# Tab 6: AuditChain
# ═══════════════════════════════════════════════════════════════
with tab_audit:
    st.header("🔗 区块链审计链")
    st.caption("SHA-256 哈希链 | 数据存证 | 防篡改验证")

    c1, c2, c3 = st.columns(3)
    chain = st.session_state.audit
    c1.metric("总记录", len(chain.entries))
    valid = chain.verify_chain()
    c2.metric("链完整性", "✅ 完整" if valid else "❌ 已篡改")
    summary = chain.get_summary()
    c3.metric("操作类型", summary.get("action_types", 0))

    st.divider()

    sub_a1, sub_a2 = st.tabs(["审计日志", "链验证"])

    with sub_a1:
        if chain.entries:
            df = chain.to_dataframe()
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("导出审计日志", csv, "audit_chain.csv", "text/csv")
        else:
            st.info("暂无审计记录")

    with sub_a2:
        st.subheader("链完整性验证")
        if st.button("验证审计链"):
            valid = chain.verify_chain()
            if valid:
                st.success("✅ 审计链完整，所有记录未被篡改！")
            else:
                st.error("❌ 审计链已被篡改！")

        st.subheader("JSON 导出")
        json_str = chain.export_json()
        st.code(json_str[:2000] + ("..." if len(json_str) > 2000 else ""), language="json")
