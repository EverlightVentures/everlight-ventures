"""Trading shared utilities -- canonical copies for crypto_bot and xlm_bot."""

from .coinbase_api import CoinbaseAPI
from .margin_policy import evaluate_margin_policy, PolicyDecision
from .plrl3 import PLRLDecision, evaluate_plrl3, compute_initial_contracts_plrl3

__all__ = [
    "CoinbaseAPI",
    "evaluate_margin_policy",
    "PolicyDecision",
    "PLRLDecision",
    "evaluate_plrl3",
    "compute_initial_contracts_plrl3",
]
