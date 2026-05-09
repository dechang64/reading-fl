# EWA-Fed: Entropy-Weighted Aggregation for Federated Learning

[![Streamlit Cloud](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ewa-fed.streamlit.app)

**Paper Reproduction Dashboard** — Detecting conformity effects in Federated Learning via entropy-weighted class prototypes.

## What is EWA-Fed?

EWA-Fed is a **monitoring framework** (not a training algorithm) that detects whether minority expert knowledge is being suppressed by majority clients during Federated Learning training.

**Two-layer architecture:**
1. **Training Layer**: Standard FedAvg (unchanged)
2. **Monitoring Layer**: EWA analyzes structured primitives to detect conformity

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Live Demo

Deploy to Streamlit Cloud:
1. Push this repo to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy — no config needed

## Experiment Results (Real Data)

All experiments use **real datasets, real model training (PyTorch), and real softmax entropy** — no simulation.

| Task | Modality | Dataset | EWA Expert Wt | FedAvg Expert Wt | Δ (pp) |
|------|----------|---------|---------------|-----------------|--------|
| Medical CV | CV | Organoid-FL (600) | 89.9% ± 11.1% | 54.6% ± 1.7% | +35.3 |
| Financial NLP | NLP | Twitter Sentiment (9,543) | 74.9% ± 13.1% | 62.8% ± 10.5% | +12.1 |
| Medical NLP | NLP | PubMed QA (1,000) | 45.3% ± 8.5% | 38.6% ± 2.6% | +6.7 |
| **Average** | | | **70.0%** | **52.0%** | **+18.0** |

**Key finding**: EWA assigns experts 70.0% average weight share on specialty classes vs 52.0% under equal weighting (+18.0pp, 33.8% relative). Effect size correlates with task confidence — CV tasks with high accuracy show stronger EWA protection than harder NLP tasks.

## Repository Structure

```
ewa-fed/
├── app.py                  # Streamlit dashboard
├── requirements.txt        # Dependencies (numpy, streamlit, plotly)
├── README.md
├── ewa/
│   ├── __init__.py
│   ├── primitives.py       # Visual primitive encoding/decoding
│   ├── aggregator.py       # Entropy-weighted class prototype aggregation
│   ├── conformity.py       # Conformity detection across FL rounds
│   └── experiments.py      # Experiment configs + runner (simulated demo)
├── experiments/            # Real experiment scripts (require PyTorch)
│   ├── organoid_real.py    # Medical CV: DINOv2 + PCA features
│   ├── financial_real.py   # Financial NLP: Twitter + Sentence-Transformer
│   ├── medical_real.py     # Medical NLP: PubMed QA + Sentence-Transformer
│   └── aggregate_results.py
└── assets/
    └── sample_results.json # Pre-computed real results for dashboard
```

## Dependencies

**Dashboard (Streamlit Cloud):**
- **numpy** — Numerical computation
- **streamlit** — Dashboard UI
- **plotly** — Interactive charts

**Real experiments (local only):**
- **torch** — Model training
- **scikit-learn** — PCA, TF-IDF
- **sentence-transformers** — Text embeddings
- **datasets** — HuggingFace data loading

The dashboard uses pre-computed results and runs on Streamlit Cloud (pure NumPy). Real experiment scripts require PyTorch and are run locally.

## Citation

```bibtex
@article{ewa-fed-2026,
  title={EWA-Fed: Entropy-Weighted Aggregation for Trustworthy Federated Learning},
  author={},
  journal={},
  year={2026}
}
```

## License

MIT
