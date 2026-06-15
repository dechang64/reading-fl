# 一个 Rust 后端，驱动 15 个 AI 项目

> FedCtx — 联邦语义基础设施
> GitHub: github.com/dechang64/unified-fl-backend
> License: Apache-2.0

---

## 一句话

**数据不动，知识流动。** 一个 9.3MB 的 Rust 二进制文件，提供向量搜索、联邦聚合、审计链、知识图谱、记忆存储——你的 Python/Streamlit/React 前端直接调用，零外部依赖。

---

## 为什么需要 FedCtx？

你做联邦学习，用 Flower。做向量搜索，用 Milvus。做审计链，自己写。做知识图谱，用 Neo4j。做记忆，用 Redis。

**5 个服务，5 套运维，5 个故障点。**

FedCtx 把这些全部塞进一个二进制：

| 能力 | 实现 | 一行启动 |
|---|---|---|
| HNSW 向量搜索 | f64 精度，元数据过滤，upsert | `POST /api/search` |
| 联邦聚合 | FedAvg / FedProx / EWA + 差分隐私 | `POST /api/fl/aggregate` |
| 审计链 | SHA-256 + Ed25519 签名，防篡改 | `GET /api/audit` |
| 知识图谱 | 邻接索引 + BFS 遍历 | `POST /api/graph/nodes` |
| 记忆存储 | HNSW + 艾宾浩斯遗忘曲线 | `POST /api/memory/remember` |
| GraphRAG | 图谱 + 向量混合检索 | `POST /api/graphrag/query` |
| 混合检索 | 查询路由 + RRF 融合 + PageRank | `POST /api/hybrid-search` |

三种协议接入：**gRPC**（服务间）、**REST**（Web）、**MCP**（AI Agent）。

---

## 15 个项目，一套后端

FedCtx 不是为某个项目写的——它是从 15 个真实项目中提炼出来的公共基础设施。

### 🏥 医疗 × 生物

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **organoid-fl** | 类器官影像 FL | HNSW 影像检索 + FedAvg 聚合 + 审计链（医疗合规）+ KG（细胞-药物-基因图谱） |
| **medical-fl** | 医疗联邦学习 | FedAvg + 审计链（HIPAA 合规）+ HNSW（病例相似匹配） |
| **NeuroSync** | fMRI 预测建模 | HNSW（脑连接模式匹配）+ 审计链（医疗数据溯源） |

**为什么适合**：医疗数据不能出域——FedCtx 的联邦聚合 + 审计链天然满足合规要求。HNSW 让相似病例检索在本地完成，不泄露隐私。

### 🏭 工业 × 制造

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **PCB-Defect-FL** | PCB 缺陷检测 | HNSW（缺陷模式匹配）+ FedAvg（多产线协同）+ 审计链（质检合规） |
| **embroidery-agent** | 刺绣 AI Agent | HNSW（图案匹配）+ KG（针法-图案-风格图谱）+ 记忆存储（设计偏好） |
| **mural-restoration** | 壁画修复 | HNSW（损伤模式匹配）+ FedAvg（多博物馆协同）+ 审计链（文物溯源） |

**为什么适合**：工业场景需要跨工厂/跨机构协同训练，但数据不能外传。FedCtx 的 FedAvg + DP 让模型参数安全聚合，审计链保证每一步可追溯。

### 💰 金融 × 经济

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **FundFL** | 基金风险分析 | HNSW（基金相似匹配）+ FedAvg（多机构协同）+ PageRank（基金重要性）+ 审计链（金融合规） |
| **delta** | LLM Agent 股票预测 | HNSW（相似公告检索）+ PageRank（分析师影响力排序）+ 审计链（交易可追溯） |
| **monetary-policy-lab** | 货币政策研究 | HNSW（相似政策检索）+ KG（央行-政策-资产图谱）+ GraphRAG |
| **ewa-fed** | 熵加权聚合 | FedAvg/EWA 聚合（后端原生支持）+ 审计链（实验可复现） |

**为什么适合**：金融合规要求每笔操作可追溯——FedCtx 的审计链是刚需。PageRank 排序让"谁最重要"不再靠直觉。

### 🤖 具身智能 × 机器人

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **embodied-fl** | 具身智能 FL | HNSW（场景匹配）+ FedAvg（多机器人协同）+ KG（任务-环境-机器人图谱）+ PageRank |

**为什么适合**：不同机器人在不同环境，任务相似度决定聚合策略——HNSW 做任务匹配，KG 做环境图谱，FedAvg 做安全聚合。

### 📚 教育 × 阅读

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **reading-fl** | AI 读书会 | HNSW（读者匹配）+ FedAvg（多校区情感模型）+ KG（书-人-情感图谱）+ PageRank + 审计链 |

**为什么适合**：✅ **已完成集成**。817 行适配代码，零配置降级——FedCtx 不可用时自动回退本地 Python 实现。

### 🏛️ 技术转移 × 政策

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **suzhou-tt-research** | 苏州技术转移 OPC | HNSW（专利匹配）+ KG（供应链图谱）+ PageRank + 审计链 + 混合检索 |

**为什么适合**：✅ **已完成集成**。技术转移需要跨机构数据协同——FedCtx 让专利库、企业库、专家库在不出域的前提下实现语义检索和图谱发现。

### 🌸 社交 × 疗愈

| 项目 | 领域 | 用 FedCtx 做什么 |
|---|---|---|
| **dgy-treehole** | 心理疗愈平台 | HNSW（相似心情匹配）+ 记忆存储（对话记忆）+ 审计链（隐私保护） |

**为什么适合**：匿名社交的核心是"找到和你一样的人"——HNSW 做语义匹配，记忆存储让 AI 角色记住你，审计链保护隐私。

---

## 技术亮点

### 1. 零配置降级

```python
# Python 前端适配层（817 行，reading-fl 已验证）
from core.grpc_client import get_fedctx_client

client = get_fedctx_client()  # 自动检测 FedCtx 是否可用
if client.available:
    results = client.hybrid_search(query, query_vector, k=10)  # Rust 加速
else:
    results = local_hnsw.search(query_vector, k=10)  # 本地降级
```

FedCtx 挂了？你的应用不挂。

### 2. 单二进制，零依赖

```bash
cargo build --release
# 9.3MB，无外部服务，无 Docker 依赖
./fedctx --data-dir ./data
```

对比：Milvus (2GB+) + Neo4j (500MB+) + Redis (50MB) + 自写审计链 = **至少 3 个容器**。

### 3. 三协议接入

```
gRPC :50051  →  服务间高性能调用
REST  :8080  →  Web 前端 / Streamlit
MCP   stdio  →  Claude Desktop / Cursor / AI Agent
```

### 4. 审计即默认

每一次数据写入、每一次模型聚合、每一次图谱更新，都自动记录到 SHA-256 审计链。不是可选功能，是默认行为。

---

## 60 秒上手

```bash
# 1. 构建
git clone https://github.com/dechang64/unified-fl-backend.git
cd unified-fl-backend
cargo build --release

# 2. 启动
./target/release/fedctx --data-dir ./data

# 3. 插入向量
curl -X POST http://localhost:8080/api/vectors \
  -H "Content-Type: application/json" \
  -d '{"id": "test1", "values": [0.1, 0.2, 0.3], "metadata": {"type": "demo"}}'

# 4. 搜索
curl -X POST http://localhost:8080/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": [0.1, 0.2, 0.3], "k": 5}'

# 5. 查看审计链
curl http://localhost:8080/api/audit?limit=10
```

---

## 适用场景速查

| 你的场景 | 用 FedCtx 的哪个能力 |
|---|---|
| 跨机构协同训练，数据不能出域 | FedAvg/FedProx/EWA + DP |
| 语义检索 / 相似匹配 | HNSW 向量搜索 |
| 合规要求每步可追溯 | SHA-256 审计链 |
| "谁最重要"排序 | PageRank + 混合检索 |
| 领域关系发现 | 知识图谱 + GraphRAG |
| AI Agent 需要记忆 | 记忆存储（艾宾浩斯遗忘） |
| 多前端接入（Python/React/AI） | gRPC + REST + MCP |

---

## 项目数据

- **语言**：Rust 1.95（核心）+ Python（前端适配层）
- **测试**：60/60 通过，0 clippy 警告
- **体积**：9.3MB 单二进制
- **协议**：Apache-2.0
- **已集成项目**：reading-fl, suzhou-tt-research（817 行适配代码验证）
- **待集成项目**：organoid-fl, embodied-fl, PCB-Defect-FL, FundFL, delta, dgy-treehole 等 13 个

---

## 引用

```bibtex
@software{fedctx2026,
  title = {FedCtx: Federated Semantic Infrastructure},
  author = {Dechang Xu},
  year = {2026},
  url = {https://github.com/dechang64/unified-fl-backend}
}
```

---

*数据不动，知识流动。一个 Rust 后端，驱动你的联邦智能。*
