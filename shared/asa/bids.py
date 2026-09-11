#!/usr/bin/env python3
"""Безопасное массовое изменение ставок Apple Search Ads (v5).

Почему отдельный модуль, а не разовый скрипт: 2026-09-11 на проекте Songria
поднятие ставок по 61 адгруппе оборвалось на третьей кампании из трёх. Первые
две успели записать конфиг, повторный запуск считал цель как «конфиг + шаг» и
применил шаг второй раз — +$0.60 вместо +$0.30 по 46 адгруппам.

Здесь собрано то, что это предотвращает:
  * цель считается от ФАКТИЧЕСКОЙ ставки в кабинете, не от локального конфига;
  * уже применённое пропускается сравнением, а не слепым PUT;
  * конфиг сохраняется после каждой адгруппы, не после кампании;
  * сетевые обрывы ретраятся с нарастающей паузой.

Работает поверх campaigns_v2.json (формат asa-launch). Путь к проекту —
аргументом, модуль ни к какому проекту не привязан.

CLI:
    python3 shared/asa/bids.py --project ~/Work/along/songria --step 0.30 --dry-run
    python3 shared/asa/bids.py --project ~/Work/along/songria --step 0.30 --geos AT,CH
    python3 shared/asa/bids.py --project ~/Work/along/songria --step 0.60 --only-zero-impressions
"""
import json, time, requests
from pathlib import Path

V5 = "https://api.searchads.apple.com/api/v5"


def config_path(project):
    return Path(project).expanduser() / "config" / "campaigns_v2.json"


def load_config(project):
    return json.loads(config_path(project).read_text())


def save_config(project, cfg):
    config_path(project).write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def bid_ceilings(cfg):
    """Потолки ставок по гео из economics.by_geo конфига проекта."""
    econ = (cfg.get("economics") or {}).get("by_geo") or {}
    return {geo: float(v["bid_ceiling"]) for geo, v in econ.items() if "bid_ceiling" in v}


class ASA:
    """Клиент v5 с ретраями на сетевые обрывы."""

    def __init__(self, org_id=None):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from platform_api import PlatformAPI
        api = PlatformAPI(org_id=org_id)
        self.h = {"Authorization": f"Bearer {api.token()}",
                  "Content-Type": "application/json",
                  "X-AP-Context": f"orgId={api.org_id}"}

    def _req(self, method, path, body=None, tries=4):
        last = None
        for i in range(tries):
            try:
                r = requests.request(method, V5 + path, headers=self.h, json=body, timeout=60)
                if r.status_code >= 300:
                    raise RuntimeError(f"{method} {path} -> {r.status_code} {r.text[:250]}")
                return r.json()["data"]
            except requests.exceptions.RequestException as e:
                last = e
                if i == tries - 1:
                    break
                time.sleep(2 * (i + 1))
        raise RuntimeError(f"{method} {path}: сеть недоступна после {tries} попыток ({last})")

    def get(self, path):
        sep = "&" if "?" in path else "?"
        return self._req("GET", path + sep + "limit=1000")

    def post(self, path, body):
        return self._req("POST", path, body)

    def put(self, path, body):
        return self._req("PUT", path, body)

    # --- ставки ---

    def live_bids(self, campaign_id):
        """{adgroup_id: текущая defaultBidAmount} прямо из кабинета."""
        return {a["id"]: float(a["defaultBidAmount"]["amount"])
                for a in self.get(f"/campaigns/{campaign_id}/adgroups")}

    def zero_impression_adgroups(self, campaign_id, since, until):
        """{adgroup_id} с нулём показов за период — те, кто не входит в аукцион.

        Нужен, чтобы поднимать ставку точечно: адгруппе, которая уже получает
        показы, шаг только удорожает тот же трафик.
        """
        body = {"startTime": since, "endTime": until,
                "selector": {"orderBy": [{"field": "localSpend", "sortOrder": "DESCENDING"}],
                             "pagination": {"offset": 0, "limit": 1000}},
                "returnRecordsWithNoMetrics": True, "returnRowTotals": True}
        rows = self.post(f"/reports/campaigns/{campaign_id}/adgroups",
                         body)["reportingDataResponse"]["row"]
        return {r["metadata"]["adGroupId"] for r in rows
                if (r["total"] or {}).get("impressions", 0) == 0}

    def set_bid(self, campaign_id, adgroup_id, bid):
        """Ставит bid и на adgroup, и на его единственный keyword."""
        self.put(f"/campaigns/{campaign_id}/adgroups/{adgroup_id}",
                 {"defaultBidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}})
        kws = self.get(f"/campaigns/{campaign_id}/adgroups/{adgroup_id}/targetingkeywords")
        if kws:
            self.put(f"/campaigns/{campaign_id}/adgroups/{adgroup_id}/targetingkeywords/bulk",
                     [{"id": kws[0]["id"],
                       "bidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}}])

    def raise_bids(self, project, step, geos=None, dry_run=False,
                   zero_only_since=None, zero_only_until=None):
        """Поднимает ставки на step по всем активным keyword-адгруппам.

        Цель считается от ФАКТИЧЕСКОЙ ставки в кабинете, поэтому повторный
        запуск после обрыва не задваивает шаг. Ограничено потолком гео.

        zero_only_since/until — если заданы, шаг получают только адгруппы
        с нулём показов за этот период.
        """
        cfg = load_config(project)
        ceilings = bid_ceilings(cfg)
        changed = []
        for c in cfg["campaigns"]:
            geo = c["countries"][0]
            if not c.get("id") or "Kostenlos" in c["name"]:
                continue
            if geos and geo not in geos:
                continue
            cap = ceilings.get(geo)
            if cap is None:
                raise RuntimeError(
                    f"Нет потолка ставки для {geo}. Задай economics.by_geo.{geo}."
                    "bid_ceiling в campaigns_v2.json — без него шаг некуда ограничивать.")
            live = self.live_bids(c["id"])
            zero = (self.zero_impression_adgroups(c["id"], zero_only_since, zero_only_until)
                    if zero_only_since else None)
            for a in c["adgroups"]:
                if zero is not None and a.get("id") not in zero:
                    continue
                if not a.get("keyword") or a.get("status") == "PAUSED":
                    continue
                cur = live.get(a["id"], a["bid"])
                new = round(min(cur + step, cap), 2)
                if abs(new - cur) < 1e-6:
                    continue
                if not dry_run:
                    self.set_bid(c["id"], a["id"], new)
                    a["bid"] = new
                    save_config(project, cfg)   # после каждой адгруппы, не после кампании
                changed.append((geo, a["keyword"], cur, new))
        return changed


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Поднять ставки по всем активным адгруппам")
    ap.add_argument("--project", required=True, help="Папка проекта с config/campaigns_v2.json")
    ap.add_argument("--step", type=float, required=True, help="Шаг в USD, напр. 0.30")
    ap.add_argument("--geos", help="Через запятую: DE,AT,CH. По умолчанию все")
    ap.add_argument("--only-zero-impressions", action="store_true",
                    help="Поднимать только адгруппы без показов за период")
    ap.add_argument("--since", help="Начало периода для --only-zero-impressions (YYYY-MM-DD)")
    ap.add_argument("--until", help="Конец периода для --only-zero-impressions (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.only_zero_impressions and not (a.since and a.until):
        ap.error("--only-zero-impressions требует --since и --until")
    api = ASA()
    geos = [g.strip().upper() for g in a.geos.split(",")] if a.geos else None
    rows = api.raise_bids(a.project, a.step, geos, a.dry_run,
                          a.since if a.only_zero_impressions else None,
                          a.until if a.only_zero_impressions else None)
    for geo, kw, old, new in rows:
        print(f"  {geo} {kw[:30]:32} ${old:.2f} -> ${new:.2f}")
    print(f"\n{'(dry-run) ' if a.dry_run else ''}изменено: {len(rows)}")
