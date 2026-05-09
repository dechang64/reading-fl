//! twc_rust::vector_db — Vector Database
//!
//! High-level vector database built on HNSW index with metadata support.
//!
//! # Usage
//!
//! ```rust,ignore
//! use twc_rust::vector_db::VectorDb;
//!
//! let mut db = VectorDb::new(128);
//! db.insert("doc_1", &[0.1, 0.2, ...], Some(meta! {"source": "lab_a"}))?;
//!
//! let results = db.search(&[0.15, 0.25, ...], 5)?;
//! ```

use anyhow::Result;
use crate::hnsw::HnswIndex;
use std::collections::HashMap;

/// A search result with metadata.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub distance: f32,
    pub meta: HashMap<String, String>,
}

/// Vector database with HNSW index and metadata store.
pub struct VectorDb {
    index: HnswIndex,
    vectors: HashMap<String, Vec<f32>>,
    metadata: HashMap<String, HashMap<String, String>>,
}

impl VectorDb {
    /// Create a new vector database.
    ///
    /// # Arguments
    /// * `dimension` - Vector dimensionality.
    pub fn new(dimension: usize) -> Self {
        Self {
            index: HnswIndex::with_defaults(dimension),
            vectors: HashMap::new(),
            metadata: HashMap::new(),
        }
    }

    /// Insert or update a vector.
    ///
    /// If the ID already exists, the index is rebuilt.
    pub fn insert(
        &mut self,
        id: &str,
        vector: &[f32],
        meta: Option<HashMap<String, String>>,
    ) -> Result<()> {
        if self.vectors.contains_key(id) {
            // Update existing: rebuild index
            self.vectors.insert(id.to_string(), vector.to_vec());
            if let Some(m) = meta {
                self.metadata.insert(id.to_string(), m);
            }
            self.rebuild_index()?;
        } else {
            self.index.insert(id, vector)?;
            self.vectors.insert(id.to_string(), vector.to_vec());
            if let Some(m) = meta {
                self.metadata.insert(id.to_string(), m);
            }
        }
        Ok(())
    }

    /// Search for k nearest neighbors.
    pub fn search(&self, query: &[f32], k: usize) -> Result<Vec<SearchResult>> {
        let ef_search = std::cmp::max(k * 4, 50);
        let raw = self.index.search(query, k, ef_search)?;
        Ok(raw.into_iter().map(|(id, distance)| {
            let meta = self.metadata.get(&id).cloned().unwrap_or_default();
            SearchResult { id, distance, meta }
        }).collect())
    }

    /// Get a vector by ID.
    pub fn get(&self, id: &str) -> Option<&Vec<f32>> {
        self.vectors.get(id)
    }

    /// Delete a vector by ID (rebuilds index).
    pub fn delete(&mut self, id: &str) -> Result<bool> {
        if self.vectors.remove(id).is_some() {
            self.metadata.remove(id);
            self.rebuild_index()?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Number of vectors.
    pub fn len(&self) -> usize {
        self.vectors.len()
    }

    /// Check if empty.
    pub fn is_empty(&self) -> bool {
        self.vectors.is_empty()
    }

    fn rebuild_index(&mut self) -> Result<()> {
        let dimension = self.index.dimension();
        let mut new_index = HnswIndex::with_defaults(dimension);
        for (id, vector) in &self.vectors {
            new_index.insert(id, vector)?;
        }
        self.index = new_index;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_meta(key: &str, val: &str) -> HashMap<String, String> {
        let mut m = HashMap::new();
        m.insert(key.to_string(), val.to_string());
        m
    }

    #[test]
    fn test_insert_and_search() {
        let mut db = VectorDb::new(3);
        db.insert("a", &[1.0, 0.0, 0.0], Some(make_meta("source", "lab_a"))).unwrap();
        db.insert("b", &[0.0, 1.0, 0.0], Some(make_meta("source", "lab_b"))).unwrap();
        db.insert("c", &[0.0, 0.0, 1.0], None).unwrap();

        assert_eq!(db.len(), 3);

        let results = db.search(&[0.9, 0.1, 0.0], 2).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].id, "a");
        assert_eq!(results[0].meta.get("source").unwrap(), "lab_a");
    }

    #[test]
    fn test_update_existing() {
        let mut db = VectorDb::new(3);
        db.insert("a", &[1.0, 0.0, 0.0], None).unwrap();
        db.insert("a", &[0.0, 1.0, 0.0], Some(make_meta("v", "2"))).unwrap();

        assert_eq!(db.len(), 1);
        let results = db.search(&[0.0, 0.9, 0.0], 1).unwrap();
        assert_eq!(results[0].id, "a");
    }

    #[test]
    fn test_delete() {
        let mut db = VectorDb::new(3);
        db.insert("a", &[1.0, 0.0, 0.0], None).unwrap();
        db.insert("b", &[0.0, 1.0, 0.0], None).unwrap();

        assert!(db.delete("a").unwrap());
        assert_eq!(db.len(), 1);
        assert!(!db.delete("nonexistent").unwrap());
    }

    #[test]
    fn test_get() {
        let mut db = VectorDb::new(3);
        db.insert("a", &[1.0, 0.0, 0.0], None).unwrap();

        assert!(db.get("a").is_some());
        assert!(db.get("nonexistent").is_none());
    }
}
