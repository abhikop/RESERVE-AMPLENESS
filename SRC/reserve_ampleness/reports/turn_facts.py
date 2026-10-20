"""Print the turn-spike facts quoted in the README.

Spike = turn-day value of (SOFR measure - policy rate), in bp, minus the
trimmed median of the same spread over its own month (3rd trading day through
the 3rd-to-last), so the baseline never touches the turn.

Run from anywhere:  python -m reserve_ampleness.reports.turn_facts
"""
from __future__ import annotations

import pandas as pd

from reserve_ampleness.data.fred_load_series import load_policy_rate
from reserve_ampleness.data.nyfed_load_rates import load_rates
from reserve_ampleness.features.calendar_features import build_calendar, turn_dates
from reserve_ampleness.features.monthly_medians import trimmed_monthly_median

TURN_TYPES = ["month_end", "quarter_end", "year_end"]
PERIODS = (
    ("Apr 2018 - Feb 2020", None, "2020-02-29"),
    ("Mar 2020 - Dec 2022", "2020-03-01", "2022-12-31"),
    ("Jan 2023 onwards", "2023-01-01", None),
)


def turn_table() -> pd.DataFrame:
    """One row per turn: its type and the p99 and headline spikes in bp."""
    wide = load_rates()
    policy = load_policy_rate().reindex(wide.index).ffill()
    cal = build_calendar(wide.index)
    turns = turn_dates(cal)

    def spike(col: str, pol: str) -> pd.Series:
        spread = (wide[col] - pol) * 100.0
        baseline = trimmed_monthly_median(spread, turns)["median"]
        return spread.reindex(turns) - baseline

    return pd.DataFrame({
        "turn_type": cal.loc[turns, "turn_type"].astype(str),
        "p99": spike("SOFR_percentPercentile99", policy),
        "headline": spike("SOFR_percentRate", policy),
        "p99-p25": spike("SOFR_percentPercentile99", wide["SOFR_percentPercentile25"])
    })


def main() -> int:
    t = turn_table()
    print(f"{len(t)} turns, {t.index.min().date()} to {t.index.max().date()}\n")

    summary = (
        t.groupby("turn_type")
        .agg(turns_with_p99=("p99", "count"),
             median_p99=("p99", "median"),
             mean_p99=("p99", "mean"),
             max_p99=("p99", "max"),
             median_headline=("headline", "median"),
             mean_headline=("headline", "mean"),
             max_headline=("headline", "max"),
             median_p99_p25=("p99-p25", "median"),
             mean_p99_p25=("p99-p25", "mean"),
             max_p99_p25=("p99-p25", "max"))
        .reindex(TURN_TYPES)
    )
    print(summary.round(1).to_string())

    print("\nMedian p99 spike (bp) by period:")
    for label, start, end in PERIODS:
        sub = t.loc[start:end]
        cells = [f"{k} {sub.loc[sub['turn_type'] == k, 'p99'].median():.1f}"
                 for k in TURN_TYPES]
        print(f"  {label}: " + ", ".join(cells))
    

    print("\nMedian headline spike (bp) by period:")
    for label, start, end in PERIODS:
        sub = t.loc[start:end]
        cells = [f"{k} {sub.loc[sub['turn_type'] == k, 'headline'].median():.1f}"
                 for k in TURN_TYPES]
        print(f"  {label}: " + ", ".join(cells))
    

    print("\nMedian p99-p25 spike (bp) by period:")
    for label, start, end in PERIODS:
        sub = t.loc[start:end]
        cells = [f"{k} {sub.loc[sub['turn_type'] == k, 'p99-p25'].median():.1f}"
                 for k in TURN_TYPES]
        print(f"  {label}: " + ", ".join(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())