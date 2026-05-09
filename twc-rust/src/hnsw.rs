//! twc_rust::hnsw — HNSW Vector Index
//!
//! Fast approximate nearest neighbor search using the `hnsw` crate.
//!
//! # Usage
//!
//! ```rust,ignore
//! use twc_rust::hnsw::HnswIndex;
//!
//! let mut index = HnswIndex::new(128, 10000, 200, 16);
//! index.insert("doc_1", &[0.1, 0.2, ...])?;
//! index.insert("doc_2", &[0.3, 0.4, ...])?;
//!
//! let results = index.search(&[0.15, 0.25, ...], 5)?;
//! ```

use anyhow::Result;

/// HNSW vector index for approximate nearest neighbor search.
///
/// Wraps the `hnsw` crate with string ID mapping.
pub struct HnswIndex {
    index: hnsw::Hnsw<f32, space::Euclidean>,
    dimension: usize,
    max_elements: usize,
    ids: Vec<String>,
}

impl HnswIndex {
    /// Create a new HNSW index.
    ///
    /// # Arguments
    /// * `dimension` - Vector dimensionality.
    /// * `max_elements` - Maximum number of vectors.
    /// * `ef_construction` - Build-time search width (higher = better quality, slower build).
    /// * `m` - Max connections per node (higher = better recall, more memory).
    pub fn new(dimension: usize, max_elements: usize, ef_construction: usize, m: usize) -> Self {
        let config = hnsw::Config {
            max_elements,
            ef_construction,
            m,
            ..Default::default()
        };
        let index = hnsw::Hnsw::new(config);
        Self {
            index,
            dimension,
            max_elements,
            ids: Vec::with_capacity(max_elements),
        }
    }

    /// Create with sensible defaults (ef_construction=200, m=16).
    pub fn with_defaults(dimension: usize) -> Self {
        Self::new(dimension, 10000, 200, 16)
    }

    /// Insert a vector with an associated ID.
    ///
    /// Returns error if dimension mismatch or index is full.
    pub fn insert(&mut self, id: &str, vector: &[f32]) -> Result<()> {
        assert_eq!(
            vector.len(), self.dimension,
            "Vector dimension mismatch: expected {}, got {}",
            self.dimension, vector.len()
        );
        if self.ids.len() >= self.max_elements {
            anyhow::bail!(
                "HNSW index full: {} / {} elements",
                self.ids.len(), self.max_elements
            );
        }
        self.ids.push(id.to_string());
        self.index.insert(vector.to_vec());
        Ok(())
    }

    /// Search for k nearest neighbors.
    ///
    /// # Arguments
    /// * `query` - Query vector (must match dimension).
    /// * `k` - Number of neighbors to return.
    /// * `ef_search` - Search-time beam width (higher = better recall, slower).
    ///
    /// Returns list of (id, distance) pairs, sorted by distance.
    pub fn search(&self, query: &[f32], k: usize, ef_search: usize) -> Result<Vec<(String, f32)>> {
        assert_eq!(
            query.len(), self.dimension,
            "Query dimension mismatch: expected {}, got {}",
            self.dimension, query.len()
        );
        let neighbors = self.index.search(query, ef_search, k);
        let results: Vec<(String, f32)> = neighbors
            .into_iter()
            .filter_map(|(idx, dist)| {
                self.ids.get(idx).map(|id| (id.clone(), dist))
            })
            .collect();
        Ok(results)
    }

    /// Number of vectors in the index.
    pub fn len(&self) -> usize {
        self.ids.len()
    }

    /// Check if index is empty.
    pub fn is_empty(&self) -> bool {
        self.ids.is_empty()
    }

    /// Get the vector dimension.
    pub fn dimension(&self) -> usize {
        self.dimension
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_insert_and_search() {
        let mut index = HnswIndex::new(3, 100, 16, 4);

        index.insert("a", &[1.0, 0.0, 0.0]).unwrap();
        index.insert("b", &[0.0, 1.0, 0.0]).unwrap();
        index.insert("c", &[0.0, 0.0, 1.0]).unwrap();

        assert_eq!(index.len(), 3);

        let results = index.search(&[0.9, 0.1, 0.0], 2, 50).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, "a"); // closest to [1,0,0]
    }

    #[test]
    fn test_dimension_mismatch() {
        let mut index = HnswIndex::new(3, 100, 16, 4);
        let result = std::panic::catch_unwind(|| {
            index.insert("x", &[1.0, 2.0]).unwrap();
        });
        assert!(result.is_err());
    }

    #[test]
    fn test_empty_search() {
        let index = HnswIndex::new(3, 100, 16, 4);
        assert!(index.is_empty());
    }

    #[test]
    fn test_with_defaults() {
        let index = HnswIndex::with_defaults(128);
        assert_eq!(index.dimension(), 128);
        assert!(index.is_empty());
    }
}
