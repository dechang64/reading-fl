# twc-rust

Shared Rust infrastructure for TWC federated learning projects.

## Architecture

```
Layer 0: twc-rust (this crate) — Rust native
Layer 1: twc-core — Python ML modules
Layer 2: Domain frameworks (organoid-fl, defect-fl, embodied-fl, etc.)
Layer 3: Applications (Streamlit apps, papers, products)
```

## Modules

### `audit` — Tamper-Evident Audit Chain

Two backends:
- **`MemoryAuditChain`**: In-memory VecDeque with optional file persistence
- **`SqliteAuditChain`**: SQLite-backed persistent chain (feature-gated)

Both implement the `AuditChain` trait:
```rust
use twc_rust::audit::{MemoryAuditChain, AuditChain};

let mut chain = MemoryAuditChain::new(1000);
chain.append("model_upload", Some("lab_a"), "resnet50 weights, 23MB")?;
chain.append("aggregation", None, "FedAvg, 5 clients")?;

assert!(chain.verify_chain()?);
assert_eq!(chain.len(), 3); // genesis + 2 operations
```

### `hnsw` — HNSW Vector Index

Fast approximate nearest neighbor search:
```rust
use twc_rust::hnsw::HnswIndex;

let mut index = HnswIndex::new(128, 10000, 200, 16);
index.insert("doc_1", &[0.1, 0.2, ...])?;
let results = index.search(&[0.15, 0.25, ...], 5, 50)?;
```

### `vector_db` — Vector Database

High-level vector database with metadata:
```rust
use twc_rust::vector_db::VectorDb;

let mut db = VectorDb::new(128);
db.insert("doc_1", &[0.1, 0.2, ...], Some(meta))?;
let results = db.search(&[0.15, 0.25, ...], 5)?;
```

## Features

| Feature | Default | Description |
|---------|---------|-------------|
| `sqlite` | ✅ | SQLite-backed audit chain |

## Dependencies

- `hnsw` + `space` — HNSW index
- `sha2` + `hex` — SHA-256 hashing
- `rusqlite` — SQLite (optional)
- `serde` + `serde_json` — Serialization
- `chrono` — Timestamps
- `anyhow` — Error handling

## Extracted From

| Module | Source Projects | Lines Saved |
|--------|----------------|-------------|
| `hnsw` | defect-fl, embodied-fl, fundfl, pcb-defect-fl, organoid-fl, mural-restoration | ~400 |
| `vector_db` | defect-fl, embodied-fl, fundfl, pcb-defect-fl | ~350 |
| `audit` | defect-fl, embodied-fl, fundfl, pcb-defect-fl, organoid-fl, mural-restoration | ~1000 |
| **Total** | | **~1750 lines deduplicated** |

## Cross-Verification

The audit chain hash algorithm is verified against `twc_core.audit.AuditEngine` (Python):
```bash
cd twc-rust && PYTHONPATH=../twc-core python3 tests/test_logic.py
# All 8 tests passed!
```
