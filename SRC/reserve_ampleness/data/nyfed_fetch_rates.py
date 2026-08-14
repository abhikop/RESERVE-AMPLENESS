"""Fetch NY Fed reference rates; save an immutable dated snapshot + manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from datetime import datetime, timezone

import requests

BASE = "https://markets.newyorkfed.org/api/rates"
RATES = {"all": "all", "sofr": "secured/sofr", "tgcr": "secured/tgcr",
         "bgcr": "secured/bgcr", "effr": "unsecured/effr", "obfr": "unsecured/obfr"}
FORMATS = ("json", "csv", "xml", "xlsx")
MIN_BYTES = 200
REPO = pathlib.Path(__file__).resolve().parents[3]


def _iso_date(s: str) -> str:
    """argparse type: accept YYYY-MM-DD, reject anything else."""
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {s!r}")
    return s


def fetch(rate: str, start: str, end: str, outdir: pathlib.Path,
          fmt: str = "json", timeout: int = 30) -> pathlib.Path:
    """Download one rate series; write a dated snapshot and a sidecar manifest.

    The response is written byte-for-byte, so every format the API serves works
    unchanged. Content validation belongs in the loader, not here.
    """
    url = f"{BASE}/{RATES[rate]}/search.{fmt}"
    params = {"startDate": start, "endDate": end}

    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    if len(r.content) < MIN_BYTES:
        raise RuntimeError(
            f"response was only {len(r.content)} bytes — probably empty. "
            f"url={url} params={params}"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"nyfed_rates_{rate}_{start}_{end}_pulled{stamp}.{fmt}"
    out.write_bytes(r.content)

    manifest = {
        "url": url,
        "params": params,
        "pulled_utc": stamp,
        "n_bytes": len(r.content),
        "sha256": hashlib.sha256(r.content).hexdigest(),
    }
    out.with_name(out.name + ".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rate", choices=RATES, default="all")
    p.add_argument("--format", dest="fmt", choices=FORMATS, default="json")
    p.add_argument("--start", type=_iso_date, required=True)
    p.add_argument("--end", type=_iso_date, required=True)
    p.add_argument("--outdir", type=pathlib.Path, default=REPO / "DATA" / "RAW")
    a = p.parse_args(argv)
    out = fetch(a.rate, a.start, a.end, a.outdir, a.fmt)
    print(f"{out.stat().st_size:,} bytes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
import pathlib
from datetime import datetime, timezone
import requests
import readline

BASE = "https://markets.newyorkfed.org/api"
REPO = pathlib.Path(__file__).resolve().parents[3]
RATES = {"sofr": "secured/sofr", "effr": "unsecured/effr",
         "obfr": "unsecured/obfr", "tgcr": "secured/tgcr",
         "bgcr": "secured/bgcr", "all": "all"}
FORMATS = ("json", "csv", "xml", "xlsx")

def pick(label, options):
    while True:
        v = input(f"{label} {list(options)}: ").strip().lower()
        if v in options:
            return v
        print(f"  not one of {list(options)}")

rate  = pick("Rate", RATES)
fmt   = pick("Format", FORMATS)
start = input("Start date (YYYY-MM-DD): ").strip()
end   = input("End date   (YYYY-MM-DD): ").strip()

_in = input(f"Save to dir [{REPO / 'DATA' / 'RAW'}]: ").strip()
outdir = pathlib.Path(_in).expanduser() if _in else REPO / "DATA" / "RAW"

r = requests.get(f"{BASE}/rates/{RATES[rate]}/search.{fmt}",
                 params={"startDate": start, "endDate": end}, timeout=30)
r.raise_for_status()

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = outdir / f"nyfed_rates_{rate}_{start}_{end}_pulled{stamp}.{fmt}"
outdir.mkdir(parents=True, exist_ok=True)
out.write_bytes(r.content)
print(f"{len(r.content):,} bytes -> {out}")
"""


