#!/usr/bin/env python3
"""
Fetch App Store Connect analytics metrics (impressions, page views, app units) to CSV.
Credentials are read from projects/{app}/config/asc_config.env

Usage (run from repo root):
    python3 scripts/asc_fetch_metrics.py --project projects/my_app --days 30
    python3 scripts/asc_fetch_metrics.py --project projects/my_app --since 2026-02-01

Output:
    projects/{app}/data/reports/asc_metrics_{date}_since{date}.csv
    One file per report type (engagement, downloads, purchases)
"""

import csv
import gzip
import io
import argparse
import sys
import time
import requests
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import dotenv_values
except ImportError:
    print("Install: pip install python-dotenv")
    sys.exit(1)

try:
    import jwt
except ImportError:
    print("Install: pip install PyJWT cryptography")
    sys.exit(1)

BASE_URL = "https://api.appstoreconnect.apple.com"

# Reports we care about for ASO monitoring
TARGET_REPORTS = {
    "App Store Discovery and Engagement Standard": "engagement",
    "App Downloads Standard": "downloads",
    "App Store Installation and Deletion Standard": "installs",
    "App Sessions Standard": "sessions",
    "App Store Purchases Standard": "purchases",
}


def load_config(project_dir: Path) -> dict:
    env_path = project_dir / "config" / "asc_config.env"
    if not env_path.exists():
        print(f"Error: {env_path} not found")
        sys.exit(1)
    config = dotenv_values(str(env_path))
    key_path = project_dir / "config" / "asc_keys" / f"AuthKey_{config['ASC_KEY_ID']}.p8"
    if not key_path.exists():
        print(f"Error: key not found: {key_path}")
        sys.exit(1)
    config["_key_path"] = str(key_path)
    return config


def make_token(key_id: str, issuer_id: str, key_path: str) -> str:
    with open(key_path) as f:
        private_key = f.read()
    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 1200,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": key_id})


def api_get(token: str, url: str, params: dict = None) -> dict:
    """GET — accepts full URL or path."""
    if not url.startswith("http"):
        url = BASE_URL + url
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def api_post(token: str, path: str, body: dict) -> dict:
    r = requests.post(
        BASE_URL + path,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_ongoing_request(token: str, app_id: str) -> str:
    """Return existing ONGOING request ID, creating one if needed."""
    resp = api_get(token, f"/v1/apps/{app_id}/analyticsReportRequests")
    for item in resp.get("data", []):
        if item.get("attributes", {}).get("accessType") == "ONGOING":
            rid = item["id"]
            print(f"Using ONGOING request: {rid}")
            return rid

    # No ONGOING request found — create one
    body = {
        "data": {
            "type": "analyticsReportRequests",
            "attributes": {"accessType": "ONGOING"},
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}}
            },
        }
    }
    resp = api_post(token, "/v1/analyticsReportRequests", body)
    rid = resp["data"]["id"]
    print(f"Created ONGOING request: {rid}")
    print("Note: first instances will appear in 1-2 days")
    return rid


def get_reports(token: str, request_id: str) -> List[Dict]:
    """Get all reports for a request (handles pagination)."""
    url = f"/v1/analyticsReportRequests/{request_id}/reports?limit=200"
    resp = api_get(token, url)
    return resp.get("data", [])


def get_instances(token: str, report_id: str, start_date: str, end_date: str) -> List[Dict]:
    """Get report instances filtered by date range."""
    resp = api_get(
        token,
        f"/v1/analyticsReports/{report_id}/instances",
        params={
            "filter[processingDate]": f"{start_date},{end_date}",
            "limit": 200,
        },
    )
    return resp.get("data", [])


def download_tsv(token: str, instance_id: str) -> List[Dict]:
    """Download gzipped TSV for a report instance."""
    resp = api_get(token, f"/v1/analyticsReportInstances/{instance_id}/segments")
    segments = resp.get("data", [])
    rows = []
    for seg in segments:
        url = seg.get("attributes", {}).get("url")
        if not url:
            continue
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with gzip.open(io.BytesIO(r.content), "rt", encoding="utf-8") as f:
            content = f.read()
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        rows.extend(list(reader))
    return rows


def save_csv(rows: List[Dict], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {path}  ({len(rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description="Fetch App Store Connect metrics to CSV")
    parser.add_argument("--project", required=True, help="Path to project dir (e.g. projects/my_app)")
    parser.add_argument("--since", help="Start date YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="Number of days back (alternative to --since)")
    args = parser.parse_args()

    if not args.since and not args.days:
        print("Error: provide --since YYYY-MM-DD or --days N")
        sys.exit(1)

    project_dir = Path(args.project)
    reports_dir = project_dir / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(project_dir)
    app_id = config["ASC_APP_ID"]
    date_tag = datetime.now().strftime("%Y%m%d")

    end_date = datetime.now().strftime("%Y-%m-%d")
    if args.since:
        start_date = args.since
        period_label = args.since
    else:
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        period_label = f"{args.days}d"

    print(f"App ID: {app_id}")
    print(f"Period: {start_date} — {end_date}")

    token = make_token(config["ASC_KEY_ID"], config["ASC_ISSUER_ID"], config["_key_path"])

    request_id = get_ongoing_request(token, app_id)
    reports = get_reports(token, request_id)
    print(f"Available reports: {len(reports)}")

    # Filter to target reports only
    wanted = [(r, TARGET_REPORTS[r["attributes"]["name"]])
              for r in reports
              if r["attributes"]["name"] in TARGET_REPORTS]
    print(f"Fetching {len(wanted)} target reports...")

    for report, label in wanted:
        report_id = report["id"]
        report_name = report["attributes"]["name"]
        print(f"\n{report_name}")

        instances = get_instances(token, report_id, start_date, end_date)
        if not instances:
            print("  No instances in date range")
            continue

        print(f"  {len(instances)} instance(s)")
        all_rows = []
        for inst in instances:
            inst_id = inst["id"]
            processing_date = inst.get("attributes", {}).get("processingDate", "")
            rows = download_tsv(token, inst_id)
            print(f"  {processing_date}: {len(rows)} rows")
            all_rows.extend(rows)

        out_path = reports_dir / f"asc_{label}_{date_tag}_since{period_label}.csv"
        save_csv(all_rows, out_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
