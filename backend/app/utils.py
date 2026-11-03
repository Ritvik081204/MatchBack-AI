"""Small helpers shared across layers."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def clean(obj):
    """Recursively convert numpy/pandas scalars and NaN into plain JSON-safe Python values."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Series):
        return clean(obj.tolist())
    return obj
