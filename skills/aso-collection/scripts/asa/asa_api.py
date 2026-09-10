#!/usr/bin/env python3
"""
Официальный Apple Search Ads API v5 (JWT, без суточных cookie).

Нужен, чтобы ответить на главный вопрос перед сбором Search Popularity:
какие adamId вообще доступны в ASA-организациях пользователя.
Popularity этот API НЕ отдаёт — соответствующих эндпоинтов в v5 нет.

Требует в ~/.config/aso-tools/api_keys.env:
    APPLE_ADS_CLIENT_ID, APPLE_ADS_TEAM_ID, APPLE_ADS_KEY_ID, APPLE_ADS_PRIVATE_KEY_PATH

Usage:
    python3 asa_api.py --list-apps
    python3 asa_api.py --list-orgs
"""
import argparse, os, re, sys, time
from pathlib import Path

try:
    import jwt
except ImportError:
    sys.exit("Нужен PyJWT:  pip3 install pyjwt cryptography")
import requests

ENV_PATH = Path.home() / ".config/aso-tools/api_keys.env"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
API = "https://api.searchads.apple.com/api/v5"


def load_env() -> dict:
    if not ENV_PATH.exists():
        sys.exit(f"Нет файла {ENV_PATH}")
    return dict(re.findall(r"^([A-Z_]+)=(.*)$", ENV_PATH.read_text(), re.M))


def resolve_key_path(raw: str) -> Path:
    """Путь может быть абсолютным, ~-относительным или относительным к keys/."""
    raw = raw.strip().strip('"').strip("'")
    for cand in (Path(raw).expanduser(),
                 ENV_PATH.parent / raw,
                 ENV_PATH.parent / "keys" / Path(raw).name):
        if cand.is_file():
            return cand
    sys.exit(f"Приватный ключ не найден. Проверено: {raw}, "
             f"{ENV_PATH.parent/raw}, {ENV_PATH.parent/'keys'/Path(raw).name}")


def access_token(env: dict) -> str:
    cid = env["APPLE_ADS_CLIENT_ID"].strip()
    team = env["APPLE_ADS_TEAM_ID"].strip()
    kid = env["APPLE_ADS_KEY_ID"].strip()
    key = resolve_key_path(env.get("APPLE_ADS_PRIVATE_KEY_PATH", "apple_ads_private_key.pem")).read_text()
    now = int(time.time())
    secret = jwt.encode({"sub": cid, "aud": "https://appleid.apple.com",
                         "iat": now, "exp": now + 3600, "iss": team},
                        key, algorithm="ES256", headers={"alg": "ES256", "kid": kid})
    r = requests.post(TOKEN_URL, params={"grant_type": "client_credentials", "client_id": cid,
                                         "client_secret": secret, "scope": "searchadsorg"}, timeout=20)
    if not r.ok:
        sys.exit(f"OAuth {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]


def orgs(tok: str) -> list:
    r = requests.get(f"{API}/acls", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    r.raise_for_status()
    return r.json().get("data") or []


def campaigns(tok: str, org_id) -> list:
    h = {"Authorization": f"Bearer {tok}", "X-AP-Context": f"orgId={org_id}"}
    r = requests.get(f"{API}/campaigns", headers=h, params={"limit": 1000}, timeout=25)
    if not r.ok:
        print(f"  ⚠️  campaigns {r.status_code}: {r.text[:160]}", file=sys.stderr)
        return []
    return r.json().get("data") or []


def main():
    ap = argparse.ArgumentParser(description="Apple Search Ads API v5 — доступные org и adamId")
    ap.add_argument("--list-orgs", action="store_true")
    ap.add_argument("--list-apps", action="store_true")
    a = ap.parse_args()
    if not (a.list_orgs or a.list_apps):
        ap.error("укажи --list-orgs или --list-apps")

    tok = access_token(load_env())
    os_ = orgs(tok)
    if not os_:
        sys.exit("Организаций нет — проверь роль ключа в Apple Ads.")

    for o in os_:
        print(f"\norg {o['orgId']}  {o['orgName']}  [{','.join(o.get('roleNames') or [])}]")
        if not a.list_apps:
            continue
        seen = {}
        for c in campaigns(tok, o["orgId"]):
            adam = c.get("adamId")
            if adam:
                seen.setdefault(adam, []).append(c.get("name", "?"))
        if not seen:
            print("  (кампаний с adamId нет)")
        for adam, names in seen.items():
            print(f"  adamId {adam}  ← {', '.join(names[:3])}{' …' if len(names) > 3 else ''}")

    if a.list_apps:
        print("\n⚠️  Search Popularity доступна ТОЛЬКО для этих adamId и только по их тематике.")
        print("    Нет приложения в нужной нише → popularity получить неоткуда.")


if __name__ == "__main__":
    main()
