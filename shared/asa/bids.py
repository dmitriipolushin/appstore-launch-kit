#!/usr/bin/env python3
"""Безопасное массовое поднятие ставок Apple Search Ads (v5).

Почему отдельный модуль, а не разовый скрипт: 2026-09-11 на проекте Songria
поднятие ставок по 61 адгруппе оборвалось на третьей кампании из трёх. Первые
две успели записать конфиг, повторный запуск считал цель как «конфиг + шаг» и
применил шаг второй раз — +$0.60 вместо +$0.30 по 46 адгруппам.

Правила, зашитые в код:
  * ставка только ПОДНИМАЕТСЯ — модуль никогда не понижает ставку;
  * меняются только ACTIVE-ключи в ENABLED-адгруппах ENABLED-кампаний —
    PAUSED-ключ не трогается, даже если он первый в адгруппе;
  * цель считается от ФАКТИЧЕСКОЙ ставки ключа в кабинете, а план прогона
    (было → станет по каждому ключу) пишется в data/bid_runs/ проекта до первой
    записи. Повторный запуск с теми же параметрами в тот же день продолжает
    этот план: применённое пропускается, шаг второй раз не прибавляется;
  * default bid адгруппы подтягивается до максимальной ставки её ключей
    (только вверх, Search Match не трогается);
  * сетевые обрывы, 429 и 5xx ретраятся с нарастающей паузой.

Потолок ставки (economics.by_geo.<GEO>.bid_ceiling) — ОРИЕНТИР, а не граница.
Ставка выше потолка допустима и часто нужна: она даёт показы, а фактическая цена
тапа (аукцион второй цены) остаётся на уровне потолка или ниже. Сам потолок
плавает вместе с конверсией тап→установка и ARPU. Поэтому модуль ставку до
потолка не обрезает, а показывает его рядом с фактическим CPT и предупреждает,
когда CPT за период выше потолка на достаточном числе тапов. Жёсткий предел —
только явный --max-bid.

Режимы:
  по умолчанию              +шаг всем ACTIVE-ключам;
  --ramp-zero-impressions   +шаг только ACTIVE-ключам с 0 показов за последние
                            --days N полных дней (вчера и раньше, UTC); ключи,
                            созданные внутри окна, ждут следующего дня. Плюс отчёт:
                            кто без показов 3+ дня на ставке ≥ потолка (или
                            ≥ --max-bid) — кандидат на паузу по GATE 3.

CLI:
    python3 shared/asa/bids.py --project ~/Work/along/songria --step 0.20 --ramp-zero-impressions --dry-run
    python3 shared/asa/bids.py --project ~/Work/along/songria --step 0.20 --ramp-zero-impressions --days 1
    python3 shared/asa/bids.py --project ~/Work/along/songria --step 0.30 --geos CH --max-bid 4.00
    python3 shared/asa/bids.py --project ~/Work/along/songria --report        # только отчёт
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

V5 = "https://api.searchads.apple.com/api/v5"
MIN_TAPS_FOR_CPT = 5     # меньше тапов — CPT за период шумный, флаг «мало данных»
PAUSE_WINDOW_DAYS = 3    # GATE 3: 0 показов 3+ дня при высокой ставке


def config_path(project):
    return Path(project).expanduser() / "config" / "campaigns_v2.json"


def load_config(project):
    return json.loads(config_path(project).read_text())


def save_config(project, cfg):
    config_path(project).write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def bid_ceilings(cfg):
    """Потолки ставок по гео из economics.by_geo — ориентир, не граница."""
    econ = (cfg.get("economics") or {}).get("by_geo") or {}
    return {geo: float(v["bid_ceiling"]) for geo, v in econ.items() if "bid_ceiling" in v}


def utc_today():
    return datetime.now(timezone.utc).date()


def full_days(n):
    """(since, until) — n полных дней, заканчивая вчера (UTC)."""
    t = utc_today()
    return str(t - timedelta(days=n)), str(t - timedelta(days=1))


class ASA:
    """Клиент v5 с ретраями на сетевые обрывы, 429 и 5xx."""

    def __init__(self, org_id=None):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from platform_api import PlatformAPI
        api = PlatformAPI(org_id=org_id)
        self.h = {"Authorization": f"Bearer {api.token()}",
                  "Content-Type": "application/json",
                  "X-AP-Context": f"orgId={api.org_id}"}

    def _req(self, method, path, body=None, tries=5, full=False):
        last = None
        for i in range(tries):
            try:
                r = requests.request(method, V5 + path, headers=self.h, json=body, timeout=60)
            except requests.exceptions.RequestException as e:
                last = e
            else:
                if r.status_code == 429 or r.status_code >= 500:
                    last = f"HTTP {r.status_code}"
                elif r.status_code >= 300:
                    raise RuntimeError(f"{method} {path} -> {r.status_code} {r.text[:250]}")
                else:
                    j = r.json()
                    return j if full else j["data"]
            if i < tries - 1:
                time.sleep(min(30, 2 * 2 ** i))
        raise RuntimeError(f"{method} {path}: нет ответа после {tries} попыток ({last})")

    def get(self, path):
        sep = "&" if "?" in path else "?"
        return self._req("GET", path + sep + "limit=1000")

    def post(self, path, body):
        return self._req("POST", path, body)

    def put(self, path, body):
        return self._req("PUT", path, body)

    # --- чтение ---

    def keywords(self, campaign_id):
        """Все targeting-ключи кампании (одним find, с пагинацией)."""
        out, offset = [], 0
        while True:
            j = self._req("POST", f"/campaigns/{campaign_id}/adgroups/targetingkeywords/find",
                          {"pagination": {"offset": offset, "limit": 1000}}, full=True)
            out.extend(j["data"] or [])
            total = (j.get("pagination") or {}).get("totalResults", len(out))
            if not j["data"] or len(out) >= total:
                return out
            offset = len(out)

    def keyword_report(self, campaign_id, since, until):
        """{keyword_id: {impressions, taps, spend, cpt}} за период (UTC, обе даты включительно)."""
        body = {"startTime": since, "endTime": until, "timeZone": "UTC",
                "selector": {"orderBy": [{"field": "localSpend", "sortOrder": "DESCENDING"}],
                             "pagination": {"offset": 0, "limit": 1000}},
                "returnRecordsWithNoMetrics": True, "returnRowTotals": True,
                "returnGrandTotals": False}
        rep = self.post(f"/reports/campaigns/{campaign_id}/keywords", body) or {}
        out = {}
        for r in (rep.get("reportingDataResponse") or {}).get("row") or []:
            t = r.get("total") or {}
            taps = t.get("taps", 0)
            spend = float((t.get("localSpend") or {}).get("amount", 0) or 0)
            out[r["metadata"]["keywordId"]] = {
                "impressions": t.get("impressions", 0), "taps": taps, "spend": spend,
                "cpt": spend / taps if taps else None}
        return out

    def live_bids(self, campaign_id):
        """{adgroup_id: текущая defaultBidAmount} прямо из кабинета."""
        return {a["id"]: float(a["defaultBidAmount"]["amount"])
                for a in self.get(f"/campaigns/{campaign_id}/adgroups")}

    # --- запись ---

    def set_keyword_bid(self, campaign_id, adgroup_id, keyword_id, bid):
        self.put(f"/campaigns/{campaign_id}/adgroups/{adgroup_id}/targetingkeywords/bulk",
                 [{"id": keyword_id, "bidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}}])

    def set_adgroup_default_bid(self, campaign_id, adgroup_id, bid):
        """Только defaultBidAmount: automatedKeywordsOptIn в теле нет — Search Match не трогается."""
        self.put(f"/campaigns/{campaign_id}/adgroups/{adgroup_id}",
                 {"defaultBidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}})


def snapshot(api, cfg, geos=None, campaign_ids=None, perf=None, zero=None, pause=None):
    """ACTIVE-ключи кампаний проекта с метриками. Ничего не меняет.

    perf/zero/pause — (since, until): период для CPT, окно «0 показов» для
    ramp, окно кандидатов на паузу. zero=None — окно не нужно.
    Возвращает (rows, adgroups, skipped): adgroups — {(cid, agid): адгруппа}.
    """
    ceilings = bid_ceilings(cfg)
    rows, adgroups, skipped = [], {}, []
    for c in cfg.get("campaigns", []):
        cid = c.get("id")
        if not cid or (campaign_ids and cid not in campaign_ids):
            continue
        camp = api._req("GET", f"/campaigns/{cid}")
        geo = ",".join(camp.get("countriesOrRegions") or c.get("countries") or [])
        if geos and geo not in geos:
            continue
        if camp.get("status") != "ENABLED" or camp.get("deleted"):
            skipped.append(f"{camp.get('name', cid)} — кампания {camp.get('status')}")
            continue
        ags = {a["id"]: a for a in api.get(f"/campaigns/{cid}/adgroups")}
        for agid, a in ags.items():
            adgroups[(cid, agid)] = a
        m_perf = api.keyword_report(cid, *perf)
        m_zero = api.keyword_report(cid, *zero) if zero else {}
        m_pause = api.keyword_report(cid, *pause) if pause else {}
        for k in api.keywords(cid):
            ag = ags.get(k["adGroupId"])
            if (k.get("status") != "ACTIVE" or k.get("deleted") or not ag
                    or ag.get("status") != "ENABLED" or ag.get("deleted")):
                continue
            p = m_perf.get(k["id"], {})
            rows.append({
                "geo": geo, "campaign_id": cid, "campaign": camp["name"],
                "adgroup_id": ag["id"], "adgroup": ag["name"],
                "keyword_id": k["id"], "keyword": k["text"], "match": k["matchType"],
                "bid": float(k["bidAmount"]["amount"]), "ceiling": ceilings.get(geo),
                "impressions": p.get("impressions", 0), "taps": p.get("taps", 0),
                "spend": p.get("spend", 0.0), "cpt": p.get("cpt"),
                "created": (k.get("creationTime") or "")[:10],
                # Окно засчитывается, только если ключ существовал с его начала:
                # созданный вчера-сегодня ключ ещё не успел получить показы.
                "zero_recent": (m_zero.get(k["id"], {}).get("impressions", 0) == 0
                                and (k.get("creationTime") or "")[:10] < zero[0]) if zero else None,
                "zero_pause_window": (m_pause.get(k["id"], {}).get("impressions", 0) == 0
                                      and (k.get("creationTime") or "")[:10] < pause[0])
                                     if pause else None,
            })
    return rows, adgroups, skipped


def cpt_flag(r):
    """Флаг фактической цены тапа относительно потолка-ориентира."""
    if r["ceiling"] is None or r["cpt"] is None or r["cpt"] <= r["ceiling"]:
        return ""
    return "CPT > потолка" if r["taps"] >= MIN_TAPS_FOR_CPT else "CPT > потолка (мало тапов)"


def pause_candidates(rows, max_bid=None):
    """GATE 3: 0 показов за окно паузы при ставке ≥ потолка (или ≥ --max-bid)."""
    out = []
    for r in rows:
        high = max_bid if max_bid is not None else r["ceiling"]
        if r["zero_pause_window"] and high is not None and r["bid"] >= high - 1e-9:
            out.append(r)
    return out


def build_plan(rows, step, ramp=False, max_bid=None):
    """[(row, target)] — только подъём; при --max-bid цель не выше него."""
    plan, capped = [], []
    for r in rows:
        if ramp and not r["zero_recent"]:
            continue
        target = r["bid"] + step
        if max_bid is not None:
            target = min(target, max_bid)
        target = round(target, 2)
        if target <= r["bid"] + 1e-9:          # никогда не понижаем
            capped.append(r)
            continue
        plan.append((r, target))
    return plan, capped


def run_path(project, ramp, step, geos, campaign_ids):
    scope = "-".join(geos) if geos else "all"
    if campaign_ids:
        scope += "-c" + "-".join(str(c) for c in campaign_ids)
    mode = "ramp" if ramp else "all"
    return (Path(project).expanduser() / "data" / "bid_runs"
            / f"{utc_today()}_{mode}_step{step:.2f}_{scope}.json")


def apply_plan(api, project, cfg, plan, rows, adgroups, state_path, new_run=False, log=print):
    """Применяет план по ключам. Состояние — в state_path, после каждого ключа.

    Если файл прогона уже есть (обрыв или повторный запуск) — берётся ЕГО план:
    ключ с live == target пропускается, live == base — применяется, иное —
    конфликт (ставку меняли руками) и пропуск. Шаг второй раз не прибавляется.
    """
    live = {(r["campaign_id"], r["keyword_id"]): r["bid"] for r in rows}   # свежий снимок
    if state_path.exists() and not new_run:
        state = json.loads(state_path.read_text())
        log(f"Продолжаю прогон {state_path.name} (создан {state['created']}).")
    else:
        state = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "entries": [{"campaign_id": r["campaign_id"], "adgroup_id": r["adgroup_id"],
                              "keyword_id": r["keyword_id"], "keyword": r["keyword"],
                              "geo": r["geo"], "base": r["bid"], "target": t, "status": "planned"}
                             for r, t in plan]}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1))

    def ensure_adgroup_default(e):
        """default bid адгруппы ≥ ставки ключа; идемпотентно, только вверх."""
        ag = adgroups.get((e["campaign_id"], e["adgroup_id"])) or {}
        ag_bid = float((ag.get("defaultBidAmount") or {}).get("amount", 0) or 0)
        if e["target"] > ag_bid + 1e-9:
            api.set_adgroup_default_bid(e["campaign_id"], e["adgroup_id"], e["target"])
            if ag:
                ag["defaultBidAmount"] = {"amount": f"{e['target']:.2f}", "currency": "USD"}
            sync_config_bid(cfg, e["campaign_id"], e["adgroup_id"], e["target"])
            save_config(project, cfg)

    applied = []
    for e in state["entries"]:
        if e["status"] not in ("applied", "already"):
            cur = live.get((e["campaign_id"], e["keyword_id"]))
            if cur is None:
                cur = current_keyword_bid(api, e)
            if cur is None:
                e["status"] = "gone"           # ключ больше не ACTIVE
            elif abs(cur - e["target"]) < 1e-6:
                e["status"] = "already"
            elif abs(cur - e["base"]) > 1e-6:
                e["status"] = f"conflict: в кабинете ${cur:.2f}, план от ${e['base']:.2f}"
            else:
                api.set_keyword_bid(e["campaign_id"], e["adgroup_id"], e["keyword_id"], e["target"])
                e["status"] = "applied"
                applied.append(e)
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1))
        if e["status"] in ("applied", "already"):
            # и после обрыва между записью ключа и адгруппы
            ensure_adgroup_default(e)
    return state, applied


def current_keyword_bid(api, e):
    """Ставка ключа из кабинета, если он ACTIVE; иначе None."""
    for k in api.get(f"/campaigns/{e['campaign_id']}/adgroups/{e['adgroup_id']}/targetingkeywords"):
        if k["id"] == e["keyword_id"]:
            return float(k["bidAmount"]["amount"]) if k.get("status") == "ACTIVE" else None
    return None


def sync_config_bid(cfg, campaign_id, adgroup_id, bid):
    for c in cfg.get("campaigns", []):
        if c.get("id") == campaign_id:
            for a in c.get("adgroups", []):
                if a.get("id") == adgroup_id:
                    a["bid"] = bid


def fmt_money(x):
    return "—" if x is None else f"${x:.2f}"


def print_report(rows, plan, capped, cands, skipped, perf, ramp_window, max_bid):
    targets = {(r["campaign_id"], r["keyword_id"]): t for r, t in plan}
    print(f"CPT — за {perf[0]} … {perf[1]} (UTC). Потолок — ориентир из economics, не граница.")
    if ramp_window:
        print(f"Ramp: 0 показов за {ramp_window[0]} … {ramp_window[1]}.")
    if skipped:
        print("Пропущено: " + "; ".join(skipped))
    hdr = (f"{'гео':4} {'ключ':34} {'тип':5} {'ставка':>7} {'→':>7} {'потолок':>7} "
           f"{'CPT':>6} {'тапы':>4} {'показы':>6}  флаги")
    print("\n" + hdr + "\n" + "-" * len(hdr))
    for r in sorted(rows, key=lambda r: (r["geo"], -r["bid"], r["keyword"])):
        t = targets.get((r["campaign_id"], r["keyword_id"]))
        flags = [f for f in (cpt_flag(r),) if f]
        if r["ceiling"] is not None and r["bid"] > r["ceiling"]:
            flags.append("ставка > потолка")
        print(f"{r['geo'][:4]:4} {r['keyword'][:34]:34} {r['match'][:5]:5} {fmt_money(r['bid']):>7} "
              f"{fmt_money(t) if t else '':>7} {fmt_money(r['ceiling']):>7} "
              f"{fmt_money(r['cpt']) if r['cpt'] is not None else '—':>6} {r['taps']:>4} "
              f"{r['impressions']:>6}  {', '.join(flags)}")

    over = [r for r in rows if cpt_flag(r) == "CPT > потолка"]
    if over:
        print(f"\n⚠️  Фактический CPT выше потолка при ≥{MIN_TAPS_FOR_CPT} тапах — {len(over)} ключ(ей). "
              "Ставку не трогаем автоматически: проверь CPI/выручку по ним (GATE 3) "
              "и пересчитай потолок, если сменились CR тап→установка или ARPU.")
        for r in over:
            print(f"    {r['geo']} {r['keyword']}: CPT {fmt_money(r['cpt'])} при потолке "
                  f"{fmt_money(r['ceiling'])}, {r['taps']} тапов, ${r['spend']:.2f}")
    if capped:
        print(f"\nУпёрлись в --max-bid {fmt_money(max_bid)} — не подняты: "
              + ", ".join(f"{r['geo']} {r['keyword']}" for r in capped))
    if cands:
        print(f"\n⏸  Кандидаты на паузу (GATE 3): 0 показов {PAUSE_WINDOW_DAYS}+ дня при ставке "
              f"≥ {'--max-bid' if max_bid is not None else 'потолка'} — {len(cands)}:")
        for r in cands:
            print(f"    {r['geo']} {r['keyword']} ({r['match']}) ставка {fmt_money(r['bid'])}")
        print("    Решение о паузе — за пользователем; модуль ничего не паузит.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Поднять ставки ACTIVE-ключей (никогда не понижает). Потолок — ориентир.")
    ap.add_argument("--project", required=True, help="Папка проекта с config/campaigns_v2.json")
    ap.add_argument("--step", type=float, help="Шаг в USD, напр. 0.20")
    ap.add_argument("--report", action="store_true", help="Только отчёт: ставка, потолок, CPT, флаги")
    ap.add_argument("--ramp-zero-impressions", action="store_true",
                    help="Шаг только ACTIVE-ключам с 0 показов за последние --days полных дней")
    ap.add_argument("--days", type=int, default=1,
                    help="Окно «0 показов» для --ramp-zero-impressions, полных дней (по умолчанию 1)")
    ap.add_argument("--only-zero-impressions", action="store_true",
                    help="Как --ramp-zero-impressions, но окно задаётся --since/--until")
    ap.add_argument("--since", help="Начало окна «0 показов» (YYYY-MM-DD) для --only-zero-impressions")
    ap.add_argument("--until", help="Конец окна «0 показов» (YYYY-MM-DD) для --only-zero-impressions")
    ap.add_argument("--perf-days", type=int, default=7,
                    help="Период фактического CPT в отчёте, полных дней (по умолчанию 7)")
    ap.add_argument("--max-bid", type=float,
                    help="Явный жёсткий предел ставки. Без него ставка потолком не ограничивается")
    ap.add_argument("--geos", help="Через запятую: DE,AT,CH. По умолчанию все кампании конфига")
    ap.add_argument("--campaigns", help="ID кампаний через запятую — только они")
    ap.add_argument("--new-run", action="store_true",
                    help="Начать новый прогон, даже если сегодня такой уже был (ещё один шаг)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.report and a.step is None:
        ap.error("нужен --step (или --report)")
    if a.step is not None and a.step <= 0:
        ap.error("--step должен быть > 0: модуль только поднимает ставки")
    if a.only_zero_impressions and not (a.since and a.until):
        ap.error("--only-zero-impressions требует --since и --until")
    ramp = a.ramp_zero_impressions or a.only_zero_impressions
    geos = [g.strip().upper() for g in a.geos.split(",")] if a.geos else None
    cids = [int(c) for c in a.campaigns.split(",")] if a.campaigns else None

    perf = full_days(a.perf_days)
    zero = (a.since, a.until) if a.only_zero_impressions else (full_days(a.days) if ramp else None)
    pause = full_days(max(PAUSE_WINDOW_DAYS, a.days if ramp else 0))

    cfg = load_config(a.project)
    api = ASA()
    rows, adgroups, skipped = snapshot(api, cfg, geos, cids, perf, zero, pause)
    plan, capped = ([], []) if a.report else build_plan(rows, a.step, ramp, a.max_bid)
    cands = pause_candidates(rows, a.max_bid)
    print_report(rows, plan, capped, cands, skipped, perf, zero, a.max_bid)

    if a.report:
        raise SystemExit(0)
    state_path = run_path(a.project, ramp, a.step, geos, cids)
    if a.dry_run:
        note = (f" Есть файл прогона {state_path.name} — запуск без --dry-run продолжит ЕГО план."
                if state_path.exists() and not a.new_run else "")
        print(f"\n(dry-run) к подъёму: {len(plan)} ключ(ей).{note}")
        raise SystemExit(0)
    state, applied = apply_plan(api, a.project, cfg, plan, rows, adgroups, state_path, a.new_run)
    print(f"\nПрименено: {len(applied)}. Прогон: {state_path}")
    if not applied and all(e["status"] != "planned" for e in state["entries"]):
        print("Этот прогон уже выполнен сегодня. Ещё один шаг — --new-run.")
    for e in state["entries"]:
        if e["status"] not in ("applied", "already"):
            print(f"  ! {e['geo']} {e['keyword']}: {e['status']}")
