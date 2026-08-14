"""
Fetches Apple Search Popularity (0–100) for keywords via Search Ads internal API.

Endpoint: POST https://app-ads.apple.com/reporting/graphql
  operationName: getRecommendedKeywordsGql

Response: list of recommended keywords with `popularity` score (0–100).

IMPORTANT: The API works as keyword DISCOVERY — pass a seed/prefix (e.g. "pet health"),
get back related keywords with their popularity scores. Not an exact lookup.

SETUP (one time — cookie expires in ~24h, refresh as needed):
1. Log into https://app-ads.apple.com
2. Open DevTools → Network tab → filter XHR/Fetch
3. Open any campaign → ad group → Keywords tab (recommendations appear)
4. Find request: POST /reporting/graphql with operationName "getRecommendedKeywordsGql"
5. Right-click → Copy → Copy as cURL
6. Update APPLE_SA_COOKIE and APPLE_SA_XSRF in scripts/config/api_keys.env

Usage (run from scripts/asa/):
    python3 keyword_popularity.py --seeds "pet health,dog tracker,cat" --country US
    python3 keyword_popularity.py --seeds "pet" --storefronts US,GB,CA --out /tmp/pop.csv
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent))
from env_setup import CONFIG_DIR  # noqa: F401

COOKIE    = os.getenv("APPLE_SA_COOKIE", "")
XSRF      = os.getenv("APPLE_SA_XSRF", "")
ADAM_ID   = os.getenv("APPLE_SA_ADAM_ID", "6749845164")
ADGROUP_ID = os.getenv("APPLE_SA_ADGROUP_ID", "2146056918")
BASE_URL  = "https://app-ads.apple.com/reporting/graphql"
DELAY_SEC = 0.4

RECOMMENDATION_QUERY = (
    "query getRecommendedKeywordsGql($adamId: String!, $text: String, $storefronts: [String]) {\n"
    "  recommendationV2 {\n"
    "    getRecommendedKeywords(adamId: $adamId, text: $text, storefronts: $storefronts) {\n"
    "      id\n"
    "      name\n"
    "      popularity\n"
    "      matchType\n"
    "      __typename\n"
    "    }\n"
    "    __typename\n"
    "  }\n"
    "}"
)


def fetch_for_seed(seed: str, storefronts: list[str]) -> list[dict]:
    """
    Returns list of {"keyword": str, "popularity": int} for a given seed.
    """
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://app-ads.apple.com",
        "referer": "https://app-ads.apple.com/cm",
        "x-xsrf-token-cm": XSRF,
        "Cookie": COOKIE,
    }
    payload = {
        "operationName": "getRecommendedKeywordsGql",
        "variables": {
            "adamId": ADAM_ID,
            "text": seed,
            "storefronts": storefronts,
        },
        "query": RECOMMENDATION_QUERY,
    }

    resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=15)

    if resp.status_code in (401, 403):
        sys.exit(f"ERROR: {resp.status_code} — cookie expired. Refresh APPLE_SA_COOKIE from DevTools.")
    if not resp.ok:
        print(f"  HTTP {resp.status_code} for seed '{seed}': {resp.text[:200]}")
        return []

    data = resp.json()
    if data.get("errors"):
        print(f"  API error for '{seed}': {data['errors']}")
        return []

    items = (data.get("data") or {}).get("recommendationV2", {}).get("getRecommendedKeywords") or []
    return [
        {"keyword": item["name"], "popularity": item["popularity"]}
        for item in items
    ]


def fetch_all(seeds: list[str], storefronts: list[str]) -> dict[str, int]:
    """
    Fetches popularity for all seeds, deduplicates by keyword (takes max score).
    """
    if not COOKIE:
        sys.exit(
            "ERROR: APPLE_SA_COOKIE is not set.\n"
            "See setup instructions at the top of this file.\n"
            "Add to scripts/config/api_keys.env:\n"
            "  APPLE_SA_COOKIE=<value from DevTools>\n"
            "  APPLE_SA_XSRF=<value of XSRF-TOKEN-CM cookie>"
        )

    all_keywords: dict[str, int] = {}

    for i, seed in enumerate(seeds):
        print(f"[{i+1}/{len(seeds)}] seed: '{seed}'")
        results = fetch_for_seed(seed, storefronts)

        for item in results:
            kw, score = item["keyword"], item["popularity"]
            if kw not in all_keywords or all_keywords[kw] < score:
                all_keywords[kw] = score

        print(f"  → {len(results)} keywords (total unique: {len(all_keywords)})")

        if i < len(seeds) - 1:
            time.sleep(DELAY_SEC)

    return all_keywords


def save_csv(results: dict[str, int], path: str):
    rows = sorted(results.items(), key=lambda x: -x[1])
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "popularity"])
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} keywords → {path}")


def print_top(results: dict[str, int], n: int = 20):
    print(f"\nTop {min(n, len(results))} by popularity:")
    for kw, score in sorted(results.items(), key=lambda x: -x[1])[:n]:
        bar = "█" * (score // 5)
        print(f"  {score:3d} {bar:<20} {kw}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", required=True,
                        help="Comma-separated seed words/phrases (e.g. 'pet health,dog tracker')")
    parser.add_argument("--storefronts", default="US,GB,CA,AU",
                        help="Comma-separated country codes (default: US,GB,CA,AU)")
    parser.add_argument("--out", default="popularity_scores.csv")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    storefronts = [s.strip().upper() for s in args.storefronts.split(",") if s.strip()]

    print(f"Seeds: {seeds}")
    print(f"Storefronts: {storefronts}\n")

    results = fetch_all(seeds, storefronts)
    save_csv(results, args.out)
    print_top(results, args.top)


if __name__ == "__main__":
    main()
