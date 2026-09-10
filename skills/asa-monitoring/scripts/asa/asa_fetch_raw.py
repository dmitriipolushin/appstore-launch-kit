#!/usr/bin/env python3
"""
Fetch raw ASA keyword + search term metrics into CSV files.
No scoring, no bid recommendations — just data.

Usage (run from scripts/asa/):
    python3 asa_fetch_raw.py --project ../../projects/pet_screener --since 2026-03-01
    python3 asa_fetch_raw.py --project ../../projects/pet_screener --days 7
"""

import csv
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from env_setup import CONFIG_DIR  # noqa: F401
from utils.asa_api import SearchAdsAPI
from utils.parsing_data import transform_asa_keywords


def get_dates(days: int = None, since: str = None):
    end = datetime.now()
    if since:
        start = datetime.strptime(since, "%Y-%m-%d")
    else:
        start = end - timedelta(days=days or 7)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def fetch_keywords(api, campaign_id, start_date, end_date):
    result = api.get_keywords_report_by_date(campaign_id, start_date, end_date)
    rows = result[0] if isinstance(result, tuple) else (result or [])
    return transform_asa_keywords(rows)


def fetch_searchterms(api, campaign_id, start_date, end_date):
    try:
        result = api.get_searchterms_report_by_date(campaign_id, start_date, end_date)
    except (KeyError, TypeError):
        return []
    rows = result[0] if isinstance(result, tuple) else (result or [])
    result = []
    for row in rows:
        meta = row.get("metadata", {})
        total = row.get("total", {})
        result.append({
            "searchTerm": meta.get("searchTermText", ""),
            "keyword": meta.get("keyword", ""),
            "matchType": meta.get("matchType", ""),
            "impressions": total.get("impressions", 0),
            "taps": total.get("taps", 0),
            "installs": total.get("totalInstalls", 0),
            "ttr": round(100 * total.get("ttr", 0), 2),
            "cr": round(100 * total.get("totalInstallRate", 0), 2),
            "avgCPT": round(float(total.get("avgCPT", {}).get("amount", 0)), 2),
            "avgCPA": round(float(total.get("totalAvgCPI", {}).get("amount", 0)), 2),
            "spend": round(float(total.get("localSpend", {}).get("amount", 0)), 2),
        })
    return result


def save_csv(rows, path, fields):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch raw ASA metrics to CSV")
    parser.add_argument("--project", required=True, help="Path to project dir (e.g. ../../projects/pet_screener)")
    parser.add_argument("--since", help="Start date YYYY-MM-DD (use date of last change)")
    parser.add_argument("--days", type=int, help="Number of days to fetch (alternative to --since)")
    parser.add_argument("--campaign-id", required=True, type=int, help="Campaign ID (from campaign.json)")
    args = parser.parse_args()

    if not args.since and not args.days:
        print("Error: provide --since YYYY-MM-DD or --days N")
        sys.exit(1)

    project_dir = Path(args.project)
    reports_dir = project_dir / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    campaign_id = args.campaign_id

    start_date, end_date = get_dates(days=args.days, since=args.since)
    period_label = args.since or f"{args.days}d"
    date_tag = datetime.now().strftime("%Y%m%d")

    print(f"Campaign ID: {campaign_id}")
    print(f"Period: {start_date} — {end_date}")

    api = SearchAdsAPI.create()

    # Keywords
    keywords = fetch_keywords(api, campaign_id, start_date, end_date)
    kw_fields = ["keyword", "bid", "impressions", "taps", "installs", "ttr", "cr", "avgCPT", "avgCPA", "spends"]
    # Format ttr/cr as percentages for readability
    for kw in keywords:
        kw["ttr"] = round(kw["ttr"] * 100, 2)
        kw["cr"] = round(kw["cr"] * 100, 2)
    kw_path = reports_dir / f"asa_keywords_{date_tag}_since{period_label}_{campaign_id}.csv"
    save_csv(keywords, kw_path, kw_fields)

    # Search terms
    searchterms = fetch_searchterms(api, campaign_id, start_date, end_date)
    st_fields = ["searchTerm", "keyword", "matchType", "impressions", "taps", "installs", "ttr", "cr", "avgCPT", "avgCPA", "spend"]
    if searchterms:
        st_path = reports_dir / f"asa_searchterms_{date_tag}_since{period_label}_{campaign_id}.csv"
        save_csv(searchterms, st_path, st_fields)


if __name__ == "__main__":
    main()
