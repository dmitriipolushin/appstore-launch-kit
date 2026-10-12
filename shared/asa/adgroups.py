#!/usr/bin/env python3
"""Создание keyword-адгрупп Apple Search Ads (архитектура «1 ключ = 1 адгруппа»).

Почему отдельный модуль: `shared/asa/utils/asa_api.py` умеет создавать адгруппы,
но читает креды из api_keys.env напрямую, мимо окружения, — до второго кабинета
им не достучаться. Здесь переиспользуется клиент из bids.py, который берёт
креды через platform_api и потому работает с любым кабинетом.

Что делает за один вызов: создаёт адгруппу, кладёт в неё единственный EXACT-ключ
и дописывает её в campaigns_v2.json проекта. Идемпотентно по имени — адгруппа с
таким именем в кампании пропускается, повторный запуск ничего не задваивает.

Кампания выбирается по гео из конфига. Если на гео в конфиге несколько запущенных
кампаний (например, отдельная брендовая), нужен явный --campaign-id.

CLI:
    python3 shared/asa/adgroups.py --project ~/projects/myapp \
        --geo DE --bid 0.80 --keywords "kalorien zähler,kalorien app" --dry-run
    python3 shared/asa/adgroups.py --project ~/projects/myapp \
        --geo DE --campaign-id <id> --bid 0.80 --keywords "kalorien zähler"
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bids import ASA, load_config, save_config, bid_ceilings   # noqa: E402


def campaign_for_geo(cfg, geo, campaign_id=None):
    """Кампания конфига для гео. Несколько кандидатов без campaign_id — отказ, не догадка."""
    found = [c for c in cfg["campaigns"]
             if c.get("id") and geo in c.get("countries", [])
             and (campaign_id is None or str(c["id"]) == str(campaign_id))]
    if not found:
        raise RuntimeError(f"В конфиге нет запущенной кампании для гео {geo}"
                           + (f" с id {campaign_id}" if campaign_id else ""))
    if len(found) > 1:
        raise RuntimeError(f"На гео {geo} в конфиге несколько кампаний — укажи --campaign-id: "
                           + ", ".join(f"{c['id']} «{c.get('name', '')}»" for c in found))
    return found[0]


class AdGroupCreator(ASA):

    def existing_names(self, campaign_id):
        return {a["name"] for a in self.get(f"/campaigns/{campaign_id}/adgroups")}

    def create(self, campaign_id, name, bid, device_classes=("IPHONE",)):
        """Адгруппа + одноимённый EXACT-ключ. Возвращает (adgroup_id, keyword_id)."""
        body = {
            "name": name,
            "startTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000"),
            "automatedKeywordsOptIn": False,          # Search Match выключен всегда
            "pricingModel": "CPC",
            "defaultBidAmount": {"amount": f"{bid:.2f}", "currency": "USD"},
            "targetingDimensions": {
                "deviceClass": {"included": list(device_classes)}},
        }
        ag = self.post(f"/campaigns/{campaign_id}/adgroups", body)
        kw = self.post(
            f"/campaigns/{campaign_id}/adgroups/{ag['id']}/targetingkeywords/bulk",
            [{"text": name, "matchType": "EXACT",
              "bidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}}])
        return ag["id"], (kw[0]["id"] if kw else None)

    def add_keywords(self, project, geo, keywords, bid, dry_run=False, max_bid=None,
                     campaign_id=None):
        """Потолок из economics — ориентир: ставка выше него допустима (см. bids.py),
        печатается предупреждение. Жёсткий предел — только явный max_bid."""
        cfg = load_config(project)
        if max_bid is not None and bid > max_bid:
            raise RuntimeError(f"Ставка ${bid:.2f} выше заданного --max-bid ${max_bid:.2f}")
        cap = bid_ceilings(cfg).get(geo)
        if cap is None:
            print(f"  ⚠️  нет economics.by_geo.{geo}.bid_ceiling — сверить ставку не с чем")
        elif bid > cap:
            print(f"  ⚠️  ставка ${bid:.2f} выше потолка-ориентира {geo} ${cap:.2f}: допустимо, "
                  "но следи, чтобы фактический CPT не держался выше потолка")
        camp = campaign_for_geo(cfg, geo, campaign_id)
        have = self.existing_names(camp["id"])
        made = []
        for kw in keywords:
            kw = kw.strip()
            if not kw or kw in have:
                continue
            if dry_run:
                made.append((geo, kw, bid, None))
                continue
            agid, kwid = self.create(camp["id"], kw, bid)
            camp.setdefault("adgroups", []).append(
                {"id": agid, "name": kw, "keyword": kw, "keyword_id": kwid,
                 "bid": bid, "match_type": "EXACT", "status": "ENABLED"})
            save_config(project, cfg)      # после каждой адгруппы, не в конце
            made.append((geo, kw, bid, agid))
        return made


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Создать keyword-адгруппы (1 ключ = 1 адгруппа)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--geo", required=True)
    ap.add_argument("--campaign-id", help="Нужен, если на гео в конфиге несколько кампаний")
    ap.add_argument("--bid", type=float, required=True)
    ap.add_argument("--keywords", required=True, help="Через запятую")
    ap.add_argument("--max-bid", type=float, help="Явный жёсткий предел ставки (необязательно)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = AdGroupCreator().add_keywords(
        a.project, a.geo.upper(), a.keywords.split(","), a.bid, a.dry_run, a.max_bid,
        a.campaign_id)
    for geo, kw, bid, agid in rows:
        print(f"  {geo} {kw[:34]:36} ${bid:.2f}  {agid or ''}")
    print(f"\n{'(dry-run) ' if a.dry_run else ''}создано: {len(rows)}")
