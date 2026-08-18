from __future__ import annotations
import json
import pandas as pd
from reserve_ampleness.data.registry import resolve

SECURED = ("TGCR", "BGCR", "SOFR")

NUMERIC_COLS = (
    'average30day', 'average90day', 'average180day', 'index', 'percentRate', 'percentPercentile1', 'percentPercentile25', 'percentPercentile75', 'percentPercentile99', 'targetRateFrom', 'targetRateTo', 'volumeInBillions', 'intraDayLow', 'intraDayHigh', 'stdDeviation'
)

PCTL_ORDER = (
    "percentPercentile1", "percentPercentile25", "percentRate", "percentPercentile75", "percentPercentile99",
)

def load_long(key: str = "nyfed_all_rates") -> pd.DataFrame:
    data0 = json.loads(resolve("nyfed_all_rates").read_text())
    data1 = pd.json_normalize(data0['refRates'])

    data1['effectiveDate'] = pd.to_datetime(data1['effectiveDate'])
    present = [c for c in NUMERIC_COLS if c in data1.columns]
    data1[present] = data1[present].apply(pd.to_numeric, errors = 'coerce')

    dup = data1.duplicated(subset = ["effectiveDate", "type"])
    if dup.any():
        raise ValueError(
            f"{dup.sum()} duplicate (effectiveDate, type) rows; "
            f"first few:\n{data1.loc[dup, ['effectiveDate', 'type']].head()}"
        )
    return data1.sort_values(["effectiveDate", "type"]).reset_index(drop=True)


def to_wide(long: pd.DataFrame, types: tuple[str, ...] = SECURED) -> pd.DataFrame:
    frames = []
    for t in types:
        sub = long.loc[long["type"] == t].set_index("effectiveDate")
        frames.append(sub.drop(columns=["type"]).add_prefix(f"{t}_"))
    
    ref = frames[0].index
    for t, f in zip(types[1:], frames[1:]):
        if not f.index.equals(ref):
            missing, extra = ref.difference(f.index), f.index.difference(ref)
            raise ValueError(
                f"{t} dates disagree with {types[0]}: {len(missing)} missing,"
                f"{len(extra)} extra (e.g., missing {list(missing[:3].date)},"
                f"extra {list(extra[:3].date)})"
            )
    return pd.concat(frames, axis=1)


def validate(wide: pd.DataFrame, expect_rows: int | None = None) -> None:

    if not wide.index.is_unique:
        raise ValueError("duplicate dates in wide frame")

    vol = {t: f"{t}_volumeInBillions" for t in SECURED}
    if all(c in wide.columns for c in vol.values()):
        for hi, lo in (("SOFR", "BGCR"), ("BGCR", "TGCR")):
            bad = wide[vol[hi]] < wide[vol[lo]]
            if bad.any():
                raise ValueError(
                    f"{hi} volume < {lo} volume on {bad.sum()} dates: "
                    f"{list(wide.index[bad][:5].date)}"
                )

    cols = [f"SOFR_{c}" for c in PCTL_ORDER]
    if all(c in wide.columns for c in cols):
        complete = wide[cols].notna().all(axis=1)
        ordered = pd.concat(
            [wide[a] <= wide[b] for a, b in zip(cols, cols[1:])], axis=1
        ).all(axis=1)
        bad = complete & ~ordered
        if bad.any():
            raise ValueError(
                f"SOFR percentiles out of order on {bad.sum()} dates: "
                f"{list(wide.index[bad][:5].date)}"
            )

    if wide.index.min() != pd.Timestamp("2018-04-02"):
        raise ValueError(f"unexpected first date: {wide.index.min().date()}")

    if expect_rows is not None and len(wide) != expect_rows:
        raise ValueError(f"expected {expect_rows} rows, got {len(wide)}")


def quality_report(wide: pd.DataFrame) -> dict:
    
    order = (
        (wide["TGCR_percentRate"] <= wide["BGCR_percentRate"])
        & (wide["BGCR_percentRate"] <= wide["SOFR_percentRate"])
    )
    pctl = [f"SOFR_{c}" for c in PCTL_ORDER]
    incomplete = ~wide[pctl].notna().all(axis=1)
    revised = pd.concat(
        [wide[f"{t}_revisionIndicator"].fillna("").str.len() > 0 for t in SECURED],
        axis=1,
    ).any(axis=1)
    return {
        "n_dates": len(wide),
        "first": wide.index.min().date(),
        "last": wide.index.max().date(),
        "rate_ordering_ok_frac": round(float(order.mean()), 4),
        "rate_ordering_violations": list(wide.index[~order].date),
        "incomplete_percentile_rows": int(incomplete.sum()),
        "revised_rows": int(revised.sum()),
    }


def load_rates(key: str = "nyfed_all_rates", types: tuple[str, ...] = SECURED, expect_rows: int | None = None) -> pd.DataFrame:
    wide = to_wide(load_long(key), types)
    validate(wide, expect_rows=expect_rows)
    return wide