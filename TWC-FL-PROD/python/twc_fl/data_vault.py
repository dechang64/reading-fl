"""
模块A：配方数据管理（Local Data Vault）

功能：
    - P0 配方数据导入：支持CSV/Excel/JSON格式，自动识别列类型
    - P0 配方数据脱敏：导出前自动脱敏，供FL参与时使用
    - P1 数据质量报告：自动检测异常值、缺失字段、数据分布
    - P1 配方相似度检索：基于特征向量的配方相似度匹配
"""
from __future__ import annotations

import sqlite3
import numpy as np
import pandas as pd
import json
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime


# ── TWC 配方标准列名 ──
TWC_COLUMNS = {
    # 贵金属载量 (g/L or g/ft³)
    "Pt": "platinum loading",
    "Pd": "palladium loading",
    "Rh": "rhodium loading",
    # 助剂 (wt%)
    "CeO2": "ceria loading",
    "ZrO2": "zirconia loading",
    "La2O3": "lanthana loading",
    "BaO": "baria loading",
    # 涂层参数
    "washcoat": "washcoat loading (g/L)",
    "cell_density": "cell density (cpsi)",
    "wall_thickness": "wall thickness (mil)",
    # 老化条件
    "aging_temp": "aging temperature (°C)",
    "aging_time": "aging time (h)",
    # 性能指标
    "CO_conv": "CO conversion (%)",
    "HC_conv": "HC conversion (%)",
    "NOx_conv": "NOx conversion (%)",
    "T50": "light-off temperature T50 (°C)",
    "T90": "light-off temperature T90 (°C)",
}

# 性能目标列
PERFORMANCE_COLS = ["CO_conv", "HC_conv", "NOx_conv", "T50", "T90"]

# 合规标准 (Euro 6d / China 6b)
COMPLIANCE_TARGETS = {
    "CO_conv": 94.0,
    "HC_conv": 94.0,
    "NOx_conv": 90.0,
}


@dataclass
class FormulaRecord:
    """单条配方记录。"""
    formula_id: str
    composition: Dict[str, float]  # 列名 → 值
    performance: Dict[str, float]  # 性能指标
    source: str = "manual"  # manual / experiment / literature
    created_at: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def feature_vector(self) -> np.ndarray:
        """Extract numeric feature vector (deterministic column order)."""
        vals = []
        for col in sorted(TWC_COLUMNS):
            if col in self.composition:
                vals.append(self.composition[col])
            elif col in self.performance:
                vals.append(self.performance[col])
            else:
                vals.append(0.0)
        return np.array(vals, dtype=np.float64)

    @property
    def is_compliant(self) -> bool:
        """检查是否满足排放合规标准。"""
        for metric, target in COMPLIANCE_TARGETS.items():
            val = self.performance.get(metric, 0)
            if val < target:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataQualityReport:
    """数据质量报告。"""
    total_records: int = 0
    missing_fields: Dict[str, int] = field(default_factory=dict)
    outlier_count: int = 0
    outlier_details: List[Dict[str, Any]] = field(default_factory=list)
    distribution_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    compliance_rate: float = 0.0
    warnings: List[str] = field(default_factory=list)


class DataVault:
    """配方数据管理器。

    Usage:
        vault = DataVault()
        vault.import_csv("formulas.csv")
        report = vault.quality_report()
        anonymized = vault.anonymize()
        similar = vault.search_similar(query_formula, top_k=5)
    """

    def __init__(self, db_path: str = "twc_formulas.db"):
        self.db_path = db_path
        self.records: List[FormulaRecord] = []
        self._db_conn = None
        self._init_db()

    def _init_db(self):
        conn = self._get_db()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS formulas (
                formula_id TEXT PRIMARY KEY,
                composition TEXT NOT NULL,
                performance TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_source ON formulas(source);
        """)

    # ── P0: 数据导入 ──

    def add_formula(self, composition: Dict[str, float],
                    performance: Optional[Dict[str, float]] = None,
                    source: str = "manual", tags: Optional[List[str]] = None) -> FormulaRecord:
        """添加单条配方记录。

        Args:
            composition: 成分字典，如 {"Pt": 1.5, "Pd": 0.5, "Rh": 0.1}
            performance: 性能指标字典，如 {"CO_conv": 95.2, "HC_conv": 93.1}
            source: 数据来源
            tags: 标签列表

        Returns:
            创建的 FormulaRecord
        """
        idx = len(self.records)
        formula_id = f"F-{hashlib.sha256(f'{composition}{idx}'.encode()).hexdigest()[:12]}"
        record = FormulaRecord(
            formula_id=formula_id,
            composition=composition,
            performance=performance or {},
            source=source,
            tags=tags or [],
        )
        self.records.append(record)
        self._save_record(record)
        return record

    def import_csv(self, file_path: str, source: str = "manual") -> Tuple[int, List[str]]:
        """Import CSV file with automatic column type detection.

        Returns:
            (import_count, warning_list)
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        df = pd.read_csv(file_path)
        return self._import_dataframe(df, source)

    def import_excel(self, file_path: str, sheet_name: str = "Sheet1",
                     source: str = "manual") -> Tuple[int, List[str]]:
        """Import Excel file."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return self._import_dataframe(df, source)

    def import_json(self, file_path: str, source: str = "manual") -> Tuple[int, List[str]]:
        """Import JSON file (array format)."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        with open(file_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            return 0, ["Invalid JSON format"]
        return self._import_dataframe(df, source)

    def _import_dataframe(self, df: pd.DataFrame, source: str) -> Tuple[int, List[str]]:
        """内部：从 DataFrame 导入。"""
        warnings = []
        count = 0

        # 标准化列名
        col_map = self._auto_map_columns(df.columns.tolist())
        if col_map:
            df = df.rename(columns=col_map)
            warnings.append(f"列名映射: {col_map}")

        # 分离成分列和性能列
        comp_cols = [c for c in df.columns if c in TWC_COLUMNS and c not in PERFORMANCE_COLS]
        perf_cols = [c for c in df.columns if c in PERFORMANCE_COLS]

        if not comp_cols:
            warnings.append("⚠️ 未识别到成分列，请检查列名")
        if not perf_cols:
            warnings.append("⚠️ 未识别到性能列 (CO_conv, HC_conv, NOx_conv, T50, T90)")

        for idx, row in df.iterrows():
            composition = {}
            performance = {}
            for c in comp_cols:
                val = self._to_float(row.get(c))
                if val is not None:
                    composition[c] = val
            for c in perf_cols:
                val = self._to_float(row.get(c))
                if val is not None:
                    performance[c] = val

            if not composition:
                continue

            formula_id = f"F-{hashlib.sha256(f'{composition}{idx}'.encode()).hexdigest()[:12]}"
            record = FormulaRecord(
                formula_id=formula_id,
                composition=composition,
                performance=performance,
                source=source,
            )
            self.records.append(record)
            self._save_record(record)
            count += 1

        return count, warnings

    def _auto_map_columns(self, columns: List[str]) -> Dict[str, str]:
        """自动映射常见列名变体到标准名。"""
        aliases = {
            "pt_loading": "Pt", "pt_load": "Pt", "platinum": "Pt", "Pt loading": "Pt",
            "pd_loading": "Pd", "pd_load": "Pd", "palladium": "Pd", "Pd loading": "Pd",
            "rh_loading": "Rh", "rh_load": "Rh", "rhodium": "Rh", "Rh loading": "Rh",
            "ceo2": "CeO2", "ceria": "CeO2", "CeO2 loading": "CeO2",
            "zro2": "ZrO2", "zirconia": "ZrO2",
            "co_conversion": "CO_conv", "CO": "CO_conv", "co_conv": "CO_conv",
            "hc_conversion": "HC_conv", "HC": "HC_conv", "hc_conv": "HC_conv",
            "nox_conversion": "NOx_conv", "NOx": "NOx_conv", "nox_conv": "NOx_conv",
            "t50": "T50", "T50_temperature": "T50",
            "t90": "T90", "T90_temperature": "T90",
            "cell_density": "cell_density", "cpsi": "cell_density",
            "aging_temperature": "aging_temp", "aging_temp_c": "aging_temp",
        }
        mapping = {}
        for col in columns:
            key = col.strip().lower().replace(" ", "_")
            if key in aliases and aliases[key] not in columns:
                mapping[col] = aliases[key]
        return mapping

    @staticmethod
    def _to_float(val) -> Optional[float]:
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    def _get_db(self):
        """获取数据库连接（复用连接）。"""
        if self._db_conn is None:
            self._db_conn = sqlite3.connect(self.db_path)
            self._db_conn.execute("PRAGMA journal_mode=WAL")
        return self._db_conn

    def close(self):
        """关闭数据库连接。"""
        if self._db_conn is not None:
            self._db_conn.close()
            self._db_conn = None

    def _save_record(self, record: FormulaRecord):
        conn = self._get_db()
        conn.execute(
            "INSERT OR REPLACE INTO formulas VALUES (?, ?, ?, ?, ?, ?)",
            (record.formula_id, json.dumps(record.composition),
             json.dumps(record.performance), record.source,
             record.created_at, json.dumps(record.tags)),
        )
        conn.commit()

    def load_from_db(self):
        """从数据库加载所有记录。"""
        conn = self._get_db()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM formulas").fetchall()
        conn.row_factory = None
        self.records = [
            FormulaRecord(
                formula_id=r["formula_id"],
                composition=json.loads(r["composition"]),
                performance=json.loads(r["performance"]),
                source=r["source"],
                created_at=r["created_at"],
                tags=json.loads(r["tags"]),
            )
            for r in rows
        ]

    # ── P0: 数据脱敏 ──

    def anonymize(self, noise_scale: float = 0.05,
                  keep_performance: bool = False,
                  seed: Optional[int] = None) -> pd.DataFrame:
        """生成脱敏数据集用于 FL 训练。

        Args:
            noise_scale: 添加高斯噪声的标准差比例 (相对于列标准差)
            keep_performance: 是否保留性能指标（FL 预测目标需要）
            seed: 随机种子，保证可复现

        Returns:
            脱敏后的 DataFrame
        """
        if not self.records:
            return pd.DataFrame()

        rng = np.random.default_rng(seed)
        rows = []
        for rec in self.records:
            row = {}
            for k, v in rec.composition.items():
                # 添加噪声
                noise = rng.normal(0, max(abs(v) * noise_scale, 0.001))
                row[k] = round(v + noise, 4)
            if keep_performance:
                row.update(rec.performance)
            rows.append(row)

        return pd.DataFrame(rows)

    # ── P1: 数据质量报告 ──

    def quality_report(self) -> DataQualityReport:
        """生成数据质量报告。"""
        report = DataQualityReport(total_records=len(self.records))

        if not self.records:
            report.warnings.append("无数据记录")
            return report

        # 检查缺失字段
        all_cols = set(TWC_COLUMNS.keys())
        for col in all_cols:
            missing = sum(1 for r in self.records if col not in r.composition and col not in r.performance)
            if missing > 0:
                report.missing_fields[col] = missing

        # 统计分布
        for col in TWC_COLUMNS:
            vals = []
            for r in self.records:
                if col in r.composition:
                    vals.append(r.composition[col])
                elif col in r.performance:
                    vals.append(r.performance[col])
            if vals:
                arr = np.array(vals)
                report.distribution_stats[col] = {
                    "mean": float(np.mean(arr)),
                    "std": float(np.std(arr)),
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "median": float(np.median(arr)),
                }

        # 检测异常值 (IQR method)
        for col, stats in report.distribution_stats.items():
            vals = []
            for r in self.records:
                v = r.composition.get(col) if col in r.composition else r.performance.get(col)
                if v is not None:
                    vals.append(v)
            if len(vals) < 4:
                continue
            arr_vals = np.array(vals)
            q1 = np.percentile(arr_vals, 25)
            q3 = np.percentile(arr_vals, 75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            for r in self.records:
                val = r.composition.get(col) if col in r.composition else r.performance.get(col)
                if val is not None and (val < lower or val > upper):
                    report.outlier_count += 1
                    report.outlier_details.append({
                        "formula_id": r.formula_id, "column": col,
                        "value": val, "range": [round(lower, 2), round(upper, 2)],
                    })

        # 合规率
        compliant = sum(1 for r in self.records if r.is_compliant)
        report.compliance_rate = compliant / len(self.records) * 100 if self.records else 0

        # 警告
        if report.compliance_rate < 50:
            report.warnings.append(f"合规率仅 {report.compliance_rate:.1f}%，低于 50%")
        if report.outlier_count > len(self.records) * 0.1 and len(self.records) > 0:
            report.warnings.append(f"异常值占比 {report.outlier_count/len(self.records)*100:.1f}%，建议检查")

        return report

    # ── P1: 配方相似度检索 ──

    def search_similar(self, query: FormulaRecord, top_k: int = 5,
                       metric: str = "cosine") -> List[Tuple[FormulaRecord, float]]:
        """基于特征向量的配方相似度检索。

        Args:
            query: 查询配方
            top_k: 返回最相似的 k 个
            metric: "cosine" 或 "euclidean"

        Returns:
            [(配方, 相似度分数), ...] 按相似度降序
        """
        if not self.records:
            return []

        # Accept both FormulaRecord and dict
        if isinstance(query, dict):
            vals = []
            for col in sorted(TWC_COLUMNS):
                if col in query:
                    try:
                        vals.append(float(query[col]))
                    except (ValueError, TypeError):
                        vals.append(0.0)
                else:
                    vals.append(0.0)
            query_vec = np.array(vals, dtype=np.float64)
        else:
            query_vec = query.feature_vector
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        scored = []
        for rec in self.records:
            rec_vec = rec.feature_vector
            if metric == "cosine":
                rec_norm = np.linalg.norm(rec_vec)
                if rec_norm == 0:
                    continue
                sim = float(np.dot(query_vec, rec_vec) / (query_norm * rec_norm))
            else:
                dist = float(np.linalg.norm(query_vec - rec_vec))
                sim = -dist  # 距离越小越相似
            scored.append((rec, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def to_dataframe(self) -> pd.DataFrame:
        """导出为 DataFrame。"""
        if not self.records:
            return pd.DataFrame()
        rows = []
        for r in self.records:
            row = {"formula_id": r.formula_id, "source": r.source, "compliant": r.is_compliant}
            row.update(r.composition)
            row.update(r.performance)
            rows.append(row)
        return pd.DataFrame(rows)
