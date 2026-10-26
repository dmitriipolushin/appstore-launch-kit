#!/usr/bin/env python3
"""
Оценка ниши App Store по оценкам выручки AppStoreSpy.

Два шага, между ними — ручная чистка списка:

    # 1. собрать кандидатов: по словам в названии и/или от известных конкурентов
    python3 niche_analyzer.py collect --project ./niche-plant-id \
        --name "plant identifier" --name "plant id" --seed 1252497129

    # 2. проставить include=0 приложениям не из ниши в candidates.csv, затем
    python3 niche_analyzer.py score --project ./niche-plant-id

collect пишет <project>/candidates.csv и <project>/meta.json.
score печатает отчёт и сохраняет <project>/report.md и <project>/metrics.json.

Критерии «хорошей ниши» и пороги по умолчанию — в SCORE_DEFAULTS, каждый
порог переопределяется флагом score. Методология — skills/niche-analysis/SKILL.md.

Выручка и загрузки AppStoreSpy — модельная ОЦЕНКА за последний месяц,
глобальная (от страны запроса не зависит) и округлённая ступенями
(…, 6 000, 10 000, 30 000, …, 300 000, 900 000, 6 000 000). Пороговые сравнения
поэтому приблизительны: 79% и 81% доли лидера — по сути одно и то же.
"""

import argparse
import csv
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import date

try:
    import appstorespy as spy
except ImportError:  # вызов из другого каталога — добавим себя в path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import appstorespy as spy

PAGE_SIZE = 200
FIELDS = ["id", "name", "developer_name", "category", "category_type",
          "revenue_month", "downloads_month", "release_date"]
CSV_COLUMNS = ["include", "id", "name", "developer_name", "category",
               "category_type", "release_date", "revenue_month",
               "downloads_month", "source"]

SCORE_DEFAULTS = {
    "total_min": 300_000,      # суммарная выручка ниши в месяц, USD
    "earning_min": 5_000,      # с какой выручки в месяц приложение «зарабатывает»
    "earning_count_min": 6,    # зарабатывающих приложений больше пяти
    "new_years": 2,            # «новое» = релиз за последние N лет
    "new_share_min": 0.25,     # доля выручки новых приложений
    "rpd_min": 1.0,            # выручка на загрузку, USD
    "leader_share_max": 0.80,  # доля крупнейшего игрока (разработчика)
    "small_new_max": 30_000,   # потолок выручки «небольшого нового» приложения
    "small_new_count_min": 3,  # сколько таких нужно, чтобы ниша была открыта
}


# --------------------------------------------------------------------------
# collect
# --------------------------------------------------------------------------

def _revenue(app):
    return app.get("revenue_month") or 0


def _collect_by_name(term, category, category_type, max_pages):
    """Все приложения со словами term в названии, у которых есть выручка.

    Сортировка по убыванию выручки, поэтому листаем до первой нулевой —
    дальше только приложения без денег, кредиты на них не тратим.
    """
    flt = {"published": True, "name": term}
    if category:
        flt["category"] = category
    if category_type:
        flt["category_type"] = category_type
    found = []
    for page in range(1, max_pages + 1):
        data = spy.query_apps(flt, fields=FIELDS, sort="-revenue_month",
                              limit=PAGE_SIZE, page=page)["data"]
        earning = [a for a in data if _revenue(a) > 0]
        found.extend(earning)
        if len(earning) < len(data) or len(data) < PAGE_SIZE:
            return found, False
    return found, True  # упёрлись в max_pages, хвост мог остаться


def _collect_by_seed(app_id):
    """Сам seed и его похожие в обе стороны: кого показывают рядом и кто показывает его."""
    found = []
    seed = spy.get_app(app_id, fields=["id", "name", "developer_name", "category",
                                       "type", "revenue", "downloads", "released"])
    found.append({
        "id": seed.get("id") or app_id,
        "name": seed.get("name"),
        "developer_name": seed.get("developer_name"),
        "category": seed.get("category"),
        "category_type": seed.get("type"),
        "revenue_month": seed.get("revenue"),
        "downloads_month": seed.get("downloads"),
        "release_date": seed.get("released"),
    })
    for link in spy.SIMILAR_LINKS:
        data = spy.similar_apps(app_id, link=link, fields=FIELDS,
                                sort="-revenue_month", limit=100)["data"]
        found.extend(a for a in data if _revenue(a) > 0)
    return found


def _summary(term, category, category_type):
    """Сверочный агрегат AppStoreSpy по тому же фильтру; None, если тариф не пускает."""
    flt = {"published": True, "name": term}
    if category:
        flt["category"] = category
    if category_type:
        flt["category_type"] = category_type
    try:
        return spy.summary_apps(flt)
    except spy.AppStoreSpyError as e:
        print(f"  ⚠️  summary по «{term}» недоступен: {e}", file=sys.stderr)
        return None


def cmd_collect(args):
    if not args.name and not args.seed:
        sys.exit("❌ нужен хотя бы один --name или --seed")
    os.makedirs(args.project, exist_ok=True)

    apps = {}  # id → строка CSV
    sources = defaultdict(set)
    meta = {"as_of": date.today().isoformat(), "names": args.name or [],
            "seeds": args.seed or [], "category": args.category,
            "category_type": args.category_type, "summary": {}, "truncated": []}

    def add(found, source):
        for a in found:
            app_id = str(a["id"])
            sources[app_id].add(source)
            if app_id not in apps:
                cat = a.get("category")
                apps[app_id] = {
                    "include": 1,
                    "id": app_id,
                    "name": a.get("name") or "",
                    "developer_name": a.get("developer_name") or "",
                    "category": ",".join(cat) if isinstance(cat, list) else (cat or ""),
                    "category_type": a.get("category_type") or "",
                    "release_date": a.get("release_date") or "",
                    "revenue_month": _revenue(a),
                    "downloads_month": a.get("downloads_month") or 0,
                }

    for term in args.name or []:
        found, truncated = _collect_by_name(term, args.category, args.category_type,
                                            args.max_pages)
        print(f"  название «{term}»: {len(found)} приложений с выручкой"
              + (" (упёрлись в --max-pages)" if truncated else ""), file=sys.stderr)
        if truncated:
            meta["truncated"].append(term)
        add(found, f"name:{term}")
        meta["summary"][term] = _summary(term, args.category, args.category_type)

    for app_id in args.seed or []:
        found = _collect_by_seed(app_id)
        print(f"  seed {app_id}: {len(found)} приложений", file=sys.stderr)
        add(found, f"seed:{app_id}")

    rows = sorted(apps.values(), key=lambda r: -r["revenue_month"])
    for r in rows:
        r["source"] = ";".join(sorted(sources[r["id"]]))

    path = os.path.join(args.project, "candidates.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(args.project, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    total = sum(r["revenue_month"] for r in rows)
    print(f"\n{len(rows)} кандидатов, суммарно ${total:,.0f}/мес → {path}")
    print("Дальше: проставь include=0 приложениям не из ниши и запусти score.")


# --------------------------------------------------------------------------
# score
# --------------------------------------------------------------------------

def _years_ago(d, years):
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # 29 февраля
        return d.replace(year=d.year - years, day=28)


def _load(project, exclude):
    path = os.path.join(project, "candidates.csv")
    if not os.path.exists(path):
        sys.exit(f"❌ нет {path} — сначала collect")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    apps = []
    for r in rows:
        if r["include"].strip() in ("0", "") or r["id"] in exclude:
            continue
        r["revenue_month"] = float(r["revenue_month"] or 0)
        r["downloads_month"] = float(r["downloads_month"] or 0)
        apps.append(r)
    meta_path = os.path.join(project, "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    return apps, len(rows), meta


def compute(apps, as_of, t):
    """Метрики ниши и вердикт по каждому критерию. t — словарь порогов."""
    total = sum(a["revenue_month"] for a in apps)
    cutoff = _years_ago(as_of, t["new_years"]).isoformat()
    new = [a for a in apps if a["release_date"] and a["release_date"] >= cutoff]
    new_rev = sum(a["revenue_month"] for a in new)
    earning = [a for a in apps if a["revenue_month"] >= t["earning_min"]]

    # RPD — только по приложениям, у которых есть и выручка, и загрузки:
    # у части приложений модель AppStoreSpy не оценивает загрузки вовсе
    # (0 или null даже в estimates) — это «нет оценки», а не ноль установок.
    monetized = [a for a in apps if a["revenue_month"] > 0 and a["downloads_month"] > 0]
    monetized_rev = sum(a["revenue_month"] for a in monetized)
    rpd = (monetized_rev / sum(a["downloads_month"] for a in monetized)) if monetized else None
    rpd_median = (statistics.median(a["revenue_month"] / a["downloads_month"]
                                    for a in monetized) if monetized else None)

    # «Игрок» — разработчик: у одного издателя бывает несколько клонов в нише.
    by_dev = defaultdict(float)
    for a in apps:
        by_dev[a["developer_name"] or a["id"]] += a["revenue_month"]
    devs = sorted(by_dev.items(), key=lambda kv: -kv[1])
    leader, leader_rev = devs[0] if devs else ("—", 0)
    leader_share = leader_rev / total if total else None
    hhi = sum((v / total) ** 2 for v in by_dev.values()) if total else None
    top_app_share = (max(a["revenue_month"] for a in apps) / total) if total else None

    small_new = [a for a in new
                 if t["earning_min"] <= a["revenue_month"] <= t["small_new_max"]]
    new_share = new_rev / total if total else None

    criteria = [
        {"key": "total", "title": "Выручка ниши в месяц",
         "value": total, "threshold": f"≥ ${t['total_min']:,.0f}",
         "ok": total >= t["total_min"]},
        {"key": "earning", "title": f"Зарабатывающих приложений (≥ ${t['earning_min']:,.0f}/мес)",
         "value": len(earning), "threshold": f"≥ {t['earning_count_min']}",
         "ok": len(earning) >= t["earning_count_min"]},
        {"key": "new_share", "title": f"Доля выручки новых (релиз ≥ {cutoff})",
         "value": new_share, "threshold": f"≥ {t['new_share_min']:.0%}",
         "ok": new_share is not None and new_share >= t["new_share_min"]},
        {"key": "rpd", "title": "RPD ниши (выручка / загрузки)",
         "value": rpd, "threshold": f"≥ ${t['rpd_min']:.2f}",
         "ok": rpd is not None and rpd >= t["rpd_min"]},
        {"key": "leader", "title": "Доля крупнейшего игрока",
         "value": leader_share, "threshold": f"< {t['leader_share_max']:.0%}",
         "ok": leader_share is not None and leader_share < t["leader_share_max"]},
        {"key": "small_new",
         "title": f"Новых с выручкой ${t['earning_min']:,.0f}–{t['small_new_max']:,.0f}",
         "value": len(small_new), "threshold": f"≥ {t['small_new_count_min']}",
         "ok": len(small_new) >= t["small_new_count_min"]},
    ]
    return {
        "as_of": as_of.isoformat(),
        "new_cutoff": cutoff,
        "apps_count": len(apps),
        "total_revenue": total,
        "new_revenue": new_rev,
        "new_share": new_share,
        "earning_count": len(earning),
        "rpd": rpd,
        "rpd_median": rpd_median,
        "rpd_apps": len(monetized),
        "rpd_revenue_coverage": monetized_rev / total if total else None,
        "leader": leader,
        "leader_share": leader_share,
        "top_app_share": top_app_share,
        "hhi": hhi,
        "developers": [{"developer": d, "revenue": v, "share": v / total if total else None}
                       for d, v in devs],
        "small_new": [a["id"] for a in small_new],
        "criteria": criteria,
        # ниша не консолидирована = оба последних критерия разом
        "good": all(c["ok"] for c in criteria),
    }


def _money(v):
    return "—" if v is None else f"${v:,.0f}"


def _fmt(c):
    v = c["value"]
    if v is None:
        return "нет данных"
    if c["key"] == "total":
        return _money(v)
    if c["key"] == "rpd":
        return f"${v:.2f}"
    if c["key"] in ("new_share", "leader"):
        return f"{v:.0%}"
    return str(v)


def render(m, apps, meta, t, top):
    by_id = {a["id"]: a for a in apps}
    lines = []
    title = ", ".join(f"«{n}»" for n in meta.get("names", [])) or "ниша"
    lines.append(f"# Ниша: {title}")
    lines.append("")
    lines.append(f"Данные AppStoreSpy на {m['as_of']}: оценка модели за последний месяц, "
                 "глобально, округлено ступенями. Порядок величины, не факт.")
    lines.append("")
    verdict = "✅ ХОРОШАЯ — проходит все критерии" if m["good"] else \
        "❌ НЕ ПРОХОДИТ: " + "; ".join(c["title"] for c in m["criteria"] if not c["ok"])
    lines.append(f"**Вердикт: {verdict}**")
    lines.append("")
    lines.append("| Критерий | Значение | Порог | |")
    lines.append("|---|---|---|---|")
    for c in m["criteria"]:
        lines.append(f"| {c['title']} | {_fmt(c)} | {c['threshold']} | {'✅' if c['ok'] else '❌'} |")
    lines.append("")
    lines.append("Два последних критерия вместе — «ниша не консолидирована».")
    lines.append("")
    lines.append("## Дополнительно")
    lines.append("")
    lines.append(f"- Приложений с выручкой в нише: {m['apps_count']}")
    lines.append(f"- Выручка новых: {_money(m['new_revenue'])}")
    if m["rpd_median"] is not None:
        lines.append(f"- RPD посчитан по {m['rpd_apps']} приложениям с оценкой загрузок — "
                     f"это {m['rpd_revenue_coverage']:.0%} выручки ниши; у остальных "
                     "AppStoreSpy загрузки не оценивает")
        lines.append(f"- Медианный RPD по приложению: ${m['rpd_median']:.2f} "
                     "(RPD ниши взвешен выручкой и тянется к лидеру)")
    if m["top_app_share"] is not None:
        lines.append(f"- Крупнейший игрок: {m['leader']}; доля крупнейшего отдельного "
                     f"приложения {m['top_app_share']:.0%}")
    if m["hhi"] is not None:
        lines.append(f"- HHI по разработчикам: {m['hhi']:.2f} "
                     "(< 0.15 — раздроблено, > 0.25 — концентрировано)")
    for term, s in (meta.get("summary") or {}).items():
        if s:
            lines.append(f"- Сверка: AppStoreSpy summary по «{term}» — "
                         f"{s.get('total')} приложений, {_money(s.get('revenue'))}/мес "
                         "(включая приложения, исключённые из ниши)")
    if meta.get("truncated"):
        lines.append(f"- ⚠️ Список по {', '.join(meta['truncated'])} обрезан --max-pages: "
                     "выручка ниши занижена")
    lines.append("")

    lines.append(f"## Топ-{top} приложений по выручке")
    lines.append("")
    lines.append("| Приложение | Разработчик | Релиз | Выручка/мес | Загрузки/мес | RPD |")
    lines.append("|---|---|---|---|---|---|")
    for a in sorted(apps, key=lambda a: -a["revenue_month"])[:top]:
        rpd = f"${a['revenue_month'] / a['downloads_month']:.2f}" if a["downloads_month"] else "—"
        new_mark = " 🆕" if a["release_date"] >= m["new_cutoff"] else ""
        lines.append(f"| {a['name']} ({a['id']}){new_mark} | {a['developer_name']} | "
                     f"{a['release_date']} | {_money(a['revenue_month'])} | "
                     f"{a['downloads_month']:,.0f} | {rpd} |")
    lines.append("")

    new_apps = sorted((a for a in apps if a["release_date"] >= m["new_cutoff"]),
                      key=lambda a: -a["revenue_month"])
    lines.append(f"## Новые приложения (релиз ≥ {m['new_cutoff']}) — {len(new_apps)}")
    lines.append("")
    if new_apps:
        lines.append("| Приложение | Релиз | Выручка/мес | Загрузки/мес |")
        lines.append("|---|---|---|---|")
        for a in new_apps:
            lines.append(f"| {a['name']} ({a['id']}) | {a['release_date']} | "
                         f"{_money(a['revenue_month'])} | {a['downloads_month']:,.0f} |")
    else:
        lines.append("Ни одного нового приложения с выручкой.")
    lines.append("")

    lines.append("## Доли разработчиков")
    lines.append("")
    lines.append("| Разработчик | Выручка/мес | Доля |")
    lines.append("|---|---|---|")
    for d in m["developers"][:10]:
        share = f"{d['share']:.0%}" if d["share"] is not None else "—"
        lines.append(f"| {d['developer']} | {_money(d['revenue'])} | {share} |")
    lines.append("")
    return "\n".join(lines)


def cmd_score(args):
    exclude = {x.strip() for x in (args.exclude or "").split(",") if x.strip()}
    apps, candidates, meta = _load(args.project, exclude)
    if not apps:
        sys.exit("❌ после исключений в нише не осталось приложений")
    as_of = date.fromisoformat(args.as_of or meta.get("as_of") or date.today().isoformat())
    t = {k: getattr(args, k) for k in SCORE_DEFAULTS}

    m = compute(apps, as_of, t)
    m["thresholds"] = t
    m["candidates"] = candidates
    m["excluded"] = candidates - len(apps)
    report = render(m, apps, meta, t, args.top)

    with open(os.path.join(args.project, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(args.project, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(report)
    print(f"В расчёте {len(apps)} из {candidates} кандидатов "
          f"(исключено {m['excluded']}). Сохранено: report.md, metrics.json",
          file=sys.stderr)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="niche_analyzer.py",
        description="Оценка ниши App Store по выручке AppStoreSpy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Методология: skills/niche-analysis/SKILL.md",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("collect", help="собрать кандидатов в нишу → candidates.csv")
    p.add_argument("--project", required=True, help="каталог для файлов ниши")
    p.add_argument("--name", action="append",
                   help="слова в названии приложения; флаг можно повторять")
    p.add_argument("--seed", action="append",
                   help="ID известного приложения ниши: берётся оно и его похожие; можно повторять")
    p.add_argument("--category", help="ограничить --name категорией, напр. EDUCATION")
    p.add_argument("--category-type", choices=spy.CATEGORY_TYPES,
                   help="ограничить --name типом: APP или GAME")
    p.add_argument("--max-pages", type=int, default=5,
                   help=f"страниц по {PAGE_SIZE} на каждый --name (по умолчанию 5)")

    p = sub.add_parser("score", help="посчитать критерии по candidates.csv → report.md")
    p.add_argument("--project", required=True)
    p.add_argument("--exclude", help="ID через запятую — исключить в дополнение к include=0")
    p.add_argument("--as-of", help="дата отсчёта «новых», YYYY-MM-DD; по умолчанию дата collect")
    p.add_argument("--top", type=int, default=15, help="сколько приложений в топе отчёта")
    for key, default in SCORE_DEFAULTS.items():
        p.add_argument(f"--{key.replace('_', '-')}", dest=key,
                       type=type(default), default=default,
                       help=f"порог, по умолчанию {default}")
    return parser


def main():
    args = build_parser().parse_args()
    try:
        cmd_collect(args) if args.command == "collect" else cmd_score(args)
    except spy.AppStoreSpyError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
