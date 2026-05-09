"""
模块C：Bayesian配方优化（Bayesian Optimizer）

功能：
    - P0 历史数据导入：建立初始Surrogate Model
    - P0 推荐实验批次：基于贝叶斯优化，推荐下一批3至5个候选配方
    - P1 实验结果回填：自动更新模型

使用纯NumPy实现高斯过程（GP），无PyTorch依赖，适合Streamlit Cloud。
"""
from __future__ import annotations

import math
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class OptimizeTarget(Enum):
    """优化目标类型。"""
    MINIMIZE = "minimize"  # 如 T50
    MAXIMIZE = "maximize"  # 如 CO_conv, HC_conv, NOx_conv


@dataclass
class CandidateFormula:
    """贝叶斯优化推荐的候选配方。"""
    composition: Dict[str, float]
    predicted_performance: Dict[str, float]
    uncertainty: Dict[str, float]  # 预测不确定性
    acquisition_score: float  # 采集函数值
    expected_improvement: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composition": self.composition,
            "predicted_performance": self.predicted_performance,
            "uncertainty": self.uncertainty,
            "acquisition_score": self.acquisition_score,
        }


@dataclass
class OptimizationResult:
    """优化结果。"""
    candidates: List[CandidateFormula]
    current_best: Dict[str, float]
    improvement_potential: float
    model_confidence: float
    num_observations: int


class GaussianProcess:
    """简化版高斯过程回归（纯NumPy实现）。

    使用RBF核 + 稳定Cholesky分解。
    """

    def __init__(self, length_scale: float = 1.0, noise: float = 1e-6):
        self.length_scale = length_scale
        self.noise = noise
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.alpha: Optional[np.ndarray] = None
        self.L: Optional[np.ndarray] = None
        self.K_inv: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        """训练GP模型。"""
        self.X_train = np.array(X, dtype=np.float64)
        self.y_train = np.array(y, dtype=np.float64)
        n = len(self.y_train)

        # RBF kernel matrix
        K = self._rbf_kernel(self.X_train, self.X_train) + self.noise * np.eye(n)

        # Stable Cholesky decomposition
        self.L = self._stable_cholesky(K)
        self.alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, self.y_train))
        self.K_inv = np.linalg.solve(self.L.T, np.linalg.solve(self.L, np.eye(n)))

    def predict(self, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """预测均值和标准差。

        Returns:
            (mean, std)
        """
        X_test = np.array(X_test, dtype=np.float64)
        K_s = self._rbf_kernel(X_test, self.X_train)
        K_ss = self._rbf_kernel(X_test, X_test)

        mu = K_s @ self.alpha
        v = np.linalg.solve(self.L, K_s.T)
        var = np.diag(K_ss) - np.sum(v ** 2, axis=0)
        std = np.sqrt(np.maximum(var, 1e-10))

        return mu, std

    def _rbf_kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        """RBF（平方指数）核。"""
        sq_dist = np.sum(X1 ** 2, axis=1, keepdims=True) - \
                  2 * X1 @ X2.T + np.sum(X2 ** 2, axis=1)
        return np.exp(-0.5 * sq_dist / (self.length_scale ** 2))

    @staticmethod
    def _stable_cholesky(A: np.ndarray, max_tries: int = 10) -> np.ndarray:
        """带抖动的稳定Cholesky分解。"""
        jitter = 1e-8
        for _ in range(max_tries):
            try:
                return np.linalg.cholesky(A + jitter * np.eye(len(A)))
            except np.linalg.LinAlgError:
                jitter *= 10
        # Fallback: use eigenvalue decomposition
        eigvals, eigvecs = np.linalg.eigh(A)
        eigvals = np.maximum(eigvals, 1e-8)
        return eigvecs @ np.diag(np.sqrt(eigvals)) @ eigvecs.T


class BayesianOptimizer:
    """贝叶斯配方优化器。

    Usage:
        optimizer = BayesianOptimizer()
        optimizer.add_observations(compositions, performances)
        result = optimizer.recommend_candidates(
            target="NOx_conv",
            mode="maximize",
            constraints={"CO_conv": (94, None), "HC_conv": (94, None)},
            n_candidates=5,
        )
    """

    def __init__(self, length_scale: float = 1.0):
        self.length_scale = length_scale
        self.observations: List[Dict[str, Any]] = []
        self.feature_names: List[str] = []
        self.target_name: str = ""
        self.gp: Optional[GaussianProcess] = None

    def add_observations(self, compositions: List[Dict[str, float]],
                         performances: List[Dict[str, float]]):
        """添加历史观测数据。"""
        for comp, perf in zip(compositions, performances):
            self.observations.append({"composition": comp, "performance": perf})

        # 自动推断特征名
        if not self.feature_names and self.observations:
            self.feature_names = sorted(self.observations[0]["composition"].keys())

    def add_single_observation(self, composition: Dict[str, float],
                               performance: Dict[str, float]):
        """添加单条实验结果（实验回填）。"""
        self.observations.append({"composition": composition, "performance": performance})
        if not self.feature_names:
            self.feature_names = sorted(composition.keys())

    def recommend_candidates(self, target: str, mode: str = "maximize",
                             n_candidates: int = 5,
                             constraints: Optional[Dict[str, Tuple[float, float]]] = None,
                             n_random: int = 1000) -> OptimizationResult:
        """推荐下一批候选配方。

        Args:
            target: 优化目标（如 "NOx_conv", "T50"）
            mode: "maximize" 或 "minimize"
            constraints: 约束条件，如 {"CO_conv": (94, None)} 表示 CO_conv >= 94
            n_candidates: 推荐候选数量
            n_random: 随机采样点数量（用于采集函数优化）

        Returns:
            OptimizationResult
        """
        if len(self.observations) < 3:
            return self._random_recommendation(target, mode, n_candidates)

        self.target_name = target
        opt_mode = OptimizeTarget.MAXIMIZE if mode == "maximize" else OptimizeTarget.MINIMIZE

        X_train, y_train = self._prepare_training_data(target)
        if X_train is None or len(X_train) < 3:
            return self._random_recommendation(target, mode, n_candidates)

        # 标准化
        X_mean, X_std = X_train.mean(axis=0), X_train.std(axis=0) + 1e-8
        y_mean, y_std = y_train.mean(), y_train.std() + 1e-8
        X_norm = (X_train - X_mean) / X_std
        y_norm = (y_train - y_mean) / y_std

        # 训练GP
        self.gp = GaussianProcess(length_scale=self.length_scale)
        self.gp.fit(X_norm, y_norm)

        # 生成候选点
        candidates = self._generate_candidates(
            X_mean, X_std, y_mean, y_std, y_norm, opt_mode, constraints, n_candidates, n_random
        )

        # 当前最优
        if opt_mode == OptimizeTarget.MAXIMIZE:
            best_val = float(y_train.max())
        else:
            best_val = float(y_train.min())

        # 模型置信度
        y_pred, y_std = self.gp.predict(X_norm)
        residuals = np.abs(y_norm - y_pred)
        confidence = float(1.0 - np.mean(residuals))

        return OptimizationResult(
            candidates=candidates,
            current_best={target: round(best_val, 2)},
            improvement_potential=round(float(candidates[0].acquisition_score) if candidates else 0, 4),
            model_confidence=round(confidence, 4),
            num_observations=len(self.observations),
        )

    def _prepare_training_data(self, target: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """准备GP训练数据。"""
        X_list, y_list = [], []
        for obs in self.observations:
            if target not in obs["performance"]:
                continue
            vec = [obs["composition"].get(f, 0.0) for f in self.feature_names]
            X_list.append(vec)
            y_list.append(obs["performance"][target])

        if not X_list:
            return None, None
        return np.array(X_list), np.array(y_list)

    def _generate_candidates(self, X_mean, X_std, y_mean, y_std, y_norm,
                             opt_mode, constraints, n_candidates, n_random):
        """生成候选配方。"""
        # 在训练数据范围内随机采样
        X_all = []
        for obs in self.observations:
            vec = [obs["composition"].get(f, 0.0) for f in self.feature_names]
            X_all.append(vec)
        X_all = np.array(X_all)

        # Sampling range: training data range ± 20% (handles zero-range features)
        X_min = X_all.min(axis=0)
        X_max = X_all.max(axis=0)
        X_range = X_max - X_min
        # For features with zero range, use ±1.0 as default
        X_range = np.where(X_range < 1e-10, 2.0, X_range)
        X_min = X_min - 0.2 * X_range
        X_max = X_max + 0.2 * X_range

        # 随机采样
        X_samples = np.random.uniform(X_min, X_max, size=(n_random, len(self.feature_names)))
        X_norm = (X_samples - X_mean) / X_std

        # GP预测
        y_pred, y_std_pred = self.gp.predict(X_norm)

        # 计算采集函数（Expected Improvement）
        if opt_mode == OptimizeTarget.MAXIMIZE:
            best_y = y_norm.max()
            ei = self._expected_improvement(y_pred, y_std_pred, best_y, maximize=True)
        else:
            best_y = y_norm.min()
            ei = self._expected_improvement(y_pred, y_std_pred, best_y, maximize=False)

        # 筛选满足约束的候选
        valid_indices = list(range(len(X_samples)))
        if constraints:
            valid_indices = self._apply_constraints(X_samples, constraints, valid_indices)

        if not valid_indices:
            # 无满足约束的候选，放宽约束返回top-k
            valid_indices = list(range(len(X_samples)))

        # 按采集函数排序
        valid_indices.sort(key=lambda i: ei[i], reverse=True)
        top_indices = valid_indices[:n_candidates]

        candidates = []
        for idx in top_indices:
            comp = {self.feature_names[j]: round(float(X_samples[idx, j]), 4)
                    for j in range(len(self.feature_names))}
            pred_perf = {self.target_name: round(float(y_pred[idx] * y_std + y_mean), 2)}
            unc = {self.target_name: round(float(y_std_pred[idx] * y_std), 2)}
            candidates.append(CandidateFormula(
                composition=comp,
                predicted_performance=pred_perf,
                uncertainty=unc,
                acquisition_score=round(float(ei[idx]), 4),
            ))

        return candidates

    def _apply_constraints(self, X_samples, constraints, indices):
        """Apply constraints to filter candidates."""
        if not isinstance(constraints, dict):
            return indices
        valid = []
        for idx in indices:
            ok = True
            for col, (lo, hi) in constraints.items():
                if col in self.feature_names:
                    j = self.feature_names.index(col)
                    val = X_samples[idx, j]
                    if lo is not None and val < lo:
                        ok = False
                    if hi is not None and val > hi:
                        ok = False
            if ok:
                valid.append(idx)
        return valid

    @staticmethod
    def _expected_improvement(mu, sigma, best_y, maximize=True):
        """计算Expected Improvement采集函数。"""
        try:
            from scipy.stats import norm as scipy_norm
            _phi = scipy_norm.cdf
            _pdf = scipy_norm.pdf
        except ImportError:
            # Pure NumPy fallback: standard normal CDF via error function
            _phi = lambda z: 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))
            _pdf = lambda z: np.exp(-0.5 * z ** 2) / math.sqrt(2.0 * math.pi)

        if maximize:
            improvement = mu - best_y
        else:
            improvement = best_y - mu

        with np.errstate(divide="ignore", invalid="ignore"):
            ei = improvement * _phi(improvement / (sigma + 1e-10)) + \
                 sigma * _pdf(improvement / (sigma + 1e-10))
        ei = np.where(sigma > 1e-10, ei, 0.0)
        return ei

    def _random_recommendation(self, target, mode, n_candidates):
        """数据不足时的随机推荐。"""
        features = self.feature_names or ["Pt", "Pd", "Rh"]
        candidates = []
        for _ in range(n_candidates):
            comp = {f: round(np.random.uniform(0.1, 5.0), 2) for f in features}
            candidates.append(CandidateFormula(
                composition=comp,
                predicted_performance={target: 0.0},
                uncertainty={target: 1.0},
                acquisition_score=0.0,
            ))
        return OptimizationResult(
            candidates=candidates,
            current_best={target: 0.0},
            improvement_potential=0.0,
            model_confidence=0.0,
            num_observations=len(self.observations),
        )
