#!/usr/bin/env python3
"""Check App Store search positions, write directly to CSVs.

Usage:
    python3 scripts/search_positions.py \
      --keyword "lebensmittel scanner" \
      --app-id YOUR_APP_ID \
      --country de \
      --project ./ASO/aso-monitoring
"""
import argparse
import csv
from datetime import date
from pathlib import Path

import requests


def search_top50(keyword: str, country: str) -> list:
    resp = requests.get(
        "https://itunes.apple.com/search",
        params={"term": keyword, "entity": "software", "limit": 50, "country": country},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "position": i + 1,
            "app_id": str(r.get("trackId", "")),
            "app_name": r.get("trackName", ""),
        }
        for i, r in enumerate(resp.json().get("results", []))
    ]


def append_csv(path: Path, fieldnames: list, rows: list):
    write_header = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--app-id", required=True, help="Our app ID")
    parser.add_argument("--country", default="us")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    today = date.today().isoformat()
    data_dir = Path(args.project) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    results = search_top50(args.keyword, args.country)

    our = next((r for r in results if r["app_id"] == args.app_id), None)
    our_position = our["position"] if our else None

    append_csv(
        data_dir / "keyword_signals.csv",
        fieldnames=["keyword", "locale", "app_id", "date", "organic_position", "metadata_source"],
        rows=[{
            "keyword": args.keyword,
            "locale": args.country,
            "app_id": args.app_id,
            "date": today,
            "organic_position": our_position,
            "metadata_source": "",
        }],
    )

    append_csv(
        data_dir / "competitor_positions.csv",
        fieldnames=["keyword", "locale", "date", "app_id", "app_name", "position"],
        rows=[{
            "keyword": args.keyword,
            "locale": args.country,
            "date": today,
            "app_id": r["app_id"],
            "app_name": r["app_name"],
            "position": r["position"],
        } for r in results],
    )

    pos_str = f"#{our_position}" if our_position else "not found (>50)"
    print(f"[{args.country.upper()}] {args.keyword}: {pos_str}")


if __name__ == "__main__":
    main()
