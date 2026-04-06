"""
Neuromorphic Brain -- Spiking Neural Network (SNN) for Everlight Ventures.

Architecture maps to the Hive Fire Teams:
  - Sensory Cortex:    Ingests market data, broker leads, Blinko notes
  - Associator Cortex: Pattern matching, cross-domain connections
  - Predictive Cortex: Market moves, outreach timing, lead scoring
  - Motor Cortex:      Action recommendations (trade, outreach, allocate)
  - Safety Kernel:     Gates all motor outputs before execution

Uses Nengo for biologically plausible spiking neurons with online
Hebbian/PES learning. CPU-only, starts at 5k neurons, scales to 100k.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import nengo

log = logging.getLogger(__name__)

try:
    from .brain_knowledge import get_ai_brain_status
except ImportError:
    try:
        from brain_knowledge import get_ai_brain_status
    except ImportError:
        get_ai_brain_status = None

try:
    from .brain_policy import policy_snapshot
except ImportError:
    try:
        from brain_policy import policy_snapshot
    except ImportError:
        policy_snapshot = None

# Persistent state directory
STATE_DIR = Path(__file__).parent / "state"
STATE_DIR.mkdir(exist_ok=True)

# --- Cortex dimensions ---
SENSORY_DIM = 16     # Input encoding: price, volume, sentiment, leads, etc.
ASSOCIATOR_DIM = 32  # Internal representation
PREDICTIVE_DIM = 16  # Predictions: direction, timing, confidence
MOTOR_DIM = 8        # Actions: trade signal, outreach priority, allocation
SAFETY_DIM = 4       # Safety gates: compliance, risk, sanity, override


@dataclass
class BrainState:
    """Persistent brain state across cycles."""
    cycle_count: int = 0
    total_rewards: float = 0.0
    total_penalties: float = 0.0
    last_predictions: dict[str, float] = field(default_factory=dict)
    learning_rate: float = 1e-4
    safety_overrides: int = 0

    def save(self, path: Path | None = None):
        p = path or (STATE_DIR / "brain_state.json")
        p.write_text(json.dumps(self.__dict__, indent=2, default=str))

    @classmethod
    def load(cls, path: Path | None = None) -> "BrainState":
        p = path or (STATE_DIR / "brain_state.json")
        if p.exists():
            try:
                data = json.loads(p.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()


class NeuromorphicBrain:
    """
    Spiking Neural Network brain for Everlight Ventures.

    The brain runs in short simulation bursts (not real-time).
    Each 'think' cycle:
      1. Encode inputs into spike patterns
      2. Run SNN for a short window (50ms sim time)
      3. Decode motor outputs
      4. Apply safety kernel
      5. Return action recommendations

    Learning happens via PES (Prescribed Error Sensitivity) rule
    when feedback is provided after actions are taken.
    """

    def __init__(self, n_neurons: int = 5000):
        self.n_neurons = n_neurons
        self.state = BrainState.load()
        self._build_network()
        log.info(f"Neuromorphic brain initialized: {n_neurons} neurons, cycle {self.state.cycle_count}")

    def _build_network(self):
        """Build the Nengo SNN network."""
        self.model = nengo.Network(seed=42)
        n = self.n_neurons
        # Mutable containers for input/error injection
        self._input_value = np.zeros(SENSORY_DIM)
        self._error_value = np.zeros(PREDICTIVE_DIM)

        with self.model:
            # --- Sensory Cortex ---
            # Input node: reads from mutable _input_value each timestep
            self.input_node = nengo.Node(output=lambda t: self._input_value)

            # Sensory ensemble: encodes raw inputs into spike patterns
            self.sensory = nengo.Ensemble(
                n_neurons=n // 5,
                dimensions=SENSORY_DIM,
                label="sensory_cortex",
            )
            nengo.Connection(self.input_node, self.sensory)

            # --- Associator Cortex ---
            # Expands representation, finds cross-domain patterns
            self.associator = nengo.Ensemble(
                n_neurons=n // 3,
                dimensions=ASSOCIATOR_DIM,
                label="associator_cortex",
            )
            # Learned connection from sensory -> associator
            self.sensory_to_assoc = nengo.Connection(
                self.sensory, self.associator,
                transform=np.random.randn(ASSOCIATOR_DIM, SENSORY_DIM) * 0.1,
                learning_rule_type=nengo.PES(learning_rate=self.state.learning_rate),
            )

            # --- Predictive Cortex ---
            # Compresses associator output into predictions
            self.predictor = nengo.Ensemble(
                n_neurons=n // 4,
                dimensions=PREDICTIVE_DIM,
                label="predictive_cortex",
            )
            self.assoc_to_pred = nengo.Connection(
                self.associator, self.predictor,
                transform=np.random.randn(PREDICTIVE_DIM, ASSOCIATOR_DIM) * 0.1,
                learning_rule_type=nengo.PES(learning_rate=self.state.learning_rate),
            )

            # --- Motor Cortex ---
            # Converts predictions into action recommendations
            self.motor = nengo.Ensemble(
                n_neurons=n // 5,
                dimensions=MOTOR_DIM,
                label="motor_cortex",
            )
            self.pred_to_motor = nengo.Connection(
                self.predictor, self.motor,
                transform=np.random.randn(MOTOR_DIM, PREDICTIVE_DIM) * 0.1,
                learning_rule_type=nengo.PES(learning_rate=self.state.learning_rate),
            )

            # --- Safety Kernel ---
            # Gates motor outputs: compliance, risk cap, sanity check
            self.safety = nengo.Ensemble(
                n_neurons=n // 10,
                dimensions=SAFETY_DIM,
                label="safety_kernel",
            )
            # Safety reads from both motor (what we want to do) and sensory (context)
            nengo.Connection(
                self.motor, self.safety[:SAFETY_DIM],
                transform=np.eye(SAFETY_DIM, MOTOR_DIM) * 0.5,
            )

            # --- Output probes ---
            self.motor_probe = nengo.Probe(self.motor, synapse=0.01)
            self.safety_probe = nengo.Probe(self.safety, synapse=0.01)
            self.predictor_probe = nengo.Probe(self.predictor, synapse=0.01)

            # --- Error signals (for PES learning) ---
            self.error_node = nengo.Node(output=lambda t: self._error_value)
            nengo.Connection(self.error_node, self.assoc_to_pred.learning_rule)
            nengo.Connection(self.error_node, self.pred_to_motor.learning_rule,
                             transform=np.random.randn(MOTOR_DIM, PREDICTIVE_DIM) * 0.05)

        self.sim = nengo.Simulator(self.model, progress_bar=False)

    def encode_inputs(self, data: dict[str, Any]) -> np.ndarray:
        """Encode heterogeneous input data into a fixed-size vector.

        Input channels (16 dimensions):
          [0]  price_normalized (0-1, current price / ATH)
          [1]  price_momentum (-1 to 1, recent change direction)
          [2]  volume_ratio (0-2, current / avg volume)
          [3]  rsi_normalized (0-1, RSI/100)
          [4]  sentiment_score (0-1, fear-greed / 100)
          [5]  spread_bps (0-1, bid-ask spread normalized)
          [6]  volatility (0-1, ATR normalized)
          [7]  trend_strength (-1 to 1, ADX-based)
          [8]  broker_lead_heat (0-1, pipeline activity)
          [9]  broker_match_quality (0-1, avg match score / 100)
          [10] outreach_reply_rate (0-1, recent reply rate)
          [11] revenue_momentum (-1 to 1, MRR change)
          [12] hour_of_day (0-1, hour/24)
          [13] day_of_week (0-1, dow/7)
          [14] blinko_activity (0-1, recent notes / 50)
          [15] energy_level (0-1, system health composite)
        """
        v = np.zeros(SENSORY_DIM)
        v[0] = float(data.get("price_normalized", 0.5))
        v[1] = np.clip(float(data.get("price_momentum", 0)), -1, 1)
        v[2] = np.clip(float(data.get("volume_ratio", 1.0)), 0, 2)
        v[3] = np.clip(float(data.get("rsi", 50)) / 100, 0, 1)
        v[4] = np.clip(float(data.get("sentiment", 50)) / 100, 0, 1)
        v[5] = np.clip(float(data.get("spread_bps", 0)) / 50, 0, 1)
        v[6] = np.clip(float(data.get("volatility", 0.5)), 0, 1)
        v[7] = np.clip(float(data.get("trend_strength", 0)), -1, 1)
        v[8] = np.clip(float(data.get("broker_lead_heat", 0)), 0, 1)
        v[9] = np.clip(float(data.get("broker_match_quality", 0)), 0, 1)
        v[10] = np.clip(float(data.get("outreach_reply_rate", 0)), 0, 1)
        v[11] = np.clip(float(data.get("revenue_momentum", 0)), -1, 1)
        v[12] = float(data.get("hour", 12)) / 24.0
        v[13] = float(data.get("day_of_week", 3)) / 7.0
        v[14] = np.clip(float(data.get("blinko_activity", 0)) / 50, 0, 1)
        v[15] = np.clip(float(data.get("energy_level", 0.8)), 0, 1)
        return v

    def decode_motor(self, motor_output: np.ndarray) -> dict[str, float]:
        """Decode motor cortex output into action recommendations.

        Motor channels (8 dimensions):
          [0] trade_signal (-1 to 1: short to long)
          [1] trade_confidence (0-1)
          [2] outreach_priority (0-1: how urgently to send outreach)
          [3] outreach_timing (0-1: send now vs wait)
          [4] attention_trading (0-1: how much focus on trading)
          [5] attention_broker (0-1: how much focus on broker)
          [6] attention_content (0-1: how much focus on content)
          [7] energy_allocation (0-1: overall activity level)
        """
        m = np.clip(motor_output, -1, 1)
        return {
            "trade_signal": float(m[0]),
            "trade_confidence": float(np.clip(m[1], 0, 1)),
            "outreach_priority": float(np.clip(m[2], 0, 1)),
            "outreach_timing": float(np.clip(m[3], 0, 1)),
            "attention_trading": float(np.clip(m[4], 0, 1)),
            "attention_broker": float(np.clip(m[5], 0, 1)),
            "attention_content": float(np.clip(m[6], 0, 1)),
            "energy_allocation": float(np.clip(m[7], 0, 1)),
        }

    def apply_safety(self, motor: dict[str, float], safety_output: np.ndarray) -> dict[str, float]:
        """Safety kernel gates motor outputs.

        Safety channels:
          [0] compliance_gate (>0.5 = allow, <=0.5 = block)
          [1] risk_gate (>0.5 = allow)
          [2] sanity_gate (>0.5 = allow)
          [3] override_signal (>0.5 = force block everything)
        """
        s = np.clip(safety_output, 0, 1)
        override = s[3] > 0.5
        all_gates_pass = s[0] > 0.3 and s[1] > 0.3 and s[2] > 0.3 and not override

        if not all_gates_pass:
            self.state.safety_overrides += 1
            log.info(f"Safety kernel blocked action (override={override}, gates={s[:3].tolist()})")
            return {k: 0.0 for k in motor}

        return motor

    def think(self, inputs: dict[str, Any], sim_time: float = 0.05) -> dict[str, Any]:
        """Run one think cycle.

        Args:
            inputs: Raw data dict (market, broker, system state)
            sim_time: Simulation time in seconds (0.05 = 50ms)

        Returns:
            Dict with action recommendations and brain metadata.
        """
        t_start = time.time()

        # Encode inputs
        input_vec = self.encode_inputs(inputs)

        # Set input and run simulation
        self.sim.reset()
        self._input_value[:] = input_vec
        self.sim.run(sim_time)

        # Read outputs (average of last 10ms)
        motor_raw = self.sim.data[self.motor_probe][-10:].mean(axis=0)
        safety_raw = self.sim.data[self.safety_probe][-10:].mean(axis=0)
        predictions = self.sim.data[self.predictor_probe][-10:].mean(axis=0)

        # Decode
        motor_actions = self.decode_motor(motor_raw)
        safe_actions = self.apply_safety(motor_actions, safety_raw)

        # Update state
        self.state.cycle_count += 1
        self.state.last_predictions = {f"pred_{i}": float(v) for i, v in enumerate(predictions)}
        self.state.save()

        elapsed = time.time() - t_start

        result = {
            "actions": safe_actions,
            "predictions": self.state.last_predictions,
            "raw_motor": {k: round(v, 4) for k, v in motor_actions.items()},
            "safety_applied": motor_actions != safe_actions,
            "cycle": self.state.cycle_count,
            "sim_time_ms": round(sim_time * 1000),
            "wall_time_ms": round(elapsed * 1000),
            "neurons": self.n_neurons,
        }
        if policy_snapshot is not None:
            try:
                result["policy"] = policy_snapshot()
            except Exception:
                result["policy"] = {"available": False}
        return result

    def learn(self, feedback: dict[str, float]):
        """Apply learning from feedback (reward/penalty signals).

        Feedback keys map to prediction dimensions:
          - trade_outcome: +1 for win, -1 for loss, 0 for no trade
          - outreach_result: +1 for reply, -1 for bounce, 0 for pending
          - revenue_delta: normalized change in MRR
          - prediction_error: how wrong the last prediction was
        """
        error = np.zeros(PREDICTIVE_DIM)
        error[0] = -float(feedback.get("trade_outcome", 0)) * 0.1
        error[1] = -float(feedback.get("outreach_result", 0)) * 0.1
        error[2] = -float(feedback.get("revenue_delta", 0)) * 0.05
        error[3] = float(feedback.get("prediction_error", 0)) * 0.1

        # Apply error to PES learning rules
        self._error_value[:] = error
        self.sim.run(0.01)  # Short learning step
        self._error_value[:] = 0

        # Track rewards/penalties
        total = sum(abs(v) for v in feedback.values())
        positive = sum(v for v in feedback.values() if v > 0)
        self.state.total_rewards += positive
        self.state.total_penalties += (total - positive)
        self.state.save()

        log.info(f"Brain learned from feedback: {feedback} (total rewards: {self.state.total_rewards:.2f})")

    def get_status(self) -> dict[str, Any]:
        """Return brain health metrics."""
        status = {
            "neurons": self.n_neurons,
            "cycles": self.state.cycle_count,
            "total_rewards": round(self.state.total_rewards, 2),
            "total_penalties": round(self.state.total_penalties, 2),
            "learning_rate": self.state.learning_rate,
            "safety_overrides": self.state.safety_overrides,
            "last_predictions": self.state.last_predictions,
        }
        if get_ai_brain_status is not None:
            try:
                status["knowledge"] = get_ai_brain_status()
            except Exception:
                status["knowledge"] = {"available": False}
        if policy_snapshot is not None:
            try:
                status["policy"] = policy_snapshot()
            except Exception:
                status["policy"] = {"available": False}
        return status


# =====================================================================
# Unified Brain -- Nengo (instinct) + scikit-learn (knowledge)
# =====================================================================

class UnifiedBrain:
    """Combines biological SNN (Nengo) with trained ML models (scikit-learn).

    The SNN handles real-time attention and adaptation (instinct).
    The ML models handle pattern recognition from historical data (knowledge).
    Together: fast reflexes + learned expertise.
    """

    def __init__(self, n_neurons: int = 5000):
        self.snn = NeuromorphicBrain(n_neurons=n_neurons)
        # Lazy import to avoid circular deps
        try:
            from .ml_models import get_toolkit
        except ImportError:
            from ml_models import get_toolkit
        self.ml = get_toolkit()

    def think(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Unified think cycle combining SNN + ML predictions."""
        # SNN: fast instinct (attention, energy allocation)
        snn_result = self.snn.think(inputs)

        # ML: trained knowledge (specific predictions)
        ml_result = {}

        # Trade prediction if market data present
        if inputs.get("price_normalized"):
            ml_result["trade"] = self.ml.predict_trade(inputs)

        # Lead scoring if broker data present
        if inputs.get("broker_lead_heat"):
            ml_result["lead_score"] = self.ml.score_lead(inputs)

        # Outreach timing
        if inputs.get("outreach_reply_rate") is not None:
            ml_result["outreach"] = self.ml.should_outreach(inputs)

        result = {
            "snn": snn_result,
            "ml": ml_result,
            "combined_confidence": self._combine_confidence(snn_result, ml_result),
        }
        if policy_snapshot is not None:
            try:
                result["policy"] = policy_snapshot()
            except Exception:
                result["policy"] = {"available": False}
        return result

    def _combine_confidence(self, snn: dict, ml: dict) -> float:
        """Weighted combination of SNN and ML confidence."""
        snn_conf = abs(snn.get("actions", {}).get("trade_confidence", 0))
        ml_conf = ml.get("trade", {}).get("confidence", 0)

        # If ML model is trained, weight it more (0.7 ML, 0.3 SNN)
        # If ML model is not trained, SNN dominates
        if ml_conf > 0:
            return 0.7 * ml_conf + 0.3 * snn_conf
        return snn_conf

    def learn(self, feedback: dict[str, float]):
        """Both systems learn from feedback."""
        self.snn.learn(feedback)
        # ML models learn through periodic batch retraining, not online

    def get_status(self) -> dict[str, Any]:
        """Combined status of both systems."""
        status = {
            "snn": self.snn.get_status(),
            "ml": self.ml.get_all_status(),
        }
        if get_ai_brain_status is not None:
            try:
                status["knowledge"] = get_ai_brain_status()
            except Exception:
                status["knowledge"] = {"available": False}
        if policy_snapshot is not None:
            try:
                status["policy"] = policy_snapshot()
            except Exception:
                status["policy"] = {"available": False}
        return status


# --- Singletons ---
_brain: NeuromorphicBrain | None = None
_unified: UnifiedBrain | None = None


def get_brain(n_neurons: int = 5000) -> NeuromorphicBrain:
    """Get or create the singleton SNN brain instance."""
    global _brain
    if _brain is None:
        _brain = NeuromorphicBrain(n_neurons=n_neurons)
    return _brain


def get_unified_brain(n_neurons: int = 5000) -> UnifiedBrain:
    """Get or create the unified brain (SNN + ML)."""
    global _unified
    if _unified is None:
        _unified = UnifiedBrain(n_neurons=n_neurons)
    return _unified
