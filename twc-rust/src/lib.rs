//! twc-rust — Shared Rust Infrastructure for TWC Federated Learning Projects
//!
//! Layer 0: Rust native implementations shared across all TWC projects.
//!
//! Modules:
//!   - `audit`: Tamper-evident audit chain (SQLite or in-memory backend)
//!   - `hnsw`: HNSW vector index for approximate nearest neighbor search
//!   - `vector_db`: Vector database built on HNSW index
//!
//! Architecture:
//!   Layer 0: twc-rust (this crate) — Rust native
//!   Layer 1: twc-core — Python ML modules
//!   Layer 2: Domain frameworks (organoid-fl, defect-fl, etc.)
//!   Layer 3: Applications (Streamlit apps, papers, products)

pub mod audit;
pub mod hnsw;
pub mod vector_db;
