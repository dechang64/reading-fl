# ── src/grpc_service.rs
use std::sync::Arc;
use tonic::{Request, Response, Status};
use tracing::info;

use crate::task_registry::TaskRegistry;
use crate::fed_server::FedServer;
use crate::contribution_tracker::ContributionTracker;
use crate::vector_db::VectorDb;
use crate::audit::AuditChain;

pub struct DefectFlService {
    pub task_registry: Arc<TaskRegistry>,
    pub fed_server: Arc<FedServer>,
    pub contribution: Arc<ContributionTracker>,
    pub vector_db: Arc<std::sync::RwLock<VectorDb>>,
    pub audit: Arc<AuditChain>,
}

impl DefectFlService {
    pub fn new(
        task_registry: Arc<TaskRegistry>,
        fed_server: Arc<FedServer>,
        contribution: Arc<ContributionTracker>,
        vector_db: Arc<std::sync::RwLock<VectorDb>>,
        audit: Arc<AuditChain>,
    ) -> Self {
        Self { task_registry, fed_server, contribution, vector_db, audit }
    }
}
