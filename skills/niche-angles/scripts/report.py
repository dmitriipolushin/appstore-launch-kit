#!/usr/bin/env python3
"""HTML-отчёт по углам ниши из <project>/config.json + sub/*/metrics.json + кэшей apps.py и asa.py.

  python3 report.py --project P            # → P/report.html
  python3 report.py --project P --check    # только проверки: пересечения подниш, пустые офферы, нет метрик

Углы сортируются по скору «шансы соло-разработчика» (common.score). Порядок в config.json не важен.
"""
import argparse, glob, html, json, sys
from collections import defaultdict
from pathlib import Path
from common import all_rows, angle_apps, load_config, load_json, metrics, new_cutoff, score, sub_rows

e = lambda s: html.escape(str(s if s is not None else ""))
CCN = {"us": "США", "gb": "UK", "ca": "Канада", "au": "Австралия", "de": "Германия", "fr": "Франция", "es": "Испания", "it": "Италия",
       "br": "Бразилия", "mx": "Мексика", "jp": "Япония", "kr": "Корея", "tw": "Тайвань", "ar": "Аргентина", "nl": "Нидерланды",
       "be": "Бельгия", "se": "Швеция", "pt": "Португалия", "ae": "ОАЭ", "sa": "Сауд. Аравия", "in": "Индия", "cn": "Китай", "hk": "Гонконг",
       "vn": "Вьетнам", "th": "Таиланд", "ph": "Филиппины", "id": "Индонезия", "tr": "Турция", "pl": "Польша", "ch": "Швейцария",
       "at": "Австрия", "no": "Норвегия", "dk": "Дания", "fi": "Финляндия", "nz": "Нов. Зеландия", "za": "ЮАР", "uk": "UK", "ru": "Россия", "am": "Армения"}


def money(v):
    if v is None: return "—"
    v = float(v)
    if v >= 1e6: return f"${v/1e6:.1f}M".replace(".0M", "M")
    if v >= 1e3: return f"${v/1e3:.0f}k"
    return f"${v:.0f}"


def num(v):
    v = float(v or 0)
    return f"{v/1e6:.1f}M".replace(".0M", "M") if v >= 1e6 else f"{v/1e3:.0f}k" if v >= 1e3 else f"{v:.0f}"


def pct(v): return "—" if v is None else f"{float(v)*100:.0f}%"


def popcell(p):
    if p is None: return '<span class="muted">—</span>'
    return f'<span class="pp {"hi" if p >= 40 else "mid" if p >= 20 else "lo"}">{p}</span>'


def sclass(sc): return "hi" if sc >= 70 else "mid" if sc >= 50 else "lo"


def criteria(m):
    c = {x["key"]: x for x in m["criteria"]}
    return [("Выручка ≥ $300k", money(c["total"]["value"]), c["total"]["ok"]),
            ("≥ 6 зарабатывающих", c["earning"]["value"], c["earning"]["ok"]),
            ("Новые ≥ 25%", pct(c["new_share"]["value"]), c["new_share"]["ok"]),
            ("RPD ≥ $1", f'${c["rpd"]["value"] or 0:.2f}', c["rpd"]["ok"]),
            ("Лидер < 80%, ≥ 3 малых новых", f'{pct(c["leader"]["value"])}, {c["small_new"]["value"]} шт.', c["leader"]["ok"] and c["small_new"]["ok"])]


def geo(lst):
    return ", ".join(CCN.get(str(c).lower(), str(c).upper()) for c in (lst or [])[:3] if c) or "—"


def spark(vals):
    pts = [(i, v) for i, v in enumerate(vals) if v]
    if not pts: return '<span class="muted">—</span>'
    lo, hi = 40, 80
    xy = lambda i, v: f"{i * 8 + 2:.0f},{20 - (min(max(v, lo), hi) - lo) / (hi - lo) * 18:.1f}"
    segs, cur = [], []
    for i, v in enumerate(vals):
        if v: cur.append(xy(i, v))
        elif cur: segs.append(cur); cur = []
    if cur: segs.append(cur)
    lines = "".join(f'<polyline points="{" ".join(sg)}"/>' if len(sg) > 1 else
                    f'<circle cx="{sg[0].split(",")[0]}" cy="{sg[0].split(",")[1]}" r="1.6"/>' for sg in segs)
    return f'<svg class="spk" viewBox="0 0 94 22" width="94" height="22">{lines}</svg><span class="muted sm"> {pts[0][1]}→{pts[-1][1]}</span>'


def app_card(x, leader=False):
    shots = "".join(f'<img loading="lazy" src="{e(u)}" alt="">' for u in (x.get("shots") or [])[:4])
    rating = f'★ {x["rating"]:.1f} · {num(x.get("ratings"))} оценок' if x.get("rating") else ""
    desc = (x.get("desc") or "").strip().split("\n")[0][:220]
    nets = x.get("networks") or []
    return f'''<div class="comp">
  <div class="ch">{f'<img class="ic" src="{e(x["icon"])}" alt="">' if x.get("icon") else '<div class="ic"></div>'}
    <div><a class="cn" href="https://apps.apple.com/app/id{e(x["id"])}" target="_blank" rel="noopener">{e(x.get("name"))}</a>
    <div class="cs">{e(x.get("subtitle") or "")}</div></div></div>
  <div class="cm"><span><b>{money(x["revenue"])}</b>/мес</span><span>{num(x["downloads"])} загрузок/мес</span>
    <span>{"лидер, вышло" if leader else "вышло"} {e(x["released"][:7])}</span>{f"<span>{rating}</span>" if rating else ""}</div>
  <div class="cm"><span>Гео выручки: <b>{geo(x.get("top_rev"))}</b></span><span>Реклама: <b>{", ".join(nets) if nets else "не замечена"}</b></span></div>
  {f'<p class="cd">{e(desc)}</p>' if desc else ""}
  <div class="shots">{shots or '<span class="muted sm">скриншоты недоступны</span>'}</div>
</div>'''


def offer_box(an):
    if not an.get("offer"): return ""
    return (f'<div class="ojb"><div><span class="lb">Главный оффер</span><p>{e(an["offer"])}</p></div>'
            f'<div><span class="lb">Главная джоба</span><p>{e(an.get("job"))}</p></div>'
            f'<div class="hk"><span class="lb">Крючки на скриншотах</span>{"".join(f"<i>{e(h)}</i>" for h in an.get("hooks", []))}</div></div>')


def asa_block(an, POP, RAW):
    a = an.get("asa") or {}
    if not a.get("verdict") and not a.get("terms"): return ""
    months = RAW.get("months", [])
    rows = ""
    for cc, term, kind in a.get("terms", []):
        cc, term = cc.lower(), term.lower()
        others = sorted(((c, POP.get(f"{c}|{term}")) for c in CCN if c != cc and POP.get(f"{c}|{term}")), key=lambda x: -x[1])
        tr = RAW.get("trend", {}).get(f"{cc}|{term}", {})
        rows += (f'<tr><td>{e(term)}</td><td><span class="kd {kind}">{"бренд" if kind == "b" else "общий"}</span></td>'
                 f'<td class="c">{CCN.get(cc, cc.upper())}</td><td class="r">{popcell(POP.get(f"{cc}|{term}"))}</td><td>{spark([tr.get(m) for m in months])}</td>'
                 f'<td class="sm muted">{", ".join(f"{CCN.get(c, c)} {v}" for c, v in others[:5]) or "—"}</td></tr>')
    period = f"{months[0][5:]}.{months[0][:4]} → {months[-1][5:]}.{months[-1][:4]}" if months else ""
    table = (f'<div class="tw"><table class="asa"><tr><th>Головной запрос</th><th>Тип</th><th class="c">Страна</th><th class="r">Popularity</th>'
             f'<th>Тренд {period}</th><th>Другие страны</th></tr>{rows}</table></div>') if rows else ""
    return f'<div class="asab"><span class="lb">Apple Ads: поисковый спрос</span><p>{e(a.get("verdict"))}</p>{table}</div>'


def asa_max(an, POP):
    t = (an.get("asa") or {}).get("terms", [])
    g = [(POP.get(f"{cc.lower()}|{x.lower()}") or 0, cc.lower()) for cc, x, k in t if k == "g"]
    b = [(POP.get(f"{cc.lower()}|{x.lower()}") or 0, cc.lower()) for cc, x, k in t if k == "b"]
    if g and max(g)[0]: v, cc = max(g); return f'{popcell(v)} <span class="muted sm">{CCN.get(cc, cc)}</span>'
    if b and max(b)[0]: v, cc = max(b); return f'<span class="muted sm">только бренды: {v}</span>'
    return '<span class="muted sm">ниже порога</span>'


def hint_positions(P):
    pos = {}
    for f in glob.glob(str(P / "hints*.json")):
        d = json.load(open(f))
        for cc, v in d.items():
            for r in v.get("results", []): pos[(cc.lower(), r["term"].lower())] = r.get("best_position")
    return pos


def check(P, cfg):
    ok = True
    where = defaultdict(list)
    for an in cfg["angles"]:
        if not (P / "sub" / an["sub"] / "metrics.json").exists():
            print(f"✗ {an['id']}: нет sub/{an['sub']}/metrics.json — запусти niche_analyzer score"); ok = False; continue
        for r in sub_rows(P, an["sub"]):
            if r["revenue"] > 0: where[r["id"]].append(an["id"])
        if not an.get("offer"): print(f"! {an['id']}: нет offer/job/hooks")
        if not (an.get("asa") or {}).get("verdict"): print(f"! {an['id']}: нет asa.verdict")
    pool = all_rows(P)
    for i, ids in where.items():
        if len(set(ids)) > 1:
            print(f"! пересечение: {pool.get(i, {}).get('name', i)} (${pool.get(i, {}).get('revenue', 0)/1e3:.0f}k) засчитан в {sorted(set(ids))} — оставь в одном углу (include=0 в остальных)"); ok = False
    print("проверки пройдены" if ok else "есть замечания")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    P = Path(a.project); cfg = load_config(P)
    check(P, cfg)
    if a.check: return
    cutoff = new_cutoff(cfg["as_of"])
    cache = load_json(P / "cache_apps.json", {})
    POP = load_json(P / "popularity.json", {})
    RAW = load_json(P / "asa_raw.json", {})
    hpos = hint_positions(P)
    items = []
    for an in cfg["angles"]:
        m = metrics(P, an["sub"]); sc, pts = score(m)
        apps, leader = angle_apps(P, an, cutoff)
        n_new = sum(1 for r in sub_rows(P, an["sub"]) if r["released"] >= cutoff and r["revenue"] >= 5000)
        items.append((sc, pts, an, m, apps, leader, n_new))
    items.sort(key=lambda x: -x[0])
    cards, srows = "", ""
    missing = []
    for pos, (sc, pts, an, m, apps, leader, n_new) in enumerate(items, 1):
        crit = criteria(m)
        kws = sorted(an.get("keywords", []), key=lambda k: -(POP.get(f'{k.get("country", "us").lower()}|{k["kw"].lower()}') or -1))
        kw_rows = "".join(
            f'<tr><td>{e(k["kw"])}</td><td class="c">{e(k.get("country", "us").upper())}</td>'
            f'<td class="r">{popcell(POP.get(k.get("country", "us").lower() + "|" + k["kw"].lower()))}</td>'
            f'<td class="r muted">{e(hpos.get((k.get("country", "us").lower(), k["kw"].lower())) or "—")}</td></tr>' for k in kws)
        comps = ""
        for x in apps:
            c = cache.get(x["id"])
            if not c: missing.append(x["id"]); c = {}
            comps += app_card({**c, **x}, leader)
        comp_title = an.get("comp_note") or ("Новых зарабатывающих приложений в этом угле нет — ниже лидеры (старые приложения)" if leader
                                             else f"Новички угла (вышли после {cutoff[:7]}, выручка ≥ $5k): {n_new} шт., показаны главные")
        cards += f'''<article class="ang" id="{e(an["id"])}">
  <div class="ah"><span class="rk">{pos}</span><h3>{e(an["title"])}</h3>
    <span class="sc {sclass(sc)}" title="{e(", ".join(f"{k}: {v:.0f}" for k, v in pts.items()))}">скор {sc}</span>
    <span class="muted sm">критериев выполнено: {sum(c[2] for c in crit)}/5</span>{f'<span class="pill fail">{e(an["score_note"])}</span>' if an.get("score_note") else ""}</div>
  {offer_box(an)}
  <p class="ess">{e(an.get("essence"))}</p>
  <div class="crit">{"".join(f'<span class="ck {"y" if c[2] else "n"}"><i>{"✓" if c[2] else "✗"}</i>{e(c[0])}: <b>{e(c[1])}</b></span>' for c in crit)}</div>
  {asa_block(an, POP, RAW)}
  <h4>{e(comp_title)}</h4>
  <div class="comps">{comps}</div>
  {f'<details><summary>Ключи для Apple Ads ({len(kws)}) — EXACT, 1 ключ = 1 адгруппа; «—» = ниже порога головной выборки</summary><div class="tw"><table class="kw"><tr><th>Ключ</th><th class="c">Гео</th><th class="r">Popularity</th><th class="r">Позиция в подсказках</th></tr>{kw_rows}</table></div></details>' if kws else ""}
</article>'''
        srows += (f'<tr><td><a href="#{e(an["id"])}">{pos}. {e(an["title"])}</a></td><td><span class="sc {sclass(sc)}">{sc}</span></td>'
                  f'<td class="r">{money(m["total_revenue"])}</td><td class="r">{pct(m["new_share"])}</td><td class="r">{len(m["small_new"])}</td>'
                  f'<td>{asa_max(an, POP)}</td><td class="sm">{e(an.get("offer", ""))}</td></tr>')
    rej = cfg.get("rejected") or []
    rej_html = ("<details class='rej'><summary>Какие углы проверили и отбросили</summary><ul>" +
                "".join(f"<li><b>{e(r['title'])}</b> — {e(r['reason'])}</li>" for r in rej) + "</ul></details>") if rej else ""
    month = RAW.get("month")
    pop_note = (f"Popularity — Apple Ads Search Popularity (1–100) за {month}, официальные данные Apple по головным запросам; запросы ниже порога выборки (≈45–50) Apple не отдаёт — они помечены «—»."
                if POP else "Popularity Apple Ads не собиралась.")
    body = (f'<section class="niche"><div class="who">{e(cfg.get("participant", ""))}</div><h2>{e(cfg["niche"])}</h2>{cards}{rej_html}</section>')
    out = (TPL.replace("{{TITLE}}", e(cfg.get("title", "Углы ниши"))).replace("{{NICHE}}", e(cfg["niche"])).replace("{{ASOF}}", e(cfg["as_of"]))
           .replace("{{SUMM}}", srows).replace("{{BODY}}", body).replace("{{POPNOTE}}", pop_note))
    (P / "report.html").write_text(out, encoding="utf-8")
    if missing: print("! нет в кэше (запусти apps.py):", ", ".join(missing))
    print(f"ok: {P / 'report.html'} — {len(items)} углов")


TPL = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}}</title>
<style>
:root{--bg:#f6f6f4;--surface:#fcfcfb;--line:#e4e3df;--text:#0b0b0b;--text2:#52514e;--muted:#8a8984;--blue:#2a78d6;--good:#1a7f4b;--goodbg:#e3f4ea;--bad:#b42318;--badbg:#fdeceb;--warnbg:#fff4d6;--warn:#8a5a00}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121211;--surface:#1a1a19;--line:#2e2e2c;--text:#f0efec;--text2:#c3c2b7;--muted:#8d8c85;--blue:#3987e5;--good:#5cc98d;--goodbg:#173323;--bad:#f08b80;--badbg:#3a1a17;--warnbg:#3a2e10;--warn:#f0c860}}
:root[data-theme="dark"]{--bg:#121211;--surface:#1a1a19;--line:#2e2e2c;--text:#f0efec;--text2:#c3c2b7;--muted:#8d8c85;--blue:#3987e5;--good:#5cc98d;--goodbg:#173323;--bad:#f08b80;--badbg:#3a1a17;--warnbg:#3a2e10;--warn:#f0c860}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14.5px/1.5 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",sans-serif}
.wrap{max-width:1160px;margin:0 auto;padding:28px 16px 80px}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:26px;margin:0 0 6px}h2{font-size:22px;margin:0 0 16px}h3{font-size:17px;margin:0}h4{font-size:13px;margin:16px 0 8px;color:var(--text2);font-weight:500}
.lead{color:var(--text2);margin:0 0 18px;max-width:860px}.muted{color:var(--muted)}.sm{font-size:13px}
.card,.niche{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:22px}
.who{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font-weight:500;color:var(--text2);font-size:12.5px}.r{text-align:right;white-space:nowrap}.c{text-align:center}.tw{overflow-x:auto}
.sc{display:inline-block;min-width:34px;text-align:center;padding:1px 9px;border-radius:99px;font-size:12.5px;font-weight:600;white-space:nowrap}.sc.hi{background:var(--goodbg);color:var(--good)}.sc.mid{background:var(--warnbg);color:var(--warn)}.sc.lo{background:var(--badbg);color:var(--bad)}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;white-space:nowrap}.pill.fail{background:var(--badbg);color:var(--bad)}
.ang{border-top:1px solid var(--line);padding:18px 0 6px}.ang:first-of-type{border-top:0;padding-top:4px}
.ah{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.rk{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--text);color:var(--surface);font-size:13px;font-weight:600;flex:none}
.ess{margin:10px 0;max-width:900px;color:var(--text2)}
.asab{margin:12px 0;padding:12px 14px;border-radius:10px;border:1px solid var(--line)}.asab .lb,.ojb .lb{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}.asab p{margin:3px 0 8px;font-size:14px}
.asa td,.asa th{padding:5px 8px}.kd{font-size:11.5px;padding:1px 7px;border-radius:99px;border:1px solid var(--line)}.kd.b{color:var(--warn);background:var(--warnbg);border-color:transparent}
.spk{vertical-align:middle}.spk polyline{fill:none;stroke:var(--blue);stroke-width:1.6}.spk circle{fill:var(--blue)}
.ojb{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;margin:12px 0;padding:12px 14px;border-radius:10px;background:var(--bg);border:1px solid var(--line)}
.ojb p{margin:2px 0 0;font-size:14px}.ojb .hk{grid-column:1/-1}.ojb .hk i{display:inline-block;font-style:normal;font-size:12.5px;padding:1px 8px;margin:4px 6px 0 0;border-radius:99px;border:1px solid var(--line);background:var(--surface)}
.crit{display:flex;flex-wrap:wrap;gap:6px}.ck{font-size:12px;padding:2px 9px;border-radius:6px;color:var(--text2);border:1px solid var(--line)}.ck i{font-style:normal;margin-right:4px;font-weight:700}.ck.y i{color:var(--good)}.ck.n{background:var(--badbg)}.ck.n i{color:var(--bad)}
.comps{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.comp{border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:6px;min-width:0}
.ch{display:flex;gap:10px;align-items:center}.ic{width:48px;height:48px;border-radius:11px;flex:none;background:var(--line);object-fit:cover}
.cn{font-weight:600;font-size:14.5px}.cs{font-size:12.5px;color:var(--text2);font-style:italic}
.cm{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12.5px;color:var(--text2)}.cm b{color:var(--text)}.cd{font-size:12.5px;color:var(--text2);margin:0}
.shots{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px}.shots img{height:230px;width:auto;border-radius:8px;border:1px solid var(--line);flex:none;background:var(--line)}
details{margin:10px 0}summary{cursor:pointer;color:var(--text2);font-size:13.5px}.rej ul{font-size:13px;color:var(--text2)}
.kw{max-width:640px}.pp{display:inline-block;min-width:30px;text-align:center;border-radius:6px;padding:0 6px;font-weight:600}.pp.hi{background:var(--goodbg);color:var(--good)}.pp.mid{background:var(--warnbg);color:var(--warn)}.pp.lo{color:var(--muted)}
@media(max-width:700px){.ojb{grid-template-columns:1fr}.comps{grid-template-columns:1fr}.shots img{height:190px}.card,.niche{padding:16px}}
</style></head><body><div class="wrap">
<h1>{{NICHE}}: углы</h1>
<p class="lead">Конкретные позиционирования внутри ниши, отсортированные по скору «шансы соло-разработчика». Для каждого: главный оффер и джоба (по текстам скриншотов и описаниям новичков), суть угла, 5 критериев подниши, поисковый спрос в Apple Ads, новички со скриншотами App Store, гео и рекламными сетями. Выручка и загрузки — оценки AppStoreSpy за месяц (модель, а не факт), данные на {{ASOF}}. {{POPNOTE}}</p>
<div class="card"><h3 style="margin-bottom:10px">Все углы</h3><div class="tw"><table><tr><th>Угол</th><th>Скор</th><th class="r">Выручка подниши</th><th class="r">Доля новых</th><th class="r">Малых новых</th><th>Спрос в ASA (макс. общий)</th><th>Главный оффер</th></tr>{{SUMM}}</table></div>
<details><summary>Как считается</summary><ul class="sm"><li><b>Скор 0–100 — шансы соло-разработчика зайти в угол.</b> Веса: малые новички с $5–30k/мес — 25; доля выручки новых приложений — 25; доля лидера — 15; RPD — 15; выручка подниши — 10; число зарабатывающих — 10. На опорном значении критерий даёт половину веса, вдвое лучше и выше — полный вес, хуже — пропорционально меньше. Опорные значения: 3 малых новичка, 25% новых, лидер 50%, RPD $1, $300k, 6 зарабатывающих. 70+ — сильный угол, 50–69 — средний, ниже 50 — слабый. Наведите на скор — баллы по каждому критерию.</li>
<li><b>Подниша</b> — только приложения, которые продают именно это обещание; одно приложение засчитано только в одном угле. Пороги критериев: выручка ≥ $300k/мес; ≥ 6 приложений с выручкой ≥ $5k; приложения моложе 2 лет берут ≥ 25% выручки; RPD ≥ $1; лидер &lt; 80% и ≥ 3 новых приложения с $5–30k.</li>
<li><b>Гео выручки</b> — топ-3 страны приложения по выручке. <b>Реклама</b> — сети, где AppStoreSpy видел креативы (Apple Search Ads в этих данных не отслеживается). Приложения без выручки и без загрузок в отчёт не попадают.</li></ul></details></div>
{{BODY}}
</div></body></html>'''

if __name__ == "__main__":
    main()
