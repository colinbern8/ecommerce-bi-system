"""
Churn prediction model: feature preparation, LogisticRegression training, and evaluation plots.
Uses StandardScaler, train_test_split, and sklearn metrics.
"""

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


class ChurnPredictionModel:
    """
    Prepares churn features, trains a logistic regression model with class_weight='balanced',
    and provides evaluation plots and result persistence.
    """

    def __init__(self, output_dir: str = "reports") -> None:
        """
        Set output directory for saved plots and result file.

        Args:
            output_dir: Directory for outputs (relative to project root or absolute).
        """
        project_root = Path(__file__).resolve().parent.parent
        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = project_root / self.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scaler = StandardScaler()
        self.model: Optional[LogisticRegression] = None
        self.feature_names_: list[str] = []
        self._trained = False

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Select and derive churn features; add is_churned target.
        Expects columns: order_count_12m, revenue_12m, last_order_date, is_churned.
        Converts last_order_date to days_since_last_order for numeric use.

        Args:
            df: Churn features DataFrame from BusinessAnalytics.calculate_churn_features().

        Returns:
            DataFrame with numeric feature columns and is_churned.
        """
        if df.empty:
            return df
        out = df.copy()
        if "last_order_date" in out.columns:
            last = pd.to_datetime(out["last_order_date"], errors="coerce")
            ref = pd.Timestamp("now").normalize()
            out["days_since_last_order"] = (ref - last).dt.days
            out["days_since_last_order"] = out["days_since_last_order"].fillna(999).clip(0, 999)
        else:
            out["days_since_last_order"] = 999
        out["avg_order_value"] = out["revenue_12m"] / (out["order_count_12m"] + 1)
        out["log_revenue"] = np.log10(out["revenue_12m"] + 1)
        out["order_count_sq"] = out["order_count_12m"] ** 2
        out["recency_bucket"] = pd.cut(out["days_since_last_order"], bins=[-1, 30, 60, 90, 999], labels=[1, 2, 3, 4]).astype(float)
        out["is_high_value"] = (out["revenue_12m"] >= out["revenue_12m"].median()).astype(int)
        out["orders_per_month"] = out["order_count_12m"] / 12.0
        out["revenue_per_order"] = out["revenue_12m"] / (out["order_count_12m"] + 1)

        feature_cols = [
            "order_count_12m", "revenue_12m", "days_since_last_order",
            "avg_order_value", "log_revenue", "order_count_sq", "recency_bucket",
            "is_high_value", "orders_per_month",
        ]
        available = [c for c in feature_cols if c in out.columns]
        self.feature_names_ = available
        # Keep only rows with valid target
        out = out.dropna(subset=["is_churned"])
        return out

    def train_model(self, X: pd.DataFrame, y: pd.Series) -> LogisticRegression:
        """
        Fit StandardScaler and LogisticRegression with class_weight='balanced'.

        Args:
            X: Feature matrix (columns must match feature set used in prepare_features).
            y: Binary target (is_churned).

        Returns:
            Fitted LogisticRegression model.
        """
        self.feature_names_ = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)
        self.model = LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000)
        self.model.fit(X_scaled, y)
        self._trained = True
        return self.model

    def plot_feature_importance(self, save: bool = True) -> None:
        """
        Plot logistic regression coefficients as feature importance (bar chart).

        Args:
            save: If True, save PNG to output_dir.
        """
        if not self._trained or self.model is None:
            print("plot_feature_importance: model not trained, skipping")
            return
        coef = self.model.coef_[0]
        names = self.feature_names_
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(names, coef, color="steelblue", alpha=0.8)
        ax.set_xlabel("Coefficient")
        ax.set_title("Churn Model Feature Importance (Coefficients)")
        fig.tight_layout()
        if save:
            path = self.output_dir / "churn_feature_importance.png"
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def plot_confusion_matrix(self, confusion_mat: np.ndarray, save: bool = True) -> None:
        """
        Plot confusion matrix as heatmap.

        Args:
            confusion_mat: 2x2 confusion matrix (e.g. from sklearn.metrics.confusion_matrix).
            save: If True, save PNG to output_dir.
        """
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(
            confusion_mat,
            annot=True,
            fmt="d",
            cmap="Blues",
            ax=ax,
            xticklabels=["Not churned", "Churned"],
            yticklabels=["Not churned", "Churned"],
        )
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title("Churn Model Confusion Matrix")
        fig.tight_layout()
        if save:
            path = self.output_dir / "churn_confusion_matrix.png"
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def plot_roc_curve(
        self,
        y_test: np.ndarray,
        y_pred_proba: np.ndarray,
        roc_auc: float,
        save: bool = True,
    ) -> None:
        """
        Plot ROC curve with AUC in title.

        Args:
            y_test: True labels.
            y_pred_proba: Predicted probabilities for positive class (e.g. model.predict_proba(X)[:, 1]).
            roc_auc: AUC score.
            save: If True, save PNG to output_dir.
        """
        fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC (AUC = {roc_auc:.3f})")
        ax.plot([0, 1], [0, 1], color="navy", lw=1, linestyle="--")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title("Churn Model ROC Curve")
        ax.legend(loc="lower right")
        fig.tight_layout()
        if save:
            path = self.output_dir / "churn_roc_curve.png"
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")
        else:
            plt.show()

    def save_model_results(self, results: dict[str, Any], output_path: Optional[str] = None) -> Path:
        """
        Write model results (accuracy, report, etc.) to a text file.

        Args:
            results: Dict with keys such as accuracy, classification_report, confusion_matrix.
            output_path: Optional file path; default reports/churn_model_results.txt.

        Returns:
            Path to saved file.
        """
        if output_path is None:
            output_path = self.output_dir / "churn_model_results.txt"
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("Churn Model Results\n")
            f.write("=" * 50 + "\n")
            for k, v in results.items():
                f.write(f"\n{k}:\n{v}\n")
        print(f"Results saved: {path}")
        return path

    def train_and_evaluate(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Master method: prepare features, split, train, evaluate, and generate plots.

        Args:
            df: Churn features DataFrame from calculate_churn_features().

        Returns:
            Dict with accuracy, classification_report, confusion_matrix, roc_auc,
            y_test, y_pred_proba for optional use.
        """
        prepared = self.prepare_features(df)
        if prepared.empty or "is_churned" not in prepared.columns:
            print("train_and_evaluate: no valid data after prepare_features")
            return {}
        feature_cols = [c for c in self.feature_names_ if c in prepared.columns]
        if not feature_cols:
            feature_cols = [
                "order_count_12m", "revenue_12m", "days_since_last_order",
                "avg_order_value", "log_revenue", "order_count_sq", "recency_bucket",
                "is_high_value", "orders_per_month",
            ]
            feature_cols = [c for c in feature_cols if c in prepared.columns]
        if not feature_cols:
            print("train_and_evaluate: no feature columns found")
            return {}
        X = prepared[feature_cols].fillna(0)
        y = prepared["is_churned"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        self.train_model(X_train, y_train)
        X_test_scaled = self.scaler.transform(X_test)
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        cm = confusion_matrix(y_test, y_pred)
        acc = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0.0
        report = classification_report(y_test, y_pred, target_names=["Not churned", "Churned"])
        self.plot_feature_importance(save=True)
        self.plot_confusion_matrix(cm, save=True)
        self.plot_roc_curve(np.asarray(y_test), y_pred_proba, roc_auc, save=True)
        results = {
            "accuracy": acc,
            "roc_auc": roc_auc,
            "classification_report": report,
            "confusion_matrix": cm,
        }
        self.save_model_results(results)
        return results
