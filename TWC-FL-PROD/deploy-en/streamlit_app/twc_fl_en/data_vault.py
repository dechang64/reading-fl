"""
Module A: Formula Data Management (Local Data Vault)

Features:
    - P0 Formula data import: CSV/Excel/JSON with automatic column type detection
    - P0 Formula anonymization: automatic anonymization before FL participation
    - P1 Data quality report: outlier detection, missing field analysis, distribution stats
    - P1 Formula similarity search: feature-vector-based similarity matching
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


# ── TWC Formula Standard Column Names ──
TWC_COLUMNS = {
    # Precious metal loadings (g/L or g/ft³)
    "Pt": "platinum loading",
    "Pd": "palladium loading",
    "Rh": "rhodium loading",
    # Promoters (wt%)
    "CeO2": "ceria loading",
    "ZrO2": "zirconia loading",
    "La2O3": "lanthana loading",
    "BaO": "baria loading",
    # Washcoat parameters
    "washcoat": "washcoat loading (g/L)",
    "cell_density": "cell density (cpsi)",
    "wall_thickness": "wall thickness (mil)",
    # Aging conditions
    "aging_temp": "aging temperature (°C)",
    "aging_time": "aging time (h)",
    # Performance metrics
    "CO_conv": "CO conversion (%)",
    "HC_conv": "HC conversion (%)",
    "NOx_conv": "NOx conversion (%)",
    "T50": "light-off temperature T50 (°C)",
    "T90": "light-off temperature T90 (°C)",
}

# Performance target columns
PERFORMANCE_COLS = ["CO_conv", "HC_conv", "NOx_conv", "T50", "T90"]

# Compliance targets (Euro 6d / China 6b)
COMPLIANCE_TARGETS = {
    "CO_conv": 94.0,
    "HC_conv": 94.0,
    "NOx_conv": 90.0,
}


@dataclass
class FormulaRecord:
    """Single formula record."""
    formula_id: str
    composition: Dict[str, float]  # column name -> value
    performance: Dict[str, float]  # performance metrics
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
        """Check if emission compliance targets are met."""
        for metric, target in COMPLIANCE_TARGETS.items():
            val = self.performance.get(metric, 0)
            if val < target:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataQualityReport:
    """Data quality report."""
    total_records: int = 0
    missing_fields: Dict[str, int] = field(default_factory=dict)
    outlier_count: int = 0
    outlier_details: List[Dict[str, Any]] = field(default_factory=list)
    distribution_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    compliance_rate: float = 0.0
    warnings: List[str] = field(default_factory=list)


class DataVault:
    """Formula data manager.

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

    # ── P0: Data Import ──

    def add_formula(self, composition: Dict[str, float],
                    performance: Optional[Dict[str, float]] = None,
                    source: str = "manual", tags: Optional[List[str]] = None) -> FormulaRecord:
        """Add a single formula record.

        Args:
            composition: composition dict, e.g. {"Pt": 1.5, "Pd": 0.5, "Rh": 0.1}
            performance: performance dict, e.g. {"CO_conv": 95.2, "HC_conv": 93.1}
            source: data source
            tags: tag list

        Returns:
            Created FormulaRecord
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
        """Internal: import from DataFrame."""
        warnings = []
        count = 0

        # Normalize column names
        col_map = self._auto_map_columns(df.columns.tolist())
        if col_map:
            df = df.rename(columns=col_map)
            warnings.append(f"Column mapping: {col_map}")

        # Separate composition and performance columns
        comp_cols = [c for c in df.columns if c in TWC_COLUMNS and c not in PERFORMANCE_COLS]
        perf_cols = [c for c in df.columns if c in PERFORMANCE_COLS]

        if not comp_cols:
            warnings.append("WARNING: No composition columns detected, check column names")
        if not perf_cols:
            warnings.append("WARNING: No performance columns detected (CO_conv, HC_conv, NOx_conv, T50, T90)")

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
        """Auto-map common column name variants to standard names."""
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
        """Get database connection (reuse existing)."""
        if self._db_conn is None:
            self._db_conn = sqlite3.connect(self.db_path)
            self._db_conn.execute("PRAGMA journal_mode=WAL")
        return self._db_conn

    def close(self):
        """Close database connection."""
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
        """Load all records from database."""
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

    # ── P0: Data Anonymization ──

    def anonymize(self, noise_scale: float = 0.05,
                  keep_performance: bool = False,
                  seed: Optional[int] = None) -> pd.DataFrame:
        """Generate anonymized dataset for FL training.

        Args:
            noise_scale: Gaussian noise std ratio (relative to column std)
            keep_performance: whether to keep performance metrics (needed for FL prediction targets)
            seed: random seed for reproducibility

        Returns:
            Anonymized DataFrame
        """
        if not self.records:
            return pd.DataFrame()

        rng = np.random.default_rng(seed)
        rows = []
        for rec in self.records:
            row = {}
            for k, v in rec.composition.items():
                # Add noise
                noise = rng.normal(0, max(abs(v) * noise_scale, 0.001))
                row[k] = round(v + noise, 4)
            if keep_performance:
                row.update(rec.performance)
            rows.append(row)

        return pd.DataFrame(rows)

    # ── P1: Data Quality Report ──

    def quality_report(self) -> DataQualityReport:
        """Generate data quality report."""
        report = DataQualityReport(total_records=len(self.records))

        if not self.records:
            report.warnings.append("No data records")
            return report

        # Check missing fields
        all_cols = set(TWC_COLUMNS.keys())
        for col in all_cols:
            missing = sum(1 for r in self.records if col not in r.composition and col not in r.performance)
            if missing > 0:
                report.missing_fields[col] = missing

        # Distribution statistics
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

        # Detect outliers (IQR method)
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

        # Compliance rate
        compliant = sum(1 for r in self.records if r.is_compliant)
        report.compliance_rate = compliant / len(self.records) * 100 if self.records else 0

        # Warnings
        if report.compliance_rate < 50:
            report.warnings.append(f"Compliance rate only {report.compliance_rate:.1f}%, below 50%")
        if report.outlier_count > len(self.records) * 0.1 and len(self.records) > 0:
            report.warnings.append(f"Outlier ratio {report.outlier_count/len(self.records)*100:.1f}%, recommend review")

        return report

    # ── P1: Formula Similarity Search ──

    def search_similar(self, query: FormulaRecord, top_k: int = 5,
                       metric: str = "cosine") -> List[Tuple[FormulaRecord, float]]:
        """Feature-vector-based formula similarity search.

        Args:
            query: query formula
            top_k: return top-k most similar
            metric: "cosine" or "euclidean"

        Returns:
            [(formula, similarity_score), ...] sorted by similarity descending
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
                sim = -dist  # lower distance = higher similarity
            scored.append((rec, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def to_dataframe(self) -> pd.DataFrame:
        """Export as DataFrame."""
        if not self.records:
            return pd.DataFrame()
        rows = []
        for r in self.records:
            row = {"formula_id": r.formula_id, "source": r.source, "compliant": r.is_compliant}
            row.update(r.composition)
            row.update(r.performance)
            rows.append(row)
        return pd.DataFrame(rows)
