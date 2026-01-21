"""
Fraud Detection ML Training Pipeline
=====================================
Azure ML pipeline for training fraud detection ensemble model
"""

import argparse
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

import joblib
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model, Environment
from azure.identity import DefaultAzureCredential
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    precision_recall_curve,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    average_precision_score
)
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import shap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    """Training configuration."""

    # Data paths
    DATA_PATH = os.getenv("DATA_PATH", "/mnt/data/transactions")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/mnt/outputs")

    # Model parameters
    ISOLATION_FOREST_PARAMS = {
        "n_estimators": 200,
        "contamination": 0.001,
        "max_samples": "auto",
        "random_state": 42,
        "n_jobs": -1
    }

    XGBOOST_PARAMS = {
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 500,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": 100,  # Handle class imbalance
        "random_state": 42,
        "n_jobs": -1,
        "early_stopping_rounds": 50
    }

    # Ensemble weights
    ENSEMBLE_WEIGHTS = {
        "isolation_forest": 0.30,
        "xgboost": 0.45,
        "neural_network": 0.25
    }

    # Evaluation thresholds
    TARGET_RECALL = 0.95
    MAX_FPR = 0.005


# ==============================================================================
# Feature Engineering
# ==============================================================================

class FeatureEngineer:
    """Feature engineering for fraud detection."""

    # Feature groups
    BASIC_FEATURES = [
        "amount", "currency_code", "merchant_category_code",
        "channel", "hour_of_day", "day_of_week", "is_weekend"
    ]

    VELOCITY_FEATURES = [
        "txn_count_1h", "txn_count_24h", "txn_count_7d",
        "amount_sum_1h", "amount_sum_24h", "amount_sum_7d",
        "unique_merchants_24h", "unique_countries_7d"
    ]

    BEHAVIORAL_FEATURES = [
        "amount_zscore", "time_since_last_txn_minutes",
        "distance_from_last_txn_km", "device_fingerprint_match",
        "typical_merchant_category", "typical_hour_deviation"
    ]

    CUSTOMER_FEATURES = [
        "account_age_days", "avg_transaction_amount",
        "credit_utilization", "risk_segment", "previous_fraud_count"
    ]

    GRAPH_FEATURES = [
        "shared_device_count", "account_link_score",
        "merchant_risk_score", "network_centrality"
    ]

    @classmethod
    def get_all_features(cls) -> List[str]:
        """Get all feature names."""
        return (
            cls.BASIC_FEATURES +
            cls.VELOCITY_FEATURES +
            cls.BEHAVIORAL_FEATURES +
            cls.CUSTOMER_FEATURES +
            cls.GRAPH_FEATURES
        )

    @staticmethod
    def compute_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute velocity features from transaction history."""

        # Sort by customer and timestamp
        df = df.sort_values(["customer_id", "transaction_timestamp"])

        # Group by customer
        grouped = df.groupby("customer_id")

        # Transaction counts
        df["txn_count_1h"] = grouped["transaction_id"].transform(
            lambda x: x.rolling("1H", on=df.loc[x.index, "transaction_timestamp"]).count()
        )
        df["txn_count_24h"] = grouped["transaction_id"].transform(
            lambda x: x.rolling("24H", on=df.loc[x.index, "transaction_timestamp"]).count()
        )

        # Amount sums
        df["amount_sum_1h"] = grouped["amount"].transform(
            lambda x: x.rolling("1H", on=df.loc[x.index, "transaction_timestamp"]).sum()
        )
        df["amount_sum_24h"] = grouped["amount"].transform(
            lambda x: x.rolling("24H", on=df.loc[x.index, "transaction_timestamp"]).sum()
        )

        return df

    @staticmethod
    def compute_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute behavioral deviation features."""

        # Amount z-score (deviation from customer's typical)
        customer_stats = df.groupby("customer_id")["amount"].agg(["mean", "std"])
        df = df.merge(customer_stats, on="customer_id", suffixes=("", "_customer"))
        df["amount_zscore"] = (df["amount"] - df["mean"]) / (df["std"] + 1e-6)

        # Time since last transaction
        df["time_since_last_txn_minutes"] = df.groupby("customer_id")[
            "transaction_timestamp"
        ].diff().dt.total_seconds() / 60

        return df


# ==============================================================================
# Model Training Classes
# ==============================================================================

class IsolationForestModel:
    """Isolation Forest for anomaly detection."""

    def __init__(self, params: Dict = None):
        self.params = params or Config.ISOLATION_FOREST_PARAMS
        self.model = IsolationForest(**self.params)
        self.scaler = StandardScaler()

    def fit(self, X: np.ndarray) -> "IsolationForestModel":
        """Fit the model on legitimate transactions only."""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        return self

    def predict_anomaly_score(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores (higher = more anomalous)."""
        X_scaled = self.scaler.transform(X)
        # Convert to 0-1 range where 1 is most anomalous
        raw_scores = -self.model.decision_function(X_scaled)
        # Normalize to 0-1
        scores = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-6)
        return scores

    def save(self, path: str):
        """Save model to disk."""
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "params": self.params
        }, path)

    @classmethod
    def load(cls, path: str) -> "IsolationForestModel":
        """Load model from disk."""
        data = joblib.load(path)
        instance = cls(data["params"])
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        return instance


class XGBoostFraudModel:
    """XGBoost classifier for fraud detection."""

    def __init__(self, params: Dict = None):
        self.params = params or Config.XGBOOST_PARAMS.copy()
        early_stopping = self.params.pop("early_stopping_rounds", 50)
        self.early_stopping_rounds = early_stopping
        self.model = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None
    ) -> "XGBoostFraudModel":
        """Train XGBoost model with early stopping."""

        self.model = xgb.XGBClassifier(**self.params)

        eval_set = [(X_train, y_train)]
        if X_val is not None:
            eval_set.append((X_val, y_val))

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=100
        )

        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return fraud probability."""
        return self.model.predict_proba(X)[:, 1]

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        return dict(zip(
            self.model.feature_names_in_,
            self.model.feature_importances_
        ))

    def save(self, path: str):
        """Save model to disk."""
        self.model.save_model(path)

    @classmethod
    def load(cls, path: str) -> "XGBoostFraudModel":
        """Load model from disk."""
        instance = cls()
        instance.model = xgb.XGBClassifier()
        instance.model.load_model(path)
        return instance


class FraudEnsemble:
    """Ensemble model combining multiple fraud detection models."""

    def __init__(
        self,
        isolation_forest: IsolationForestModel,
        xgboost_model: XGBoostFraudModel,
        weights: Dict[str, float] = None
    ):
        self.isolation_forest = isolation_forest
        self.xgboost_model = xgboost_model
        self.weights = weights or Config.ENSEMBLE_WEIGHTS
        self.threshold = 0.5  # Will be optimized

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        """
        Generate ensemble fraud risk score (0-100).

        Combines:
        - Isolation Forest anomaly score
        - XGBoost fraud probability
        - (Neural Network would be added here)
        """
        # Get individual model scores
        if_score = self.isolation_forest.predict_anomaly_score(X)
        xgb_score = self.xgboost_model.predict_proba(X)

        # Weighted combination (assuming no neural network for now)
        # Redistribute neural network weight
        total_weight = self.weights["isolation_forest"] + self.weights["xgboost"]
        if_weight = self.weights["isolation_forest"] / total_weight
        xgb_weight = self.weights["xgboost"] / total_weight

        ensemble_score = (if_weight * if_score) + (xgb_weight * xgb_score)

        # Scale to 0-100
        return ensemble_score * 100

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Binary prediction using optimized threshold."""
        scores = self.predict_score(X)
        return (scores >= self.threshold * 100).astype(int)

    def optimize_threshold(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
        target_recall: float = Config.TARGET_RECALL
    ) -> float:
        """
        Find threshold that achieves target recall while minimizing FPR.
        """
        scores = self.predict_score(X_val) / 100  # Normalize to 0-1

        precisions, recalls, thresholds = precision_recall_curve(y_val, scores)

        # Find threshold that achieves target recall
        valid_indices = np.where(recalls >= target_recall)[0]
        if len(valid_indices) == 0:
            logger.warning(f"Cannot achieve target recall {target_recall}")
            self.threshold = 0.5
        else:
            # Among thresholds that achieve target recall, pick one with best precision
            best_idx = valid_indices[np.argmax(precisions[valid_indices])]
            self.threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5

        logger.info(f"Optimized threshold: {self.threshold:.4f}")
        return self.threshold


# ==============================================================================
# Training Pipeline
# ==============================================================================

class FraudTrainingPipeline:
    """End-to-end training pipeline for fraud detection."""

    def __init__(self, experiment_name: str = "fraud-detection"):
        self.experiment_name = experiment_name
        self.feature_engineer = FeatureEngineer()
        self.models = {}
        self.metrics = {}

    def load_data(self, data_path: str) -> pd.DataFrame:
        """Load and prepare training data."""
        logger.info(f"Loading data from {data_path}")

        # Load transaction data (parquet format for efficiency)
        df = pd.read_parquet(data_path)

        logger.info(f"Loaded {len(df)} transactions")
        logger.info(f"Fraud rate: {df['is_fraud'].mean():.4%}")

        return df

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for training."""
        logger.info("Preparing features...")

        # Get feature columns
        feature_cols = self.feature_engineer.get_all_features()

        # Filter to available features
        available_features = [f for f in feature_cols if f in df.columns]
        logger.info(f"Using {len(available_features)} features")

        X = df[available_features].values
        y = df["is_fraud"].values

        return X, y, available_features

    def train(self, df: pd.DataFrame) -> Dict:
        """Train the fraud detection ensemble."""

        # Prepare features
        X, y, feature_names = self.prepare_features(df)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, stratify=y_train, random_state=42
        )

        logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

        with mlflow.start_run(run_name=f"fraud_training_{datetime.now().strftime('%Y%m%d_%H%M')}"):
            # Log parameters
            mlflow.log_params({
                "train_size": len(X_train),
                "val_size": len(X_val),
                "test_size": len(X_test),
                "n_features": len(feature_names),
                "fraud_rate_train": y_train.mean(),
                **Config.ISOLATION_FOREST_PARAMS,
                **{f"xgb_{k}": v for k, v in Config.XGBOOST_PARAMS.items()}
            })

            # Train Isolation Forest (on legitimate transactions only)
            logger.info("Training Isolation Forest...")
            X_train_legitimate = X_train[y_train == 0]
            if_model = IsolationForestModel()
            if_model.fit(X_train_legitimate)

            # Train XGBoost
            logger.info("Training XGBoost...")
            xgb_model = XGBoostFraudModel()
            xgb_model.fit(X_train, y_train, X_val, y_val)

            # Log feature importance
            importance = xgb_model.get_feature_importance()
            for feat, imp in sorted(importance.items(), key=lambda x: -x[1])[:20]:
                mlflow.log_metric(f"importance_{feat}", imp)

            # Create ensemble
            ensemble = FraudEnsemble(if_model, xgb_model)

            # Optimize threshold
            ensemble.optimize_threshold(X_val, y_val)

            # Evaluate on test set
            metrics = self.evaluate(ensemble, X_test, y_test)

            # Log metrics
            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value)

            # Log models
            if_model.save(os.path.join(Config.OUTPUT_PATH, "isolation_forest.joblib"))
            xgb_model.save(os.path.join(Config.OUTPUT_PATH, "xgboost_model.json"))

            mlflow.log_artifacts(Config.OUTPUT_PATH)

            # Store for later use
            self.models = {
                "isolation_forest": if_model,
                "xgboost": xgb_model,
                "ensemble": ensemble
            }
            self.metrics = metrics

            logger.info("Training complete!")
            logger.info(f"Metrics: {json.dumps(metrics, indent=2)}")

        return metrics

    def evaluate(
        self,
        model: FraudEnsemble,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """Evaluate model performance."""

        scores = model.predict_score(X_test) / 100
        predictions = model.predict(X_test)

        # Calculate metrics
        metrics = {
            "auc_roc": roc_auc_score(y_test, scores),
            "auc_pr": average_precision_score(y_test, scores),
            "precision": precision_score(y_test, predictions),
            "recall": recall_score(y_test, predictions),
            "f1": f1_score(y_test, predictions),
        }

        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()
        metrics["true_positive_rate"] = tp / (tp + fn) if (tp + fn) > 0 else 0
        metrics["false_positive_rate"] = fp / (fp + tn) if (fp + tn) > 0 else 0
        metrics["true_negatives"] = int(tn)
        metrics["false_positives"] = int(fp)
        metrics["false_negatives"] = int(fn)
        metrics["true_positives"] = int(tp)

        # Precision at target recall
        precisions, recalls, _ = precision_recall_curve(y_test, scores)
        idx = np.argmin(np.abs(recalls - Config.TARGET_RECALL))
        metrics["precision_at_95_recall"] = precisions[idx]

        return metrics

    def compute_shap_explanations(
        self,
        X: np.ndarray,
        feature_names: List[str],
        n_samples: int = 100
    ) -> np.ndarray:
        """Compute SHAP values for model explainability."""

        logger.info("Computing SHAP values...")

        # Use XGBoost model for SHAP (more interpretable)
        explainer = shap.TreeExplainer(self.models["xgboost"].model)

        # Sample if dataset is large
        if len(X) > n_samples:
            indices = np.random.choice(len(X), n_samples, replace=False)
            X_sample = X[indices]
        else:
            X_sample = X

        shap_values = explainer.shap_values(X_sample)

        return shap_values


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    """Main training entry point."""

    parser = argparse.ArgumentParser(description="Train fraud detection models")
    parser.add_argument("--data-path", type=str, required=True, help="Path to training data")
    parser.add_argument("--output-path", type=str, required=True, help="Path for model outputs")
    parser.add_argument("--experiment-name", type=str, default="fraud-detection")

    args = parser.parse_args()

    # Update config
    Config.DATA_PATH = args.data_path
    Config.OUTPUT_PATH = args.output_path

    # Create output directory
    os.makedirs(Config.OUTPUT_PATH, exist_ok=True)

    # Initialize MLflow
    mlflow.set_experiment(args.experiment_name)

    # Run training pipeline
    pipeline = FraudTrainingPipeline(args.experiment_name)
    df = pipeline.load_data(args.data_path)
    metrics = pipeline.train(df)

    # Save final metrics
    with open(os.path.join(Config.OUTPUT_PATH, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Training pipeline completed successfully!")


if __name__ == "__main__":
    main()
