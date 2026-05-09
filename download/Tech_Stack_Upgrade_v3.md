# 技术栈升级方案 v3（2026-05-01 更新）

> 基于 4/20-5/1 全部项目进展，对比 v2 方案（4/27）的完成情况和新增方向。

---

## 一、项目全景（12 个仓库）

| # | 项目 | 领域 | Rust | Python | 测试 | 状态 |
|---|------|------|------|--------|------|------|
| 1 | organoid-fl-upgrade | 医学图像FL | ✅ gRPC+HNSW+审计链 | ✅ YOLOv11+DINOv2+SAM2+Vision RAG+Grad-CAM | 63 | 🟢 工程标杆 |
| 2 | embodied-fl-upgrade | 具身智能FL | ✅ VLA扩展 | ✅ DINOv2+YOLOv11+Multi-Task+Grad-CAM | 72 | 🟢 VLA已审计 |
| 3 | defect-fl-upgrade | PCB缺陷检测 | ✅ | ✅ YOLOv11+DINOv2+FedAvg | 9 | 🟢 |
| 4 | fundfl-upgrade | 私募基金 | ✅ | ✅ 16项风险指标+余弦相似度 | 6 | 🟢 |
| 5 | reading-fl-upgrade | 阅读社区 | ✅ | ✅ DINOv2+Sentence-BERT+情感FL | 10 | 🟢 |
| 6 | mural-restoration-upgrade | 壁画修复 | ✅ Axum+HNSW+审计链 | ✅ DINOv2+Diffusion | 57 | 🟢 |
| 7 | embroidery-agent | 刺绣设计 | ✅ 13个gRPC RPC | ✅ DINOv2+K-means+审计链 | 48 | 🟡 Rust后端待集成 |
| 8 | TWC-FL-PROD | 统一FL框架 | ❌ | ✅ 12模块 v1.2.0 | 127 | 🟢 核心枢纽 |
| 9 | PAI | 慈善资产优化 | ❌ | ✅ 8模块 v0.4.0 | 110 | 🟡 缺Rust |
| 10 | medical-fl | 医学影像框架 | ❌ | ✅ ViT+MAE+原型对比 | — | 🟡 待对接Rust |
| 11 | NeuroSync | 神经同步 | — | — | — | ⚪ 早期 |
| 12 | streamlit-cloud | Streamlit部署模板 | — | ✅ 6个App | — | 🟢 |

**合计测试：~500+**

---

## 二、v2 方案完成情况（4/27 制定）

| v2 目标 | 状态 | 说明 |
|---------|------|------|
| ✅ DINOv2 成为所有 CV 项目共享模块 | **完成** | organoid/embodied/defect/reading/mural/embroidery 全部集成 |
| ✅ HNSW 向量搜索成为基础设施 | **完成** | 6 个项目复用 |
| ✅ 区块链审计链成为基础设施 | **完成** | 6 个项目复用 |
| ✅ gRPC 框架统一 | **完成** | embodied/mural/embroidery 使用 |
| ⚠️ PAI 加 Rust 后端 | **未开始** | Gates 申请已提交，PAI 仍是纯 Python |
| ⚠️ CoT（链式思考）实现 | **未开始** | 8 个项目全部零实现，仍是最大空白 |
| ✅ P0 三件专利交底书 | **完成** | 效果闭环+慈善贴现率+联邦因果推断 |
| ✅ Gates 申请提交 | **完成** | v8 最终版，4/29 截止前提交 |
| ✅ 6 个 Streamlit Cloud App | **完成** | 全部打包上传 |

---

## 三、v3 新增方向（5/1 更新）

### 3.1 🔴 EWA-Fed：Entropy-Weighted Aggregation（最高优先级）

**定位**：TA 技术栈的核心差异化创新，可产出 1 篇综述 + 1 篇研究论文。

**已完成**：
- ✅ 综述《Entropy as a Signal》（9 章 80 篇引用，DOCX 已排版）
- ✅ 研究论文大纲（4 组实验 × 6 个 baseline）
- ✅ TWC-FL-PROD v1.2.0：`primitive_codec.py` + `entropy_weighted_aggregator.py`
- ✅ 6 项单元测试全过

**待完成**：
| 步骤 | 内容 | 预估 | 依赖 |
|------|------|------|------|
| 1 | conformity_detector.py（Phase 2） | 1天 | 无 |
| 2 | organoid-fl 集成 PrimitiveCodec（端到端测试） | 2天 | Step 1 |
| 3 | embodied-fl 集成（点坐标编码） | 1天 | Step 1 |
| 4 | EWA-Fed 研究论文实验：医疗 CV（organoid-fl 数据） | 3天 | Step 2 |
| 5 | EWA-Fed 研究论文实验：工业 CV（defect-fl 数据） | 2天 | Step 1 |
| 6 | EWA-Fed 研究论文实验：医疗 NLP（ClinicalBERT + MIMIC-III） | 5天 | Step 1 |
| 7 | EWA-Fed 研究论文实验：金融 NLP（FinBERT + Financial PhraseBank） | 3天 | Step 1 |
| 8 | 论文撰写 | 5天 | Steps 4-7 |
| 9 | 综述投 arXiv | 1天 | 已完成 |
| 10 | 研究论文投 CSCWD 2026 | 1天 | Step 8 |

**预估总工期**：~5-6 周

**论文叙事**（三热点合一）：
> "Visual Primitives as Federated Communication Protocol: Entropy-Weighted Aggregation for Privacy-Preserving Multimodal FL"
> - Visual Primitives（DeepSeek 刚发，热点）
> - Entropy-Weighted Aggregation（EWA-Fed 原创）
> - Multimodal FL（前沿）

### 3.2 🟡 Visual Primitives 联邦通信协议

**定位**：DeepSeek "Thinking with Visual Primitives" 的联邦化扩展。

**已完成**：
- ✅ `primitive_codec.py`：YOLO 检测 → 视觉原语编码（ref + box/point/path + entropy）
- ✅ DeepSeek 特殊 token 格式互转
- ✅ 坐标归一化 + 跨分辨率对齐

**待完成**：
- [ ] organoid-fl 端到端集成（3 模拟实验室 → 原语 → EWA 聚合 → 全局更新）
- [ ] embodied-fl 端到端集成（点坐标 → 原语 → EWA 聚合）
- [ ] 与现有 FedAvg 并存的 `aggregation_mode="primitive"` 开关

### 3.3 🟡 TWC-FL-PROD 作为统一枢纽

**定位**：所有 FL 项目的共享代码库，避免重复实现。

**当前状态**（v1.2.0，12 模块）：
```
twc_fl/
├── data_vault.py          — 数据质量+隐私
├── knowledge_hub.py       — 20 FAQs+文献管理
├── bayesian_optimizer.py  — 贝叶斯超参优化
├── fl_engine.py           — FedAvg+DP引擎
├── audit_chain.py         — SHA-256审计链
├── primitive_codec.py     — 视觉原语编解码（v1.2.0 新增）
└── entropy_weighted_aggregator.py — EWA聚合器（v1.2.0 新增）
```

**待统一**：
| 模块 | 当前分散在 | 统一到 TWC-FL-PROD |
|------|-----------|-------------------|
| DINOv2 特征提取 | organoid/embodied/defect/reading/mural 各自实现 | `feature_extractor.py` |
| HNSW 向量索引 | embodied/mural Rust 实现 | `vector_index.py`（Python wrapper） |
| Grad-CAM 可解释性 | organoid/embodied 各自实现 | `explainability.py` |
| FedAvg 引擎 | defect/reading/fundfl 各自实现 | 已有 `fl_engine.py` |

---

## 四、5 大差异化特征完成度

| 特征 | 4/27 状态 | 5/1 状态 | 变化 |
|------|----------|----------|------|
| **联邦学习** | ✅ 5个项目 | ✅ 8个项目 + EWA原创聚合 | +EWA |
| **RAG** | ✅ PAI Federated RAG | ✅ organoid Vision RAG + PAI | +Vision RAG |
| **CoT** | ❌ 零实现 | ❌ 零实现 | 无变化，仍是最大空白 |
| **Rust** | ⚠️ 3个项目 | ⚠️ 4个项目（+embroidery proto） | +1 |
| **向量数据库** | ✅ HNSW 6项目 | ✅ HNSW 6项目 | 无变化 |

### CoT 空白分析

**为什么 CoT 仍然空白**：
- 4/25 TA 确认"产品层面现在不需要"（Reading-FL 60 个读者阶段）
- 技术壁垒层面"需要但作为研究储备"
- 联邦思维链可成为 PAI 专利组合第 4 件

**建议时机**：
- Phase 1（现在）：专注 EWA-Fed 实验 + 论文
- Phase 2（6月）：EWA-Fed 论文投出后，启动联邦 CoT 研究
- Phase 3（PMF验证后）：Reading-FL 产品级 CoT

---

## 五、PAI 特殊情况

PAI 是 Gates 申请核心项目，但技术栈与其他项目不一致：

| 维度 | 其他 FL 项目 | PAI |
|------|-------------|-----|
| Rust 后端 | ✅ 4个项目 | ❌ 纯 Python |
| HNSW | ✅ 6个项目 | ❌ |
| 审计链 | ✅ 6个项目 | ❌ |
| gRPC | ✅ 3个项目 | ❌ |
| 测试 | 63-127 | 110（OK） |

**建议**：PAI 暂不加 Rust。理由：
1. Gates 申请已提交，当前架构够用
2. PAI 面向慈善机构（非技术用户），Python + Streamlit 更易部署
3. 专利保护的是算法（联邦因果推断），不是实现语言
4. 精力应集中在 EWA-Fed（产出论文）而非 PAI 工程升级

---

## 六、优先级排序（未来 6 周）

| 优先级 | 任务 | 预估 | 产出 |
|--------|------|------|------|
| **P0** | EWA-Fed 综述投 arXiv | 1天 | arXiv preprint |
| **P0** | conformity_detector.py | 1天 | TWC-FL-PROD v1.3.0 |
| **P0** | organoid-fl 集成 PrimitiveCodec + 端到端测试 | 2天 | 验证 EWA 在真实场景有效 |
| **P1** | EWA-Fed 实验：医疗 CV + 工业 CV | 5天 | 2 组实验数据 |
| **P1** | EWA-Fed 实验：医疗 NLP + 金融 NLP | 8天 | 2 组实验数据 |
| **P1** | EWA-Fed 研究论文撰写 | 5天 | CSCWD 2026 投稿 |
| **P2** | TWC-FL-PROD 模块统一（DINOv2/Grad-CAM/HNSW） | 3天 | 减少重复代码 |
| **P2** | embodied-fl 集成 PrimitiveCodec | 1天 | 第 3 个 EWA 验证场景 |
| **P3** | embroidery-agent Rust 后端集成 | 3天 | 补齐技术一致性 |
| **P3** | 联邦 CoT 研究启动 | — | Phase 2 储备 |

---

## 七、技术架构总览（更新版）

```
                        ┌─────────────────────────────────┐
                        │       TWC-FL-PROD (统一枢纽)      │
                        │  fl_engine │ audit_chain │ EWA   │
                        │  data_vault │ knowledge_hub │     │
                        │  primitive_codec │ bayesian    │
                        └──────────┬──────────────────────┘
                                   │ 共享模块
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼─────────┐ ┌──────▼──────┐ ┌───────────▼──────────┐
    │   CV 项目群        │ │  NLP 项目群  │ │   跨模态项目群        │
    │                   │ │             │ │                      │
    │ organoid-fl (医疗) │ │ FundFL (金融)│ │ embodied-fl (具身)   │
    │ defect-fl  (工业) │ │ PAI (慈善)   │ │ embroidery (刺绣)    │
    │ mural-rest (壁画) │ │ Reading-FL   │ │                      │
    │ medical-fl (医学) │ │             │ │                      │
    │                   │ │             │ │                      │
    │ 共享: DINOv2      │ │ 共享: FedAvg │ │ 共享: DINOv2+FL     │
    │       YOLOv11     │ │       HNSW   │ │       gRPC          │
    │       Grad-CAM    │ │       审计链  │ │       审计链         │
    │       HNSW        │ │             │ │                      │
    │       审计链       │ │             │ │                      │
    └───────────────────┘ └─────────────┘ └──────────────────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                        ┌──────────▼──────────────────────┐
                        │     EWA-Fed (原创创新层)         │
                        │  entropy_weighted_aggregator     │
                        │  primitive_codec                │
                        │  conformity_detector (待建)      │
                        │  → 综述 (arXiv) + 研究论文 (CSCWD)│
                        └─────────────────────────────────┘
                                   │
                        ┌──────────▼──────────────────────┐
                        │     Rust 基础设施层               │
                        │  gRPC │ HNSW │ 审计链 │ Axum     │
                        │  (embodied/mural/embroidery)     │
                        └─────────────────────────────────┘
```

---

## 八、关键数字

| 指标 | 4/20 | 4/27 | 5/1 |
|------|------|------|-----|
| 项目数 | 5 | 9 | 12 |
| 测试总数 | ~65 | ~300 | ~500+ |
| Rust 项目 | 1 | 3 | 4 |
| Streamlit App | 0 | 6 | 6 |
| 论文 | 1 (embodied-fl) | 1 | 2 (综述+研究论文进行中) |
| 专利交底书 | 0 | 3 | 3 |
| 引用文献 | — | — | 80 (EWA-Fed 综述) |

---

*Generated by 思怡 💡 | 2026-05-01*
