"""Label a trading-day universe with reporting-calendar features.

The input is any DatetimeIndex of trading days -- historically the SOFR
publication dates, prospectively a forward-extended holiday calendar.
Nothing here knows or cares where those dates came from.
"""
from __future__ import annotations

import pandas as pd

QUARTER_END_MONTHS = (3, 6, 9, 12)
TURN_TYPES = ("month_end", "quarter_end", "year_end")


def build_calendar(trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Return one row per trading day, labelled with calendar features.

    Columns
    -------
    turn_nights         nights the overnight loan spans; <NA> on the final day
    is_last_in_month    last trading day of its month *within this index*
    month_complete      this index covers the month's calendar end
    is_quarter_end      is_last_in_month and month in (3, 6, 9, 12)
    is_year_end         is_last_in_month and month is December
    turn_type           ordered categorical: month_end < quarter_end < year_end, NA on days that are not month-ends
    """
    if not isinstance(trading_days, pd.DatetimeIndex):
        raise TypeError(f"expected DatetimeIndex, got {type(trading_days).__name__}")
    if not trading_days.is_unique:
        raise ValueError("trading_days contains duplicate dates")

    days = trading_days.sort_values()
    s = days.to_series()
    nxt = s.shift(-1)

    cal = pd.DataFrame(index=days)
    cal.index.name = trading_days.name or "date"

    cal["turn_nights"] = (nxt - s).dt.days.astype("Int64")
    cal["is_last_in_month"] = nxt.isna() | (
        nxt.dt.to_period("M") != s.dt.to_period("M")
    )
    cal["month_complete"] = (s + pd.offsets.MonthEnd(0)) <= s.max()

    month = s.dt.month
    cal["is_quarter_end"] = cal["is_last_in_month"] & month.isin(QUARTER_END_MONTHS)
    cal["is_year_end"] = cal["is_last_in_month"] & month.eq(12)

    # general -> specific, so each assignment overwrites only its own subset
    turn_type = pd.Series(pd.NA, index=days, dtype="object")
    turn_type.loc[cal["is_last_in_month"]] = "month_end"
    turn_type.loc[cal["is_quarter_end"]] = "quarter_end"
    turn_type.loc[cal["is_year_end"]] = "year_end"
    cal["turn_type"] = pd.Categorical(turn_type, categories=TURN_TYPES, ordered=True)

    return cal


def turn_dates(cal: pd.DataFrame) -> pd.DatetimeIndex:
    """Month-end turns falling in a month this index fully covers."""
    return cal.index[cal["is_last_in_month"] & cal["month_complete"]]