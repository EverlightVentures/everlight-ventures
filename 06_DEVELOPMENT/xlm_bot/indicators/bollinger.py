from __future__ import annotations

import numpy as np
import pandas as pd


def bollinger_bands(series: pd.Series, length: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    s = pd.to_numeric(series, errors="coerce")
    mid = s.rolling(length).mean()
    std = s.rolling(length).std(ddof=0)
    upper = mid + (std_mult * std)
    lower = mid - (std_mult * std)
    width = (upper - lower) / mid.replace(0, np.nan)
    return pd.DataFrame(
        {
            "mid": mid,
            "upper": upper,
            "lower": lower,
            "width": width,
        }
    )
