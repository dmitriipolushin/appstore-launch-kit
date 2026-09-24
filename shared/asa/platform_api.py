#!/usr/bin/env python3
"""Apple Ads Platform API (api.ads.apple.com/v1).

Новое семейство эндпоинтов, которого нет в Campaign Management API v5.
Главное, ради чего он нужен:

  * `/v1/suggestions/keywords/query`        — подсказки ключей с popularity 0-100
  * `/v1/insights/apps/search-term-popularity/query` — официальный топ-500
                                              запросов на жанр на страну
  * `/v1/insights/apps/impression-share/query`

Авторизация та же, что у v5 (OAuth client_credentials + ES256 JWT), но другой
базовый URL и обязательный заголовок `X-AP-Context`.

Credentials — канонические `ASA_*` из `~/.config/aso-tools/api_keys.env`
(переменные окружения перекрывают файл). Приватный ключ — `ASA_KEYS_DIR`,
по умолчанию `~/.config/aso-tools/keys/`.

`ASA_ORG_ID` можно не задавать: если ключу доступен ровно один рекламный
аккаунт, он берётся из `/acls` автоматически.

CLI:
    python3 shared/asa/platform_api.py --list-accounts
    python3 shared/asa/platform_api.py --suggest-keywords --app-id 123 \
        --seeds "ki song,suno" --country DE

    # Проверить свой список ключей: какие в топ-500 жанра и с какой popularity
    python3 shared/asa/platform_api.py --popularity --countries DE,AT \
        --terms "schrittzähler,pilates zu hause,kalorienzähler"
    python3 shared/asa/platform_api.py --popularity --countries DE --terms-file universe_*.json

    # Топ жанра / все частые запросы со словом / понедельный срез
    python3 shared/asa/platform_api.py --popularity --countries DE --genre HEALTH_FITNESS
    python3 shared/asa/platform_api.py --popularity --countries US --contains song
    python3 shared/asa/platform_api.py --popularity --week 2026-09-13 --countries DE \
        --genre PHOTO_VIDEO --out week.csv

Без --month/--week берётся последний опубликованный месяц (Apple обновляет
месячные данные 5-го числа за предыдущий месяц).
"""
import datetime, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import env_setup  # noqa: F401  — подтягивает api_keys.env в окружение

import requests
from authlib.jose import jwt
from Cryptodome.PublicKey import ECC

BASE = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

# Жанры search-term-popularity. Других нет: MUSIC, MEDICAL, BOOKS, NAVIGATION,
# WEATHER и т.п. эндпоинт не знает — их запросы ищи в ENTERTAINMENT/LIFESTYLE.
POPULARITY_GENRES = (
    "BUSINESS", "EDUCATION", "ENTERTAINMENT", "FINANCE", "FOOD_DRINK", "GAMES",
    "HEALTH_FITNESS", "LIFESTYLE", "NEW_PUBLICATION", "PHOTO_VIDEO",
    "PRODUCTIVITY_UTILITIES", "SHOPPING", "SOCIAL_NETWORKING", "SPORTS", "TRAVEL",
)
POPULARITY_PAGE = 5000   # больше Apple не отдаёт за запрос (400 VALUE_OUT_OF_RANGE)
TERMS_CHUNK = 500        # IN принимает и 2000, режем с запасом
MAX_BACKOFF = 16         # сек, по рекомендации Apple для 429


def last_published_month(today=None) -> str:
    """Последний месяц, за который Apple уже выложила данные (обновление 5-го)."""
    today = today or datetime.datetime.utcnow().date()
    first = today.replace(day=1)
    prev = first - datetime.timedelta(days=1)
    if today.day < 6:
        prev = prev.replace(day=1) - datetime.timedelta(days=1)
    return prev.strftime("%Y-%m")


def week_start(date_str: str) -> datetime.date:
    """Воскресенье недели, в которую попадает дата (недели Apple — Вс–Сб)."""
    d = datetime.date.fromisoformat(date_str)
    return d - datetime.timedelta(days=(d.weekday() + 1) % 7)


def _keys_dir() -> Path:
    return Path(os.environ.get("ASA_KEYS_DIR",
                               str(Path.home() / ".config" / "aso-tools" / "keys")))


class PlatformAPI:
    """Клиент Platform API. Ретраит сетевые обрывы — важно для батч-правок."""

    def __init__(self, client_id=None, key_id=None, org_id=None,
                 team_id=None, pem_name=None):
        self.client_id = client_id or os.environ.get("ASA_CLIENT_ID")
        self.key_id = key_id or os.environ.get("ASA_KEY_ID")
        # teamId и clientId в Apple Ads совпадают. Если в окружении лежит
        # ASA_TEAM_ID от ДРУГОГО кабинета (частый случай при работе с двумя
        # аккаунтами — api_keys.env хранит один, а clientId переопределён
        # через окружение), Apple вернёт invalid_client. Берём clientId.
        env_team = os.environ.get("ASA_TEAM_ID")
        self.team_id = team_id or (env_team if env_team == self.client_id else self.client_id)
        self.org_id = org_id or os.environ.get("ASA_ORG_ID")
        self.pem_name = pem_name or os.environ.get("ASA_PRIVATE_KEY_NAME",
                                                   "apple_ads_private_key.pem")
        missing = [n for n, v in (("ASA_CLIENT_ID", self.client_id),
                                  ("ASA_KEY_ID", self.key_id)) if not v]
        if missing:
            raise RuntimeError(
                "Не заданы переменные Apple Search Ads: " + ", ".join(missing) + ".\n"
                "Заполни ~/.config/aso-tools/api_keys.env по образцу "
                "config/api_keys.env.example, либо передай их в окружении.")
        self._token = None

    # --- auth ---

    def token(self) -> str:
        if self._token:
            return self._token
        key_path = _keys_dir() / self.pem_name
        if not key_path.is_file():
            raise RuntimeError(
                f"Приватный ключ не найден: {key_path}\n"
                "Это приватная половина пары, публичную от которой ты загрузил в "
                "Apple Ads -> Account Settings -> API. Apple её не хранит и отдать "
                "не может: если потеряна, генерируй новую пару и загружай новый "
                "публичный ключ.")
        pk = ECC.import_key(key_path.read_text())
        if not pk.has_private():
            raise RuntimeError(f"{key_path} содержит публичный ключ. Нужен приватный.")
        now = int(datetime.datetime.utcnow().timestamp())
        secret = jwt.encode(
            header={"alg": "ES256", "kid": self.key_id},
            payload={"sub": self.client_id, "aud": "https://appleid.apple.com",
                     "iat": now, "exp": now + 86400 * 180, "iss": self.team_id},
            key=pk.export_key(format="PEM")).decode()
        r = requests.post(TOKEN_URL,
                          data={"grant_type": "client_credentials",
                                "client_id": self.client_id,
                                "client_secret": secret, "scope": "searchadsorg"},
                          headers={"Host": "appleid.apple.com",
                                   "Content-Type": "application/x-www-form-urlencoded"},
                          timeout=30)
        if r.status_code == 400 and "invalid_client" in r.text:
            raise RuntimeError(
                "Apple отклонил авторизацию (invalid_client). Обычная причина: "
                "публичный ключ в кабинете не соответствует приватному, которым "
                "подписываем, либо clientId/keyId от другого кабинета.")
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _resolve_org_id(self):
        """Без X-AP-Context Apple отвечает 403 «A required header was not
        specified». Если ASA_ORG_ID не задан, а аккаунт у ключа один — берём его."""
        if self.org_id:
            return self.org_id
        accs = self.accounts()
        if len(accs) != 1:
            names = ", ".join(f"{a['name']} (orgId={a['orgId']})" for a in accs) or "нет"
            raise RuntimeError(
                "ASA_ORG_ID не задан, а автоматически выбрать аккаунт нельзя — "
                f"доступны: {names}. Пропиши нужный ASA_ORG_ID в api_keys.env.")
        self.org_id = str(accs[0]["orgId"])
        return self.org_id

    def _headers(self, ctx=None):
        h = {"Authorization": f"Bearer {self.token()}",
             "Content-Type": "application/json"}
        h["X-AP-Context"] = ctx or f"adAccountId={self._resolve_org_id()}"
        return h

    def _post(self, path, body, ctx=None, tries=4, timeout=300):
        """POST с ретраем сетевых обрывов и 429.

        На 429 ждём Retry-After (затем RateLimit-Reset), удваивая паузу до
        MAX_BACKOFF. Если окно почти исчерпано — притормаживаем заранее.
        """
        last, backoff, net_fails = None, 1, 0
        while True:
            try:
                r = requests.post(BASE + path, headers=self._headers(ctx),
                                  json=body, timeout=timeout)
            except requests.exceptions.RequestException as e:
                last, net_fails = e, net_fails + 1
                if net_fails >= tries:
                    raise RuntimeError(
                        f"POST {path}: сеть недоступна после {tries} попыток ({last})")
                time.sleep(2 * net_fails)
                continue
            if r.status_code == 429:
                wait = r.headers.get("Retry-After") or r.headers.get("RateLimit-Reset")
                time.sleep(max(float(wait or 0), backoff))
                backoff = min(backoff * 2, MAX_BACKOFF)
                continue
            if r.status_code >= 300:
                raise RuntimeError(f"POST {path} -> {r.status_code} {r.text[:300]}")
            if r.headers.get("RateLimit-Remaining") == "0":
                time.sleep(float(r.headers.get("RateLimit-Reset") or 1))
            return r.json()

    # --- эндпоинты ---

    def accounts(self):
        """Рекламные аккаунты, доступные этому ключу. Первый вызов при отладке доступа."""
        r = requests.get(BASE + "/acls",
                         headers={"Authorization": f"Bearer {self.token()}"}, timeout=30)
        r.raise_for_status()
        return [a["adAccount"] for a in r.json()["result"]["acls"]]

    def keyword_suggestions(self, app_id, seeds=None, country=None, limit=100):
        """Подсказки ключей с popularity 0-100.

        ⚠️ Фильтр countriesOrRegions Apple фактически игнорирует — выдача по
        DE/AT/CH идентична. Popularity не привязана к стране, учитывай это.
        Без `seeds` возвращает общие головные запросы жанра, они бесполезны.
        """
        filters = [
            {"field": "promotedObjectId", "operator": "EQUALS", "value": [str(app_id)]},
            {"field": "promotedObjectType", "operator": "EQUALS", "value": ["APPSTORE_APP"]},
        ]
        if country:
            filters.append({"field": "countriesOrRegions", "operator": "IN",
                            "value": [country]})
        if seeds:
            filters.append({"field": "terms", "operator": "IN", "value": list(seeds)})
        res = self._post("/suggestions/keywords/query",
                         {"pagination": {"offset": 0, "limit": limit}, "filters": filters})
        return [{"text": x.get("text"), "popularity": x.get("popularity") or 0}
                for x in (res.get("result") or [])]

    def search_term_popularity(self, month=None, week=None, countries=None,
                               genres=None, terms=None, contains=None):
        """Официальный топ-500 запросов на жанр × страну.

        month — 'YYYY-MM' (хранится 15 месяцев) или week — любая дата недели
        Вс–Сб (65 недель). Без обоих — последний опубликованный месяц.
        Фильтры применяются на стороне Apple; terms — точный поиск по списку,
        регистр не важен; contains — подстрока.

        Покрытие — только голова: в DE порог ≈ 49 по searchPopularity1to100,
        в малых странах выше. Отсутствие ключа в выдаче значит «ниже порога».
        Один запрос может встретиться в нескольких жанрах — это разные строки.
        """
        if week:
            start = week_start(week)
            tr = {"granularity": "WEEKLY_SUN_SAT", "start": start.isoformat(),
                  "end": (start + datetime.timedelta(days=6)).isoformat()}
        else:
            first = f"{month or last_published_month()}-01"
            tr = {"granularity": "MONTHLY", "start": first, "end": first}

        base = []
        if countries:
            base.append({"field": "countryOrRegion", "operator": "IN",
                         "value": [c.upper() for c in countries]})
        if genres:
            bad = [g for g in genres if g not in POPULARITY_GENRES]
            if bad:
                raise ValueError(f"Неизвестные жанры: {bad}. "
                                 f"Допустимы: {', '.join(POPULARITY_GENRES)}")
            base.append({"field": "genre", "operator": "IN", "value": list(genres)})
        if contains:
            base.append({"field": "searchTerm", "operator": "CONTAINS", "value": contains})

        term_list = list(dict.fromkeys(t.strip().lower() for t in terms or [] if t.strip()))
        chunks = [term_list[i:i + TERMS_CHUNK]
                  for i in range(0, len(term_list), TERMS_CHUNK)] or [None]
        rows = []
        for chunk in chunks:
            filters = base + ([{"field": "searchTerm", "operator": "IN", "value": chunk}]
                              if chunk else [])
            offset = 0
            while True:
                body = {"timeRange": tr,
                        "fields": ["rankInGenre", "searchPopularityInGenre",
                                   "searchPopularity1to100", "searchPopularity1to5"],
                        "pagination": {"offset": offset, "pageSize": POPULARITY_PAGE}}
                if filters:
                    body["filters"] = filters
                page = (self._post("/insights/apps/search-term-popularity/query", body)
                        .get("result") or {}).get("rows") or []
                rows.extend(page)
                if len(page) < POPULARITY_PAGE:
                    break
                offset += POPULARITY_PAGE
        return rows


def _read_terms_file(path: Path):
    """Ключи из .txt (по одному на строку) или .json — список строк либо
    объектов с полем "term" (формат universe_*.json из aso-collection)."""
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return [x["term"] if isinstance(x, dict) else str(x) for x in data]
    return path.read_text(encoding="utf-8").splitlines()


def _print_terms_report(rows, terms, countries):
    """По каждому ключу и стране: popularity и места в жанрах, либо «ниже порога»."""
    found = {}
    for r in rows:
        found.setdefault((r["searchTerm"].lower(), r["countryOrRegion"]), []).append(r)
    for term in dict.fromkeys(t.strip().lower() for t in terms if t.strip()):
        print(f"\n  {term}")
        for cc in countries:
            hits = found.get((term, cc))
            if not hits:
                print(f"    {cc}  —  не в топ-500 ни одного жанра (ниже порога выборки)")
                continue
            top = max(hits, key=lambda r: r.get("searchPopularity1to100", 0))
            places = ", ".join(f"{h['genre']}#{h.get('rankInGenre')}"
                               for h in sorted(hits, key=lambda h: h.get("rankInGenre", 0)))
            print(f"    {cc}  pop={top.get('searchPopularity1to100'):>3}"
                  f"  ({top.get('searchPopularity1to5')}/5)  {places}")


def _write_rows(rows, path: Path):
    if path.suffix.lower() == ".csv":
        import csv
        cols = ["month", "week", "countryOrRegion", "genre", "searchTerm", "rankInGenre",
                "searchPopularityInGenre", "searchPopularity1to100", "searchPopularity1to5"]
        cols = [c for c in cols if any(c in r for r in rows)] or cols
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    else:
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=1))


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-accounts", action="store_true")
    ap.add_argument("--suggest-keywords", action="store_true")
    ap.add_argument("--popularity", action="store_true")
    ap.add_argument("--app-id")
    ap.add_argument("--seeds", help="Через запятую")
    ap.add_argument("--country", default="DE")
    ap.add_argument("--countries", default="DE,AT,CH")
    ap.add_argument("--month", help="YYYY-MM; по умолчанию последний опубликованный")
    ap.add_argument("--week", help="Любая дата недели Вс–Сб, YYYY-MM-DD")
    ap.add_argument("--genre", help="Через запятую: " + ", ".join(POPULARITY_GENRES))
    ap.add_argument("--terms", help="Свои ключи через запятую — точная проверка")
    ap.add_argument("--terms-file", help=".txt — ключ на строку; .json — universe_*.json из aso-collection")
    ap.add_argument("--contains", help="Все запросы с этой подстрокой")
    ap.add_argument("--top", type=int, default=50, help="Сколько строк печатать")
    ap.add_argument("--out", help="Путь для выгрузки: .csv или .json")
    a = ap.parse_args()
    api = PlatformAPI()

    if a.list_accounts:
        for acc in api.accounts():
            print(f"  {acc['name']}  orgId={acc['orgId']}")
        return

    if a.suggest_keywords:
        if not a.app_id:
            sys.exit("--app-id обязателен")
        seeds = [s.strip() for s in a.seeds.split(",")] if a.seeds else None
        rows = api.keyword_suggestions(a.app_id, seeds, a.country)
        for x in sorted(rows, key=lambda y: -y["popularity"]):
            print(f"  pop={x['popularity']:>3}  {x['text']}")
        if a.out:
            Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
            print(f"\n→ {a.out}")
        return

    if a.popularity:
        if a.month and a.week:
            sys.exit("Укажи что-то одно: --month или --week")
        ccs = [c.strip().upper() for c in a.countries.split(",") if c.strip()]
        genres = [g.strip().upper() for g in a.genre.split(",")] if a.genre else None
        terms = [t for t in (a.terms or "").split(",") if t.strip()]
        if a.terms_file:
            terms += _read_terms_file(Path(a.terms_file))
        period = (f"неделя с {week_start(a.week)}" if a.week
                  else f"месяц {a.month or last_published_month()}")
        try:
            rows = api.search_term_popularity(a.month, a.week, ccs, genres,
                                              terms or None, a.contains)
        except ValueError as e:
            sys.exit(str(e))
        print(f"{period}, {','.join(ccs)}: строк {len(rows)}")
        if terms:
            _print_terms_report(rows, terms, ccs)
        else:
            rows.sort(key=lambda r: (-r.get("searchPopularity1to100", 0),
                                     r["countryOrRegion"], r.get("rankInGenre", 0)))
            for r in rows[:a.top]:
                print(f"  {r['countryOrRegion']}  pop={r.get('searchPopularity1to100'):>3}"
                      f"  ({r.get('searchPopularity1to5')}/5)"
                      f"  {r['genre']}#{r.get('rankInGenre')}  {r['searchTerm']}")
            if len(rows) > a.top:
                print(f"  … ещё {len(rows) - a.top}, полностью — через --out")
        if a.out:
            _write_rows(rows, Path(a.out))
            print(f"→ {a.out}")
        return

    ap.print_help()


if __name__ == "__main__":
    _cli()
