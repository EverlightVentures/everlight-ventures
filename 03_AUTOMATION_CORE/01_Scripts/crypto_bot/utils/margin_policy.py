"""
Margin Policy -- thin re-export from canonical shared module.

The canonical implementation lives at:
  src/shared/trading/margin_policy.py

This file re-exports symbols so existing imports continue to work.
"""

import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_shared_path = os.path.join(_project_root, "src")
if _shared_path not in sys.path:
    sys.path.insert(0, _shared_path)

from shared.trading.margin_policy import (  # noqa: F401, E402
    PolicyDecision,
    evaluate_margin_policy,
)

__all__ = ["PolicyDecision", "evaluate_margin_policy"]
