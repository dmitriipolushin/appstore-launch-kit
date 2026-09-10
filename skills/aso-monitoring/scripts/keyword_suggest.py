#!/usr/bin/env python3
"""
Утилита для получения поисковых подсказок App Store.

Использует недокументированный Apple Search Hints API для получения
autocomplete-подсказок, которые видят пользователи при вводе в поиск App Store.

Pipeline integration:
    from keyword_suggest import run_for_project
    run_for_project(Path("projects/my_app"), country="us")

CLI usage:
    python3 keyword_suggest.py --term "calorie" --country us
    python3 keyword_suggest.py --seeds "calorie,diet,food tracker" --country mx
    python3 keyword_suggest.py --seeds "калории,счетчик" --countries kz,ru,ua
    python3 keyword_suggest.py --trends --country br
"""

import argparse
import json
import string
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

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

REQUEST_DELAY = 0.3  # секунд между запросами

CYRILLIC_LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"

# Пороги нормализации priority → тир популярности.
# Apple Hints priority: ~0–10000+. Значения эмпирические.
TIER_HIGH = 5000    # топовые запросы ниши
TIER_MEDIUM = 1000  # средняя популярность


def priority_to_tier(priority: int) -> str:
    """Нормализует Apple Hints priority в тир популярности (HIGH/MEDIUM/LOW)."""
    if priority >= TIER_HIGH:
        return "HIGH"
    if priority >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def get_storefront_header(country_code: str) -> str:
    """Возвращает значение заголовка X-Apple-Store-Front для страны."""
    store_id = STOREFRONT_IDS.get(country_code.lower())
    if not store_id:
        raise ValueError(
            f"Неизвестный код страны: {country_code}. "
            f"Доступные: {', '.join(sorted(STOREFRONT_IDS.keys()))}"
        )
    return f"{store_id},29"


def parse_hints_xml(xml_text: str) -> List[dict]:
    """Парсит XML-ответ Apple Hints API, возвращает список {term, priority}.

    Apple убрал поле priority из ответа (≈2024). Теперь используем позицию
    в списке как surrogate: position 1 → priority 10000, position N → 10000 - (N-1)*1000.
    """
    results = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    for dict_elem in root.iter("dict"):
        term = None
        priority = None
        keys = list(dict_elem)
        for i, elem in enumerate(keys):
            if elem.tag == "key" and elem.text == "term" and i + 1 < len(keys):
                term = keys[i + 1].text
            if elem.tag == "key" and elem.text == "priority" and i + 1 < len(keys):
                try:
                    priority = int(keys[i + 1].text)
                except (ValueError, TypeError):
                    priority = 0
        if term:
            p = priority or 0
            results.append({"term": term, "priority": p})

    # Если Apple не вернул priority (новый формат) — назначаем по позиции.
    # Position 1 = 10000, position 2 = 9000, ..., position 10 = 1000.
    if results and all(r["priority"] == 0 for r in results):
        total = len(results)
        for i, r in enumerate(results):
            r["priority"] = max(1000, 10000 - i * (9000 // max(total - 1, 1)))

    for r in results:
        r["tier"] = priority_to_tier(r["priority"])

    return results


def get_suggestions(term: str, country_code: str, media: str = "software") -> List[dict]:
    """Получает подсказки App Store для заданного запроса и страны."""
    params = {
        "clientApplication": "Software",
        "term": term,
        "media": media,
    }
    headers = {
        "X-Apple-Store-Front": get_storefront_header(country_code),
    }

    try:
        resp = requests.get(HINTS_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Ошибка запроса для '{term}' ({country_code}): {e}", file=sys.stderr)
        return []

    return parse_hints_xml(resp.text)


def get_trends(country_code: str) -> List[dict]:
    """Получает трендовые поисковые запросы для страны."""
    headers = {
        "X-Apple-Store-Front": get_storefront_header(country_code),
    }

    try:
        resp = requests.get(TRENDS_URL, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Ошибка запроса трендов ({country_code}): {e}", file=sys.stderr)
        return []

    return parse_hints_xml(resp.text)


def detect_alphabet(seed: str) -> str:
    """Определяет алфавит seed-фразы: 'cyrillic' или 'latin'."""
    for ch in seed:
        if ch in CYRILLIC_LETTERS or ch in CYRILLIC_LETTERS.upper():
            return "cyrillic"
    return "latin"


def expand_seeds(seeds: List[str], country_code: str) -> List[dict]:
    """
    Расширяет список seed-фраз через алфавитный перебор.

    Для каждого seed:
    1. Запрос подсказок по seed как есть
    2. seed + пробел + каждая буква алфавита

    Возвращает дедуплицированный список {term, priority, source}.
    """
    seen = set()
    results = []
    total_seeds = len(seeds)

    for idx, seed in enumerate(seeds, 1):
        seed = seed.strip()
        if not seed:
            continue

        alphabet = detect_alphabet(seed)
        letters = CYRILLIC_LETTERS if alphabet == "cyrillic" else string.ascii_lowercase

        total_queries = 1 + len(letters)
        print(f"\n[{idx}/{total_seeds}] Расширяем: '{seed}' ({alphabet}, {total_queries} запросов)")

        hints = get_suggestions(seed, country_code)
        for h in hints:
            if h["term"].lower() not in seen:
                seen.add(h["term"].lower())
                results.append({**h, "source": seed})
        print(f"  '{seed}' → {len(hints)} подсказок")
        time.sleep(REQUEST_DELAY)

        for letter in letters:
            query = f"{seed} {letter}"
            hints = get_suggestions(query, country_code)
            new_count = 0
            for h in hints:
                if h["term"].lower() not in seen:
                    seen.add(h["term"].lower())
                    results.append({**h, "source": f"{seed}+{letter}"})
                    new_count += 1
            if new_count > 0:
                print(f"  '{query}' → +{new_count} новых")
            time.sleep(REQUEST_DELAY)

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

    Returns summary dict: {seeds, hints_found, new_keywords_added, output_file}
    """
    from project_config import load_keywords

    project_dir = Path(project_dir)
    config_dir = project_dir / "config"
    raw_dir = project_dir / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    seeds = load_keywords(config_dir, sections=["primary"])
    if not seeds:
        print("⚠️  No [primary] keywords found in config/keywords.txt — skipping keyword discovery")
        return {"seeds": 0, "hints_found": 0, "new_keywords_added": 0, "output_file": None}

    print(f"🔍 Expanding {len(seeds)} primary seeds — country: {country.upper()}")
    results = expand_seeds(seeds, country)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = raw_dir / f"apple_hints_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {"seeds": seeds, "country": country, "results": results,
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
        "output_file": str(output_file),
    }


def print_table(suggestions: List[dict], show_source: bool = False):
    """Выводит подсказки в виде таблицы."""
    if not suggestions:
        print("Подсказок не найдено.")
        return

    suggestions.sort(key=lambda x: x["priority"], reverse=True)

    max_term = max(len(s["term"]) for s in suggestions)
    max_term = max(max_term, 10)

    if show_source:
        max_source = max(len(s.get("source", "")) for s in suggestions)
        max_source = max(max_source, 8)
        header = f"{'Подсказка':<{max_term}}  {'Приоритет':>9}  {'Тир':<6}  {'Источник':<{max_source}}"
        sep = "-" * len(header)
        print(f"\n{header}")
        print(sep)
        for s in suggestions:
            print(f"{s['term']:<{max_term}}  {s['priority']:>9}  {s.get('tier', ''):<6}  {s.get('source', ''):<{max_source}}")
    else:
        header = f"{'Подсказка':<{max_term}}  {'Приоритет':>9}  {'Тир':<6}"
        sep = "-" * len(header)
        print(f"\n{header}")
        print(sep)
        for s in suggestions:
            print(f"{s['term']:<{max_term}}  {s['priority']:>9}  {s.get('tier', ''):<6}")

    print(f"\nИтого: {len(suggestions)} подсказок")


def main():
    parser = argparse.ArgumentParser(
        description="Получение поисковых подсказок App Store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры:
  python3 keyword_suggest.py --term "calorie" --country us
  python3 keyword_suggest.py --seeds "calorie,diet,food" --country mx
  python3 keyword_suggest.py --seeds "калории,счетчик" --countries kz,ru,ua
  python3 keyword_suggest.py --trends --country br
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--term", "-t", help="Поисковый запрос для получения подсказок")
    group.add_argument("--seeds", "-s", help="Список seed-фраз через запятую для расширения")
    group.add_argument("--trends", action="store_true", help="Показать трендовые запросы")

    parser.add_argument("--country", "-c", help="Код страны (us, ru, mx, ...)")
    parser.add_argument("--countries", help="Коды стран через запятую (kz,ru,ua)")

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

    if args.trends:
        for country in countries:
            print(f"\n{'='*60}")
            print(f"Тренды: {country.upper()}")
            print(f"{'='*60}")
            trends = get_trends(country)
            print_table(trends)

    elif args.term:
        for country in countries:
            print(f"\n{'='*60}")
            print(f"Подсказки для '{args.term}' — {country.upper()}")
            print(f"{'='*60}")
            suggestions = get_suggestions(args.term, country)
            print_table(suggestions)

    elif args.seeds:
        seed_list = [s.strip() for s in args.seeds.split(",") if s.strip()]
        for country in countries:
            print(f"\n{'='*60}")
            print(f"Расширение seed-фраз — {country.upper()}")
            print(f"Seeds: {', '.join(seed_list)}")
            print(f"{'='*60}")
            results = expand_seeds(seed_list, country)
            print_table(results, show_source=True)


if __name__ == "__main__":
    main()
