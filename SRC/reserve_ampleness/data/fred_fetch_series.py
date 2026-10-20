"""Fetch FRED reference rates; save an immutable dated snapshot + manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import os

from datetime import datetime, timezone


import requests
from dotenv import load_dotenv, find_dotenv



BASE = "https://api.stlouisfed.org/fred/series/observations"
FORMATS = ("json", "xml", "xlsx", "csv")
MIN_BYTES = 400
ENV_FILE = "fredapi.env"
REPO = pathlib.Path(__file__).resolve().parents[3]


def _iso_date(s: str) -> str:
    """argparse type: accept YYYY-MM-DD, reject anything else."""
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {s!r}")
    return s


def _api_key() -> str:
    if "FRED_API_KEY" not in os.environ:
        if not load_dotenv(find_dotenv(ENV_FILE)):
            raise RuntimeError(f"{ENV_FILE} not found; cannot resolve FRED_API_KEY")
    if "FRED_API_KEY" not in os.environ:
        raise RuntimeError(f"FRED_API_KEY not set (checked environment and {ENV_FILE})")
    return os.environ["FRED_API_KEY"]


def _redact(params: dict) -> dict:
    """Params with the API key removed - safe to write to disk or print."""
    return {k: v for k, v in params.items() if k != "api_key"}


def _get(params: dict, timeout: int) -> requests.Response:
    """GET with the API key kept out of every error path."""
    try:
        r = requests.get(BASE, params=params, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException as e:
        status = getattr(e.response, "status_code", None)
        raise RuntimeError(
            f"FRED request failed ({type(e).__name__}"
            f"{f', status {status}' if status else ''}) "
            f"url={BASE} params={_redact(params)}"
        ) from None
    return r


def fetch(series_id: str, start: str, end: str, outdir: pathlib.Path,
          fmt: str = "json", key: str | None = None, timeout: int = 30) -> pathlib.Path:
    """Download one FRED series; write a dated snapshot and a sidecar manifest.

    The response is written byte-for-byte. Content validation belongs in the loader. The API key is never written to disk or into an error message.
    """
    key = key or _api_key()
    params  = {
        "series_id": series_id,
        "api_key": key,
        "file_type": fmt,
        "observation_start": start,
        "observation_end":end,
    }
    

    r = _get(params, timeout)
    if len(r.content) < MIN_BYTES:
        raise RuntimeError(
            f"response was only {len(r.content)} bytes — probably empty. "
            f"url={BASE} params={_redact(params)}"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"fred_{series_id}_{start}_{end}_pulled{stamp}.{fmt}"
    out.write_bytes(r.content)

    manifest = {
        "url": BASE,
        "params": _redact(params),
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
    p.add_argument("--series-id", dest="series_id", required=True, help="FRED series id, e.g., IORB, IOER, WRESBAL")
    p.add_argument("--format", dest="fmt", choices=FORMATS, default="json")
    p.add_argument("--start", type=_iso_date, required=True)
    p.add_argument("--end", type=_iso_date, required=True)
    p.add_argument("--outdir", type=pathlib.Path, default=REPO / "DATA" / "RAW")
    a = p.parse_args(argv)
    out = fetch(a.series_id, a.start, a.end, a.outdir, a.fmt)
    print(f"{out.stat().st_size:,} bytes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())