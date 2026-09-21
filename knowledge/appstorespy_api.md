# AppStoreSpy API — инструменты анализа приложений в App Store

## Summary

AppStoreSpy — единственный внешний источник в этом ките, который отдаёт то, чего нет ни в iTunes Lookup API, ни в App Store Connect: **subtitle конкурентов**, **оценки загрузок и выручки**, **списки похожих приложений**, **позиции в топ-чартах по датам** и **данные по разработчикам**. Всё это — про чужие приложения, то есть про конкурентный анализ, который iTunes API покрыть не может.

Доступ — через CLI `shared/appstorespy_cli.py` (обёртка над `shared/appstorespy.py`). Ключ `APPSTORESPY_API_KEY`. Все команды печатают JSON в stdout, ошибки — в stderr с кодом 1.

---

## Key Principles

- **Фильтры по загрузкам и выручке у приложений API принимает в ТЫСЯЧАХ, а в ответе те же поля отдаёт абсолютными.** `downloads_month: {gte: 20000}` означает 20 миллионов, а не 20 тысяч. CLI это скрывает: в `--min-downloads` / `--min-revenue` пиши абсолютные числа, деление на 1000 происходит внутри. Если дёргаешь `shared/appstorespy.py` напрямую — учитывай сам.
- **У разработчиков те же фильтры — в абсолютных единицах.** Расхождение на стороне API, не опечатка.
- **Estimates — это модель, а не факт.** Порядок величины и динамика достоверны, точные числа нет. Никогда не выдавай их за реальные цифры конкурента.
- **Subtitle зависит от локали.** Запрашивай `app` отдельно по каждой стране/языку: `--country DE --language de_DE`. Один запрос по US не описывает немецкую страницу.
- **`rankings` — это топ-чарты категорий, а не поисковая выдача.** Позиция по ключевому слову берётся через `skills/aso-collection/scripts/search_positions.py`.
- **`search` — поиск по названиям внутри базы AppStoreSpy, а не выдача App Store.** Не путай: приложение может стоять первым в выдаче по ключу и вообще не находиться этой командой.
- **403 на одной команде при рабочих остальных = эндпоинт не входит в тариф**, а не битый ключ. См. таблицу ниже.
- **Каждый запрос тратит кредиты аккаунта.** Не выкачивай все поля, когда нужны два: `--fields name,short` вместо дефолтного «все поля».

---

## Data / Models

### Доступность эндпоинтов по тарифу

Проверено на базовом ключе 21.09.2026. На старших тарифах набор шире — если команда из нижнего блока нужна, смотри тариф на appstorespy.com/account.

| Работает на базовом | Требует старшего тарифа (403) |
|---|---|
| `app`, `subtitle`, `search`, `query`, `similar` | `summary` |
| `estimates`, `rankings` | `reviews` |
| `developer`, `developers`, `developers-query`, `developer-estimates` | `recrawl` |
| `countries`, `languages` | `aggregates-countries`, `search-jobs`, `search-job-create` |

Команды из правой колонки реализованы и корректны — они просто вернут понятную ошибку про 403, пока тариф их не покрывает.

### Коды ответа, которые значат не то, что кажется

| Код | Что на самом деле |
|---|---|
| 202 | Приложения нет в базе, оно отправлено на кроулинг. Не «не существует» — повтори запрос позже |
| 204 | Данных нет **по запрошенной стране**. В другой стране приложение может быть |
| 403 | Битый ключ **или** эндпоинт вне тарифа |
| 429 | Лимит запросов, подожди |

---

## Application

### Задача → команда

| Что нужно | Команда |
|---|---|
| Subtitle конкурента (iTunes его не отдаёт) | `subtitle <app_id> --country DE --language de_DE` |
| Полный профиль конкурента | `app <app_id> --profile` |
| Найти конкурентов, зная 1–2 приложения | `similar <app_id> --link from --limit 30` |
| Узнать, кто считает конкурентом нас | `similar <app_id> --link to` |
| Собрать конкурентов по параметрам ниши | `query --category HEALTH_AND_FITNESS --min-downloads 50000` |
| Оценить размер ниши одним числом | `summary --category HEALTH_AND_FITNESS` |
| Загрузки и выручка конкурента по месяцам | `estimates <app_id> --from 2026-01-01 --to 2026-09-01` |
| Динамика позиций в топ-чарте | `rankings --app <app_id> --from 2026-09-01 --to 2026-09-20` |
| Портфель и обороты разработчика | `developer <dev_id>`, `developer-estimates <dev_id>` |
| Найти издателей в нише | `developers-query --hq-country US --min-revenue 1000000` |
| Отзывы глубже свежей страницы RSS | `reviews <app_id> --limit 100` |
| Список сторфронтов и языков API | `countries`, `languages` |
| Обновить устаревшие данные по приложению | `recrawl <app_id>` |
| Кто реально стоит в выдаче по ключу | `search-job-create "<ключ>" --limit 50`, затем `search-jobs --term "<ключ>"` |

### Типовые сценарии

**Расширение списка конкурентов на шаге 1 aso-collection.** Пользователь назвал два приложения — разворачиваем в два-три десятка и отбираем по объёму:

```bash
python3 shared/appstorespy_cli.py similar 431006818 --link from --limit 30 \
  --fields id,name,downloads_month,revenue_month,rating_count
```

**Проверка, стоит ли вообще заходить в нишу.** Сколько там приложений и сколько денег:

```bash
python3 shared/appstorespy_cli.py summary --category HEALTH_AND_FITNESS --min-downloads 10000
```

**Subtitle по всем целевым локалям** — по запросу на локаль, потому что тексты разные:

```bash
for loc in "US en_US" "DE de_DE" "FR fr_FR"; do
  set -- $loc
  python3 shared/appstorespy_cli.py subtitle 431006818 --country "$1" --language "$2"
done
```

**Связь метаданных и результата.** Конкурент переписал title — что стало с чартом. `updated` из `app` даёт дату обновления, `rankings` — позиции вокруг неё:

```bash
python3 shared/appstorespy_cli.py app 431006818 --fields name,short,updated,version
python3 shared/appstorespy_cli.py rankings --app 431006818 \
  --from 2026-08-01 --to 2026-09-20 --countries US --collections Free --limit 200
```

### Аргументы, о которых легко не догадаться

- `--link from` — кого App Store показывает похожими **на это приложение**; `--link to` — в чьих списках похожих стоит **оно само**. Второе отвечает на вопрос «кто считает нас конкурентом» и часто даёт другой список.
- `--fields` принимает поля через запятую. У `app` набор шире, чем у `query`: там `short`, `screenshots`, `languages`, `privacy_policy`, `top_countries_downloads`. У `query` — `description_short`, `downloads_month`, `revenue_month`, `chart_info`.
- `--profile` у команды `app` — готовый набор полей под ASO-профиль вместо выкачки всего.
- `--sort` принимает только значения из списка API (`-downloads_month`, `rating_avg`, …), а `--fields` у команд `app` и `search` сверяется со списком полей модели. Неверное значение отбивается до сетевого запроса, кредиты не тратятся.
- Категории — enum из 41 значения (`GAMES_PUZZLE`, `HEALTH_AND_FITNESS`, `EDUCATION`, …). Неверная категория даёт 422 со списком допустимых прямо в тексте ошибки.

### Использование как библиотеки

Когда нужен разбор ответа, а не печать JSON:

```python
import sys; sys.path.insert(0, "shared")
from appstorespy import similar_apps, get_estimates, AppStoreSpyError

try:
    rivals = similar_apps("431006818", link="from", limit=30)["data"]
except AppStoreSpyError as e:
    print(f"AppStoreSpy недоступен: {e}")
```

`fetch_subtitle()` — единственная функция, которая не бросает исключение, а возвращает `None`: она задумана как необязательное обогащение профиля в `collect_profiles.py`, где отсутствие ключа нормально.

---

## Sources

- OpenAPI-спецификация: `https://api.appstorespy.com/v1/openapi.json` (проверена 21.09.2026)
- Документация и тарифы: `https://appstorespy.com/account`
- Единицы измерения фильтров и доступность эндпоинтов установлены эмпирически на живом API 21.09.2026 — в спецификации это не описано
