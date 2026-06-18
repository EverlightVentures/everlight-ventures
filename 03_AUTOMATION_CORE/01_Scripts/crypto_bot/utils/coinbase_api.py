"""
Coinbase API Wrapper -- thin re-export from canonical shared module.

The canonical implementation lives at:
  src/shared/trading/coinbase_api.py

This file re-exports CoinbaseAPI so existing imports continue to work.
"""

import sys
import os

# Add project root to path so shared module is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_shared_path = os.path.join(_project_root, "src")
if _shared_path not in sys.path:
    sys.path.insert(0, _shared_path)

from shared.trading.coinbase_api import CoinbaseAPI  # noqa: F401, E402

__all__ = ["CoinbaseAPI"]
