"""Monthly trimmed medians of a series.

Can be used for constructing baselines against which we measure the magnitude of the spike.
"""
from __future__ import annotations

import pandas as pd


def trimmed_monthly_median(series, turns, lo=2, hi=2):
    """Median of `series` per calendar month, trimming `lo` days off the start
    and `hi` off the end, indexed by turn date.

    The trim exists to exclude month-boundary effects; with lo=2, hi=2 the
    window runs from the 3rd trading day through the 3rd-to-last.
    Returns `median` and `n` per turn.
    """
    if hi < 1:
        raise ValueError("hi >= 1 required; hi=0 puts the turn day in its own baseline")

    per  = series.index.to_period("M")
    kept = series.groupby(per, group_keys=False).apply(lambda g: g.iloc[lo:-hi])
    kper = kept.index.to_period("M")
    tper = pd.PeriodIndex(turns, freq="M")

    out = kept.groupby(kper).agg(["median", "size"]).reindex(tper)
    out.index = pd.DatetimeIndex(turns, name=series.index.name or "date")

    last_used = kept.index.to_series().groupby(kper).max().reindex(tper).to_numpy()
    if not (last_used < turns.to_numpy()).all():
        raise ValueError("a baseline window reaches its own turn date, or a turn's month is missing")

    return out.rename(columns={"size": "n_days"})