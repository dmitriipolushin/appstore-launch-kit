#!/usr/bin/env python3
"""
Поисковые подсказки App Store (autocomplete) и обход сидов по алфавиту.

Источник — недокументированный Apple Search Hints (MZSearchHints). Авторизация
не нужна. Ответ — ПОРЯДОК подсказок в конкретном сторфронте, а не объём запроса:
объём берётся только из Apple Ads Search Popularity.

Что важно знать про источник (замеры 2026-10, сторфронты DE/AT/CH):

  * Лимит. Больше ~2 запросов/с с одного IP → HTTP 429. Обход 43 сидов ×
    (сид + a–z) ≈ 1160 запросов занимает около 20 минут на страну. Скрипт держит
    общий темп на все потоки (--rate, по умолчанию 2 запроса/с, 3 потока),
    на 429 / 5xx / таймаут повторяет запрос с нарастающей паузой и притормаживает
    все потоки сразу, пока сервер просит подождать.
  * Неудача ≠ «нет подсказок». Раньше любая ошибка запроса возвращала [] — 429
    молча превращался в «подсказок нет» и обход терял данные. Теперь запрос,
    не прошедший после всех попыток, считается неудачным: он попадает в итоговый
    счётчик и в список failed, а get_suggestions бросает HintsError.
  * Кеш. Удачные ответы пишутся на диск (страна|терм → подсказки, по умолчанию
    ~/.cache/aso-tools/search_hints.jsonl, срок 7 дней). Повторный запуск берёт
    их оттуда — прерванный обход продолжается с места обрыва, а неудачные
    запросы дозапрашиваются.
  * priority. Apple больше не отдаёт поле priority (≈2024). Скрипт ставит
    суррогат по позиции в ответе: первая подсказка → 10000. При обходе a–z почти
    каждый термин где-то оказывается первым, поэтому priority у большинства
    одинаковый (10000) и тир HIGH/MEDIUM/LOW по нему НЕ информативен. Полезнее
    `hits` — в скольких ответах термин встретился — и `best_position`.
  * Названия приложений. Подсказки вида «Suno: AI Music & Song» — это названия
    приложений, а не запросы. Они отсеиваются по символам (: - & | – — · ™ ® ! ( )),
    вернуть их — --keep-app-names.

Pipeline integration:
    from keyword_suggest import run_for_project
    run_for_project(Path("projects/my_app"), country="us")

CLI usage:
    python3 keyword_suggest.py --term "calorie" --country us
    python3 keyword_suggest.py --seeds "calorie,diet,food tracker" --country mx
    python3 keyword_suggest.py --seeds "калории,счетчик" --countries kz,ru,ua
    python3 keyword_suggest.py --seeds "ki song,suno" --country de --depth 2 --out hints_de.json
    python3 keyword_suggest.py --trends --country br
"""

import argparse
import json
import random
import string
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Маппинг ISO-кодов стран на Apple Store Front IDs
STOREFRONT_IDS = {
    "us": "143441", "ru": "143469", "ua": "143492", "kz": "143517",
    "mx": "143468", "ar": "143505", "br": "143503", "il": "143491",
    "gb": "143444", "de": "143443", "fr": "143442", "es": "143454",
    "it": "143450", "ca": "143455", "au": "143460", "jp": "143462",
    "kr": "143466", "in": "143467", "tr": "143480", "sa": "143479",
    "ae": "143481", "co": "143501", "cl": "143483", "pe": "143507",
    "pl": "143478", "nl": "143452", "se": "143456", "no": "143457",
    "dk": "143458", "fi": "143447", "pt": "143453", "at": "143445",
    "ch": "143459", "be": "143446", "cz": "143489", "hu": "143482",
    "ro": "143487", "bg": "143526", "hr": "143494", "sk": "143496",
    "eg": "143516", "ng": "143561", "za": "143472", "ke": "143529",
    "ph": "143474", "th": "143475", "vn": "143471", "id": "143476",
    "my": "143473", "sg": "143464", "tw": "143470", "hk": "143463",
    "cn": "143465",
}

HINTS_URL = "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints"
TRENDS_URL = "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/trends"

DEFAULT_RATE = 2.0        # запросов/с на ВСЕ потоки; выше ~2/с Apple отвечает 429
DEFAULT_WORKERS = 3       # потоки только прячут задержку сети, темп держит DEFAULT_RATE
DEFAULT_RETRIES = 6       # паузы 2, 4, 8, 16, 32, 60 с — около двух минут на запрос
REQUEST_TIMEOUT = 15
DEFAULT_CACHE = Path.home() / ".cache" / "aso-tools" / "search_hints.jsonl"
CACHE_TTL_DAYS = 7
DEPTH2_LIMIT = 20         # сколько подсказок первого уровня раскрывать на depth 2

CYRILLIC_LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"

# Признаки названия приложения, а не поискового запроса:
# «Suno: AI Music», «Song Maker - AI», «Voice & Music», «Musi | Stream», «Lyrics – AI».
APP_NAME_MARKERS = (":", " - ", "&", "|", "–", "—", "·", "™", "®", "!", "(", ")")

# Тиры по суррогатному priority. Оставлены для совместимости: после обхода a–z
# у большинства терминов priority = 10000, и тир почти всегда HIGH.
TIER_HIGH = 5000
TIER_MEDIUM = 1000


class HintsError(RuntimeError):
    """Запрос к Search Hints не удался после всех попыток (это НЕ «нет подсказок»)."""


def priority_to_tier(priority: int) -> str:
    """Суррогатный priority → тир (HIGH/MEDIUM/LOW). Мало информативен, см. docstring модуля."""
    if priority >= TIER_HIGH:
        return "HIGH"
    if priority >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def position_priority(index: int, total: int) -> int:
    """Суррогат priority по позиции в ответе: 1-я → 10000, последняя → 1000."""
    return max(1000, 10000 - index * (9000 // max(total - 1, 1)))


def looks_like_app_name(term: str) -> bool:
    return any(m in term for m in APP_NAME_MARKERS)


def get_storefront_header(country_code: str) -> str:
    """Возвращает значение заголовка X-Apple-Store-Front для страны."""
    store_id = STOREFRONT_IDS.get(country_code.lower())
    if not store_id:
        raise ValueError(
            f"Неизвестный код страны: {country_code}. "
            f"Доступные: {', '.join(sorted(STOREFRONT_IDS.keys()))}"
        )
    return f"{store_id},29"


def _parse_terms(xml_text: str) -> List[Tuple[str, Optional[int]]]:
    """[(term, priority|None)] в порядке ответа. Битый XML → ValueError."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"не XML: {e}") from e
    out = []
    for dict_elem in root.iter("dict"):
        term, priority = None, None
        keys = list(dict_elem)
        for i, elem in enumerate(keys):
            if elem.tag == "key" and elem.text == "term" and i + 1 < len(keys):
                term = keys[i + 1].text
            if elem.tag == "key" and elem.text == "priority" and i + 1 < len(keys):
                try:
                    priority = int(keys[i + 1].text)
                except (ValueError, TypeError):
                    priority = None
        if term:
            out.append((term, priority))
    return out


def _to_hints(terms: List[Tuple[str, Optional[int]]]) -> List[dict]:
    """[(term, priority)] → [{term, priority, position, tier}].

    Если Apple не вернул priority (так с ≈2024) — суррогат по позиции.
    """
    total = len(terms)
    out = []
    for i, (term, pr) in enumerate(terms):
        p = pr if pr else position_priority(i, total)
        out.append({"term": term, "priority": p, "position": i + 1,
                    "tier": priority_to_tier(p)})
    return out


def parse_hints_xml(xml_text: str) -> List[dict]:
    """Парсит XML-ответ Apple Hints API → [{term, priority, position, tier}]."""
    try:
        return _to_hints(_parse_terms(xml_text))
    except ValueError:
        return []


class _Throttle:
    """Общий темп запросов для всех потоков и общая пауза после 429."""

    def __init__(self, rate: float):
        self.interval = 1.0 / rate if rate > 0 else 0.0
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            at = max(time.monotonic(), self.next_at)
            self.next_at = at + self.interval
        delay = at - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    def cooldown(self, seconds: float):
        """Сервер просит подождать: ни один поток не стартует раньше чем через seconds."""
        with self.lock:
            self.next_at = max(self.next_at, time.monotonic() + seconds)
            # Каждый 429 замедляет темп на 25%, но не реже раза в 2 секунды.
            self.interval = min(2.0, max(self.interval, 0.1) * 1.25)


class HintsCache:
    """Дисковый кеш ответов: одна строка JSONL на запрос, дописывается по ходу обхода."""

    def __init__(self, path, ttl_days: float = CACHE_TTL_DAYS):
        self.path = Path(path).expanduser()
        self.lock = threading.Lock()
        self.data: Dict[str, List[str]] = {}
        if not self.path.exists():
            return
        cutoff = time.time() - ttl_days * 86400
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue                 # строка, оборванная падением процесса
                if rec.get("ts", 0) >= cutoff:
                    self.data[rec["k"]] = rec["hints"]

    def get(self, key: str) -> Optional[List[str]]:
        return self.data.get(key)

    def put(self, key: str, hints: List[str]):
        with self.lock:
            self.data[key] = hints
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"k": key, "ts": int(time.time()), "hints": hints},
                                   ensure_ascii=False) + "\n")


class HintsClient:
    """Клиент Search Hints: общий темп, ретраи, кеш и счётчики обхода."""

    def __init__(self, rate: float = DEFAULT_RATE, retries: int = DEFAULT_RETRIES,
                 cache_path=DEFAULT_CACHE, cache_ttl_days: float = CACHE_TTL_DAYS,
                 timeout: float = REQUEST_TIMEOUT):
        self.throttle = _Throttle(rate)
        self.retries = retries
        self.timeout = timeout
        self.cache = HintsCache(cache_path, cache_ttl_days) if cache_path else None
        self._local = threading.local()
        self._lock = threading.Lock()
        self.stats = {"queries": 0, "cached": 0, "fetched": 0, "retries": 0, "failed": 0}
        self.failed: List[str] = []

    def _count(self, key: str, n: int = 1):
        with self._lock:
            self.stats[key] += n

    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = self._local.session = requests.Session()
        return s

    def _get(self, url: str, params: dict, country: str) -> str:
        headers = {"X-Apple-Store-Front": get_storefront_header(country)}
        last = ""
        for attempt in range(self.retries + 1):
            self.throttle.wait()
            pause = min(60.0, 2.0 * 2 ** attempt) + random.uniform(0, 1)
            try:
                r = self._session().get(url, params=params, headers=headers,
                                        timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as e:
                last = type(e).__name__
            else:
                if r.status_code == 200:
                    return r.text
                if r.status_code != 429 and r.status_code < 500:
                    raise HintsError(f"HTTP {r.status_code}")      # 4xx не лечится повтором
                last = f"HTTP {r.status_code}"
                if r.status_code == 429:
                    try:
                        pause = max(pause, float(r.headers.get("Retry-After", 0)))
                    except ValueError:
                        pass
                    self.throttle.cooldown(pause)
            if attempt < self.retries:
                self._count("retries")
                time.sleep(pause)
        raise HintsError(f"{last} после {self.retries + 1} попыток")

    def suggestions(self, term: str, country: str, media: str = "software") -> List[dict]:
        """Подсказки для запроса. Сбой после всех попыток → HintsError, не []."""
        country = country.lower()
        key = (f"{country}|{term.strip().lower()}" if media == "software"
               else f"{country}|{media}|{term.strip().lower()}")
        self._count("queries")
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                self._count("cached")
                return _to_hints([(t, None) for t in hit])
        text = self._get(HINTS_URL, {"clientApplication": "Software", "term": term,
                                     "media": media}, country)
        try:
            terms = _parse_terms(text)
        except ValueError as e:
            raise HintsError(str(e)) from e
        self._count("fetched")
        if self.cache is not None:
            self.cache.put(key, [t for t, _ in terms])
        return _to_hints(terms)

    def suggestions_or_none(self, term: str, country: str) -> Optional[List[dict]]:
        """Как suggestions, но сбой учитывается в stats/failed и возвращается None."""
        try:
            return self.suggestions(term, country)
        except HintsError as e:
            self._count("failed")
            with self._lock:
                self.failed.append(term)
            print(f"  ✗ '{term}' ({country}): {e}", file=sys.stderr, flush=True)
            return None

    def trends(self, country: str) -> List[dict]:
        text = self._get(TRENDS_URL, {}, country)
        try:
            return _to_hints(_parse_terms(text))
        except ValueError as e:
            raise HintsError(str(e)) from e


_default_client: Optional[HintsClient] = None


def _client() -> HintsClient:
    global _default_client
    if _default_client is None:
        _default_client = HintsClient()
    return _default_client


def get_suggestions(term: str, country_code: str, media: str = "software") -> List[dict]:
    """Подсказки App Store для запроса и страны.

    Пустой список = Apple действительно ничего не подсказывает. Сетевой сбой,
    429 или 5xx после всех повторов → HintsError (раньше тоже был [], что и
    теряло данные).
    """
    return _client().suggestions(term, country_code, media)


def get_trends(country_code: str) -> List[dict]:
    """Трендовые поисковые запросы для страны. Сбой → HintsError."""
    return _client().trends(country_code)


def detect_alphabet(seed: str) -> str:
    """Определяет алфавит seed-фразы: 'cyrillic' или 'latin'."""
    for ch in seed:
        if ch in CYRILLIC_LETTERS or ch in CYRILLIC_LETTERS.upper():
            return "cyrillic"
    return "latin"


def alphabet_queries(seed: str) -> List[str]:
    """Сам seed + seed + пробел + каждая буква алфавита."""
    letters = CYRILLIC_LETTERS if detect_alphabet(seed) == "cyrillic" else string.ascii_lowercase
    return [seed] + [f"{seed} {L}" for L in letters]


def is_niche(term: str, source: str) -> bool:
    """Подсказка уточняет свой сид: содержит его целиком и длиннее него.

    `ki song generator` для сида `ki song` — нишевая; `kim kardashian` — нет.
    """
    t, s = term.lower(), source.lower()
    return t != s and s in t


def expand_seeds(seeds: List[str], country_code: str, max_workers: int = DEFAULT_WORKERS,
                 depth: int = 1, depth2_limit: int = DEPTH2_LIMIT,
                 keep_app_names: bool = False, client: Optional[HintsClient] = None,
                 stats: Optional[dict] = None) -> List[dict]:
    """Расширяет seed-фразы алфавитным перебором.

    depth=1: для каждого seed — сам seed и `seed a` … `seed z`.
    depth=2: дополнительно так же раскрываются до depth2_limit нишевых подсказок
    первого уровня (см. is_niche) — самые частые по hits.

    Возвращает [{term, priority, priority_score, tier, hits, best_position, source,
    depth}], сначала самые частые (hits), затем по лучшей позиции.

    stats (если передан dict) заполняется счётчиками: queries, cached, fetched,
    retries, failed, failed_queries, app_names_filtered. failed > 0 значит, что
    обход неполный: повторный запуск возьмёт удачное из кеша и дозапросит остальное.
    """
    client = client or _client()
    seeds = [s.strip() for s in seeds if s and s.strip()]
    agg: Dict[str, dict] = {}
    filtered = set()

    def run_level(sources: List[str], level: int):
        items = [(src, q) for src in sources for q in alphabet_queries(src)]
        total = len(items)
        print(f"Уровень {level}: {len(sources)} сидов → {total} запросов, "
              f"{max_workers} потока, темп ≤ {1 / client.throttle.interval:.1f}/с"
              if client.throttle.interval else
              f"Уровень {level}: {len(sources)} сидов → {total} запросов",
              file=sys.stderr, flush=True)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            answers = pool.map(lambda it: client.suggestions_or_none(it[1], country_code), items)
            for done, ((src, _q), hints) in enumerate(zip(items, answers), 1):
                for h in hints or []:
                    key = h["term"].lower()
                    if not keep_app_names and looks_like_app_name(h["term"]):
                        filtered.add(key)
                        continue
                    a = agg.get(key)
                    if a is None:
                        agg[key] = {"term": h["term"], "priority": h["priority"],
                                    "best_position": h["position"], "hits": 1,
                                    "source": src, "depth": level}
                    else:
                        a["hits"] += 1
                        a["priority"] = max(a["priority"], h["priority"])
                        a["best_position"] = min(a["best_position"], h["position"])
                if done % 100 == 0 or done == total:
                    s = client.stats
                    print(f"  {done}/{total} · из кеша {s['cached']} · сбоев {s['failed']} "
                          f"· {len(agg)} терминов", file=sys.stderr, flush=True)

    run_level(seeds, 1)

    if depth >= 2:
        seed_set = {s.lower() for s in seeds}
        cands = [a for a in agg.values()
                 if a["depth"] == 1 and a["term"].lower() not in seed_set
                 and is_niche(a["term"], a["source"])]
        cands.sort(key=lambda a: (-a["hits"], a["best_position"], len(a["term"])))
        run_level([a["term"] for a in cands[:depth2_limit]], 2)

    results = sorted(agg.values(), key=lambda r: (-r["hits"], r["best_position"], r["term"]))
    for r in results:
        r["priority_score"] = r["priority"]
        r["tier"] = priority_to_tier(r["priority"])

    s = dict(client.stats, failed_queries=list(client.failed),
             app_names_filtered=len(filtered))
    if stats is not None:
        stats.update(s)
    print(f"Итог: запросов {s['queries']}, из кеша {s['cached']}, из сети {s['fetched']}, "
          f"повторов {s['retries']}, НЕУДАЧНЫХ {s['failed']}, отсеяно названий "
          f"приложений {s['app_names_filtered']}", file=sys.stderr, flush=True)
    if s["failed"]:
        print(f"⚠️  Обход неполный: {s['failed']} запросов без ответа "
              f"({', '.join(client.failed[:5])}{' …' if s['failed'] > 5 else ''}). "
              "Запусти ту же команду ещё раз — удачное возьмётся из кеша, "
              "дозапросятся только сбойные.", file=sys.stderr, flush=True)
    return results


def _update_discovered_keywords(config_dir: Path, new_terms: List[str]) -> int:
    """
    Append new terms to [discovered] section of keywords.txt.
    Terms already present in any section are skipped.
    Returns count of newly added terms.
    """
    keywords_file = config_dir / "keywords.txt"

    existing = set()
    content = ""
    if keywords_file.exists():
        content = keywords_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not (
                stripped.startswith("[") and stripped.endswith("]")
            ):
                existing.add(stripped.lower())

    to_add = [t for t in new_terms if t.lower() not in existing]
    if not to_add:
        return 0

    with open(keywords_file, "a", encoding="utf-8") as f:
        if "[discovered]" not in content:
            f.write("\n[discovered]\n")
        for term in to_add:
            f.write(term + "\n")

    return len(to_add)


def run_for_project(project_dir: Path, country: str = "us") -> dict:
    """
    Pipeline-integrated keyword discovery for a project.

    Reads [primary] seeds from config/keywords.txt, expands them via Apple
    Hints API, saves raw results to data/raw/apple_hints_TIMESTAMP.json, and
    adds newly discovered terms to the [discovered] section of keywords.txt.

    Returns summary dict: {seeds, hints_found, new_keywords_added, failed_queries, output_file}
    """
    from project_config import load_keywords

    project_dir = Path(project_dir)
    config_dir = project_dir / "config"
    raw_dir = project_dir / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    seeds = load_keywords(config_dir, sections=["primary"])
    if not seeds:
        print("⚠️  No [primary] keywords found in config/keywords.txt — skipping keyword discovery")
        return {"seeds": 0, "hints_found": 0, "new_keywords_added": 0,
                "failed_queries": 0, "output_file": None}

    print(f"🔍 Expanding {len(seeds)} primary seeds — country: {country.upper()}")
    stats: dict = {}
    results = expand_seeds(seeds, country, stats=stats)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = raw_dir / f"apple_hints_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {"seeds": seeds, "country": country, "results": results, "stats": stats,
             "collected_at": datetime.now().isoformat()},
            f, indent=2, ensure_ascii=False
        )
    print(f"  ✅ Saved {len(results)} hints → {output_file.name}")

    new_terms = [r["term"] for r in results]
    added = _update_discovered_keywords(config_dir, new_terms)
    print(f"  ✅ Added {added} new keywords to [discovered] in keywords.txt")

    return {
        "seeds": len(seeds),
        "hints_found": len(results),
        "new_keywords_added": added,
        "failed_queries": stats.get("failed", 0),
        "output_file": str(output_file),
    }


def print_table(suggestions: List[dict], show_source: bool = False):
    """Выводит подсказки в виде таблицы (порядок — как передан)."""
    if not suggestions:
        print("Подсказок не найдено.")
        return

    w = max(10, max(len(s["term"]) for s in suggestions))
    if show_source:
        ws = max(8, max(len(s.get("source", "")) for s in suggestions))
        header = f"{'Подсказка':<{w}}  {'hits':>4}  {'поз.':>4}  {'ур.':>3}  {'Источник':<{ws}}"
        print(f"\n{header}\n{'-' * len(header)}")
        for s in suggestions:
            print(f"{s['term']:<{w}}  {s['hits']:>4}  {s['best_position']:>4}  "
                  f"{s['depth']:>3}  {s.get('source', ''):<{ws}}")
    else:
        header = f"{'Подсказка':<{w}}  {'поз.':>4}"
        print(f"\n{header}\n{'-' * len(header)}")
        for s in suggestions:
            print(f"{s['term']:<{w}}  {s['position']:>4}")

    print(f"\nИтого: {len(suggestions)} подсказок")


def main():
    parser = argparse.ArgumentParser(
        description="Поисковые подсказки App Store (autocomplete)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры:
  python3 keyword_suggest.py --term "calorie" --country us
  python3 keyword_suggest.py --seeds "calorie,diet,food" --country mx
  python3 keyword_suggest.py --seeds "калории,счетчик" --countries kz,ru,ua
  python3 keyword_suggest.py --seeds "ki song,suno" --country de --depth 2 --out hints_de.json
  python3 keyword_suggest.py --trends --country br

Коды выхода: 0 — всё получено; 3 — обход неполный (часть запросов без ответа,
повтори ту же команду: удачное возьмётся из кеша); 1 — ошибка.
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--term", "-t", help="Поисковый запрос для получения подсказок")
    group.add_argument("--seeds", "-s", help="Список seed-фраз через запятую для расширения")
    group.add_argument("--trends", action="store_true", help="Показать трендовые запросы")

    parser.add_argument("--country", "-c", help="Код страны (us, ru, mx, ...)")
    parser.add_argument("--countries", help="Коды стран через запятую (kz,ru,ua)")
    parser.add_argument("--depth", type=int, choices=(1, 2), default=1,
                        help="2 — раскрыть ещё и нишевые подсказки первого уровня")
    parser.add_argument("--depth2-limit", type=int, default=DEPTH2_LIMIT,
                        help=f"Сколько подсказок раскрывать на depth 2 (по умолчанию {DEPTH2_LIMIT})")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Потоков (по умолчанию {DEFAULT_WORKERS})")
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE,
                        help=f"Запросов в секунду на все потоки (по умолчанию {DEFAULT_RATE}; "
                             "выше ~2 Apple отвечает 429)")
    parser.add_argument("--cache", default=str(DEFAULT_CACHE),
                        help="JSONL-кеш ответов (по умолчанию ~/.cache/aso-tools/search_hints.jsonl)")
    parser.add_argument("--cache-ttl-days", type=float, default=CACHE_TTL_DAYS)
    parser.add_argument("--no-cache", action="store_true", help="Не читать и не писать кеш")
    parser.add_argument("--keep-app-names", action="store_true",
                        help="Не отсеивать подсказки, похожие на названия приложений")
    parser.add_argument("--out", help="Сохранить результат --seeds в JSON (по странам)")

    args = parser.parse_args()

    countries = []
    if args.countries:
        countries = [c.strip().lower() for c in args.countries.split(",")]
    elif args.country:
        countries = [args.country.strip().lower()]
    else:
        parser.error("Укажите --country или --countries")

    for c in countries:
        if c not in STOREFRONT_IDS:
            print(
                f"Ошибка: неизвестная страна '{c}'. "
                f"Доступные: {', '.join(sorted(STOREFRONT_IDS.keys()))}",
                file=sys.stderr,
            )
            sys.exit(1)

    global _default_client
    _default_client = HintsClient(rate=args.rate,
                                  cache_path=None if args.no_cache else args.cache,
                                  cache_ttl_days=args.cache_ttl_days)

    if args.trends:
        for country in countries:
            print(f"\n{'='*60}\nТренды: {country.upper()}\n{'='*60}")
            try:
                print_table(get_trends(country))
            except HintsError as e:
                print(f"Ошибка: тренды {country.upper()} не получены — {e}", file=sys.stderr)
                sys.exit(1)

    elif args.term:
        for country in countries:
            print(f"\n{'='*60}\nПодсказки для '{args.term}' — {country.upper()}\n{'='*60}")
            try:
                hints = get_suggestions(args.term, country)
            except HintsError as e:
                print(f"Ошибка: подсказки не получены — {e}. Это сбой запроса, "
                      "а не «подсказок нет».", file=sys.stderr)
                sys.exit(1)
            if not args.keep_app_names:
                hints = [h for h in hints if not looks_like_app_name(h["term"])]
            print_table(hints)

    elif args.seeds:
        seed_list = [s.strip() for s in args.seeds.split(",") if s.strip()]
        incomplete = False
        dump = {}
        for country in countries:
            print(f"\n{'='*60}\nРасширение seed-фраз — {country.upper()}\n"
                  f"Seeds: {', '.join(seed_list)}\n{'='*60}")
            _default_client.stats = dict.fromkeys(_default_client.stats, 0)
            _default_client.failed = []
            stats: dict = {}
            results = expand_seeds(seed_list, country, max_workers=args.workers,
                                   depth=args.depth, depth2_limit=args.depth2_limit,
                                   keep_app_names=args.keep_app_names, stats=stats)
            print_table(results, show_source=True)
            incomplete |= stats["failed"] > 0
            dump[country] = {"seeds": seed_list, "depth": args.depth, "results": results,
                             "stats": stats, "collected_at": datetime.now().isoformat()}
        if args.out:
            Path(args.out).expanduser().write_text(
                json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n→ {args.out}")
        if incomplete:
            sys.exit(3)


if __name__ == "__main__":
    main()
