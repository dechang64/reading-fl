# ── src/task_registry.rs
use anyhow::Result;
use rusqlite::{Connection, params};
use std::path::Path;
use std::sync::Mutex;
use chrono::Utc;

/// Factory task registry — manages PCB defect detection tasks per factory.
pub struct TaskRegistry {
    conn: Mutex<Connection>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Task {
    pub task_id: String,
    pub client_id: String,
    pub task_type: String,
    pub description: String,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
    pub rounds_participated: i32,
    pub total_contribution: f64,
    pub config_json: String,
}

impl TaskRegistry {
    pub fn new(db_path: &Path) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             CREATE TABLE IF NOT EXISTS tasks (
                 task_id TEXT PRIMARY KEY,
                 client_id TEXT NOT NULL,
                 task_type TEXT NOT NULL,
                 description TEXT DEFAULT '',
                 status TEXT DEFAULT 'active',
                 created_at TEXT NOT NULL,
                 updated_at TEXT NOT NULL,
                 rounds_participated INTEGER DEFAULT 0,
                 total_contribution REAL DEFAULT 0.0,
                 config_json TEXT DEFAULT '{}'
             );"
        )?;
        Ok(Self { conn: Mutex::new(conn) })
    }

    pub fn register(&self, task: Task) -> Result<Task> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO tasks (task_id, client_id, task_type, description, status, created_at, updated_at, rounds_participated, total_contribution, config_json) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            params![task.task_id, task.client_id, task.task_type, task.description, task.status, task.created_at, task.updated_at, task.rounds_participated, task.total_contribution, task.config_json],
        )?;
        Ok(task)
    }

    pub fn get(&self, task_id: &str) -> Result<Option<Task>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT task_id, client_id, task_type, description, status, created_at, updated_at, rounds_participated, total_contribution, config_json FROM tasks WHERE task_id = ?1")?;
        let task = stmt.query_row(params![task_id], |row| {
            Ok(Task {
                task_id: row.get(0)?, client_id: row.get(1)?, task_type: row.get(2)?,
                description: row.get(3)?, status: row.get(4)?, created_at: row.get(5)?,
                updated_at: row.get(6)?, rounds_participated: row.get(7)?,
                total_contribution: row.get(8)?, config_json: row.get(9)?,
            })
        }).optional()?;
        Ok(task)
    }

    pub fn list(&self, task_type: Option<&str>, status: Option<&str>, limit: i32) -> Result<Vec<Task>> {
        let conn = self.conn.lock().unwrap();
        let mut sql = String::from("SELECT task_id, client_id, task_type, description, status, created_at, updated_at, rounds_participated, total_contribution, config_json FROM tasks WHERE 1=1");
        if let Some(tt) = task_type { sql.push_str(&format!(" AND task_type = '{}'", tt)); }
        if let Some(s) = status { sql.push_str(&format!(" AND status = '{}'", s)); }
        sql.push_str(&format!(" ORDER BY total_contribution DESC LIMIT {}", limit));
        let mut stmt = conn.prepare(&sql)?;
        let tasks = stmt.query_map([], |row| {
            Ok(Task {
                task_id: row.get(0)?, client_id: row.get(1)?, task_type: row.get(2)?,
                description: row.get(3)?, status: row.get(4)?, created_at: row.get(5)?,
                updated_at: row.get(6)?, rounds_participated: row.get(7)?,
                total_contribution: row.get(8)?, config_json: row.get(9)?,
            })
        })?.collect::<Result<Vec<_>, _>>()?;
        Ok(tasks)
    }

    pub fn update_contribution(&self, task_id: &str, contribution: f64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE tasks SET total_contribution = total_contribution + ?1, rounds_participated = rounds_participated + 1, updated_at = ?2 WHERE task_id = ?3",
            params![contribution, Utc::now().to_rfc3339(), task_id],
        )?;
        Ok(())
    }

    pub fn stats(&self) -> Result<(i32, i32)> {
        let conn = self.conn.lock().unwrap();
        let total: i32 = conn.query_row("SELECT COUNT(*) FROM tasks", [], |r| r.get(0))?;
        let active: i32 = conn.query_row("SELECT COUNT(*) FROM tasks WHERE status = 'active'", [], |r| r.get(0))?;
        Ok((total, active))
    }
}
