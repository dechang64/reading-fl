# ── src/web_dashboard.rs
use axum::{response::Html, routing::get, Router};

pub fn create_dashboard() -> Router {
    Router::new().route("/", get(index))
}

async fn index() -> Html<String> { Html(DASHBOARD_HTML.to_string()) }

const DASHBOARD_HTML: &str = r##"<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Defect-FL — PCB缺陷联邦检测平台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0e1a;color:#e2e8f0}
.container{max-width:1280px;margin:0 auto;padding:20px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid #1e293b;margin-bottom:24px}
h1{font-size:22px;color:#f59e0b}
h1 span{color:#64748b;font-size:13px;font-weight:normal;margin-left:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.stat{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:16px}
.stat .label{color:#64748b;font-size:12px;margin-bottom:4px}
.stat .value{font-size:24px;font-weight:700}
.card{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:20px;margin-bottom:16px}
.card h2{font-size:16px;margin-bottom:12px;color:#f59e0b}
table{width:100%;border-collapse:collapse}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #1e293b;font-size:13px}
th{color:#64748b;font-weight:500}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.badge-critical{background:#7f1d1d;color:#fca5a5}
.badge-moderate{background:#78350f;color:#fcd34d}
.badge-minor{background:#14532d;color:#86efac}
</style>
</head>
<body>
<div class="container">
<header>
<h1>⚡ Defect-FL <span>PCB缺陷联邦检测平台 v2.0</span></h1>
<div style="color:#64748b;font-size:13px">Rust + PyTorch + YOLOv11 + DINOv2</div>
</header>
<div class="stats" id="stats"></div>
<div class="card"><h2>📊 联邦训练轮次</h2><div id="rounds"></div></div>
<div class="card"><h2>🏭 工厂任务</h2><div id="tasks"></div></div>
</div>
<script>
fetch('/api/v1/health').then(r=>r.json()).then(d=>{
  document.getElementById('stats').innerHTML=`
    <div class="stat"><div class="label">Status</div><div class="value" style="color:#22c55e">${d.status}</div></div>
    <div class="stat"><div class="label">Version</div><div class="value">${d.version}</div></div>`;
});
fetch('/api/v1/rounds').then(r=>r.json()).then(d=>{
  if(d.rounds&&d.rounds.length>0){
    document.getElementById('rounds').innerHTML='<table><thead><tr><th>Round</th><th>Loss</th><th>Accuracy</th><th>Participants</th></tr></thead><tbody>'+
      d.rounds.map(r=>`<tr><td>${r.round_num}</td><td>${r.global_loss.toFixed(4)}</td><td>${(r.global_accuracy*100).toFixed(1)}%</td><td>${r.num_participants}</td></tr>`).join('')+'</tbody></table>';
  }
});
fetch('/api/v1/tasks').then(r=>r.json()).then(d=>{
  if(d.tasks&&d.tasks.length>0){
    document.getElementById('tasks').innerHTML='<table><thead><tr><th>Factory</th><th>Type</th><th>Status</th><th>Contribution</th></tr></thead><tbody>'+
      d.tasks.map(t=>`<tr><td>${t.client_id}</td><td>${t.task_type}</td><td>${t.status}</td><td>${t.total_contribution.toFixed(2)}</td></tr>`).join('')+'</tbody></table>';
  }
});
</script>
</body>
</html>"##;
