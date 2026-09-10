#!/usr/bin/env python3
"""
Batch iTunes metadata fetcher for ASO Analysis.
Writes one profile_{app_id}_{timestamp}.json per app to {project}/data/raw/.

Usage:
    python collect_profiles.py --project aso_analysis/projects/my_project --app-ids 123 456 789
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from typing import Optional
from env_setup import CONFIG_DIR, KEYS_DIR  # noqa: F401

ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
APPSTORESPY_BASE = "https://api.appstorespy.com/v1/ios/apps"

ITUNES_FIELD_MAP = {
    "trackName": "title",
    "subtitle": "subtitle",
    "description": "description",
    "averageUserRating": "rating_avg",
    "userRatingCount": "rating_count",
    "currentVersionReleaseDate": "last_updated",
    "price": "price",
    "primaryGenreName": "category",
    "sellerName": "developer_name",
}


def fetch_subtitle_appstorespy(app_id: str, country: str = "us") -> Optional[str]:
    """Fetch subtitle (short) from AppStoreSpy. Returns None if unavailable."""
    api_key = os.environ.get("APPSTORESPY_API_KEY", "")
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"{APPSTORESPY_BASE}/{app_id}",
            params={"country": country.upper(), "language": "en_US"},
            headers={"API-KEY": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("short") or None
    except Exception as e:
        print(f"  ⚠️  AppStoreSpy subtitle fetch failed for {app_id}: {e}", file=sys.stderr)
        return None


def fetch_itunes(app_id: str, country: str = "us") -> Optional[dict]:
    try:
        resp = requests.get(
            ITUNES_LOOKUP,
            params={"id": app_id, "country": country, "entity": "software"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"  ⚠️  iTunes fetch failed for {app_id}: {e}", file=sys.stderr)
        return None


def build_profile(app_id: str, raw: Optional[dict]) -> dict:
    missing = []
    itunes = {}

    if raw is None:
        return {
            "app_id": app_id,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source": "itunes",
            "itunes": {},
            "_missing_fields": ["all — iTunes returned no data"],
        }

    for src_key, dst_key in ITUNES_FIELD_MAP.items():
        value = raw.get(src_key)
        if value is None:
            missing.append(dst_key)
        itunes[dst_key] = value

    # keyword_field not available from iTunes API
    itunes["keyword_field"] = None
    missing.append("keyword_field")

    return {
        "app_id": app_id,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "itunes",
        "itunes": itunes,
        "_missing_fields": missing,
    }


def save_profile(project_dir: Path, profile: dict) -> Path:
    raw_dir = project_dir / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = raw_dir / f"profile_{profile['app_id']}_{ts}.json"
    out.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    return out


def main():
    parser = argparse.ArgumentParser(description="Batch iTunes profile fetcher")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--app-ids", nargs="+", required=True, help="App Store IDs")
    parser.add_argument("--country", default="us", help="iTunes store country (default: us)")
    args = parser.parse_args()

    project_dir = Path(args.project)
    if not project_dir.exists():
        print(f"❌ Project directory not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching iTunes profiles for {len(args.app_ids)} app(s)...\n")

    for app_id in args.app_ids:
        print(f"→ {app_id}", end=" ", flush=True)
        raw = fetch_itunes(app_id, args.country)
        profile = build_profile(app_id, raw)
        # Enrich subtitle from AppStoreSpy if iTunes didn't return it
        if profile["itunes"].get("subtitle") is None:
            subtitle = fetch_subtitle_appstorespy(app_id, args.country)
            if subtitle:
                profile["itunes"]["subtitle"] = subtitle
                profile["_missing_fields"] = [f for f in profile["_missing_fields"] if f != "subtitle"]
        out = save_profile(project_dir, profile)
        title = profile["itunes"].get("title") or "no data"
        missing_count = len(profile["_missing_fields"])
        print(f'"{title}" — saved to {out.name} ({missing_count} missing fields)')
        time.sleep(0.5)

    print("\n✓ Done.")


if __name__ == "__main__":
    main()
