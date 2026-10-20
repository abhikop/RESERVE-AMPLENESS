"""Load a FRED series snapshot into a date-indexed Series."""
from __future__ import annotations

import json

import pandas as pd

from reserve_ampleness.data.registry import resolve

def load_fred(key: str) -> pd.Series:
    """Return one FRED series as a date-indexed float Series named `key`.

    FRED sends `value` as a string and writes "." for missing observations;
    the numeric coercion turns those into NaN.
    """
    obs = json.loads(resolve(key).read_text())["observations"]
    df = pd.DataFrame(obs)

    dup = df["date"].duplicated()
    if dup.any():
        raise ValueError(
            f"{dup.sum()} duplicate dates, e.g. {df.loc[dup, 'date'].head().tolist()}"
        )

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.set_index("date")["value"].rename(key).sort_index()


def load_policy_rate() -> pd.Series:
    """Interest on reserves, the rate every spread is measured against:
    IOER through 28 Jul 2021, IORB from 29 Jul 2021. The asserts check that
    the two series never overlap and meet at the same level."""
    ioer, iorb = load_fred("fred_ioer"), load_fred("fred_iorb")
    assert ioer.index.intersection(iorb.index).empty, "IOER/IORB overlap"
    assert ioer.iloc[-1] == iorb.iloc[0], "level break at the splice"
    return pd.concat([ioer, iorb]).sort_index().rename("policy_rate")