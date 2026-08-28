"""
PLRL3 (Position Level Rescue Logic v3) -- thin re-export from canonical shared module.

The canonical implementation lives at:
  src/shared/trading/plrl3.py

This file re-exports symbols so existing imports continue to work.
"""

import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_shared_path = os.path.join(_project_root, "src")
if _shared_path not in sys.path:
    sys.path.insert(0, _shared_path)

from shared.trading.plrl3 import (  # noqa: F401, E402
    PLRLDecision,
    evaluate_plrl3,
    compute_initial_contracts_plrl3,
    evaluate_atr_trail_exit,
)

__all__ = ["PLRLDecision", "evaluate_plrl3", "compute_initial_contracts_plrl3", "evaluate_atr_trail_exit"]
