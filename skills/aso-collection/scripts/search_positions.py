#!/usr/bin/env python3
"""Check App Store search positions for given app IDs by keyword.

Usage:
    python3 scripts/search_positions.py \
      --keyword "dog health" \
      --app-ids 6749845164,123456789 \
      --project projects/pet_screener

    python3 scripts/search_positions.py \
      --keyword "food scanner" \
      --app-ids 1571725006,6739765789,1092799236 \
      --country gb \
      --project projects/my_app

Output: {project}/data/raw/positions_{kw_slug}_{ts}.json
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


def search_positions(keyword: str, app_ids: list, country: str = "us") -> dict:
    url = "https://itunes.apple.com/search"
    params = {"term": keyword, "entity": "software", "limit": 50, "country": country}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    results = resp.json().get("results", [])
    all_results = [
        {
            "position": i + 1,
            "app_id": str(r.get("trackId", "")),
            "app_name": r.get("trackName", ""),
        }
        for i, r in enumerate(results)
    ]

    # Append null entries for tracked app_ids not found in top-50
    found_ids = {r["app_id"] for r in all_results}
    for aid in app_ids:
        if str(aid) not in found_ids:
            all_results.append({"position": None, "app_id": str(aid), "app_name": None})

    return {
        "keyword": keyword,
        "country": country,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "itunes_search_api",
        "results": all_results,
    }


def kw_slug(keyword: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_")


def main():
    parser = argparse.ArgumentParser(description="Check App Store search positions")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--app-ids", required=True, help="Comma-separated app IDs to track")
    parser.add_argument("--country", default="us", help="Country code (default: us)")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    app_ids = [a.strip() for a in args.app_ids.split(",")]
    result = search_positions(args.keyword, app_ids, args.country)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.project) / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = kw_slug(args.keyword)
    out_path = out_dir / f"positions_{slug}_{ts}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # Print summary for tracked app_ids
    by_id = {r["app_id"]: r for r in result["results"]}
    for aid in app_ids:
        r = by_id.get(aid, {})
        pos = r.get("position")
        name = r.get("app_name") or aid
        print(f"  #{pos if pos is not None else 'not found'}  {name} ({aid})")
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    main()
