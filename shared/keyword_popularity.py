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
6. Update APPLE_SA_COOKIE and APPLE_SA_XSRF in ~/.config/aso-tools/api_keys.env

PREFERRED: run the query from inside a logged-in app-ads.apple.com page instead —
no cookie handling at all, nothing expires. See SKILL.md step 4B.

HARD LIMIT: results are returned ONLY for adamId belonging to your own ASA org,
and only within that app's topical space. A competitor's adamId returns an empty
array with HTTP 200. Check what you have: python3 asa_api.py --list-apps

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

    try:
        resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=15)
    except requests.Timeout:
        print(f"  TIMEOUT for '{seed}' — Apple троттлит. Пауза и не быстрее 1 req/sec.")
        return []

    if resp.status_code in (401, 403):
        sys.exit(f"ERROR: {resp.status_code} — cookie истёк или пуст.\n"
                 f"Способ 1 (без cookie): выполнить запрос из браузера на залогиненной\n"
                 f"  странице app-ads.apple.com — см. SKILL.md, шаг 4В.\n"
                 f"Способ 2: обновить APPLE_SA_COOKIE / APPLE_SA_XSRF из DevTools.")
    if not resp.ok:
        print(f"  HTTP {resp.status_code} for seed '{seed}': {resp.text[:200]}")
        return []

    try:
        data = resp.json()
    except ValueError:
        sys.exit("ERROR: пришёл не JSON (обычно HTML страницы логина) — "
                 "APPLE_SA_COOKIE пуст или протух. См. SKILL.md, шаг 4В.")
    if data.get("errors"):
        print(f"  API error for '{seed}': {data['errors']}")
        return []

    items = (data.get("data") or {}).get("recommendationV2", {}).get("getRecommendedKeywords") or []

    if not items:
        # Самый частый и самый непонятный режим отказа: HTTP 200 + пустой массив.
        # Это НЕ проблема авторизации.
        print(f"  ПУСТО для '{seed}' (HTTP 200). Причина почти всегда одна:\n"
              f"    adamId={ADAM_ID} либо не из твоей ASA-организации, либо приложение\n"
              f"    не по теме этого seed. API отдаёт ключи только для своих приложений\n"
              f"    и только в их тематике; adamId конкурента всегда возвращает пусто.\n"
              f"    Проверь доступные adamId:  python3 asa_api.py --list-apps")
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
            "ERROR: APPLE_SA_COOKIE не задан.\n\n"
            "Прежде чем возиться с cookie — проверь, есть ли вообще смысл:\n"
            "    python3 asa_api.py --list-apps\n"
            "Popularity отдаётся только для adamId твоей ASA-организации и только\n"
            "в тематике этого приложения. Нет приложения в нужной нише — данных нет\n"
            "ни одним способом, включая официальный API.\n\n"
            "Способ 1 (рекомендуется, без cookie): выполнить GraphQL-запрос изнутри\n"
            "  залогиненной страницы app-ads.apple.com. См. SKILL.md, шаг 4В.\n\n"
            "Способ 2: добавить в ~/.config/aso-tools/api_keys.env:\n"
            "  APPLE_SA_COOKIE=<значение из DevTools>\n"
            "  APPLE_SA_XSRF=<значение cookie XSRF-TOKEN-CM>\n"
            "  APPLE_SA_ADAM_ID=<adamId приложения из нужной ниши>"
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
