#!/usr/bin/env python3
"""Fetch App Store reviews from iTunes RSS for a given app.

Usage:
    python3 scripts/fetch_reviews.py --app-id 1571725006 --project projects/my_app
    python3 scripts/fetch_reviews.py --app-id 1571725006 --country gb --project projects/my_app

Output: {project}/data/raw/reviews_{app_id}_{ts}.json
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


def fetch_reviews(app_id: str, country: str = "us") -> dict:
    url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    entries = data.get("feed", {}).get("entry", [])
    reviews = []
    seen_ids = set()
    for entry in entries:
        # Skip app-info entry (no im:rating key)
        if "im:rating" not in entry:
            continue
        review_id = entry.get("id", {}).get("label", "")
        if review_id in seen_ids:
            continue
        seen_ids.add(review_id)
        reviews.append({
            "id": review_id,
            "author": entry.get("author", {}).get("name", {}).get("label", ""),
            "date": entry.get("updated", {}).get("label", ""),
            "rating": int(entry.get("im:rating", {}).get("label", 0)),
            "title": entry.get("title", {}).get("label", ""),
            "text": entry.get("content", {}).get("label", ""),
        })

    return {
        "app_id": app_id,
        "country": country,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "itunes_reviews_rss",
        "total": len(reviews),
        "reviews": reviews,
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch App Store reviews from iTunes RSS")
    parser.add_argument("--app-id", required=True, help="App Store app ID")
    parser.add_argument("--country", default="us", help="Country code (default: us)")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    result = fetch_reviews(args.app_id, args.country)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.project) / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"reviews_{args.app_id}_{ts}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved {result['total']} reviews → {out_path}")


if __name__ == "__main__":
    main()
