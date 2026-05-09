# ── src/rest_api.rs
use std::sync::Arc;
use axum::{extract::State, http::StatusCode, response::Json, Router, routing::get};
use serde::Serialize;

use crate::task_registry::TaskRegistry;
use crate::fed_server::FedServer;
use crate::contribution_tracker::ContributionTracker;
use crate::vector_db::VectorDb;
use crate::audit::AuditChain;

#[derive(Clone)]
pub struct ApiState {
    pub task_registry: Arc<TaskRegistry>,
    pub fed_server: Arc<FedServer>,
    pub contribution: Arc<ContributionTracker>,
    pub vector_db: Arc<std::sync::RwLock<VectorDb>>,
    pub audit: Arc<AuditChain>,
}

#[derive(Serialize)]
struct ApiError { error: String }

pub fn create_router(state: ApiState) -> Router {
    Router::new()
        .route("/api/v1/health", get(health))
        .route("/api/v1/tasks", get(list_tasks))
        .route("/api/v1/rounds", get(list_rounds))
        .route("/api/v1/model", get(get_model))
        .route("/api/v1/audit", get(audit_logs))
        .route("/api/v1/audit/verify", get(audit_verify))
        .with_state(state)
}

async fn health(State(_s): State<ApiState>) -> Json<serde_json::Value> {
    Json(serde_json::json!({"status": "healthy", "service": "defect-fl", "version": "2.0.0"}))
}

async fn list_tasks(State(s): State<ApiState>) -> Result<Json<serde_json::Value>, (StatusCode, Json<ApiError>)> {
    let tasks = s.task_registry.list(None, None, 50).map_err(|e| err(&e))?;
    Ok(Json(serde_json::json!({"tasks": tasks})))
}

async fn list_rounds(State(s): State<ApiState>) -> Result<Json<serde_json::Value>, (StatusCode, Json<ApiError>)> {
    let rounds = s.fed_server.get_history(20).map_err(|e| err(&e))?;
    Ok(Json(serde_json::json!({"rounds": rounds})))
}

async fn get_model(State(s): State<ApiState>) -> Result<Json<serde_json::Value>, (StatusCode, Json<ApiError>)> {
    let model = s.fed_server.get_global_model().map_err(|e| err(&e))?;
    Ok(Json(serde_json::json!({"model": model})))
}

async fn audit_logs(State(s): State<ApiState>) -> Result<Json<serde_json::Value>, (StatusCode, Json<ApiError>)> {
    let logs = s.audit.get_recent(100, None).map_err(|e| err(&e))?;
    Ok(Json(serde_json::json!({"logs": logs})))
}

async fn audit_verify(State(s): State<ApiState>) -> Result<Json<serde_json::Value>, (StatusCode, Json<ApiError>)> {
    let (valid, length, hash) = s.audit.verify_chain().map_err(|e| err(&e))?;
    Ok(Json(serde_json::json!({"valid": valid, "chain_length": length, "latest_hash": hash})))
}

fn err(e: &anyhow::Error) -> (StatusCode, Json<ApiError>) {
    (StatusCode::INTERNAL_SERVER_ERROR, Json(ApiError { error: e.to_string() }))
}
