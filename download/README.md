# TWC-FL Platform

**Three-Way Catalyst Federated Learning Collaboration Platform**

Privacy-preserving collaborative optimization for automotive catalyst R&D. Enterprises train locally, share only model updates, and benefit from collective intelligence without exposing proprietary formulas.

![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Why

Catalyst manufacturers hold proprietary formula data (Pd/Pt/Rh loadings, conversion rates) they cannot share. But reducing Rhodium usage and meeting tighter emission standards demands cross-enterprise learning. TWC-FL solves this with **Federated Learning** — raw data never leaves the enterprise, only model updates are shared.

## Architecture

```
┌──────────────────────────────────────────────────┐
│              Streamlit Dashboard                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ DataVault│ │Knowledge │ │Bayesian  │         │
│  │          │ │  Hub     │ │Optimizer │         │
│  └────┬─────┘ └──────────┘ └────┬─────┘         │
│       │                          │                │
│       ▼                          ▼                │
│  ┌───────────────────────────────────────┐       │
│  │        FL Engine (FedAvg + DP)         │       │
│  └───────────────────────────────────────┘       │
└──────────────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
    │Client A │   │Client B │   │Client C │
    └─────────┘   └─────────┘   └─────────┘
```

## Modules

**💾 DataVault** — Formula data management with multi-format import (CSV/Excel/JSON), quality reports (outlier detection, distribution stats), similarity search, and Gaussian-noise anonymization for FL participation.

```python
from twc_fl import DataVault
vault = DataVault(":memory:")
vault.add_formula({"Pt": 1.5, "Pd": 2.0, "Rh": 0.1},
                  {"CO_conv": 95.0, "HC_conv": 93.0, "NOx_conv": 90.0})
report = vault.quality_report()
anon = vault.anonymize(seed=42, noise_scale=0.5)
```

**🎯 BayesianOptimizer** — Gaussian Process surrogate model with Expected Improvement acquisition. Supports constraint bounds on individual metal loadings and iterative active learning from experiment feedback.

```python
from twc_fl import BayesianOptimizer
opt = BayesianOptimizer()
opt.add_single_observation({"Pt": 1.5, "Pd": 2.0, "Rh": 0.1}, {"NOx_conv": 90.0})
result = opt.recommend_candidates("NOx_conv", "maximize", top_k=5)
```

**🌐 FLEngine** — Pure NumPy FedAvg with configurable Differential Privacy (Laplace mechanism). Multi-client simulation with per-round convergence tracking.

```python
from twc_fl import FLEngine, FLClient, FLConfig
engine = FLEngine(FLConfig(dp_epsilon=10.0, learning_rate=0.01))
engine.add_client(FLClient("c1", "Enterprise A", num_samples=200))
engine.add_client(FLClient("c2", "Enterprise B", num_samples=150))
history = engine.run_simulation(num_rounds=10)
```

**📚 KnowledgeHub** — Built-in domain knowledge: 20 FAQs covering formulation, aging, regulation, and FL topics, plus curated literature references on Pd-Rh catalysis and OSC materials.

```python
from twc_fl import KnowledgeHub
hub = KnowledgeHub()
results = hub.search("how to reduce Rh loading")
refs = hub.recommend_literature("Pd Rh catalyst")
```

**🔗 AuditChain** — SHA-256 hash chain for tamper-proof audit trail. Every data import, FL round, and formula change is recorded and verifiable.

```python
from twc_fl import AuditChain
chain = AuditChain()
chain.append("data_import", "user", {"count": 100})
assert chain.verify_chain()  # True
```

## Quick Start

```bash
git clone https://github.com/KaRROB/TWC-FL-Platform.git
cd TWC-FL-Platform
pip install -r requirements.txt
cd streamlitapp && streamlit run app.py
```

For **Streamlit Cloud**: push to GitHub, connect the repo, set entry point to `streamlitapp/app.py`.

Dependencies: `streamlit`, `numpy`, `pandas` — no PyTorch or TensorFlow needed.

## License

MIT
