#!/usr/bin/env python3
"""
CLI к AppStoreSpy API — анализ приложений и разработчиков в App Store.

Все команды печатают JSON в stdout, ошибки — в stderr с кодом возврата 1.
Значит, вывод можно класть в файл или прогонять через jq.

    python3 shared/appstorespy_cli.py app 284882215 --fields name,short,downloads
    python3 shared/appstorespy_cli.py similar 431006818 --link from --limit 20
    python3 shared/appstorespy_cli.py rankings --app 431006818 --from 2026-09-01 --to 2026-09-20

Полный список команд: --help. Справочник «задача → команда» и подводные камни —
в knowledge/appstorespy_api.md.

Нужен APPSTORESPY_API_KEY в ~/.config/aso-tools/api_keys.env или в окружении.
"""

import argparse
import json
import sys

import appstorespy as spy


def _out(data) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _fields(value):
    """--fields name,short,downloads → ['name','short','downloads']"""
    if not value:
        return None
    return [f.strip() for f in value.split(",") if f.strip()]


def _list(value):
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _range(gte, lte, scale=1):
    """Диапазон {gte/lte} для фильтров; None, если обе границы пустые.

    scale делит значения перед отправкой. Нужен, потому что фильтры
    downloads_month / revenue_month у приложений принимают ТЫСЯЧИ, хотя в ответе
    те же поля приходят абсолютными. Пользователь CLI везде пишет абсолютные
    числа, расхождение API прячется здесь.
    """
    r = {}
    if gte is not None:
        r["gte"] = gte / scale if scale != 1 else gte
    if lte is not None:
        r["lte"] = lte / scale if scale != 1 else lte
    return r or None


def _build_app_filter(args) -> dict:
    """Собрать SearchFilterIos из плоских аргументов CLI."""
    f = {"published": not args.include_unpublished}
    if args.name:
        f["name"] = args.name
    if args.category:
        f["category"] = args.category
    if args.category_type:
        f["category_type"] = args.category_type
    if args.developer:
        f["developer"] = args.developer
    if args.developer_id:
        f["developer_id"] = args.developer_id
    if args.countries:
        f["active_countries"] = _list(args.countries)
    if args.iap is not None:
        f["iap"] = args.iap
    for key, gte, lte, scale in (
        ("downloads_month", args.min_downloads, args.max_downloads, 1000),
        ("revenue_month", args.min_revenue, args.max_revenue, 1000),
        ("rating_count", args.min_rating_count, args.max_rating_count, 1),
        ("rating_avg", args.min_rating, args.max_rating, 1),
        ("release_date", args.released_after, args.released_before, 1),
        ("update_date", args.updated_after, args.updated_before, 1),
    ):
        rng = _range(gte, lte, scale)
        if rng:
            f[key] = rng
    return f


def _add_filter_args(p) -> None:
    """Общий набор фильтров для команд query и summary."""
    p.add_argument("--name", help="подстрока в названии приложения")
    p.add_argument("--category", help="категория App Store, напр. HEALTH_AND_FITNESS")
    p.add_argument("--category-type", choices=spy.CATEGORY_TYPES, help="APP или GAME")
    p.add_argument("--developer", help="название разработчика")
    p.add_argument("--developer-id", help="ID разработчика")
    p.add_argument("--countries", help="сторфронты через запятую, напр. US,GB,DE")
    p.add_argument("--iap", type=lambda v: v.lower() == "true",
                   help="true/false — наличие встроенных покупок")
    p.add_argument("--min-downloads", type=int, help="загрузок в месяц, от (абсолютное число)")
    p.add_argument("--max-downloads", type=int, help="загрузок в месяц, до (абсолютное число)")
    p.add_argument("--min-revenue", type=int, help="выручка в месяц, от (USD)")
    p.add_argument("--max-revenue", type=int, help="выручка в месяц, до (USD)")
    p.add_argument("--min-rating-count", type=int, help="число оценок, от")
    p.add_argument("--max-rating-count", type=int, help="число оценок, до")
    p.add_argument("--min-rating", type=float, help="средний рейтинг, от")
    p.add_argument("--max-rating", type=float, help="средний рейтинг, до")
    p.add_argument("--released-after", help="релиз не раньше YYYY-MM-DD")
    p.add_argument("--released-before", help="релиз не позже YYYY-MM-DD")
    p.add_argument("--updated-after", help="обновлён не раньше YYYY-MM-DD")
    p.add_argument("--updated-before", help="обновлён не позже YYYY-MM-DD")
    p.add_argument("--include-unpublished", action="store_true",
                   help="включить снятые с публикации приложения")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appstorespy_cli.py",
        description="AppStoreSpy: анализ приложений и разработчиков в App Store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Справочник «задача → команда»: knowledge/appstorespy_api.md",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- приложения ---
    p = sub.add_parser("app", help="профиль приложения по ID (единственный источник subtitle)")
    p.add_argument("app_id")
    p.add_argument("--country", default="US")
    p.add_argument("--language", default="en_US")
    p.add_argument("--fields", help="поля через запятую; по умолчанию все")
    p.add_argument("--profile", action="store_true",
                   help="готовый набор полей для ASO-профиля вместо всех")

    p = sub.add_parser("subtitle", help="только subtitle приложения, одной строкой")
    p.add_argument("app_id")
    p.add_argument("--country", default="US")
    p.add_argument("--language", default="en_US")

    p = sub.add_parser("search", help="поиск приложений по названию")
    p.add_argument("query")
    p.add_argument("--country", default="US")
    p.add_argument("--fields")
    p.add_argument("--sort", choices=spy.SORT_VALUES)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("query", help="поиск приложений по параметрам ниши")
    _add_filter_args(p)
    p.add_argument("--fields")
    p.add_argument("--sort", choices=spy.SORT_VALUES, default="-downloads_month")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--country", default="US")
    p.add_argument("--language", default="en_US")

    p = sub.add_parser("similar", help="похожие приложения — быстрый способ найти конкурентов")
    p.add_argument("app_id")
    p.add_argument("--link", choices=spy.SIMILAR_LINKS, default="from",
                   help="from — кого показывают похожими на это приложение; "
                        "to — в чьих списках похожих стоит оно само")
    p.add_argument("--fields")
    p.add_argument("--sort", choices=spy.SORT_VALUES, default="-downloads_month")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--country", default="US")
    p.add_argument("--language", default="en_US")

    p = sub.add_parser("summary", help="агрегат по нише: сколько приложений, загрузок, выручки")
    _add_filter_args(p)

    p = sub.add_parser("reviews", help="отзывы приложения")
    p.add_argument("app_id")
    p.add_argument("--country", default="US")
    p.add_argument("--fields")
    p.add_argument("--sort")
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("estimates", help="оценки загрузок и выручки по приложениям за период")
    p.add_argument("app_ids", nargs="+")
    p.add_argument("--from", dest="start", help="YYYY-MM-DD")
    p.add_argument("--to", dest="end", help="YYYY-MM-DD")

    p = sub.add_parser("rankings", help="позиции в топ-чартах по датам (не поисковая выдача)")
    p.add_argument("--app", help="ID приложений через запятую")
    p.add_argument("--from", dest="date_start", help="YYYY-MM-DD")
    p.add_argument("--to", dest="date_end", help="YYYY-MM-DD")
    p.add_argument("--countries", help="через запятую, напр. US,GB")
    p.add_argument("--categories", help="через запятую")
    p.add_argument("--collections", help=f"через запятую: {', '.join(spy.COLLECTIONS)}")
    p.add_argument("--platforms", help="iPhone,iPad")
    p.add_argument("--rank-start", type=int)
    p.add_argument("--rank-end", type=int)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("recrawl", help="поставить приложение в очередь на пересбор данных")
    p.add_argument("app_id")
    p.add_argument("--country", default="US")
    p.add_argument("--language", default="en_US")

    # --- разработчики ---
    p = sub.add_parser("developer", help="карточка разработчика по ID")
    p.add_argument("developer_id")
    p.add_argument("--fields")

    p = sub.add_parser("developers", help="поиск разработчиков по названию")
    p.add_argument("query", nargs="?")
    p.add_argument("--fields")
    p.add_argument("--sort", choices=spy.DEV_SORT_VALUES, default="-downloads")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("developers-query", help="поиск разработчиков по параметрам")
    p.add_argument("--hq-country", help="страны регистрации через запятую")
    p.add_argument("--type", dest="dev_type", choices=spy.CATEGORY_TYPES)
    p.add_argument("--category")
    p.add_argument("--seller-name", help="точные юрлица через запятую")
    p.add_argument("--min-revenue", type=int, help="выручка в месяц, от (USD)")
    p.add_argument("--max-revenue", type=int, help="выручка в месяц, до (USD)")
    p.add_argument("--min-downloads", type=int, help="загрузок в месяц, от")
    p.add_argument("--max-downloads", type=int, help="загрузок в месяц, до")
    p.add_argument("--min-apps", type=int)
    p.add_argument("--max-apps", type=int)
    p.add_argument("--fields")
    p.add_argument("--sort", choices=spy.DEV_SORT_VALUES, default="-revenue")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("developer-estimates", help="оценки по портфелю разработчика")
    p.add_argument("developer_ids", nargs="+")
    p.add_argument("--from", dest="start", help="YYYY-MM-DD")
    p.add_argument("--to", dest="end", help="YYYY-MM-DD")

    p = sub.add_parser("aggregates-countries", help="разработчики в разрезе страны регистрации")
    p.add_argument("--category-type", choices=spy.CATEGORY_TYPES)

    # --- справочники ---
    sub.add_parser("countries", help="доступные сторфронты")
    sub.add_parser("languages", help="доступные языки метаданных")

    # --- keyword crawl jobs ---
    p = sub.add_parser("search-job-create",
                       help="заказать сбор выдачи App Store по ключу (тратит кредиты)")
    p.add_argument("term")
    p.add_argument("--country", default="US")
    p.add_argument("--lang", default="en_US")
    p.add_argument("--limit", type=int, default=10, help="глубина выдачи, 1..250")
    p.add_argument("--repeat", type=int, help="повторять сбор N раз")

    p = sub.add_parser("search-jobs", help="статус и результаты заказанных сборов выдачи")
    p.add_argument("--term")
    p.add_argument("--country")
    p.add_argument("--search-id")
    p.add_argument("--updated-after", dest="updated_gte", help="YYYY-MM-DD")
    p.add_argument("--updated-before", dest="updated_lte", help="YYYY-MM-DD")

    return parser


def dispatch(args):
    cmd = args.command

    if cmd == "app":
        fields = spy.FIELDS_PROFILE if args.profile else _fields(args.fields)
        return spy.get_app(args.app_id, args.country, args.language, fields)

    if cmd == "subtitle":
        return {"app_id": args.app_id, "country": args.country,
                "subtitle": spy.fetch_subtitle(args.app_id, args.country, args.language)}

    if cmd == "search":
        return spy.search_apps(args.query, args.country, _fields(args.fields),
                               args.sort, args.limit, args.page)

    if cmd == "query":
        return spy.query_apps(_build_app_filter(args), _fields(args.fields) or spy.FIELDS_QUERY_MARKET,
                              args.sort, args.limit, args.page, args.country, args.language)

    if cmd == "similar":
        return spy.similar_apps(args.app_id, args.link, None, _fields(args.fields),
                                args.sort, args.limit, args.page, args.country, args.language)

    if cmd == "summary":
        return spy.summary_apps(_build_app_filter(args))

    if cmd == "reviews":
        return spy.get_reviews(args.app_id, args.country, _fields(args.fields),
                               args.sort, args.limit)

    if cmd == "estimates":
        return spy.get_estimates(args.app_ids, args.start, args.end)

    if cmd == "rankings":
        return spy.get_rankings(_list(args.app), args.date_start, args.date_end,
                                _list(args.countries), _list(args.categories),
                                _list(args.collections), _list(args.platforms),
                                args.rank_start, args.rank_end, args.limit, args.page)

    if cmd == "recrawl":
        return spy.recrawl_app(args.app_id, args.country, args.language)

    if cmd == "developer":
        return spy.get_developer(args.developer_id, _fields(args.fields))

    if cmd == "developers":
        return spy.search_developers(args.query, _fields(args.fields), args.sort,
                                     args.limit, args.page)

    if cmd == "developers-query":
        f = {}
        if args.hq_country:
            f["hq_country"] = _list(args.hq_country)
        if args.dev_type:
            f["type"] = args.dev_type
        if args.category:
            f["category"] = args.category
        if args.seller_name:
            f["seller_name"] = _list(args.seller_name)
        for key, gte, lte in (
            ("revenue", args.min_revenue, args.max_revenue),
            ("downloads", args.min_downloads, args.max_downloads),
            ("total_apps", args.min_apps, args.max_apps),
        ):
            rng = _range(gte, lte)
            if rng:
                f[key] = rng
        return spy.query_developers(f, _fields(args.fields), args.sort, args.limit, args.page)

    if cmd == "developer-estimates":
        return spy.get_developer_estimates(args.developer_ids, args.start, args.end)

    if cmd == "aggregates-countries":
        return spy.aggregate_developers_by_country(args.category_type)

    if cmd == "countries":
        return spy.list_countries()

    if cmd == "languages":
        return spy.list_languages()

    if cmd == "search-job-create":
        return spy.create_search_job(args.term, args.country, args.lang,
                                     args.limit, repeat=args.repeat)

    if cmd == "search-jobs":
        return spy.list_search_jobs(args.term, args.country, args.search_id,
                                    updated_gte=args.updated_gte,
                                    updated_lte=args.updated_lte)

    raise AssertionError(f"необработанная команда: {cmd}")


def main():
    args = build_parser().parse_args()
    try:
        _out(dispatch(args))
    except spy.AppStoreSpyError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
