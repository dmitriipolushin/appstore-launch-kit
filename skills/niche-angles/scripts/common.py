"""Общее для скриптов niche-angles: конфиг проекта, скор, чтение подниш.

Общий код кита лежит рядом симлинками на shared/ (appstorespy.py, env_setup.py,
asa/platform_api.py) — как в остальных скиллах. Поэтому скрипты работают и из клона,
и после install.sh, в том числе в режиме --copy, где симлинки разыменовываются.
"""
import csv, json, sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "asa"))


def new_cutoff(as_of):
    """«Новое» приложение — релиз не раньше, чем за 2 года до даты сбора."""
    y, rest = as_of[:4], as_of[4:]
    return f"{int(y) - 2}{rest}"


def load_config(project):
    return json.loads((Path(project) / "config.json").read_text())


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1))


def load_json(path, default=None):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else default


def sub_rows(project, sub):
    """Приложения подниши (include != 0) из sub/<sub>/candidates.csv, по убыванию выручки."""
    f = Path(project) / "sub" / sub / "candidates.csv"
    rows = []
    for r in csv.DictReader(open(f)):
        if r.get("include", "1") == "0": continue
        rows.append({"id": r["id"], "name": r["name"], "developer": r.get("developer_name", ""),
                     "revenue": float(r["revenue_month"] or 0), "downloads": float(r["downloads_month"] or 0),
                     "released": (r.get("release_date") or "")[:10]})
    return sorted(rows, key=lambda r: -r["revenue"])


def all_rows(project):
    """Все приложения всех подниш проекта (в т.ч. исключённые) — пул для явных списков apps."""
    pool = {}
    for f in (Path(project) / "sub").glob("*/candidates.csv"):
        for r in csv.DictReader(open(f)):
            pool.setdefault(r["id"], {"id": r["id"], "name": r["name"], "developer": r.get("developer_name", ""),
                                      "revenue": float(r["revenue_month"] or 0), "downloads": float(r["downloads_month"] or 0),
                                      "released": (r.get("release_date") or "")[:10]})
    return pool


def metrics(project, sub):
    return json.loads((Path(project) / "sub" / sub / "metrics.json").read_text())


def score(m):
    """Скор 0–100 «шансы соло-разработчика». Вес = максимум баллов; на опорном значении — половина веса,
    вдвое лучше и выше — полный вес, хуже — пропорционально меньше."""
    # У подниши без выручки niche_analyzer пишет new_share/rpd/leader = null — это 0 баллов, а не ошибка.
    c = {x["key"]: x["value"] for x in m["criteria"]}
    part = lambda ratio, w: w * min(max(ratio, 0), 2) / 2
    pts = {
        "Малых новых $5–30k (25)": part(c["small_new"] / 3, 25),
        "Доля новых (25)": part((c["new_share"] or 0) / 0.25, 25),
        "Доля лидера (15)": part(0.5 / c["leader"], 15) if c["leader"] else 0,
        "RPD (15)": part((c["rpd"] or 0) / 1.0, 15),
        "Выручка (10)": part(c["total"] / 300000, 10),
        "Зарабатывающих (10)": part(c["earning"] / 6, 10),
    }
    return round(sum(pts.values())), pts


def angle_apps(project, angle, cutoff):
    """Приложения-примеры угла: явный список apps, иначе новички подниши с выручкой ≥ $5k.
    Пустой список apps=[] — показать лидеров (новичков нет). Без выручки и без загрузок — не показываем."""
    leader = False
    if angle.get("apps") is None:
        apps = [r for r in sub_rows(project, angle["sub"]) if r["released"] >= cutoff and r["revenue"] >= 5000][:6]
    elif angle["apps"]:
        pool = all_rows(project)
        apps = [pool[i] for i in angle["apps"] if i in pool]
    else:
        apps, leader = sub_rows(project, angle["sub"])[:3], True
    return [a for a in apps if a["revenue"] or a["downloads"]], leader
