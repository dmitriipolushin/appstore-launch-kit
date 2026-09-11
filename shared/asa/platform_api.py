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

CLI:
    python3 shared/asa/platform_api.py --list-accounts
    python3 shared/asa/platform_api.py --suggest-keywords --app-id 123 \
        --seeds "ki song,suno" --country DE
    python3 shared/asa/platform_api.py --popularity --month 2026-08 \
        --countries DE,AT,CH --out popularity.json
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

    def _headers(self, ctx=None):
        h = {"Authorization": f"Bearer {self.token()}",
             "Content-Type": "application/json"}
        if ctx:
            h["X-AP-Context"] = ctx
        elif self.org_id:
            h["X-AP-Context"] = f"adAccountId={self.org_id}"
        return h

    def _post(self, path, body, ctx=None, tries=4, timeout=300):
        last = None
        for i in range(tries):
            try:
                r = requests.post(BASE + path, headers=self._headers(ctx),
                                  json=body, timeout=timeout)
                if r.status_code >= 300:
                    raise RuntimeError(f"POST {path} -> {r.status_code} {r.text[:300]}")
                return r.json()
            except requests.exceptions.RequestException as e:
                last = e
                if i == tries - 1:
                    break
                time.sleep(2 * (i + 1))
        raise RuntimeError(f"POST {path}: сеть недоступна после {tries} попыток ({last})")

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

    def search_term_popularity(self, month, countries=None):
        """Официальный топ-500 запросов на жанр на страну за месяц.

        month — 'YYYY-MM'. Тело фильтров не принимает: эндпоинт отдаёт весь
        датасет (~300k строк за месяц), фильтруем на своей стороне.
        Покрытие обрывается на SP≈48-51 — длинный хвост сюда не попадает.
        """
        start = f"{month}-01"
        res = self._post("/insights/apps/search-term-popularity/query",
                         {"timeRange": {"granularity": "MONTHLY",
                                        "start": start, "end": start}})
        rows = res["result"]["rows"]
        if countries:
            rows = [r for r in rows if r["countryOrRegion"] in set(countries)]
        return rows


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
    ap.add_argument("--month", help="YYYY-MM")
    ap.add_argument("--out", help="Путь для JSON-выгрузки")
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
        if not a.month:
            sys.exit("--month обязателен, формат YYYY-MM")
        ccs = [c.strip().upper() for c in a.countries.split(",")]
        rows = api.search_term_popularity(a.month, ccs)
        print(f"строк по {','.join(ccs)}: {len(rows)}")
        if a.out:
            Path(a.out).write_text(json.dumps(rows, ensure_ascii=False))
            print(f"→ {a.out}")
        return

    ap.print_help()


if __name__ == "__main__":
    _cli()
