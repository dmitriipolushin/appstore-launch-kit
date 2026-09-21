#!/usr/bin/env python3
"""
Клиент AppStoreSpy API — все iOS-эндпоинты.

Это библиотечный слой. Для работы из командной строки используй
`shared/appstorespy_cli.py`, он обёртка ровно над этими функциями.

Ключ: APPSTORESPY_API_KEY (из ~/.config/aso-tools/api_keys.env или окружения).
Справочник «задача → метод» — в knowledge/appstorespy_api.md.

Главная ловушка: в ОТВЕТЕ revenue/downloads абсолютные (USD и штуки), а в
ФИЛЬТРАХ query_apps/summary_apps те же downloads_month/revenue_month задаются в
ТЫСЯЧАХ ({"gte": 20000} = 20 млн). У разработчиков фильтры абсолютные.
CLI это расхождение прячет, при прямом вызове функций учитывай сам.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Union

import requests

try:
    import env_setup  # noqa: F401  — подхватывает ~/.config/aso-tools/api_keys.env
except ImportError:  # вызов из другого каталога — добавим себя в path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import env_setup  # noqa: F401

BASE_URL = "https://api.appstorespy.com/v1"
DEFAULT_TIMEOUT = 30

# Значения, допустимые в API. Держим списки здесь, чтобы CLI мог валидировать
# аргументы до похода в сеть и не тратить кредиты на заведомо битый запрос.
SORT_FIELDS = (
    "revenue_month", "downloads_month", "update_date", "release_date",
    "removal_date", "downloads_exact", "downloads_mark", "rating_count",
    "rating_value", "review_count", "rating_avg", "chart_info",
)
SORT_VALUES = tuple(s for f in SORT_FIELDS for s in (f, f"-{f}"))
DEV_SORT_VALUES = tuple(
    s for f in ("revenue", "downloads", "total_apps", "rating_count")
    for s in (f, f"-{f}")
)
CATEGORY_TYPES = ("APP", "GAME")
SIMILAR_LINKS = ("to", "from")
COLLECTIONS = ("Free", "Grossing", "Paid")

# Поля модели IosApp (эндпоинты /ios/apps и /ios/apps/{id}). Неизвестное поле
# API отбивает с HTTP 400, поэтому проверяем список до запроса — иначе кредит
# списывается за заведомо битый вызов.
APP_FIELDS = (
    "id", "bundle", "country", "lang", "published", "available", "available_in",
    "available_not", "category", "type", "emails", "website", "url",
    "privacy_policy", "version", "released", "updated", "size", "iap",
    "developer_id", "developer_name", "rating_count", "rating_value",
    "rating_avg", "revenue", "downloads", "devices", "arcade", "name", "short",
    "whatsnew", "description", "icon", "trailer", "languages", "crawled",
    "removed", "age", "screenshots", "top_countries_revenue",
    "top_countries_downloads", "countries_list", "url_appstorespy", "ads",
    "advertised", "transferred", "previous_developer_id",
    "previous_developer_name", "copyright", "seller",
)

# Пустой fields = все поля, но ответ тогда тяжёлый, поэтому для типовых задач
# держим готовые наборы.
FIELDS_PROFILE = [
    "id", "name", "short", "description", "developer_id", "developer_name",
    "category", "type", "url", "icon", "screenshots", "version", "released",
    "updated", "rating_avg", "rating_count", "iap", "age", "languages",
    "privacy_policy", "website", "downloads", "revenue",
]
FIELDS_MARKET = [
    "id", "name", "developer_name", "category", "downloads", "revenue",
    "rating_avg", "rating_count", "released", "updated", "url_appstorespy",
]
FIELDS_QUERY_MARKET = [
    "id", "name", "developer_name", "category", "category_type",
    "downloads_month", "revenue_month", "rating_avg", "rating_count",
    "review_count", "release_date", "update_date", "url_appstorespy",
]


class AppStoreSpyError(RuntimeError):
    """Ошибка обращения к AppStoreSpy: нет ключа, отказ API, битый ответ."""


def _api_key() -> str:
    key = os.environ.get("APPSTORESPY_API_KEY", "").strip()
    if not key:
        raise AppStoreSpyError(
            "APPSTORESPY_API_KEY не задан. Скопируй config/api_keys.env.example "
            "в ~/.config/aso-tools/api_keys.env и впиши ключ с appstorespy.com/account"
        )
    return key


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    """Выкинуть None — API не любит пустые значения в фильтрах."""
    return {k: v for k, v in d.items() if v is not None}


def _csv(value: Union[str, Sequence[str], None]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return ",".join(str(v) for v in value)


def _check_app_fields(fields: Optional[Sequence[str]]) -> None:
    """Отсеять неизвестные поля модели IosApp до сетевого запроса."""
    if not fields:
        return
    unknown = [f for f in fields if f not in APP_FIELDS]
    if unknown:
        raise AppStoreSpyError(
            f"неизвестные поля: {', '.join(unknown)}. "
            f"Допустимые: {', '.join(APP_FIELDS)}"
        )


def _request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    headers = {"accept": "application/json", "API-KEY": _api_key()}
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    try:
        resp = requests.request(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            params=_clean(params or {}),
            json=json_body,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise AppStoreSpyError(f"сеть недоступна: {e}") from e

    # Коды из документации API — разворачиваем в понятные сообщения,
    # чтобы агент не принял 204 за «приложения не существует».
    if resp.status_code == 202:
        raise AppStoreSpyError(
            f"{path}: приложения нет в базе AppStoreSpy, оно отправлено на кроулинг. "
            "Повтори запрос позже."
        )
    if resp.status_code == 204:
        raise AppStoreSpyError(f"{path}: нет данных по запрошенной стране")
    if resp.status_code == 403:
        # 403 приходит и на битый ключ, и на эндпоинт вне тарифа. Отличить можно
        # только по тому, работают ли другие эндпоинты тем же ключом.
        raise AppStoreSpyError(
            f"{path}: отказано (403). Либо ключ недействителен, либо этот эндпоинт "
            "не входит в твой тариф AppStoreSpy — проверь на appstorespy.com/account. "
            "Если другие команды тем же ключом работают, дело в тарифе."
        )
    if resp.status_code == 429:
        raise AppStoreSpyError("превышен лимит запросов (429), подожди и повтори")
    if resp.status_code >= 400:
        raise AppStoreSpyError(f"{path}: HTTP {resp.status_code} — {resp.text[:300]}")

    try:
        return resp.json()
    except ValueError as e:
        raise AppStoreSpyError(f"{path}: ответ не JSON — {resp.text[:200]}") from e


# --------------------------------------------------------------------------
# Приложения
# --------------------------------------------------------------------------

def get_app(
    app_id: str,
    country: str = "US",
    language: Optional[str] = "en_US",
    fields: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """GET /ios/apps/{id} — полный листинг приложения по числовому ID.

    Единственный источник subtitle конкурента (поле `short`) — iTunes Lookup
    его не отдаёт. Запрашивай отдельно по каждой локали: subtitle у локалей разный.
    """
    _check_app_fields(fields)
    return _request(
        "GET",
        f"/ios/apps/{app_id}",
        params={
            "country": country.upper(),
            "language": language,
            "fields": _csv(fields),
        },
    )


def search_apps(
    q: str,
    country: str = "US",
    fields: Optional[Sequence[str]] = None,
    sort: Optional[str] = None,
    limit: int = 10,
    page: int = 1,
) -> Dict[str, Any]:
    """GET /ios/apps — поиск приложений по свободному запросу.

    Это поиск по названиям в базе AppStoreSpy, а НЕ выдача App Store по ключу.
    Для реальной выдачи используй search_positions.py или create_search_job().
    """
    _check_app_fields(fields)
    return _request(
        "GET",
        "/ios/apps",
        params={
            "q": q,
            "country": country.upper(),
            "fields": _csv(fields),
            "sort": sort,
            "limit": limit,
            "page": page,
        },
    )


def query_apps(
    filter: Dict[str, Any],
    fields: Optional[Sequence[str]] = None,
    sort: str = "-downloads_month",
    limit: int = 10,
    page: int = 1,
    country: str = "US",
    language: str = "en_US",
) -> Dict[str, Any]:
    """POST /ios/apps/query — структурированный поиск по фильтру.

    Фильтр (ключи SearchFilterIos): name, published, category, category_type,
    developer, developer_id, active_countries, iap, with_ads, advertised,
    similar_apps, bundle, и диапазоны {gte/lte}: revenue_month, downloads_month,
    rating_count, rating_avg, review_count, release_date, update_date.

    Основной инструмент поиска конкурентов «по параметрам ниши», когда список
    приложений заранее неизвестен.
    """
    body = _clean({
        "filter": filter,
        "fields": list(fields) if fields else None,
        "sort": sort,
        "limit": limit,
        "page": page,
        "country": country.upper(),
        "language": language,
    })
    return _request("POST", "/ios/apps/query", json_body=body)


def similar_apps(
    app_id: str,
    link: str = "from",
    filter: Optional[Dict[str, Any]] = None,
    fields: Optional[Sequence[str]] = None,
    sort: str = "-downloads_month",
    limit: int = 10,
    page: int = 1,
    country: str = "US",
    language: str = "en_US",
) -> Dict[str, Any]:
    """POST /ios/apps/similar — приложения, связанные с указанным по similar-спискам.

    link="from" — кого App Store показывает похожими на это приложение;
    link="to"   — в чьих списках похожих оно само появляется (кто считает нас конкурентом).

    Быстрый способ расширить список конкурентов от 2-3 известных до десятков.
    """
    if link not in SIMILAR_LINKS:
        raise AppStoreSpyError(f"link должен быть 'to' или 'from', получено: {link!r}")
    body = _clean({
        "id": str(app_id),
        "link": link,
        "filter": filter if filter is not None else {"published": True},
        "fields": list(fields) if fields else None,
        "sort": sort,
        "limit": limit,
        "page": page,
        "country": country.upper(),
        "language": language,
    })
    return _request("POST", "/ios/apps/similar", json_body=body)


def summary_apps(
    filter: Dict[str, Any],
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """POST /ios/apps/summary — агрегат по всем приложениям, подходящим под фильтр.

    Размер ниши одним запросом: сколько приложений, суммарные загрузки и выручка.
    Дешевле, чем выкачивать выдачу постранично и складывать самому.
    """
    return _request("POST", "/ios/apps/summary", json_body=_clean({"filter": filter, "q": q}))


def get_reviews(
    app_id: str,
    country: str = "US",
    fields: Optional[Sequence[str]] = None,
    sort: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """GET /ios/apps/{id}/reviews — отзывы приложения.

    Поля отзыва: id, app, country, user_name, title, created, stars, comment.
    В отличие от iTunes RSS (fetch_reviews.py) отдаёт историю глубже свежей страницы.
    """
    return _request(
        "GET",
        f"/ios/apps/{app_id}/reviews",
        params={
            "country": country.upper(),
            "fields": _csv(fields),
            "sort": sort,
            "limit": limit,
        },
    )


def recrawl_app(app_id: str, country: str = "US", language: str = "en_US") -> Dict[str, Any]:
    """GET /ios/apps/{id}/recrawl — поставить приложение в очередь на пересбор.

    Нужен, когда конкурент только что обновил метаданные, а в базе висят старые.
    Данные обновятся не мгновенно — перезапроси get_app() через несколько минут.
    """
    return _request(
        "GET",
        f"/ios/apps/{app_id}/recrawl",
        params={"country": country.upper(), "language": language},
    )


def get_estimates(
    app_ids: Sequence[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, Any]:
    """GET /ios/estimates — оценки загрузок и выручки по списку приложений за период.

    Даты в формате YYYY-MM-DD. Это модельная ОЦЕНКА, а не факт из App Store Connect:
    порядок величины и динамика достоверны, точные числа — нет.
    """
    return _request(
        "GET",
        "/ios/estimates",
        params={"id": _csv(app_ids), "start": start, "end": end},
    )


def get_rankings(
    app_ids: Optional[Sequence[str]] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    countries: Optional[Sequence[str]] = None,
    categories: Optional[Sequence[str]] = None,
    collections: Optional[Sequence[str]] = None,
    platforms: Optional[Sequence[str]] = None,
    rank_start: Optional[int] = None,
    rank_end: Optional[int] = None,
    limit: int = 10,
    page: int = 1,
) -> Dict[str, Any]:
    """GET /ios/rankings — позиции в чартах по датам.

    collections: Free / Grossing / Paid. platforms: iPhone / iPad.
    Это позиции в ТОП-ЧАРТАХ категорий, а не позиции в поисковой выдаче по ключу —
    для поисковых позиций есть skills/aso-collection/scripts/search_positions.py.
    """
    return _request(
        "GET",
        "/ios/rankings",
        params={
            "app": _csv(app_ids),
            "date_start": date_start,
            "date_end": date_end,
            "country": _csv(countries),
            "category": _csv(categories),
            "collection": _csv(collections),
            "platform": _csv(platforms),
            "rank_start": rank_start,
            "rank_end": rank_end,
            "limit": limit,
            "page": page,
        },
    )


# --------------------------------------------------------------------------
# Разработчики
# --------------------------------------------------------------------------

def get_developer(developer_id: str, fields: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """GET /ios/developers/{id} — карточка разработчика по ID."""
    return _request(
        "GET", f"/ios/developers/{developer_id}", params={"fields": _csv(fields)}
    )


def search_developers(
    q: Optional[str] = None,
    fields: Optional[Sequence[str]] = None,
    sort: str = "-downloads",
    limit: int = 10,
    page: int = 1,
) -> Dict[str, Any]:
    """GET /ios/developers — поиск разработчиков по свободному запросу."""
    return _request(
        "GET",
        "/ios/developers",
        params={
            "q": q,
            "fields": _csv(fields),
            "sort": sort,
            "limit": limit,
            "page": page,
        },
    )


def query_developers(
    filter: Dict[str, Any],
    fields: Optional[Sequence[str]] = None,
    sort: str = "-revenue",
    limit: int = 10,
    page: int = 1,
) -> Dict[str, Any]:
    """POST /ios/developers/query — структурированный поиск разработчиков.

    Фильтр (SearchFilterDevIos): hq_country [список], type (APP/GAME),
    category, seller_name [список], и диапазоны {gte/lte}: revenue, downloads, total_apps.
    """
    body = _clean({
        "filter": filter,
        "fields": list(fields) if fields else None,
        "sort": sort,
        "limit": limit,
        "page": page,
    })
    return _request("POST", "/ios/developers/query", json_body=body)


def get_developer_estimates(
    developer_ids: Sequence[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, Any]:
    """GET /ios/developers/{id}/estimates — оценки по всему портфелю разработчика.

    ID разработчиков передаются через запятую прямо в пути — так устроен API.
    """
    return _request(
        "GET",
        f"/ios/developers/{_csv(developer_ids)}/estimates",
        params={"start": start, "end": end},
    )


def aggregate_developers_by_country(category_type: Optional[str] = None) -> Dict[str, Any]:
    """GET /ios/aggregates/countries — разработчики в разрезе страны регистрации."""
    return _request(
        "GET", "/ios/aggregates/countries", params={"category_type": category_type}
    )


# --------------------------------------------------------------------------
# Справочники
# --------------------------------------------------------------------------

def list_countries() -> Any:
    """GET /ios/info/countries — сторфронты, доступные в API."""
    return _request("GET", "/ios/info/countries")


def list_languages() -> Any:
    """GET /ios/info/languages — языки метаданных, доступные в API."""
    return _request("GET", "/ios/info/languages")


# --------------------------------------------------------------------------
# Keyword crawl jobs — кто реально ранжируется по поисковому запросу
# --------------------------------------------------------------------------

def create_search_job(
    term: str,
    country: str = "US",
    lang: str = "en_US",
    limit: int = 1,
    store: str = "ios",
    repeat: Optional[int] = None,
    limit_apps: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """POST /jobs/search — поставить задачу на сбор выдачи App Store по ключу.

    Асинхронно: создаёшь задачу, потом забираешь результат через list_search_jobs()
    по возвращённому search_id. limit — глубина выдачи (1..250).

    Единственный способ в этом API узнать, кто реально стоит в выдаче по ключу,
    то есть оценить конкурентность ключа перед тем, как брать его в метаданные.
    """
    if not 1 <= limit <= 250:
        raise AppStoreSpyError(f"limit должен быть в диапазоне 1..250, получено: {limit}")
    body = _clean({
        "store": store,
        "term": term,
        "country": country.upper(),
        "lang": lang,
        "limit": limit,
        "repeat": repeat,
        "limit_apps": list(limit_apps) if limit_apps else None,
    })
    return _request("POST", "/jobs/search", json_body=body)


def list_search_jobs(
    term: Optional[str] = None,
    country: Optional[str] = None,
    search_id: Optional[str] = None,
    store: Optional[str] = "ios",
    updated_gte: Optional[str] = None,
    updated_lte: Optional[str] = None,
) -> Any:
    """GET /jobs/search — статус и результаты задач по сбору выдачи."""
    return _request(
        "GET",
        "/jobs/search",
        params={
            "store": store,
            "term": term,
            "country": country.upper() if country else None,
            "search_id": search_id,
            "updated_gte": updated_gte,
            "updated_lte": updated_lte,
        },
    )


# --------------------------------------------------------------------------
# Хелперы под задачи кита
# --------------------------------------------------------------------------

def fetch_subtitle(app_id: str, country: str = "us", language: str = "en_US") -> Optional[str]:
    """Subtitle приложения (поле `short`) или None, если ключа нет / данных нет.

    Не бросает исключений: используется как необязательное обогащение профиля
    в collect_profiles.py, где отсутствие ключа — нормальная ситуация.
    """
    try:
        return get_app(app_id, country=country, language=language, fields=["short"]).get("short") or None
    except AppStoreSpyError as e:
        print(f"  ⚠️  AppStoreSpy subtitle не получен для {app_id}: {e}", file=sys.stderr)
        return None
