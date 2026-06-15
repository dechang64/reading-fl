# FedPageIndex：联邦混合检索与知识图谱排序系统

## 技术方案 v1.0

> 日期：2026-06-15
> 作者：思怡 + 杨家小蠹
> 状态：Phase 1+2 已实现，47 测试全过

---

## 1. 核心洞察

PageIndex 号称"取代向量数据库"，实际上只取代了**结构化长文档的检索场景**。真正的机会不是替代，而是**混合**——把 PageIndex 的树推理检索、HNSW 的语义向量检索、知识图谱的关系推理、PageRank 的重要性排序四层叠加，再通过联邦学习实现跨客户端的知识聚合。

**学术空白**：目前没有人做过 PageIndex + HNSW 混合检索 + 联邦 PageRank on KG 的系统。

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                        查询入口                               │
│                  (Axum HTTP / gRPC)                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
               ┌───────▼───────┐
               │   查询路由器   │  LLM 判断查询类型 + 意图分解
               └───┬───────┬───┘
                   │       │
        ┌──────────▼┐ ┌────▼──────────┐
        │ PageIndex │ │    HNSW       │   混合检索层
        │  树搜索    │ │  向量检索      │
        │(结构推理)  │ │(语义相似)      │
        └─────┬─────┘ └─────┬─────────┘
              │             │
        ┌─────▼─────────────▼──────┐
        │  RRF 融合 + KG 重排序     │   融合排序层
        │  PageRank 分数加权        │
        └────────────┬─────────────┘
                     │
        ┌────────────▼─────────────┐
        │       知识图谱层          │   关系推理层
        │  实体/关系 → 三元组存储    │
        │  PageRank → 节点重要性    │
        │  子图检索 → 关联发现      │
        └────────────┬─────────────┘
                     │
        ┌────────────▼─────────────┐
        │       联邦学习层          │   隐私聚合层
        │  FedAvg 聚合 KG Embed    │
        │  联邦 PageRank 分数聚合   │
        │  差分隐私 + 梯度裁剪      │
        │  (Rust gRPC 通信)        │
        └──────────────────────────┘
```

---

## 3. 四层详解

### 3.1 混合检索层：PageIndex + HNSW

#### PageIndex 树搜索通道

PageIndex 的核心流程（源码分析）：

```
PDF → PyMuPDF/PyPDF2 提取页面文本
    → LLM 生成目录结构（title + physical_index）
    → LLM 验证标题是否出现在对应页面
    → 修正页码 → 构建层级树（structure 字段）
    → 每个节点：{node_id, title, summary, start_index, end_index, text}
    → 查询时：LLM Agent 调用 get_document_structure() → get_page_content()
```

**关键接口**（来自 `pageindex/client.py`）：

| 方法 | 输入 | 输出 | 用途 |
|------|------|------|------|
| `index(file_path)` | PDF/MD 路径 | doc_id | 构建树索引 |
| `get_document(doc_id)` | doc_id | 元数据 JSON | 文档概览 |
| `get_document_structure(doc_id)` | doc_id | 树结构 JSON（无 text） | 导航定位 |
| `get_page_content(doc_id, pages)` | doc_id + 页码范围 | 页面文本 JSON | 内容提取 |

**树结构示例**（来自 2023-annual-report）：

```json
{
  "title": "Monetary Policy and Economic Developments",
  "start_index": 9,
  "end_index": 9,
  "nodes": [
    {"title": "March 2024 Summary", "start_index": 9, "end_index": 14, "node_id": "0004"},
    {"title": "June 2023 Summary", "start_index": 15, "end_index": 20, "node_id": "0005"}
  ],
  "node_id": "0003"
}
```

**局限**：
- 每次查询需 LLM 推理（延迟 2-10s），不适合实时场景
- 只支持 PDF/MD，不支持图像/传感器数据
- 树索引质量依赖文档自身结构（无目录的文档效果差）

#### HNSW 向量检索通道

现有代码（`fundfl-upgrade/src/hnsw_index.rs`）：

```rust
pub struct HnswIndex {
    index: hnsw::Hnsw<f32, space::Euclidean>,
    dimension: usize,
    max_elements: usize,
    ids: Vec<String>,
}
// 核心方法：insert(id, vector), search(query, k, ef_search)
```

**优势**：语义相似搜索、跨文档检索、亚毫秒延迟
**局限**：分块策略影响质量、缺乏结构理解、无法精确定位页码

#### 混合策略：查询路由器

```python
def route_query(query: str) -> List[RetrievalChannel]:
    """LLM 判断查询走哪条通道"""
    # 结构化文档查询 → PageIndex
    #   例："2023年报中关于金融稳定的部分说了什么？"
    # 语义相似查询 → HNSW
    #   例："找所有跟联邦学习隐私保护相关的段落"
    # 混合查询 → 两者并行
    #   例："哪些专利跟这个技术最相似？它们的核心权利要求是什么？"
```

融合排序用 **RRF（Reciprocal Rank Fusion）**：

```
RRF_score(d) = Σ_{r∈R} 1 / (k + rank_r(d))    # k=60 典型值
```

### 3.2 知识图谱层

#### KG 构建

```
文档 → NER（命名实体识别）→ 实体
     → RE（关系抽取）→ 三元组 (head, relation, tail)
     → 实体对齐 → 跨文档实体合并
     → 存储为属性图
```

**专利领域 KG 示例**（对接省AI专班 Proposal）：

```
(专利A) --引用--> (专利B)
(专利A) --属于--> (技术领域: 联邦学习)
(专利A) --申请人--> (机构X)
(专利A) --发明人--> (张三)
(专利A) --相似--> (专利C)  [HNSW 语义相似度]
```

#### 存储选型

| 方案 | 优势 | 劣势 | 推荐 |
|------|------|------|------|
| Neo4j | 成熟、Cypher 查询、GDS 库内置 PageRank | Java 依赖重、部署复杂 | MVP 阶段 |
| Rust 原生图（petgraph） | 无外部依赖、性能极致 | 需自写 PageRank、无 Cypher | 生产阶段 |
| SQLite + 邻接表 | 最简单 | 无图查询能力 | 原型验证 |

**推荐**：MVP 用 Neo4j（快速验证），生产版用 Rust petgraph（性能+无依赖）。

### 3.3 PageRank 排序层

#### 标准 PageRank on KG

```
PR(v) = (1-d)/N + d × Σ_{u∈in(v)} PR(u) / |out(u)|
```

- d = 0.85（阻尼系数）
- N = 节点总数
- in(v) = 指向 v 的节点集合
- out(u) = u 指出的边集合

**在检索中的作用**：PageRank 分数作为 RRF 融合的权重因子——高 PageRank 的文档/实体在排序中提升。

#### 联邦 PageRank（核心创新点）

**问题**：各客户端有本地 KG 子图，不能共享原始三元组（隐私），但需要全局 PageRank 分数。

**方案**：

```
Round t:
  1. 各客户端 k 在本地 KG 上跑 PageRank → {PR_k(v) : v ∈ V_k}
  2. 上传：对共享节点 v，上传 PR_k(v) 和本地入边权重
  3. 服务器 FedAvg 聚合：
     PR_global(v) = Σ_k (n_k / N) × PR_k(v)    # n_k = 客户端k的样本数
  4. 下发 PR_global(v) 到各客户端
  5. 客户端用全局分数修正本地排序
```

**收敛性**：PageRank 本身是幂迭代法，联邦版等价于分布式 PageRank（Gleich et al., 2015），在连通图上收敛。需证明：FedAvg 聚合的 PageRank 分数等价于中心化 PageRank 的近似解。

**差分隐私**：上传 PR_k(v) 前加高斯噪声：

```
PR̃_k(v) = PR_k(v) + N(0, σ²)    # σ 由 (ε, δ)-DP 确定
```

### 3.4 联邦学习层

#### 复用现有基础设施

| 组件 | 现有代码 | 复用方式 |
|------|---------|---------|
| FedAvg 聚合 | 43个 Python 实现 + 2个 Rust 实现 | 扩展：聚合 KG embedding + PageRank 分数 |
| gRPC 通信 | tonic/prost 定义 | 新增 KG 相关 protobuf 消息 |
| HNSW 索引 | 4个 Rust 实现 | 直接复用，作为混合检索的向量通道 |
| 差分隐私 | twc-core 的 DP-SGD | 复用，保护 PageRank 分数上传 |
| 梯度裁剪 | 5处实现 | 复用，裁剪 KG embedding 梯度 |
| 区块链审计 | embodied-fl 的 audit chain | 记录 KG 更新/查询审计日志 |

#### 新增 Protobuf 消息

```protobuf
// 知识图谱相关消息
message KGTriplet {
    string head = 1;
    string relation = 2;
    string tail = 3;
    float confidence = 4;
}

message PageRankUpdate {
    string node_id = 1;
    float pr_score = 2;
    int32 local_samples = 3;
    float noise_sigma = 4;  // 差分隐私噪声
}

message KGEmbeddingUpdate {
    string node_id = 1;
    repeated float embedding = 2;  // TransE/TransR embedding
    int32 local_samples = 3;
}

message FedKGAgregateRequest {
    repeated PageRankUpdate pr_updates = 1;
    repeated KGEmbeddingUpdate embed_updates = 2;
    int32 client_id = 3;
    int32 round = 4;
}
```

---

## 4. 数据流：端到端示例

### 场景：专利检索

```
用户查询："找跟联邦学习差分隐私相关的核心专利"

1. 查询路由器判断：混合查询（语义 + 结构）
   → 并行触发 PageIndex + HNSW

2. PageIndex 通道：
   → LLM 在专利全文树索引上推理
   → 定位到"权利要求书"和"技术领域"章节
   → 返回：[专利A的claim 1-5, 专利B的claim 3-8]

3. HNSW 通道：
   → 查询向量 = embed("联邦学习差分隐私")
   → 返回：[专利A(0.92), 专利C(0.87), 专利D(0.85)]

4. RRF 融合：
   → 专利A: 1/(60+1) + 1/(60+1) = 0.033  (两条通道都命中)
   → 专利C: 0 + 1/(60+2) = 0.016
   → 专利D: 0 + 1/(60+3) = 0.016

5. KG 重排序：
   → KG 中专利A被12篇专利引用 → PageRank = 0.0045
   → KG 中专利C被3篇专利引用 → PageRank = 0.0012
   → 加权：专利A_score = 0.033 × (1 + α × 0.0045)
   → 专利A 进一步提升

6. 联邦聚合（后台）：
   → 客户端1（机构X的专利库）：本地 PageRank → 上传 PR̃_1(v)
   → 客户端2（机构Y的专利库）：本地 PageRank → 上传 PR̃_2(v)
   → 服务器 FedAvg → PR_global(v) → 下发 → 更新检索排序
```

---

## 5. 实施路线

### Phase 1：混合检索 MVP（2周）

**目标**：PageIndex + HNSW 混合检索 + RRF 融合

| 天 | 任务 | 产出 |
|----|------|------|
| 1-2 | PageIndex Python 集成测试 | 能索引 PDF 并查询 |
| 3-4 | HNSW Rust → Python FFI 桥接 | Python 可调用 HNSW search |
| 5-6 | 查询路由器（LLM 分类器） | 自动判断走哪条通道 |
| 7-8 | RRF 融合排序器 | 两路结果合并 |
| 9-10 | Axum HTTP API + 测试 | 可 curl 调用的混合检索服务 |

**技术栈**：Python（PageIndex）+ Rust（HNSW）+ PyO3 桥接

### Phase 2：知识图谱 + PageRank（2周）

**目标**：专利 KG 构建 + PageRank 排序 + 检索重排

| 天 | 任务 | 产出 |
|----|------|------|
| 1-3 | NER/RE 管线（LLM 抽取三元组） | 专利 → 三元组 |
| 4-5 | Neo4j 存储 + Cypher 查询 | KG 可查询 |
| 6-7 | PageRank 计算（Neo4j GDS） | 节点重要性分数 |
| 8-9 | PageRank 加权重排序 | 检索结果重排 |
| 10 | 端到端测试 | 专利检索 Demo |

**技术栈**：Python（NER/RE）+ Neo4j（KG + PageRank）

### Phase 3：联邦学习集成（3周）

**目标**：联邦 PageRank + 联邦 KG Embedding + 差分隐私

| 天 | 任务 | 产出 |
|----|------|------|
| 1-3 | Protobuf 定义 + gRPC 服务 | 联邦通信框架 |
| 4-6 | 联邦 PageRank 实现 | 多客户端 PageRank 聚合 |
| 7-9 | 联邦 KG Embedding（TransE） | 多客户端 Embedding 聚合 |
| 10-12 | 差分隐私 + 梯度裁剪 | 隐私保护 |
| 13-15 | 多客户端模拟 + 评估 | 联邦 vs 中心化对比 |

**技术栈**：Rust（gRPC 服务器）+ Python（客户端）+ PyTorch（KG Embedding）

### Phase 4：Rust 原生优化（2周）

**目标**：Neo4j → petgraph，Python PageIndex → Rust 重写

| 天 | 任务 | 产出 |
|----|------|------|
| 1-4 | Rust petgraph PageRank | 无 Neo4j 依赖 |
| 5-7 | Rust PageIndex 树构建器 | 无 Python 依赖 |
| 8-10 | 全链路性能测试 | 延迟/吞吐基准 |

---

## 6. 学术价值

### 可发论文的方向

| # | 方向 | 创新点 | 目标会议/期刊 |
|---|------|--------|--------------|
| 1 | 联邦 PageRank | FedAvg 聚合本地 PageRank 分数 + 收敛性证明 | AAAI / IJCAI |
| 2 | 混合检索（PageIndex + HNSW） | 树推理 + 向量检索 + RRF 融合 | SIGIR / WWW |
| 3 | 联邦 KG Embedding + DP | TransE/TransR 的联邦训练 + 差分隐私 | NeurIPS / ICML |
| 4 | 专利检索系统 | 端到端系统论文 | KDD Applied Data Science |

### 与省AI专班 Proposal 的对接

Proposal 中的四大 AI 引擎可以直接用 FedPageIndex 支撑：

| AI 引擎 | FedPageIndex 组件 |
|---------|------------------|
| 需求挖掘引擎 | PageIndex 解析企业需求文档 → HNSW 匹配技术方案 |
| 专利解析引擎 | PageIndex 解析专利全文 → KG 构建专利关系网 |
| 双端评级引擎 | PageRank 排出核心专利 → KTRS 评级输入 |
| 融资增信引擎 | 联邦聚合多机构数据 → 信用评分 |

---

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| PageIndex 查询延迟高（2-10s） | 用户体验差 | 异步预计算 + 缓存热门查询 + HNSW 快速通道兜底 |
| KG 构建质量依赖 NER/RE | 三元组噪声多 | LLM 抽取 + 人工校验 + 置信度过滤 |
| 联邦 PageRank 收敛性未证明 | 论文被审稿人质疑 | 先做实验验证，再补理论证明（参考分布式 PageRank 文献） |
| PageIndex 依赖 OpenAI API | 成本高、不可控 | LiteLLM 支持多模型切换，可用国产模型替代 |
| 专利数据获取 | 数据源受限 | 国家知识产权局公开 API + Google Patents |

---

## 8. 与现有代码的集成点

### 直接复用

```
fundfl-upgrade/src/hnsw_index.rs     → 混合检索的向量通道
defect-fl-upgrade/src/fed_server.rs  → gRPC 联邦通信框架
twc-core/twc_core/fl_engine.py       → FedAvg 聚合逻辑
twc-core/twc_core/ewa/aggregator.py  → 熵加权聚合（可扩展为 KG Embedding 聚合）
embodied-fl-upgrade/src/audit_chain  → KG 操作审计日志
```

### 需要新写

```
src/hybrid_retriever.rs    → 混合检索路由器 + RRF 融合
src/kg_builder.py          → NER/RE → 三元组抽取
src/pagerank.rs            → Rust 原生 PageRank（petgraph）
src/fed_pagerank.rs        → 联邦 PageRank 聚合
src/kg_embedding.py        → TransE/TransR 训练
src/query_router.py        → LLM 查询分类器
proto/fed_kg.proto         → 联邦 KG 通信协议
```

---

## 9. 命名

**FedPageIndex** — 联邦混合检索与知识图谱排序系统

- Fed = Federated（联邦学习）
- Page = PageIndex（树索引）+ PageRank（重要性排序）
- Index = 混合索引（树 + 向量 + 图）

---

## 附录 A：PageIndex 源码关键发现

1. **依赖极轻**：只需 litellm + PyPDF2 + pymupdf + pyyaml，无向量库依赖
2. **LLM 调用密集**：建索引时每个节点调 LLM 2-3 次（生成标题、验证页码、生成摘要），成本高
3. **树结构是 JSON**：`{node_id, title, summary, start_index, end_index, text, nodes[]}`，可直接映射为 KG 节点
4. **检索是 Agent 模式**：LLM 调用 `get_document_structure()` → `get_page_content()` 工具链，不是传统检索
5. **支持 Markdown**：`page_index_md.py` 处理 MD 文件，行号替代页码
6. **config.yaml 默认 gpt-4o**：可通过 LiteLLM 切换任意模型

## 附录 B：联邦 PageRank 数学推导（草案）

设全局图 G = ∪_k G_k，其中 G_k 是客户端 k 的本地子图。

**中心化 PageRank**：
$$PR(v) = \frac{1-d}{N} + d \sum_{u \in in(v)} \frac{PR(u)}{|out(u)|}$$

**联邦近似**：
$$\widetilde{PR}(v) = \sum_{k=1}^{K} \frac{n_k}{N} PR_k(v)$$

其中 $PR_k(v)$ 是客户端 k 在本地子图 $G_k$ 上的 PageRank 值。

**误差界**（待证明）：
$$\|\widetilde{PR} - PR\|_1 \leq \frac{d}{1-d} \cdot \frac{\sum_k |E_{cross,k}|}{|E|}$$

其中 $E_{cross,k}$ 是跨客户端的边（被截断的边），$E$ 是全局边集。

直觉：跨客户端边越少（数据越本地化），联邦近似越准确。

---

*本文档随项目进展持续更新。*
