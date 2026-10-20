"""Write the two README figures to FIGURES/.
 
event_study.png  SOFR and its 99th percentile on the days around each turn,
                 in bp above that turn's own-month baseline; the line is the
                 median across turns of each type. Day 0 is the spike that
                 turn_facts summarises.
turn_spikes.png  every turn's p99 spike since April 2018, by turn type, with
                 the three periods turn_facts reports shaded and labelled.
 
Spikes, baselines and periods all come from turn_facts and the features
package, so the figures and the printed table cannot drift apart.
 
Run from anywhere:  python -m reserve_ampleness.reports.figures
"""

import numpy as np, pandas as pd, matplotlib.pyplot as plt
from reserve_ampleness.data.nyfed_load_rates import load_rates
from reserve_ampleness.data.fred_load_series import load_policy_rate
from reserve_ampleness.features.calendar_features import build_calendar, turn_dates
from reserve_ampleness.features.monthly_medians import trimmed_monthly_median
from reserve_ampleness.reports.turn_facts import PERIODS, TURN_TYPES, turn_table
from pathlib import Path

FIGURES = Path(__file__).resolve().parents[3] / "FIGURES"

COLOR  = {"month_end": "#898781", "quarter_end": "#2a78d6", "year_end": "#eb6834"}
MARKER = {"month_end": "o", "quarter_end": "s", "year_end": "D"}
NOTE = ("Spread: SOFR rate or percentile minus interest on reserves "
        "(IOER to 28 Jul 2021, IORB from 29 Jul 2021).\n"
        "Spike: turn-day spread minus the median spread from the month's 3rd "
        "to its 3rd-to-last trading day.\n"
        "Sources: Federal Reserve Bank of New York; FRED.")



def event_study(path: Path) -> None:

    wide   = load_rates()
    policy = load_policy_rate().reindex(wide.index).ffill()
    cal    = build_calendar(wide.index)
    turns  = turn_dates(cal)

    def turn_type(ts):
        if ts.month == 12:        return "year_end"
        if ts.month in (3, 6, 9): return "quarter_end"
        return "month_end"

    types = pd.Series([turn_type(t) for t in turns], index=turns)
    OFF   = list(range(-10, 4))
    pos   = {d: i for i, d in enumerate(wide.index)}

    def panel(col):
        spread = (wide[col] - policy) * 100.0          # bp
        baseline = trimmed_monthly_median(spread, turns)["median"]
        rows = {t: {k: (spread.iloc[pos[t]+k] if 0 <= pos[t]+k < len(spread) else np.nan)
                    for k in OFF} for t in turns}
        return pd.DataFrame(rows).T.sub(baseline, axis=0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharex=True, sharey=True)
    for ax, (col, label) in zip(axes, [("SOFR_percentPercentile99", "SOFR 99th percentile"), ("SOFR_percentRate", "SOFR")]):
        P = panel(col)
        med = P.groupby(types).median()
        for t in ["month_end", "quarter_end", "year_end"]:
            ax.plot(OFF, med.loc[t].values, marker=MARKER[t], color = COLOR[t], ms=3, label=f"{t} (n={int((types==t).sum())})")
        ax.axvline(0, lw=0.8, color="k", alpha=0.4)
        ax.set_title(f"{label}" + " - IORB (median)")
        ax.set_xlabel("trading days from turn"); ax.set_ylabel("bp above the month's baseline")
        ax.grid(alpha=0.25)
    axes[0].legend(fontsize=8)
    plt.tight_layout()
    fig.text(0.01, 0, NOTE, ha="left", va="top", fontsize=8, color="#52514e")
    fig.savefig(path, dpi=300, bbox_inches = "tight")
    plt.close(fig)



def spike_timeline(path: Path) -> None:

    

    spikes = turn_table()

    
    CLIP = 60

    left  = spikes.index.min() - pd.Timedelta(days=45)
    right = spikes.index.max() + pd.Timedelta(days=45)

    fig, axes = plt.subplots(2, 1, figsize=(9, 6.5), sharey=True, sharex=True)
    for ax, (key, title) in zip (axes, [("p99", "SOFR 99th percentile"), ("headline", "SOFR")]):
        for t in TURN_TYPES:
            y = spikes.loc[spikes['turn_type'] == t, key].dropna()
            on, off = y[y <= CLIP], y[y > CLIP]
            ax.scatter(on.index, on, s=15, color=COLOR[t], marker=MARKER[t], label=f"{t} ({len(y)})")
            ax.scatter(off.index, np.full(len(off), CLIP), s=20, color=COLOR[t], marker="^")
        clipped = spikes.loc[spikes[key] > CLIP, key]
        for i, (d, v) in enumerate(clipped.items()):
            crowded = i + 1 < len(clipped) and (clipped.index[i + 1] - d).days < 120
            xy, ha, va = ((-7, 0), "right", "center") if crowded else ((0, 6), "center", "bottom")
            ax.annotate(f"{v:.0f}", (d, CLIP), xytext=xy, textcoords="offset points",
                        ha=ha, va=va, fontsize=9)
        for i, (name, start, end) in enumerate(PERIODS):
            a = pd.Timestamp(start) if start else left
            b = pd.Timestamp(end) if end else right
            if i == 1:
                ax.axvspan(a, b, color="#ebeae6", lw=0, zorder=0)
            if ax is axes[0]:
                ax.text(a + (b - a) / 2, 1.01, name, transform=ax.get_xaxis_transform(),
                        ha="center", va="bottom", fontsize=9, color="#52514e")
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_ylabel("bp above the month's baseline")
        ax.set_title(title + " - IORB", loc="left", pad=20 if ax is axes[0] else 6)

    ax.set_xlim(left, right)
    ax.set_ylim(-12, CLIP + 12)
    axes[0].scatter([], [], s=50, color="#52514e", marker="^", label=f"above {CLIP} bp, value shown")
    band = (pd.Timestamp(PERIODS[1][1]) - left) / (right - left)
    axes[0].legend(loc="upper left", bbox_to_anchor=(band, 1.0), frameon=False)
    fig.tight_layout()
    fig.text(0.01, 0, NOTE, ha="left", va="top", fontsize=8, color="#52514e")
    fig.savefig(path, dpi=300, bbox_inches = "tight")
    plt.close(fig)


def main() -> int:
    FIGURES.mkdir(exist_ok=True)
    #with plt.rc_context(RC):
    event_study(FIGURES / "event_study.png")
    spike_timeline(FIGURES / "turn_spikes.png")
    print(f"Wrote event_study.png and turn_spikes.png to {FIGURES}")
    return 0
 
 
if __name__ == "__main__":
    raise SystemExit(main())



