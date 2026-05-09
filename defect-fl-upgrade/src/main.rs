# ── src/main.rs
use std::sync::Arc;
use tracing::info;
use tracing_subscriber;

mod task_registry;
mod fed_server;
mod contribution_tracker;
mod audit;
mod vector_db;
mod hnsw_index;
mod grpc_service;
mod rest_api;
mod web_dashboard;

use task_registry::TaskRegistry;
use fed_server::FedServer;
use contribution_tracker::ContributionTracker;
use vector_db::VectorDb;
use audit::AuditChain;
use rest_api::ApiState;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "defect_fl=info,tower_http=debug".parse().unwrap())
        )
        .init();

    info!("╔══════════════════════════════════════════════════╗");
    info!("║   Defect-FL v2.0.0                             ║");
    info!("║   PCB Defect Federated Detection Platform        ║");
    info!("║   + YOLOv11 + DINOv2 + SAM2 + Grad-CAM         ║");
    info!("╚══════════════════════════════════════════════════╝");

    let task_registry = Arc::new(TaskRegistry::new(std::path::Path::new("data/tasks.db"))?);
    info!("TaskRegistry initialized");

    let fed_server = Arc::new(FedServer::new(
        Arc::clone(&task_registry),
        Arc::clone(&task_registry),
        Arc::clone(&task_registry),
    ));
    info!("FedServer initialized");

    let contribution = Arc::new(ContributionTracker::new(std::path::Path::new("data/contributions.db"))?);
    info!("ContributionTracker initialized");

    let vector_db = Arc::new(std::sync::RwLock::new(VectorDb::new(768)));
    info!("VectorDb initialized (768-dim for DINOv2)");

    let audit = Arc::new(AuditChain::new(std::path::Path::new("data/audit.db"))?);
    info!("AuditChain initialized");

    let api_state = ApiState {
        task_registry: Arc::clone(&task_registry),
        fed_server: Arc::clone(&fed_server),
        contribution: Arc::clone(&contribution),
        vector_db: Arc::clone(&vector_db),
        audit: Arc::clone(&audit),
    };

    let rest_app = rest_api::create_router(api_state)
        .merge(web_dashboard::create_dashboard());
    let rest_listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
    let rest_server = axum::serve(rest_listener, rest_app);

    info!("REST server ready on 0.0.0.0:8080");
    info!("Web dashboard: http://0.0.0.0:8080");
    info!("");
    info!("Quick start:");
    info!("  1. cargo run                    # Start server");
    info!("  2. python python/sim/client.py  # Start factory client");
    info!("  3. Open http://localhost:8080   # View dashboard");
    info!("");

    Ok(rest_server.await?)
}
