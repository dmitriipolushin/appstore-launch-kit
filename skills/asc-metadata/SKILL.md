---
name: asc-metadata
description: Загрузка и обновление метаданных приложения в App Store Connect через официальный API (title, subtitle, keywords, description, whatsNew по всем локалям). Use when uploading metadata to App Store Connect programmatically instead of by hand.
---

# asc-metadata

Загружает и обновляет метаданные приложений в App Store Connect через официальный API. Поддерживает несколько приложений и несколько аккаунтов разработчика. Умеет обновлять title, subtitle и keyword field по всем локалям.

## Когда использовать

- Нужно залить title/subtitle/keywords/description в App Store Connect через API (не вручную)
- Работаешь с несколькими приложениями или аккаунтами разработчика
- Нужно обновить конкретные поля в конкретных локалях без затрагивания остальных

## Credentials

Для каждого приложения нужны три значения:
- **KEY_ID** — ID ключа API из App Store Connect → Users and Access → Integrations → App Store Connect API
- **ISSUER_ID** — Issuer ID из той же страницы (один на аккаунт)
- **KEY_FILE** — путь к `.p8` файлу (скачивается один раз при создании ключа)

Хранить в `projects/{app}/config/asc_keys/AuthKey_{KEY_ID}.p8` и прописывать KEY_ID / ISSUER_ID в `projects/{app}/STATUS.md`.

## Аутентификация — JWT (ES256)

```python
import jwt, time, requests

def make_token(key_id: str, issuer_id: str, key_file: str) -> str:
    key = open(key_file).read()
    return jwt.encode(
        {'iss': issuer_id, 'exp': int(time.time()) + 1200, 'aud': 'appstoreconnect-v1'},
        key,
        algorithm='ES256',
        headers={'kid': key_id}
    )

def headers(token: str) -> dict:
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
```

Токен живёт 20 минут (1200 секунд). Для большого батча пересоздавать заранее.

---

## Архитектура API — что где лежит

App Store Connect разделяет метаданные на два ресурса:

| Поле | Ресурс | Эндпоинт |
|------|--------|----------|
| `keywords` | `appStoreVersionLocalizations` | `/v1/appStoreVersionLocalizations/{id}` |
| `description`, `whatsNew`, `promotionalText` | `appStoreVersionLocalizations` | то же |
| `supportUrl`, `marketingUrl` | `appStoreVersionLocalizations` | то же |
| `name` (title) | `appInfoLocalizations` | `/v1/appInfoLocalizations/{id}` |
| `subtitle` | `appInfoLocalizations` | то же |
| `privacyPolicyUrl`, `privacyChoicesUrl` | `appInfoLocalizations` | то же |

**title и subtitle — НЕ в appStoreVersionLocalizations.** Это распространённая ошибка.

---

## КРИТИЧНО: два appInfo на каждое приложение

У каждого опубликованного приложения **два объекта appInfo**:
- `READY_FOR_SALE` — текущая версия в магазине. **Нередактируемая.** Попытка изменить → 409 `ENTITY_ERROR.ATTRIBUTE.INVALID.INVALID_STATE`.
- `PREPARE_FOR_SUBMISSION` — черновик следующей версии. **Только её редактировать.**

```python
BASE = 'https://api.appstoreconnect.apple.com/v1'

def get_editable_app_info(app_id: str, h: dict) -> str:
    r = requests.get(f'{BASE}/apps/{app_id}/appInfos', headers=h)
    r.raise_for_status()
    for info in r.json()['data']:
        state = info['attributes'].get('appStoreState') or info['attributes'].get('state', '')
        if state == 'PREPARE_FOR_SUBMISSION':
            return info['id']
    raise ValueError(f'No PREPARE_FOR_SUBMISSION appInfo for app {app_id}')
```

---

## Шаг 1 — Получить ID локализаций

### appStoreVersionLocalizations (keywords, description)

```python
def get_version_loc_ids(app_id: str, h: dict) -> dict:
    """Returns {locale: loc_id} for keywords/description updates."""
    # Get current editable version (latest)
    r = requests.get(f'{BASE}/apps/{app_id}/appStoreVersions?filter[appStoreState]=PREPARE_FOR_SUBMISSION', headers=h)
    r.raise_for_status()
    versions = r.json()['data']
    if not versions:
        # Fall back to any version with localizations
        r = requests.get(f'{BASE}/apps/{app_id}/appStoreVersions', headers=h)
        r.raise_for_status()
        versions = r.json()['data']
    version_id = versions[0]['id']

    r = requests.get(f'{BASE}/appStoreVersions/{version_id}/appStoreVersionLocalizations', headers=h)
    r.raise_for_status()
    return {item['attributes']['locale']: item['id'] for item in r.json()['data']}
```

### appInfoLocalizations (title, subtitle)

```python
def get_info_loc_ids(app_info_id: str, h: dict) -> dict:
    """Returns {locale: loc_id} for title/subtitle updates."""
    r = requests.get(f'{BASE}/appInfos/{app_info_id}/appInfoLocalizations', headers=h)
    r.raise_for_status()
    return {item['attributes']['locale']: item['id'] for item in r.json()['data']}
```

---

## Шаг 2 — Обновить или создать локализацию

### Обновить существующую

```python
def update_version_loc(loc_id: str, h: dict, keywords: str = None, description: str = None,
                       whats_new: str = None, promotional_text: str = None):
    attrs = {}
    if keywords is not None: attrs['keywords'] = keywords
    if description is not None: attrs['description'] = description
    if whats_new is not None: attrs['whatsNew'] = whats_new
    if promotional_text is not None: attrs['promotionalText'] = promotional_text
    if not attrs:
        return
    payload = {'data': {'type': 'appStoreVersionLocalizations', 'id': loc_id, 'attributes': attrs}}
    r = requests.patch(f'{BASE}/appStoreVersionLocalizations/{loc_id}', headers=h, json=payload)
    r.raise_for_status()

def update_info_loc(loc_id: str, name: str, subtitle: str, h: dict):
    attrs = {}
    if name: attrs['name'] = name
    if subtitle: attrs['subtitle'] = subtitle
    payload = {'data': {'type': 'appInfoLocalizations', 'id': loc_id, 'attributes': attrs}}
    r = requests.patch(f'{BASE}/appInfoLocalizations/{loc_id}', headers=h, json=payload)
    r.raise_for_status()
```

### Создать новую локализацию (если её ещё нет)

```python
def create_version_loc(version_id: str, locale: str, h: dict, keywords: str = None,
                       description: str = None) -> str:
    attrs = {'locale': locale}
    if keywords is not None: attrs['keywords'] = keywords
    if description is not None: attrs['description'] = description
    payload = {'data': {'type': 'appStoreVersionLocalizations',
                        'attributes': attrs,
                        'relationships': {'appStoreVersion': {'data': {'type': 'appStoreVersions', 'id': version_id}}}}}
    r = requests.post(f'{BASE}/appStoreVersionLocalizations', headers=h, json=payload)
    r.raise_for_status()
    return r.json()['data']['id']

def create_info_loc(app_info_id: str, locale: str, name: str, subtitle: str, h: dict) -> str:
    payload = {'data': {'type': 'appInfoLocalizations',
                        'attributes': {'locale': locale, 'name': name, 'subtitle': subtitle},
                        'relationships': {'appInfo': {'data': {'type': 'appInfos', 'id': app_info_id}}}}}
    r = requests.post(f'{BASE}/appInfoLocalizations', headers=h, json=payload)
    r.raise_for_status()
    return r.json()['data']['id']
```

---

## Полный сценарий: обновить пакет локалей

```python
def upload_metadata_package(app_id, key_id, issuer_id, key_file, locales_data):
    """
    locales_data: [{'locale': 'en-US', 'title': '...', 'subtitle': '...', 'keywords': '...',
                    'description': '...', 'whats_new': '...', 'promotional_text': '...'}, ...]
    Любое поле необязательно — обновляется только то, что передано.
    """
    token = make_token(key_id, issuer_id, key_file)
    h = headers(token)

    app_info_id = get_editable_app_info(app_id, h)
    version_loc_ids = get_version_loc_ids(app_id, h)
    info_loc_ids = get_info_loc_ids(app_info_id, h)

    for entry in locales_data:
        locale = entry['locale']
        print(f'  → {locale}')

        # Keywords, description, whatsNew, promotionalText
        version_fields = {k: entry[k] for k in ('keywords', 'description', 'whats_new', 'promotional_text') if k in entry}
        if version_fields:
            if locale in version_loc_ids:
                update_version_loc(version_loc_ids[locale], h, **version_fields)
            else:
                version_id = get_version_id(app_id, h)
                create_version_loc(version_id, locale, h, **version_fields)

        # Title + Subtitle
        title = entry.get('title')
        subtitle = entry.get('subtitle')
        if title or subtitle:
            if locale in info_loc_ids:
                update_info_loc(info_loc_ids[locale], title or '', subtitle or '', h)
            else:
                create_info_loc(app_info_id, locale, title or '', subtitle or '', h)
```

---

## Коды локалей — важные нюансы

| Язык | Код в API | Ошибки |
|------|-----------|--------|
| Arabic | `ar-SA` | ❌ `ar` → 422 |
| Chinese Simplified | `zh-Hans` | ✓ |
| Chinese Traditional | `zh-Hant` | ✓ |
| Russian | `ru` | ✓ |
| Vietnamese | `vi` | ✓ |
| Korean | `ko` | ✓ |
| Portuguese (Brazil) | `pt-BR` | ✓ |
| Spanish (Mexico) | `es-MX` | ✓ |
| French | `fr-FR` | ✓ |
| English (US) | `en-US` | ✓ |
| Ukrainian | `uk` | ✓ |
| English (GB) | `en-GB` | ✓ |

---

## Зависимости

```bash
pip install PyJWT cryptography requests
```

Стандартный `jwt.encode()` из PyJWT 2.x возвращает строку (не байты) — `Authorization: Bearer` работает без `.decode()`.

---

## Где хранить credentials

```
projects/
└── {app}/
    ├── STATUS.md           ← KEY_ID и ISSUER_ID
    └── config/
        └── asc_keys/
            └── AuthKey_{KEY_ID}.p8
```

Для нескольких аккаунтов — отдельные `.p8` файлы в каждом проекте. Скрипт принимает пути явно, не читает из глобального конфига.

---

## Диагностика ошибок

| HTTP | Код ошибки | Причина | Решение |
|------|-----------|---------|---------|
| 409 | `ENTITY_ERROR.ATTRIBUTE.INVALID.INVALID_STATE` | Используется `READY_FOR_SALE` appInfo | Переключиться на `PREPARE_FOR_SUBMISSION` |
| 422 | `PARAMETER_ERROR.REQUIRED` | Неверный код локали (`ar` вместо `ar-SA`) | Использовать полный код |
| 401 | `NOT_AUTHORIZED` | Истёк JWT или неверный ключ | Пересоздать токен |
| 404 | — | Нет версии в статусе PREPARE_FOR_SUBMISSION | Создать новую версию в ASC |
| 409 | `ENTITY_ERROR.RELATIONSHIP.INVALID` | Локализация уже существует, попытка POST | Использовать PATCH |

---

## Скрипт-пример для быстрого старта

Готовый скрипт: `~/.claude/skills/asc-metadata/scripts/upload_metadata.py`

Использование:
```bash
python3 upload_metadata.py \
  --app-id {APP_ID} \
  --key-id {KEY_ID} \
  --issuer-id {ISSUER_ID} \
  --key-file projects/{app}/config/asc_keys/AuthKey_{KEY_ID}.p8 \
  --json-file projects/{app}/data/reports/metadata.json
```
