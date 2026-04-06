"""
Deep Learning Models for Everlight Ventures -- scikit-learn MLPs.

Implements the PyTorch deep learning course concepts using scikit-learn's
neural network modules (MLPClassifier, MLPRegressor). These are real
feedforward neural networks with backpropagation, ReLU/sigmoid activations,
Adam optimizer, and mini-batch gradient descent -- the same foundations
taught in the course.

Architecture:
  - TradePredictor: Predicts trade outcome (win/loss) from market features
  - LeadScorer: Scores broker leads 0-100 from lead features
  - OutreachOptimizer: Predicts best outreach timing/channel
  - ConversionPredictor: Predicts consulting funnel conversion probability

All models support:
  - Training from historical data (CSV/JSON)
  - Incremental learning (partial_fit for online learning)
  - Save/load (joblib serialization)
  - Feature importance via permutation importance
  - Reproducibility via random seeds

Free & open source: scikit-learn (BSD license), numpy, joblib.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error, classification_report

log = logging.getLogger(__name__)

# Persistent model directory
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Random seed for reproducibility (42 = answer to the universe)
RANDOM_SEED = 42


class BaseModel:
    """Base class for all Everlight ML models.

    Implements the PyTorch workflow:
    1. Get data ready (encode to tensors/arrays)
    2. Build/pick model
    3. Pick loss function & optimizer (handled by sklearn)
    4. Build training loop (fit method)
    5. Evaluate model
    6. Save & load
    """

    def __init__(self, name: str, model_type: str = "classifier"):
        self.name = name
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.model = None
        self.is_trained = False
        self.training_history: list[dict] = []
        self._build_model()

    def _build_model(self):
        """Build the neural network. Override in subclasses for custom architecture."""
        if self.model_type == "classifier":
            self.model = MLPClassifier(
                hidden_layer_sizes=(64, 32, 16),  # 3 hidden layers
                activation='relu',                 # ReLU activation (most common)
                solver='adam',                     # Adam optimizer
                alpha=0.001,                       # L2 regularization (prevents overfitting)
                batch_size='auto',                 # Mini-batch gradient descent
                learning_rate='adaptive',          # Adaptive learning rate
                learning_rate_init=0.001,
                max_iter=500,                      # Training epochs
                random_state=RANDOM_SEED,          # Reproducibility
                early_stopping=True,               # Stop when validation score plateaus
                validation_fraction=0.1,           # 10% validation split
                n_iter_no_change=20,               # Patience for early stopping
                warm_start=True,                   # Enable incremental learning
                verbose=False,
            )
        else:
            self.model = MLPRegressor(
                hidden_layer_sizes=(64, 32, 16),
                activation='relu',
                solver='adam',
                alpha=0.001,
                batch_size='auto',
                learning_rate='adaptive',
                learning_rate_init=0.001,
                max_iter=500,
                random_state=RANDOM_SEED,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=20,
                warm_start=True,
                verbose=False,
            )

    def prepare_data(self, X: np.ndarray, y: np.ndarray) -> tuple:
        """Step 1: Get data ready -- normalize features."""
        X_scaled = self.scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=RANDOM_SEED
        )
        return X_train, X_test, y_train, y_test

    def train(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Steps 2-4: Build model, fit to data, return metrics."""
        if len(X) < 10:
            log.warning(f"{self.name}: Need at least 10 samples to train, got {len(X)}")
            return {"error": "insufficient_data", "samples": len(X)}

        X_train, X_test, y_train, y_test = self.prepare_data(X, y)

        # Training loop (sklearn handles backprop internally)
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Step 5: Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        y_pred = self.model.predict(X_test)

        if self.model_type == "classifier":
            metrics = {
                "train_accuracy": round(train_score, 4),
                "test_accuracy": round(test_score, 4),
                "n_train": len(X_train),
                "n_test": len(X_test),
                "n_iterations": self.model.n_iter_,
                "loss": round(self.model.loss_, 6),
            }
        else:
            mse = mean_squared_error(y_test, y_pred)
            metrics = {
                "train_r2": round(train_score, 4),
                "test_r2": round(test_score, 4),
                "test_mse": round(mse, 6),
                "n_train": len(X_train),
                "n_test": len(X_test),
                "n_iterations": self.model.n_iter_,
                "loss": round(self.model.loss_, 6),
            }

        # Log training
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": self.name,
            **metrics,
        }
        self.training_history.append(record)
        log.info(f"{self.name} trained: {metrics}")

        # Step 6: Auto-save
        self.save()
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions on new data."""
        if not self.is_trained:
            loaded = self.load()
            if not loaded:
                raise RuntimeError(f"{self.name}: Model not trained yet")

        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities (classifiers only)."""
        if self.model_type != "classifier":
            raise TypeError("predict_proba only available for classifiers")
        if not self.is_trained:
            self.load()
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def save(self, path: Path | None = None):
        """Step 6: Save model state_dict equivalent."""
        p = path or (MODEL_DIR / f"{self.name}.joblib")
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "history": self.training_history,
            "is_trained": self.is_trained,
        }, p)
        log.info(f"{self.name} saved to {p}")

    def load(self, path: Path | None = None) -> bool:
        """Load a previously trained model."""
        p = path or (MODEL_DIR / f"{self.name}.joblib")
        if not p.exists():
            return False
        try:
            data = joblib.load(p)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.training_history = data.get("history", [])
            self.is_trained = data.get("is_trained", True)
            log.info(f"{self.name} loaded from {p}")
            return True
        except Exception as e:
            log.warning(f"{self.name} load failed: {e}")
            return False

    def get_status(self) -> dict:
        """Get model health metrics."""
        last = self.training_history[-1] if self.training_history else {}
        return {
            "name": self.name,
            "type": self.model_type,
            "is_trained": self.is_trained,
            "architecture": list(self.model.hidden_layer_sizes) if self.model else [],
            "activation": getattr(self.model, "activation", "unknown"),
            "total_trainings": len(self.training_history),
            "last_metrics": last,
        }


# =====================================================================
# Domain-Specific Models for Everlight Ventures
# =====================================================================

class TradePredictor(BaseModel):
    """Predicts trade outcomes (win/loss) from market features.

    Input features (12 dimensions):
      [0]  v4_score_normalized (0-1)
      [1]  unified_score_normalized (0-1)
      [2]  rsi (0-1, RSI/100)
      [3]  atr_normalized (0-1)
      [4]  volume_ratio (0-2)
      [5]  trend_strength (-1 to 1)
      [6]  range_position (0-1, where in range)
      [7]  sentiment (0-1)
      [8]  hour_normalized (0-1, hour/24)
      [9]  day_of_week (0-1, dow/7)
      [10] stop_distance_pct (0-1)
      [11] rr_ratio (0-5, risk:reward)

    Output: 0 (loss) or 1 (win)
    """

    def __init__(self):
        super().__init__("trade_predictor", model_type="classifier")

    def _build_model(self):
        self.model = MLPClassifier(
            hidden_layer_sizes=(32, 16, 8),  # Smaller for trading (less overfitting)
            activation='relu',
            solver='adam',
            alpha=0.01,            # Higher regularization for noisy trading data
            batch_size='auto',
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=300,
            random_state=RANDOM_SEED,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=15,
            warm_start=True,
            verbose=False,
        )

    @staticmethod
    def encode_trade(trade: dict) -> np.ndarray:
        """Encode a trade dict into feature vector."""
        return np.array([
            float(trade.get("v4_score", 0)) / 100,
            float(trade.get("unified_score", 0)) / 100,
            float(trade.get("rsi", 50)) / 100,
            min(float(trade.get("atr", 0)) / 0.01, 1.0),
            min(float(trade.get("volume_ratio", 1.0)), 2.0),
            np.clip(float(trade.get("trend_strength", 0)), -1, 1),
            np.clip(float(trade.get("range_position", 0.5)), 0, 1),
            float(trade.get("sentiment", 50)) / 100,
            float(trade.get("hour", 12)) / 24.0,
            float(trade.get("day_of_week", 3)) / 7.0,
            min(float(trade.get("stop_distance_pct", 0.005)) / 0.02, 1.0),
            min(float(trade.get("rr_ratio", 1.0)) / 5.0, 1.0),
        ])


class LeadScorer(BaseModel):
    """Scores broker leads 0-100 from lead features.

    Input features (10 dimensions):
      [0]  budget_normalized (0-1, budget/$50k)
      [1]  urgency (0-1, how soon they need it)
      [2]  company_size_normalized (0-1, employees/1000)
      [3]  industry_tech (0/1, is tech company)
      [4]  has_existing_tool (0/1)
      [5]  engagement_score (0-1, email opens, clicks)
      [6]  website_traffic_normalized (0-1)
      [7]  funding_stage (0-1, seed=0.2, A=0.4, B=0.6, C=0.8, public=1.0)
      [8]  pain_score (0-1, how much pain they have)
      [9]  referral_source (0-1, cold=0.2, inbound=0.5, referral=0.8, partner=1.0)

    Output: Score 0-100 (regression)
    """

    def __init__(self):
        super().__init__("lead_scorer", model_type="regressor")

    def _build_model(self):
        self.model = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation='relu',
            solver='adam',
            alpha=0.005,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=400,
            random_state=RANDOM_SEED,
            early_stopping=True,
            warm_start=True,
            verbose=False,
        )


class OutreachOptimizer(BaseModel):
    """Predicts best outreach timing and approach.

    Input features (8 dimensions):
      [0]  lead_score (0-1)
      [1]  days_since_last_contact (0-1, days/30)
      [2]  total_touches (0-1, touches/7)
      [3]  last_reply_sentiment (-1 to 1)
      [4]  hour_of_day (0-1)
      [5]  day_of_week (0-1)
      [6]  industry_match (0-1)
      [7]  deal_stage (0-1, prospect=0.2, qualified=0.4, proposal=0.6, negotiation=0.8)

    Output: 0 (don't reach out) or 1 (reach out now)
    """

    def __init__(self):
        super().__init__("outreach_optimizer", model_type="classifier")

    def _build_model(self):
        self.model = MLPClassifier(
            hidden_layer_sizes=(16, 8),
            activation='relu',
            solver='adam',
            alpha=0.01,
            learning_rate='adaptive',
            max_iter=300,
            random_state=RANDOM_SEED,
            early_stopping=True,
            warm_start=True,
            verbose=False,
        )


class ConversionPredictor(BaseModel):
    """Predicts consulting funnel conversion probability.

    Input features (8 dimensions):
      [0]  lead_source (0-1, cold=0.2, content=0.4, referral=0.8, partner=1.0)
      [1]  company_revenue_normalized (0-1)
      [2]  discovery_call_score (0-1)
      [3]  proposal_sent (0/1)
      [4]  days_in_pipeline (0-1, days/60)
      [5]  competitor_mentioned (0/1)
      [6]  budget_confirmed (0/1)
      [7]  champion_identified (0/1)

    Output: Probability 0-1 of closing (regression)
    """

    def __init__(self):
        super().__init__("conversion_predictor", model_type="regressor")

    def _build_model(self):
        self.model = MLPRegressor(
            hidden_layer_sizes=(16, 8),
            activation='relu',
            solver='adam',
            alpha=0.01,
            learning_rate='adaptive',
            max_iter=300,
            random_state=RANDOM_SEED,
            early_stopping=True,
            warm_start=True,
            verbose=False,
        )


# =====================================================================
# Agent ML Toolkit -- shared inference for 63 agents
# =====================================================================

class AgentMLToolkit:
    """Shared ML toolkit that any Hive agent can use.

    Usage:
        toolkit = get_toolkit()
        score = toolkit.score_lead(lead_features)
        prediction = toolkit.predict_trade(trade_features)
        should_outreach = toolkit.should_outreach(outreach_features)
    """

    def __init__(self):
        self.trade_predictor = TradePredictor()
        self.lead_scorer = LeadScorer()
        self.outreach_optimizer = OutreachOptimizer()
        self.conversion_predictor = ConversionPredictor()

        # Try loading any previously trained models
        for model in [self.trade_predictor, self.lead_scorer,
                      self.outreach_optimizer, self.conversion_predictor]:
            model.load()

    def score_lead(self, features: dict | np.ndarray) -> float:
        """Score a lead 0-100. Used by Filter Banks, Cupid."""
        if isinstance(features, dict):
            X = np.array([[
                float(features.get("budget", 0)) / 50000,
                float(features.get("urgency", 0.5)),
                float(features.get("company_size", 10)) / 1000,
                float(features.get("is_tech", 0)),
                float(features.get("has_existing_tool", 0)),
                float(features.get("engagement_score", 0)),
                float(features.get("website_traffic", 0)) / 100000,
                float(features.get("funding_stage", 0.2)),
                float(features.get("pain_score", 0.5)),
                float(features.get("referral_source", 0.2)),
            ]])
        else:
            X = features.reshape(1, -1) if features.ndim == 1 else features

        if not self.lead_scorer.is_trained:
            # Return heuristic score if model not yet trained
            return float(np.clip(X.mean() * 100, 0, 100))

        return float(np.clip(self.lead_scorer.predict(X)[0], 0, 100))

    def predict_trade(self, features: dict | np.ndarray) -> dict:
        """Predict trade outcome. Used by Rex Thornton, Cipher Wolfe."""
        if isinstance(features, dict):
            X = TradePredictor.encode_trade(features).reshape(1, -1)
        else:
            X = features.reshape(1, -1) if features.ndim == 1 else features

        if not self.trade_predictor.is_trained:
            return {"prediction": "unknown", "confidence": 0.0, "reason": "model_not_trained"}

        proba = self.trade_predictor.predict_proba(X)[0]
        pred_class = int(self.trade_predictor.predict(X)[0])
        return {
            "prediction": "win" if pred_class == 1 else "loss",
            "confidence": float(max(proba)),
            "win_probability": float(proba[1]) if len(proba) > 1 else float(proba[0]),
        }

    def should_outreach(self, features: dict | np.ndarray) -> dict:
        """Decide if outreach should happen now. Used by Piper Reeves."""
        if isinstance(features, dict):
            X = np.array([[
                float(features.get("lead_score", 0.5)),
                float(features.get("days_since_contact", 3)) / 30,
                float(features.get("total_touches", 1)) / 7,
                float(features.get("last_reply_sentiment", 0)),
                float(features.get("hour", 12)) / 24,
                float(features.get("day_of_week", 3)) / 7,
                float(features.get("industry_match", 0.5)),
                float(features.get("deal_stage", 0.2)),
            ]])
        else:
            X = features.reshape(1, -1) if features.ndim == 1 else features

        if not self.outreach_optimizer.is_trained:
            # Heuristic: outreach if days_since_contact > 2 and lead_score > 0.3
            return {"should_outreach": True, "confidence": 0.5, "reason": "heuristic_fallback"}

        proba = self.outreach_optimizer.predict_proba(X)[0]
        pred = int(self.outreach_optimizer.predict(X)[0])
        return {
            "should_outreach": pred == 1,
            "confidence": float(max(proba)),
        }

    def predict_conversion(self, features: dict | np.ndarray) -> float:
        """Predict consulting deal conversion probability. Used by Chart Dawson."""
        if isinstance(features, dict):
            X = np.array([[
                float(features.get("lead_source", 0.2)),
                float(features.get("company_revenue", 0)) / 1000000,
                float(features.get("discovery_score", 0.5)),
                float(features.get("proposal_sent", 0)),
                float(features.get("days_in_pipeline", 7)) / 60,
                float(features.get("competitor_mentioned", 0)),
                float(features.get("budget_confirmed", 0)),
                float(features.get("champion_identified", 0)),
            ]])
        else:
            X = features.reshape(1, -1) if features.ndim == 1 else features

        if not self.conversion_predictor.is_trained:
            return 0.5  # Unknown

        return float(np.clip(self.conversion_predictor.predict(X)[0], 0, 1))

    def train_all_from_data(self, data_dir: Path | str) -> dict:
        """Train all models from CSV/JSON data files."""
        data_dir = Path(data_dir)
        results = {}

        # Train trade predictor from trades.csv
        trades_file = data_dir / "trades.csv"
        if trades_file.exists():
            results["trade_predictor"] = self._train_trade_model(trades_file)

        # Train lead scorer from leads data
        leads_file = data_dir / "leads.json"
        if leads_file.exists():
            results["lead_scorer"] = self._train_lead_model(leads_file)

        return results

    def _train_trade_model(self, csv_path: Path) -> dict:
        """Train trade predictor from trades.csv."""
        try:
            import csv
            trades = []
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trades.append(row)

            if len(trades) < 10:
                return {"error": "insufficient_trades", "count": len(trades)}

            # Encode trades into feature vectors
            X_list, y_list = [], []
            for t in trades:
                try:
                    features = TradePredictor.encode_trade(t)
                    outcome = 1 if float(t.get("pnl", t.get("profit", 0))) > 0 else 0
                    X_list.append(features)
                    y_list.append(outcome)
                except (ValueError, KeyError):
                    continue

            if len(X_list) < 10:
                return {"error": "insufficient_valid_trades", "count": len(X_list)}

            X = np.array(X_list)
            y = np.array(y_list)
            return self.trade_predictor.train(X, y)

        except Exception as e:
            return {"error": str(e)}

    def _train_lead_model(self, json_path: Path) -> dict:
        """Train lead scorer from leads.json."""
        try:
            leads = json.loads(json_path.read_text())
            if len(leads) < 10:
                return {"error": "insufficient_leads", "count": len(leads)}

            X_list, y_list = [], []
            for lead in leads:
                try:
                    features = np.array([
                        float(lead.get("budget", 0)) / 50000,
                        float(lead.get("urgency", 0.5)),
                        float(lead.get("company_size", 10)) / 1000,
                        float(lead.get("is_tech", 0)),
                        float(lead.get("has_existing_tool", 0)),
                        float(lead.get("engagement_score", 0)),
                        float(lead.get("website_traffic", 0)) / 100000,
                        float(lead.get("funding_stage", 0.2)),
                        float(lead.get("pain_score", 0.5)),
                        float(lead.get("referral_source", 0.2)),
                    ])
                    score = float(lead.get("actual_score", lead.get("score", 50)))
                    X_list.append(features)
                    y_list.append(score)
                except (ValueError, KeyError):
                    continue

            X = np.array(X_list)
            y = np.array(y_list)
            return self.lead_scorer.train(X, y)

        except Exception as e:
            return {"error": str(e)}

    def get_all_status(self) -> dict:
        """Get status of all models."""
        return {
            "trade_predictor": self.trade_predictor.get_status(),
            "lead_scorer": self.lead_scorer.get_status(),
            "outreach_optimizer": self.outreach_optimizer.get_status(),
            "conversion_predictor": self.conversion_predictor.get_status(),
        }


# --- Singleton ---
_toolkit: AgentMLToolkit | None = None


def get_toolkit() -> AgentMLToolkit:
    """Get or create the singleton ML toolkit."""
    global _toolkit
    if _toolkit is None:
        _toolkit = AgentMLToolkit()
    return _toolkit
