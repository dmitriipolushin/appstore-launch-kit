#!/usr/bin/env python3
"""Конкуренты-примеры по углам: детали из iTunes Lookup (скриншоты, иконка, рейтинг, описание) и AppStoreSpy
(subtitle, гео выручки/загрузок, рекламные сети), скачивание скриншотов и OCR текстов на них (macOS Vision).

  python3 apps.py --project P            # собрать кэш + скриншоты + OCR
  python3 apps.py --project P --digest   # вывести по углам: subtitle, тексты со скриншотов, начало описания —
                                         # из этого пишутся offer / job / hooks в config.json
  python3 apps.py --project P --ids 123,456 --digest   # то же для произвольных приложений (напр. без выручки)
"""
import argparse, json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from common import SKILL, angle_apps, load_config, load_json, new_cutoff, save_json

NETS = {"Facebook": "Meta", "FacebookNative": "Meta", "InstagramNative": "Meta", "facebookinstagramaudience": "Meta",
        "Instagram": "Meta", "Admob": "AdMob", "Applovin": "AppLovin", "Tiktok": "TikTok", "Inmobi": "InMobi"}


def nets_of(ads):
    out = set()
    for ad in (ads if isinstance(ads, list) else [ads] if ads else []):
        if not isinstance(ad, dict): continue
        n = ad.get("network"); n = "".join(n) if isinstance(n, list) else n
        if n: out.add(NETS.get(n, n))
        for k in ("video", "image"):
            u = ad.get(k).get("url", "") if isinstance(ad.get(k), dict) else ""
            if "/ios/" in u:
                x = u.split("/ios/")[1].split("/")[0]; out.add(NETS.get(x, x))
    return sorted(out)


def fetch(ids, cache, countries=("us", "gb", "fr", "de", "es", "jp")):
    import appstorespy as asp  # заодно подтягивает api_keys.env через env_setup
    need = [i for i in ids if "shots" not in cache.get(i, {})]
    if not need: return
    if not os.environ.get("APPSTORESPY_API_KEY", "").strip():
        sys.exit("❌ APPSTORESPY_API_KEY не задан — без него нет subtitle, гео выручки и рекламных сетей. "
                 "Впиши ключ в ~/.config/aso-tools/api_keys.env (шаблон — config/api_keys.env.example)")
    it = {}
    for cc in countries:
        left = [i for i in need if i not in it]
        for k in range(0, len(left), 50):
            r = requests.get("https://itunes.apple.com/lookup", params={"id": ",".join(left[k:k + 50]), "country": cc, "entity": "software"}, timeout=20).json()
            for x in r.get("results", []): it[str(x["trackId"])] = dict(x, _cc=cc)
            time.sleep(1)

    def spy(i):
        err = None
        for _ in range(3):
            try: return i, asp.get_app(i, fields=["name", "short", "top_countries_revenue", "top_countries_downloads", "advertised", "ads"]), None
            except asp.AppStoreSpyError as e: err = e; time.sleep(2)
        return i, {}, err
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(spy, need))
    sp = {i: d for i, d, _ in res}
    for i, _, err in res:
        if err: print(f"  ⚠️  AppStoreSpy не отдал {i}: {err} — в карточке не будет subtitle, гео и рекламы", file=sys.stderr)
    for i in need:
        x, s = it.get(i, {}), sp.get(i, {}) or {}
        s = s.get("data", s)
        cc = lambda lst: [c if isinstance(c, str) else (c.get("country") if isinstance(c, dict) else c[0]) for c in (lst or [])][:5]
        cache[i] = {"name": x.get("trackName") or s.get("name"), "subtitle": s.get("short"), "top_rev": cc(s.get("top_countries_revenue")),
                    "top_dl": cc(s.get("top_countries_downloads")), "advertised": s.get("advertised"), "networks": nets_of(s.get("ads")),
                    "icon": x.get("artworkUrl512") or x.get("artworkUrl100"), "shots": (x.get("screenshotUrls") or [])[:4],
                    "rating": x.get("averageUserRating"), "ratings": x.get("userRatingCount"), "desc": (x.get("description") or "")[:900],
                    "store_cc": x.get("_cc")}


def download_and_ocr(project, ids, cache):
    shots = Path(project) / "shots"; shots.mkdir(exist_ok=True)
    jobs = [(i, k, u.replace("320x480bb", "600x0w")) for i in ids for k, u in enumerate(cache.get(i, {}).get("shots") or [])]

    def get(j):
        i, k, u = j; f = shots / f"{i}_{k}.jpg"
        if not f.exists():
            r = requests.get(u, timeout=30)
            if r.ok: f.write_bytes(r.content)
    with ThreadPoolExecutor(8) as ex: list(ex.map(get, jobs))
    ocr = load_json(Path(project) / "cache_ocr.json", {})
    if all(f.name in ocr for f in shots.glob("*.jpg")): return
    ocr_bin = SKILL / "scripts" / "ocr"
    if not ocr_bin.exists():
        # OCR — только macOS Vision. Без него digest всё равно печатается: subtitle и описание есть.
        if sys.platform != "darwin" or not shutil.which("swiftc"):
            print("  ⚠️  OCR пропущен: нужен macOS и swiftc (Xcode Command Line Tools). "
                  "Тексты скриншотов в digest будут пустыми — опирайся на subtitle и описание", file=sys.stderr)
            return
        subprocess.run(["swiftc", "-O", str(SKILL / "scripts" / "ocr.swift"), "-o", str(ocr_bin)], check=True)
    out = Path(project) / "cache_ocr_new.json"
    subprocess.run([str(ocr_bin), str(shots), str(out)], check=True, capture_output=True)
    ocr.update(json.loads(out.read_text())); out.unlink()
    save_json(Path(project) / "cache_ocr.json", ocr)


def digest(project, groups, cache):
    ocr = load_json(Path(project) / "cache_ocr.json", {})
    for title, ids in groups:
        print(f"\n## {title}")
        for i in ids:
            x = cache.get(i, {})
            heads = [" | ".join(ocr.get(f"{i}_{k}.jpg", "").split(" | ")[:3]) for k in range(4)]
            print(f"* {x.get('name')} «{x.get('subtitle') or ''}»")
            print("   S:", " // ".join(h for h in heads if h)[:450])
            print("   D:", (x.get("desc") or "").replace("\n", " ")[:260])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--ids", help="произвольные App Store ID через запятую")
    a = ap.parse_args()
    P = Path(a.project); cfg = load_config(P)
    cutoff = new_cutoff(cfg["as_of"])
    cache = load_json(P / "cache_apps.json", {})
    if a.ids:
        groups = [("ids", a.ids.split(","))]
    else:
        groups = [(f'{an["id"]}: {an["title"]}', [x["id"] for x in angle_apps(P, an, cutoff)[0]]) for an in cfg["angles"]]
    ids = sorted({i for _, g in groups for i in g})
    fetch(ids, cache); save_json(P / "cache_apps.json", cache)
    download_and_ocr(P, ids, cache)
    print(f"ok: {len(ids)} приложений, скриншоты и OCR в {P}/shots, {P}/cache_ocr.json")
    if a.digest: digest(P, groups, cache)


if __name__ == "__main__":
    main()
