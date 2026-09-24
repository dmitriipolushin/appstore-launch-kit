#!/usr/bin/env python3
"""
Fetch ASA metrics in two requests:
  1. reports/campaigns  — all campaign metrics at once (O(1) regardless of campaign count)
  2. per-campaign keyword fetch — only for orphan campaigns not in config

С --keywords вместо строки-на-кампанию пишется строка-на-ключ (1 запрос на
кампанию). Нужно для архитектуры «1 ключ = 1 адгруппа»: там в кампании
десятки ключей, и campaign-level строка схлопывает их в одну, теряя разбивку.

⚠️ В keyword-режиме не видно Search Match: у Discovery-адгруппы нет targeting-
ключей, и в keyword-отчёт она не попадает вовсе. Сумма строк будет меньше
расхода кампании ровно на неё — сверять объём только по campaign-level.

Usage:
    python3 asa_fetch.py --project ./asa-monitoring --config ./asa-launch/config/campaigns_v2.json --days 7
    python3 asa_fetch.py --project ./asa-monitoring --config ./asa-launch/config/campaigns_v2.json --since 2026-04-23
    python3 asa_fetch.py --project ./asa-monitoring --config ./asa-launch/config/campaigns_v2.json --days 7 --searchterms

    # Single campaign (ad-hoc):
    python3 asa_fetch.py --project ./asa-monitoring --campaign-id <campaign_id> --days 7

Output (appended, never overwritten):
    {project}/data/asa_metrics.csv       — keyword-level metrics, all campaigns
    {project}/data/asa_searchterms.csv   — search term data, all campaigns (only with --searchterms)
"""

import csv
import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from env_setup import CONFIG_DIR  # noqa: F401
from utils.asa_api import SearchAdsAPI
from utils.parsing_data import transform_asa_keywords


METRICS_FILE = "asa_metrics.csv"
SEARCHTERMS_FILE = "asa_searchterms.csv"

METRICS_FIELDS = [
    "fetch_date", "period_start", "period_end",
    "campaign_id", "campaign_name", "country", "status",
    "keyword", "bid",
    "impressions", "taps", "installs", "spend",
    "ttr", "cr", "avg_cpt", "avg_cpa", "ipm",
]

SEARCHTERMS_FIELDS = [
    "fetch_date", "period_start", "period_end",
    "campaign_id", "campaign_name", "country",
    "search_term", "keyword", "match_type",
    "impressions", "taps", "installs", "spend",
    "ttr", "cr", "avg_cpt", "avg_cpa",
]


def get_dates(days=None, since=None, end=None):
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()
    if since:
        start_dt = datetime.strptime(since, "%Y-%m-%d")
    else:
        start_dt = end_dt - timedelta(days=days or 7)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def fetch_api_meta(api, campaign_ids):
    """Return {cid: {country, keyword, bid}} read from the live API.

    Used when no config file supplies keyword/bid/country — otherwise country
    silently defaults to DE and bid to 0, which is wrong for non-DE campaigns.
    Cost: 1 call for the campaign list + 2 calls per campaign.
    """
    meta = {}
    wanted = {str(c) for c in campaign_ids}

    countries = {}
    for c in api.get_campaigns():
        cid = str(c.get("id"))
        if cid in wanted:
            countries[cid] = ",".join(c.get("countriesOrRegions") or [])

    for cid in wanted:
        entry = {"country": countries.get(cid, ""), "keyword": "", "bid": 0.0}
        try:
            adgroups = api.get_adgroups(int(cid)) or []
            kws = []
            for ag in adgroups:
                kws.extend(api.get_targeting_keywords(int(cid), ag["id"]) or [])
            active = [k for k in kws if k.get("status") != "PAUSED"] or kws
            if active:
                bids = [float((k.get("bidAmount") or {}).get("amount", 0)) for k in active]
                entry["bid"] = max(bids) if bids else 0.0
                if len(active) == 1:
                    entry["keyword"] = active[0].get("text", "")
        except Exception as e:
            print(f"    meta fetch error for {cid}: {e}")
        meta[cid] = entry

    return meta


def infer_country(name):
    n = name.upper()
    if n.startswith("AT ") or n.startswith("AT—") or n.startswith("AT —"):
        return "AT"
    if n.startswith("CH ") or n.startswith("CH—") or n.startswith("CH —"):
        return "CH"
    return "DE"


def infer_keyword_from_name(name):
    """Extract keyword from campaign name — no API call needed.

    Patterns:
      'PS — gluten free scanner'                   → 'gluten free scanner'
      'KT — gluten free scanner'                   → 'gluten free scanner'
      'Lebensmittel Scanner KI - AT - glutenfrei'  → 'glutenfrei'
      'Lebensmittel Scanner KI - CH - histamin...' → 'histamin...'
      'Product Scanner - laktoseintoleranz'        → 'laktoseintoleranz'
    """
    # 'PS — kw' or 'KT — kw'
    if " — " in name:
        return name.split(" — ", 1)[1].strip()
    # 'Lebensmittel Scanner KI - GEO - kw'  (two dashes)
    parts = name.split(" - ")
    if len(parts) >= 3:
        return " - ".join(parts[2:]).strip()
    # 'Product Scanner - kw'  (one dash)
    if len(parts) == 2:
        return parts[1].strip()
    return ""


def build_config_lookup(config_path, app_id):
    """Return {campaign_id: {keyword, bid, country, name, status}} from config."""
    with open(config_path) as f:
        cfg = json.load(f)

    lookup = {}
    seen = set()

    def add(cid, name, country, status, keyword, bid):
        if not cid or cid in seen:
            return
        seen.add(cid)
        lookup[str(cid)] = {
            "name": name,
            "country": country,
            "status": status,
            "keyword": keyword,
            "bid": bid,
        }

    for c in cfg.get("campaigns", []):
        if not isinstance(c, dict) or "_comment" in c:
            continue
        cid = c.get("id")
        kws = c.get("keywords", [])
        kw_text = kws[0]["text"] if kws else ""
        kw_bid = float(kws[0].get("bid", 0)) if kws else 0.0
        add(cid, c.get("name", ""), c.get("country") or infer_country(c.get("name", "")),
            c.get("status", "ACTIVE"), kw_text, kw_bid)

    kt = cfg.get("keyword_tester", {})
    for c in kt.get("active_campaigns", []):
        if not isinstance(c, dict):
            continue
        cid = c.get("campaign_id")
        kw = c.get("keyword", "")
        bid = float(c.get("bid", 0))
        name = f"KT — {kw}"
        add(cid, name, "DE", c.get("status", "ACTIVE"), kw, bid)

    return lookup


def parse_campaign_row(row):
    """Extract metrics from a campaigns-report row."""
    meta = row.get("metadata", {})
    total = row.get("total", {})
    return {
        "campaign_id": str(meta.get("campaignId", "")),
        "campaign_name": meta.get("campaignName", ""),
        "status": meta.get("campaignStatus", "ACTIVE"),
        "impressions": total.get("impressions", 0),
        "taps": total.get("taps", 0),
        "installs": total.get("totalInstalls", 0),
        "spend": round(float(total.get("localSpend", {}).get("amount", 0)), 4),
        "ttr": round(total.get("ttr", 0) * 100, 2),
        "cr": round(total.get("totalInstallRate", 0) * 100, 2),
        "avg_cpt": round(float(total.get("avgCPT", {}).get("amount", 0)), 4),
        "avg_cpa": round(float(total.get("totalAvgCPI", {}).get("amount", 0)), 4),
    }


def fetch_keywords_for_orphan(api, campaign_id, campaign_name, start_date, end_date):
    """Fallback: per-campaign keyword fetch for campaigns not in config."""
    try:
        result = api.get_keywords_report_by_date(campaign_id, start_date, end_date)
        rows = result[0] if isinstance(result, tuple) else (result or [])
        return transform_asa_keywords(rows)
    except Exception as e:
        print(f"    keyword fetch error for {campaign_id}: {e}")
        return []


def fetch_searchterms(api, campaign_id, start_date, end_date):
    try:
        result = api.get_searchterms_report_by_date(campaign_id, start_date, end_date)
    except (KeyError, TypeError):
        return []
    rows = result[0] if isinstance(result, tuple) else (result or [])
    out = []
    for row in rows:
        meta = row.get("metadata", {})
        total = row.get("total", {})
        out.append({
            "searchTerm": meta.get("searchTermText", ""),
            "keyword": meta.get("keyword", ""),
            "matchType": meta.get("matchType", ""),
            "impressions": total.get("impressions", 0),
            "taps": total.get("taps", 0),
            "installs": total.get("totalInstalls", 0),
            "ttr": round(100 * total.get("ttr", 0), 2),
            "cr": round(100 * total.get("totalInstallRate", 0), 2),
            "avgCPT": round(float(total.get("avgCPT", {}).get("amount", 0)), 4),
            "avgCPA": round(float(total.get("totalAvgCPI", {}).get("amount", 0)), 4),
            "spend": round(float(total.get("localSpend", {}).get("amount", 0)), 4),
        })
    return out


def load_csv(csv_path, fields):
    """Load all rows from CSV, return list of dicts. Returns [] if file missing."""
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def upsert_rows(csv_path, fields, new_rows, period_key):
    """Replace all rows matching period_key with new_rows (upsert semantics).

    period_key: dict with fetch_date, period_start, period_end.
    Rows NOT matching period_key are preserved unchanged.
    Running this multiple times with identical inputs produces identical output.
    """
    existing = load_csv(csv_path, fields)
    kept = [
        r for r in existing
        if not (
            r.get("fetch_date") == period_key["fetch_date"]
            and r.get("period_start") == period_key["period_start"]
            and r.get("period_end") == period_key["period_end"]
        )
    ]
    final = kept + new_rows
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(final)
    return len(kept), len(new_rows)


def main():
    parser = argparse.ArgumentParser(description="Fetch ASA metrics — 1 bulk call + orphan fallback")
    parser.add_argument("--project", required=True)
    parser.add_argument("--config", help="Path to campaigns_v2.json (optional)")
    parser.add_argument("--app-id", help="App Adam ID (alternative to --config)")
    parser.add_argument("--campaign-id", type=int, help="Single campaign (ad-hoc)")
    parser.add_argument("--campaign-name", default="")
    parser.add_argument("--country", default="DE")
    parser.add_argument("--since", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int)
    parser.add_argument("--keywords", action="store_true",
                        help="Строка на ключ, а не на кампанию (архитектура «1 ключ = 1 адгруппа»)")
    parser.add_argument("--searchterms", action="store_true",
                        help="Also fetch search terms (only for campaigns with impressions > 0)")
    args = parser.parse_args()

    if not args.since and not args.days:
        print("Error: provide --since YYYY-MM-DD or --days N")
        sys.exit(1)

    project_dir = Path(args.project)
    data_dir = project_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = data_dir / METRICS_FILE
    st_path = data_dir / SEARCHTERMS_FILE

    start_date, end_date = get_dates(days=args.days, since=args.since, end=args.end)
    fetch_date = datetime.now().strftime("%Y-%m-%d")

    api = SearchAdsAPI.create()

    period_key = {"fetch_date": fetch_date, "period_start": start_date, "period_end": end_date}

    # ── Single-campaign mode (ad-hoc) ──────────────────────────────────────
    if args.campaign_id:

        kws = fetch_keywords_for_orphan(api, args.campaign_id, args.campaign_name, start_date, end_date)
        rows = []
        for kw in kws:
            impr = kw.get("impressions", 0)
            inst = kw.get("installs", 0)
            rows.append({
                "fetch_date": fetch_date, "period_start": start_date, "period_end": end_date,
                "campaign_id": args.campaign_id, "campaign_name": args.campaign_name,
                "country": args.country, "status": "ACTIVE",
                "keyword": kw.get("keyword", ""), "bid": kw.get("bid", 0),
                "impressions": impr, "taps": kw.get("taps", 0), "installs": inst,
                "spend": round(kw.get("spends", 0), 4),
                "ttr": round(kw.get("ttr", 0) * 100, 2),
                "cr": round(kw.get("cr", 0) * 100, 2),
                "avg_cpt": round(kw.get("avgCPT", 0), 4),
                "avg_cpa": round(kw.get("avgCPA", 0), 4),
                "ipm": round(inst / impr * 1000, 1) if impr else 0,
            })
        upsert_rows(metrics_path, METRICS_FIELDS, rows, period_key)
        print(f"✓ {len(rows)} keyword rows for campaign {args.campaign_id}")
        return

    # ── Bulk mode ──────────────────────────────────────────────────────────
    if not args.config and not args.app_id:
        print("Error: provide --config, --app-id, or --campaign-id")
        sys.exit(1)

    # Build config lookup (campaign_id → keyword, bid, country, ...)
    if args.config:
        config_lookup = build_config_lookup(args.config, None)
        with open(args.config) as f:
            cfg = json.load(f)
        app_id = str(cfg.get("app_id", ""))
    else:
        config_lookup = {}
        app_id = str(args.app_id)

    print(f"Period: {start_date} → {end_date}")
    print(f"Config campaigns: {len(config_lookup)}")

    # ── REQUEST 1: single bulk call for all campaign metrics ───────────────
    print("Fetching all campaign metrics (1 API call)… ", end="", flush=True)
    all_rows = api.get_campaigns_report_by_date(
        start_date, end_date,
        return_grand_totals=False,
    )
    print(f"{len(all_rows)} campaigns returned")

    # Filter to our app (adamId is nested under metadata.app.adamId)
    app_rows = []
    for row in all_rows:
        meta = row.get("metadata", {})
        if str(meta.get("app", {}).get("adamId", "")) != app_id:
            continue
        app_rows.append(row)

    print(f"Our app ({app_id}): {len(app_rows)} campaigns")

    # Aggregate API rows by campaign_id — API may return multiple rows per campaign
    # (e.g. per geo/adgroup). Sum numeric fields, keep first non-empty metadata.
    from collections import defaultdict
    aggregated = {}  # cid → aggregated dict

    for row in app_rows:
        parsed = parse_campaign_row(row)
        cid = parsed["campaign_id"]

        if cid not in aggregated:
            aggregated[cid] = parsed.copy()
        else:
            agg = aggregated[cid]
            for field in ("impressions", "taps", "installs", "spend"):
                agg[field] = round(agg[field] + parsed[field], 4)

    # Campaigns with no config entry: read real country/keyword/bid from the API
    orphans = [cid for cid in aggregated if cid not in config_lookup]
    api_meta = {}
    if orphans:
        print(f"Enriching {len(orphans)} campaigns without config (country/bid from API)…")
        api_meta = fetch_api_meta(api, orphans)

    metrics_rows = []
    st_campaign_ids = []
    unknown_kw = 0

    # Строка на ключ вместо строки на кампанию. В кампании с десятками адгрупп
    # campaign-level агрегат теряет разбивку, а fetch_api_meta проставляет
    # keyword только когда активный ключ в кампании ровно один.
    if args.keywords:
        for cid, parsed in aggregated.items():
            cname = parsed["campaign_name"]
            country = (config_lookup.get(cid, {}).get("country")
                       or api_meta.get(cid, {}).get("country") or infer_country(cname))
            kws = fetch_keywords_for_orphan(api, int(cid), cname, start_date, end_date)
            for kw in kws:
                impr = kw.get("impressions", 0)
                inst = kw.get("installs", 0)
                metrics_rows.append({
                    "fetch_date": fetch_date, "period_start": start_date, "period_end": end_date,
                    "campaign_id": cid, "campaign_name": cname,
                    "country": country, "status": parsed["status"],
                    "keyword": kw.get("keyword", ""), "bid": kw.get("bid", 0),
                    "impressions": impr, "taps": kw.get("taps", 0), "installs": inst,
                    "spend": round(kw.get("spends", 0), 4),
                    "ttr": round(kw.get("ttr", 0) * 100, 2),
                    "cr": round(kw.get("cr", 0) * 100, 2),
                    "avg_cpt": round(kw.get("avgCPT", 0), 4),
                    "avg_cpa": round(kw.get("avgCPA", 0), 4),
                    "ipm": round(inst / impr * 1000, 1) if impr else 0,
                })
            st_campaign_ids.append((cid, cname))
        upsert_rows(metrics_path, METRICS_FIELDS, metrics_rows, period_key)
        with_impr = sum(1 for r in metrics_rows if r["impressions"] > 0)
        print(f"\n\u2713 Upserted {len(metrics_rows)} keyword rows "
              f"({with_impr} with impressions) \u2192 {metrics_path}")
        if args.searchterms:
            st_rows = []
            for cid, cname in st_campaign_ids:
                st_rows.extend(fetch_searchterms(api, int(cid), start_date, end_date))
            upsert_rows(st_path, SEARCHTERMS_FIELDS, st_rows, period_key)
            print(f"\u2713 Upserted {len(st_rows)} search term rows \u2192 {st_path}")
        return

    for cid, parsed in aggregated.items():
        info = config_lookup.get(cid)

        if info:
            keyword = info["keyword"]
            bid = info["bid"]
            country = info["country"]
            name = info["name"] or parsed["campaign_name"]
        else:
            cname = parsed["campaign_name"]
            m = api_meta.get(cid, {})
            keyword = m.get("keyword") or infer_keyword_from_name(cname)
            if not keyword:
                unknown_kw += 1
            bid = m.get("bid", 0.0)
            country = m.get("country") or infer_country(cname)
            name = cname

        status = parsed["status"]
        impr = parsed["impressions"]
        inst = parsed["installs"]
        taps = parsed["taps"]
        metrics_rows.append({
            "fetch_date": fetch_date, "period_start": start_date, "period_end": end_date,
            "campaign_id": cid, "campaign_name": name, "country": country, "status": status,
            "keyword": keyword, "bid": bid,
            "impressions": impr, "taps": taps, "installs": inst,
            "spend": parsed["spend"],
            "ttr": round(taps / impr * 100, 2) if impr else 0,
            "cr": round(inst / taps * 100, 2) if taps else 0,
            "avg_cpt": round(parsed["spend"] / taps, 4) if taps else 0,
            "avg_cpa": round(parsed["spend"] / inst, 4) if inst else 0,
            "ipm": round(inst / impr * 1000, 1) if impr else 0,
        })

        if impr > 0:
            st_campaign_ids.append((cid, name, country))

    # Write metrics — upsert: replace all rows for this period, keep other periods
    kept, written = upsert_rows(metrics_path, METRICS_FIELDS, metrics_rows, period_key)

    print(f"\n✓ Upserted {written} campaign rows (kept {kept} rows from other periods)")
    print(f"  with-impressions={len(st_campaign_ids)}  unknown-keyword={unknown_kw}")
    print(f"  → {metrics_path}")

    # ── Search terms: only if --searchterms flag, only impressions > 0 ─────
    if not args.searchterms:
        return

    st_rows = []

    print(f"\nFetching search terms for {len(st_campaign_ids)} campaigns with impressions…")
    for cid, cname, country in st_campaign_ids:
        print(f"  {cname}… ", end="", flush=True)
        sts = fetch_searchterms(api, int(cid), start_date, end_date)
        for st in sts:
            st_rows.append({
                "fetch_date": fetch_date, "period_start": start_date, "period_end": end_date,
                "campaign_id": cid, "campaign_name": cname, "country": country,
                "search_term": st.get("searchTerm", ""), "keyword": st.get("keyword", ""),
                "match_type": st.get("matchType", ""),
                "impressions": st.get("impressions", 0), "taps": st.get("taps", 0),
                "installs": st.get("installs", 0), "spend": st.get("spend", 0),
                "ttr": st.get("ttr", 0), "cr": st.get("cr", 0),
                "avg_cpt": st.get("avgCPT", 0), "avg_cpa": st.get("avgCPA", 0),
            })
        print(f"{len(sts)} terms")

    upsert_rows(st_path, SEARCHTERMS_FIELDS, st_rows, period_key)
    print(f"✓ {len(st_rows)} search term rows → {st_path}")


if __name__ == "__main__":
    main()
