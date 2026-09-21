#!/usr/bin/env python3
"""
Защита от повторного расхождения базы знаний.

Проверяет два инварианта:
1. Общие файлы внутри скиллов остаются симлинками на knowledge/ и не битые.
   Реальный файл на месте симлинка = кто-то отредактировал копию → расхождение.
2. Пофайловые (aso_theory_base, aso_metrics_iteration) сознательно различаются
   между скиллами, но не должны расходиться в общей части: скрипт показывает
   объём расхождения, чтобы дрейф был виден до того, как станет проблемой.

Exit code 1, если нарушен инвариант 1.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["aso-collection", "aso-monitoring", "asa-launch", "asa-monitoring"]
# Строго общие: внутри скилла обязаны быть симлинком на knowledge/
SHARED = ["aso_algorithms.md", "aso_creatives.md", "aso_foundations.md",
          "aso_social_signals.md", "aso_metadata.md", "aso_keyword_research.md"]
# Общие с правом override: симлинк по умолчанию, но скилл может держать
# свою версию, если у неё есть содержательные добавления (например ASA-разделы).
OVERRIDABLE = ["aso_theory_base.md", "aso_metrics_iteration.md"]

fail = False

print("── общие файлы должны быть симлинками на knowledge/")
for skill in SKILLS:
    kdir = REPO / "skills" / skill / "knowledge"
    if not kdir.is_dir():
        print(f"  ⚠️  нет каталога {kdir.relative_to(REPO)}")
        continue
    for name in SHARED:
        p = kdir / name
        if not p.exists() and not p.is_symlink():
            print(f"  ✗ отсутствует       {skill}/{name}")
            fail = True
        elif not p.is_symlink():
            print(f"  ✗ РЕАЛЬНЫЙ ФАЙЛ     {skill}/{name} — правка ушла в копию, "
                  f"перенеси её в knowledge/{name} и верни симлинк")
            fail = True
        elif not p.exists():
            print(f"  ✗ битый симлинк     {skill}/{name} → {p.readlink()}")
            fail = True
if not fail:
    print(f"  ✓ все {len(SKILLS) * len(SHARED)} симлинков на месте и резолвятся")

print("\n── общие с override: своя версия допустима, если что-то добавляет")
for name in OVERRIDABLE:
    canon = REPO / "knowledge" / name
    if not canon.is_file():
        print(f"  ✗ нет канонического knowledge/{name}")
        fail = True
        continue
    for skill in SKILLS:
        p = REPO / "skills" / skill / "knowledge" / name
        if p.is_symlink():
            print(f"  ✓ симлинк   {skill}/{name}")
            continue
        if not p.is_file():
            continue
        out = subprocess.run(["diff", str(canon), str(p)],
                             capture_output=True, text=True).stdout
        adds = sum(1 for ln in out.splitlines() if ln.startswith(">"))
        drops = sum(1 for ln in out.splitlines() if ln.startswith("<"))
        if adds == 0:
            print(f"  ✗ БЕСПОЛЕЗНЫЙ override {skill}/{name}: ничего не добавляет "
                  f"(и отстал на {drops} строк) — заменить симлинком")
            fail = True
        else:
            note = f", отстал на {drops}" if drops else ""
            print(f"  ✓ override  {skill}/{name}: +{adds} строк{note}")

print("\n── общие скрипты должны быть симлинками на shared/")
SHARED_SCRIPTS = {
    "scripts/env_setup.py": "env_setup.py",
    "scripts/keyword_suggest.py": "keyword_suggest.py",
    "scripts/collect_profiles.py": "collect_profiles.py",
    "scripts/appstorespy.py": "appstorespy.py",
    "scripts/appstorespy_cli.py": "appstorespy_cli.py",
    "scripts/project_config.py": "project_config.py",
    "scripts/asa/keyword_popularity.py": "keyword_popularity.py",
    # ASA-тулкит, общий для asa-launch и asa-monitoring
    "scripts/asa/logic.py": "asa/logic.py",
    "scripts/asa/settings.py": "asa/settings.py",
    "scripts/asa/utils/asa_api.py": "asa/utils/asa_api.py",
    "scripts/asa/utils/create_secret.py": "asa/utils/create_secret.py",
    "scripts/asa/utils/geonames.py": "asa/utils/geonames.py",
    "scripts/asa/utils/parsing_data.py": "asa/utils/parsing_data.py",
    "scripts/asa/utils/reports.py": "asa/utils/reports.py",
}
n_ok = 0
for skill in SKILLS:
    for rel, canon in SHARED_SCRIPTS.items():
        p = REPO / "skills" / skill / rel
        if not p.exists() and not p.is_symlink():
            continue                      # скрипт этому скиллу не нужен
        if not p.is_symlink():
            print(f"  ✗ РЕАЛЬНЫЙ ФАЙЛ     {skill}/{rel} — перенеси правку в shared/{canon}")
            fail = True
        elif not p.exists():
            print(f"  ✗ битый симлинк     {skill}/{rel}")
            fail = True
        else:
            n_ok += 1
print(f"  ✓ {n_ok} симлинков на shared/ на месте")

print("\n── лишние копии общих файлов вне knowledge/")
strays = [p for p in (REPO / "skills").rglob("*.md")
          if p.name in SHARED and p.is_file() and not p.is_symlink()]
if strays:
    for p in strays:
        print(f"  ✗ {p.relative_to(REPO)}")
    fail = True
else:
    print("  ✓ нет")

sys.exit(1 if fail else 0)
