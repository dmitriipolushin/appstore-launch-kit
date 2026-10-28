#!/usr/bin/env python3
"""Popularity ключей углов из Apple Ads Platform API (search-term-popularity).

Покрытие — только «голова»: запросы из топ-выборки жанра × страны, порог ≈ 45–50 по 1–100.
Ключа нет в ответе = ниже порога (малый объём), а не 0.

  python3 asa.py --project P discover   # по angle.asa.roots: все головные запросы с подстрокой → печать для отбора
  python3 asa.py --project P measure    # ключи углов + asa.terms по config.countries за последний месяц
                                        # и тренд 12 мес по стране каждого терма → asa_raw.json, popularity.json
Нужны ASA_CLIENT_ID / ASA_KEY_ID (+ ASA_ORG_ID) в ~/.config/aso-tools/api_keys.env и ключ в ~/.config/aso-tools/keys/.
"""
import argparse, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
from common import load_config, load_json, save_json
from platform_api import PlatformAPI, last_published_month  # noqa: E402


def months_back(month, n=12):
    y, m = map(int, month.split("-"))
    return [f"{(y * 12 + m - 1 - k) // 12}-{(y * 12 + m - 1 - k) % 12 + 1:02d}" for k in range(n - 1, -1, -1)]


def discover(P, cfg, api, month):
    out = {}
    for an in cfg["angles"]:
        roots = (an.get("asa") or {}).get("roots") or []
        found = {}
        for cc, root in roots:
            for r in api.search_term_popularity(month=month, countries=[cc.upper()], contains=root):
                k = (cc.lower(), r["searchTerm"].lower()); p = r.get("searchPopularity1to100") or 0
                if p > found.get(k, (0,))[0]: found[k] = (p, r.get("genre"), r.get("rankInGenre"))
        rows = sorted(found.items(), key=lambda x: -x[1][0])
        out[an["id"]] = [{"country": k[0], "term": k[1], "pop": v[0], "genre": v[1], "rank": v[2]} for k, v in rows]
        print(f"\n## {an['id']} {an['title']}: {len(rows)}")
        print("  " + "; ".join(f"{k[1]}={v[0]}({k[0]},{v[1]})" for k, v in rows[:40]))
    raw = load_json(P / "asa_raw.json", {}); raw["discovery"] = out; raw["month"] = month
    save_json(P / "asa_raw.json", raw)


def measure(P, cfg, api, month):
    countries = [c.upper() for c in cfg.get("countries", ["US", "GB", "CA", "AU", "DE", "FR", "ES", "IT", "BR", "MX", "JP", "KR", "TW"])]
    terms, pairs = set(), set()
    for an in cfg["angles"]:
        for k in an.get("keywords", []):
            terms.add(k["kw"].lower()); pairs.add((k.get("country", "us").lower(), k["kw"].lower()))
        for cc, t, _ in (an.get("asa") or {}).get("terms", []):
            terms.add(t.lower()); pairs.add((cc.lower(), t.lower()))
    rows = api.search_term_popularity(month=month, countries=countries, terms=sorted(terms))
    pop = {}
    for r in rows:
        k = f'{r["countryOrRegion"].lower()}|{r["searchTerm"].lower()}'
        pop[k] = max(pop.get(k, 0), r.get("searchPopularity1to100") or 0)
    save_json(P / "popularity.json", pop)
    months = months_back(month)
    by_cc = {}
    for cc, t in pairs: by_cc.setdefault(cc, set()).add(t)
    trend = {}
    for cc, ts in by_cc.items():
        for mo in months:
            for r in api.search_term_popularity(month=mo, countries=[cc.upper()], terms=sorted(ts)):
                d = trend.setdefault(f'{cc}|{r["searchTerm"].lower()}', {})
                d[mo] = max(d.get(mo, 0), r.get("searchPopularity1to100") or 0)
    raw = load_json(P / "asa_raw.json", {}); raw.update({"month": month, "months": months, "trend": trend})
    save_json(P / "asa_raw.json", raw)
    print(f"ok: {len(pop)} пар страна|ключ в голове из {len(terms)} ключей × {len(countries)} стран; тренд по {len(pairs)} парам")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("cmd", choices=["discover", "measure"])
    ap.add_argument("--month", help="YYYY-MM; по умолчанию последний опубликованный")
    a = ap.parse_args()
    P = Path(a.project); cfg = load_config(P); api = PlatformAPI()
    month = a.month or last_published_month()
    (discover if a.cmd == "discover" else measure)(P, cfg, api, month)


if __name__ == "__main__":
    main()
