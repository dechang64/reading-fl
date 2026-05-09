# ── src/fed_server.rs
use anyhow::Result;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tracing::info;

use crate::task_registry::TaskRegistry;
use crate::audit::AuditChain;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RoundState {
    pub round_num: i32,
    pub status: RoundStatus,
    pub target_task_id: String,
    pub participants: Vec<String>,
    pub updates_received: HashMap<String, ClientUpdate>,
    pub aggregation_weights: HashMap<String, f32>,
    pub global_loss: f64,
    pub started_at: String,
    pub completed_at: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
pub enum RoundStatus { Pending, Running, Aggregating, Completed, Failed }

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ClientUpdate {
    pub client_id: String,
    pub task_id: String,
    pub round_num: i32,
    pub num_samples: i32,
    pub local_loss: f64,
    pub local_accuracy: f32,
    pub num_defects_detected: i32,
    pub defect_breakdown: HashMap<String, i32>,
    pub weights_hash: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AggregationResult {
    pub round_num: i32,
    pub num_participants: usize,
    pub global_loss: f64,
    pub global_accuracy: f32,
    pub strategy: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GlobalModel {
    pub version: i32,
    pub round_num: i32,
    pub params_hash: String,
    pub accuracy: f32,
    pub loss: f64,
    pub num_participants_last_round: usize,
}

pub struct FedServer {
    current_round: Mutex<Option<RoundState>>,
    aggregation_history: Mutex<Vec<AggregationResult>>,
    task_registry: Arc<TaskRegistry>,
    task_matcher: Arc<TaskRegistry>,
    audit: Arc<AuditChain>,
    round_counter: Mutex<i32>,
}

impl FedServer {
    pub fn new(
        task_registry: Arc<TaskRegistry>,
        task_matcher: Arc<TaskRegistry>,
        audit: Arc<AuditChain>,
    ) -> Self {
        Self {
            current_round: Mutex::new(None),
            aggregation_history: Mutex::new(Vec::new()),
            task_registry,
            task_matcher,
            audit,
            round_counter: Mutex::new(0),
        }
    }

    pub fn start_round(&self, target_task_id: &str, participants: Vec<String>) -> Result<RoundState> {
        let mut counter = self.round_counter.lock().unwrap();
        *counter += 1;
        let round_num = *counter;

        let round = RoundState {
            round_num,
            status: RoundStatus::Running,
            target_task_id: target_task_id.to_string(),
            participants: participants.clone(),
            updates_received: HashMap::new(),
            aggregation_weights: HashMap::new(),
            global_loss: 0.0,
            started_at: chrono::Utc::now().to_rfc3339(),
            completed_at: None,
        };

        *self.current_round.lock().unwrap() = Some(round.clone());
        info!("Started FL round {} with {} participants", round_num, participants.len());
        Ok(round)
    }

    pub fn submit_update(&self, client_id: &str, update: ClientUpdate) -> Result<()> {
        let mut round = self.current_round.lock().unwrap();
        if let Some(ref mut r) = *round {
            r.updates_received.insert(client_id.to_string(), update);
            info!("Received update from {} for round {}", client_id, r.round_num);
        }
        Ok(())
    }

    pub fn aggregate(&self) -> Result<AggregationResult> {
        let mut round = self.current_round.lock().unwrap();
        let round = round.as_mut().ok_or_else(|| anyhow::anyhow!("No active round"))?;

        round.status = RoundStatus::Aggregating;
        let n = round.updates_received.len();
        if n == 0 {
            round.status = RoundStatus::Failed;
            return Err(anyhow::anyhow!("No updates received"));
        }

        let total_loss: f64 = round.updates_received.values().map(|u| u.local_loss).sum();
        let total_acc: f32 = round.updates_received.values().map(|u| u.local_accuracy).sum();

        let result = AggregationResult {
            round_num: round.round_num,
            num_participants: n,
            global_loss: total_loss / n as f64,
            global_accuracy: total_acc / n as f32,
            strategy: "fedavg".to_string(),
            timestamp: chrono::Utc::now().to_rfc3339(),
        };

        round.global_loss = result.global_loss;
        round.status = RoundStatus::Completed;
        round.completed_at = Some(chrono::Utc::now().to_rfc3339());

        self.aggregation_history.lock().unwrap().push(result.clone());
        info!("Completed round {}: loss={:.4f}, acc={:.4f}", result.round_num, result.global_loss, result.global_accuracy);
        Ok(result)
    }

    pub fn get_round(&self, round_id: i64) -> Result<Option<RoundState>> {
        let history = self.aggregation_history.lock().unwrap();
        Ok(history.iter().find(|r| r.round_num as i64 == round_id).map(|r| {
            RoundState {
                round_num: r.round_num, status: RoundStatus::Completed,
                target_task_id: String::new(), participants: vec![],
                updates_received: HashMap::new(), aggregation_weights: HashMap::new(),
                global_loss: r.global_loss, started_at: r.timestamp.clone(),
                completed_at: Some(r.timestamp.clone()),
            }
        }))
    }

    pub fn get_round_updates(&self, _round_id: i64) -> Vec<ClientUpdate> {
        vec![]
    }

    pub fn get_history(&self, limit: usize) -> Vec<AggregationResult> {
        let history = self.aggregation_history.lock().unwrap();
        history.iter().rev().take(limit).cloned().collect()
    }

    pub fn get_global_model(&self) -> Result<GlobalModel> {
        let round = self.current_round.lock().unwrap();
        let last_agg = self.aggregation_history.lock().unwrap().last().cloned();
        Ok(GlobalModel {
            version: round.as_ref().map(|r| r.round_num).unwrap_or(0),
            round_num: round.as_ref().map(|r| r.round_num).unwrap_or(0),
            params_hash: last_agg.as_ref().map(|a| format!("agg_r{}", a.round_num)).unwrap_or_else(|| "init".to_string()),
            accuracy: last_agg.as_ref().map(|a| a.global_accuracy).unwrap_or(0.0),
            loss: last_agg.as_ref().map(|a| a.global_loss).unwrap_or(0.0),
            num_participants_last_round: last_agg.as_ref().map(|a| a.num_participants).unwrap_or(0),
        })
    }
}
