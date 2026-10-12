#!/usr/bin/env python3
"""Сверка кабинета Apple Ads с учётом проекта — первый шаг сессии asa-monitoring.

Только чтение: ничего в кабинете не меняет.

Ловит то, что не видно ни в конфиге проекта, ни в выгрузке метрик:
  1. Кампании аккаунта, которых нет в config/campaigns_v2.json и README.md
     проекта (так находятся кампании, которые завёл кто-то другой и никто не ведёт).
  2. ENABLED-адгруппы, где все ключи PAUSED: в интерфейсе адгруппа выглядит
     работающей, а показов нет и не будет. С Search Match такая адгруппа
     работает только через Search Match — это тоже отмечается.
  3. Кампании, адгруппы и ключи, изменённые после последней записи
     asa_changelog.md, — правки руками в кабинете или незаписанные сессии.

CLI:
    python3 shared/asa/reconcile.py --project ~/projects/myapp
    python3 shared/asa/reconcile.py --project ~/projects/myapp --since 2026-10-09
    python3 shared/asa/reconcile.py --project ~/projects/myapp --all-apps

Креды кабинета — из окружения (ASA_ORG_ID, ASA_CLIENT_ID, ASA_KEY_ID), как у bids.py:
если README проекта задаёт свой кабинет — экспортируй его переменные перед запуском.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bids import ASA, load_config   # noqa: E402

CHANGELOG_CANDIDATES = ("asa_changelog.md", "ASA/asa_changelog.md")
HEADING_DATE = re.compile(r"^#{2,4}\s+(\d{4}-\d{2}-\d{2})", re.M)


def find_changelog(project, explicit=None):
    if explicit:
        return Path(explicit).expanduser()
    for rel in CHANGELOG_CANDIDATES:
        p = Path(project).expanduser() / rel
        if p.exists():
            return p
    return None


def last_changelog_date(path):
    """Дата самой поздней записи `### YYYY-MM-DD …` или None."""
    if not path or not path.exists():
        return None
    dates = HEADING_DATE.findall(path.read_text(encoding="utf-8"))
    return max(dates) if dates else None


def project_refs(project, cfg):
    """Что проект знает о кампаниях: id/имена из конфига, id/имена из README."""
    in_config = {c["id"] for c in cfg.get("campaigns", []) if c.get("id")}
    names_config = {c.get("name") for c in cfg.get("campaigns", []) if c.get("name")}
    readme = Path(project).expanduser() / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    return in_config, names_config, text


def mention(cid, name, text):
    return bool(text) and (str(cid) in text or (name and name in text))


def scan(api, app_id=None):
    """Кампании, адгруппы и ключи кабинета: [(campaign, [adgroup], [keyword])]."""
    out = []
    for c in api.get("/campaigns"):
        if c.get("deleted"):
            continue
        if app_id and str(c.get("adamId")) != str(app_id):
            out.append((c, None, None))          # чужое приложение: только строка в списке
            continue
        ags = [a for a in api.get(f"/campaigns/{c['id']}/adgroups") if not a.get("deleted")]
        kws = [k for k in api.keywords(c["id"]) if not k.get("deleted")]
        out.append((c, ags, kws))
    return out


def silent_adgroups(camp, ags, kws):
    """ENABLED-адгруппы без единого ACTIVE-ключа (при наличии ключей)."""
    by_ag = {}
    for k in kws:
        by_ag.setdefault(k["adGroupId"], []).append(k)
    res = []
    for a in ags:
        ks = by_ag.get(a["id"], [])
        if a.get("status") != "ENABLED" or not ks:
            continue
        if any(k.get("status") == "ACTIVE" for k in ks):
            continue
        res.append((camp, a, len(ks), bool(a.get("automatedKeywordsOptIn"))))
    return res


def modified_since(camp, ags, kws, since):
    """Сущности с modificationTime (UTC) не раньше since (YYYY-MM-DD)."""
    res = []
    if (camp.get("modificationTime") or "")[:10] >= since:
        res.append(("кампания", camp["name"], camp.get("status"), camp["modificationTime"]))
    names = {a["id"]: a["name"] for a in ags}
    for a in ags:
        if (a.get("modificationTime") or "")[:10] >= since:
            res.append(("адгруппа", a["name"], a.get("status"), a["modificationTime"]))
    for k in kws:
        if (k.get("modificationTime") or "")[:10] >= since:
            res.append(("ключ", f"{k['text']} [{k['matchType']}] в «{names.get(k['adGroupId'], k['adGroupId'])}»",
                        f"{k.get('status')} ${float(k['bidAmount']['amount']):.2f}",
                        k["modificationTime"]))
    return res


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Сверка кабинета Apple Ads с учётом проекта (только чтение)")
    ap.add_argument("--project", required=True, help="Папка проекта с config/campaigns_v2.json")
    ap.add_argument("--changelog", help="Путь к asa_changelog.md (по умолчанию ищется в проекте)")
    ap.add_argument("--since", help="Искать изменения с этой даты (YYYY-MM-DD) вместо даты "
                                    "последней записи changelog")
    ap.add_argument("--all-apps", action="store_true",
                    help="Проверки 2–3 по кампаниям всех приложений аккаунта, не только app_id проекта")
    ap.add_argument("--json", help="Сохранить результат в JSON")
    a = ap.parse_args()

    cfg = load_config(a.project)
    app_id = None if a.all_apps else cfg.get("app_id")
    in_config, names_config, readme = project_refs(a.project, cfg)
    log = find_changelog(a.project, a.changelog)
    last = last_changelog_date(log)
    since = a.since or last

    api = ASA()
    data = scan(api, app_id)

    # 1. Кампании
    print("1. Кампании аккаунта" + (f" (детально — приложение {app_id})" if app_id else ""))
    unknown = []
    for c, _, _ in sorted(data, key=lambda t: (str(t[0].get("adamId")) != str(app_id),
                                               t[0].get("status") != "ENABLED", t[0]["name"])):
        known = []
        if c["id"] in in_config or c["name"] in names_config:
            known.append("конфиг")
        if mention(c["id"], c["name"], readme):
            known.append("README")
        own = not app_id or str(c.get("adamId")) == str(app_id)
        mark = "  " if known else "⚠ "
        if not known and own:
            unknown.append(c)
        geo = ",".join(c.get("countriesOrRegions") or [])
        geo = geo if len(geo) <= 14 else geo[:12] + "…"
        print(f"  {mark}{c['id']}  {c['name'][:40]:40} {c.get('status', ''):8} "
              f"{c.get('displayStatus', ''):9} {geo:14} app {c.get('adamId')}  "
              f"{'/'.join(known) or 'НЕ УЧТЕНА'}")
    if unknown:
        running = [c for c in unknown if c.get("status") == "ENABLED"]
        print(f"  → не учтено в проекте: {len(unknown)}, из них ENABLED: {len(running)}"
              + (" — " + ", ".join(c["name"] for c in running) if running else "")
              + ". Внести в README/конфиг или выяснить у владельца, чья это кампания.")

    # 2. Адгруппы без активных ключей
    print("\n2. ENABLED-адгруппы, где все ключи PAUSED")
    silent = []
    for c, ags, kws in data:
        if ags is None or c.get("status") != "ENABLED":
            continue
        silent.extend(silent_adgroups(c, ags, kws))
    if not silent:
        print("  нет")
    groups = {}
    for c, ag, n, sm in silent:
        groups.setdefault((c["name"], sm), []).append(f"{ag['name']}" + (f" ({n})" if n > 1 else ""))
    for (cname, sm), names in groups.items():
        note = ("работают только через Search Match" if sm
                else "не показываются, хотя в интерфейсе выглядят работающими")
        print(f"  ⚠ {cname}: {len(names)} адгрупп — {note}:")
        print("    " + ", ".join(names))
    if silent:
        print("  → поставить такие адгруппы на паузу или включить нужный ключ (с подтверждения пользователя).")

    # 3. Изменения после changelog
    changes = []
    print(f"\n3. Изменения в кабинете с {since or '—'}"
          + (f" (последняя запись {log.name}: {last})" if last else
             f" (changelog {'не найден' if not log else 'без датированных записей'})"))
    if since:
        for c, ags, kws in data:
            if ags is None:
                continue
            changes.extend((c["name"],) + m for m in modified_since(c, ags, kws, since))
        # С датой из changelog правки того же дня могут быть уже записаны —
        # их показываем отдельно; с явным --since подозрительно всё.
        later = [ch for ch in changes if a.since or ch[4][:10] > since]
        same = [ch for ch in changes if not a.since and ch[4][:10] == since]
        if not changes:
            print("  нет")
        for camp, kind, what, status, ts in sorted(later, key=lambda x: x[4]):
            print(f"  ⚠ {ts[:16]}  {camp[:24]:24} {kind:8} {what} — {status}")
        if same:
            print(f"  в день последней записи ({since}) изменено {len(same)} — сверь с записью:")
            for camp, kind, what, status, ts in sorted(same, key=lambda x: x[4])[:12]:
                print(f"    {ts[:16]}  {camp[:24]:24} {kind:8} {what} — {status}")
            if len(same) > 12:
                print(f"    … ещё {len(same) - 12}")
        if later:
            print("  → изменения позже последней записи changelog: выяснить, кто и зачем, и записать.")
    else:
        print("  пропущено: задай --since или --changelog")

    if a.json:
        Path(a.json).expanduser().write_text(json.dumps({
            "unknown_campaigns": [{"id": c["id"], "name": c["name"], "status": c.get("status")}
                                  for c in unknown],
            "silent_adgroups": [{"campaign": c["name"], "adgroup_id": ag["id"], "adgroup": ag["name"],
                                 "paused_keywords": n, "search_match": sm}
                                for c, ag, n, sm in silent],
            "changes_since": since,
            "changes": [dict(zip(("campaign", "kind", "what", "status", "modified"), ch))
                        for ch in changes],
        }, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
