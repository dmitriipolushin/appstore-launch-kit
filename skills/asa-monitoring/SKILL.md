---
name: asa-monitoring
description: Мониторинг работающих Apple Search Ads кампаний: сбор метрик по ключам и search terms, gate-проверки, корректировка ставок, пауза неэффективных ключей, расширение ядра, сверка paid vs organic. Вызывай когда нужно проверить ASA-кампанию, оптимизировать ставки или разобраться, почему растёт CPA.
---

# asa-monitoring

Ежедневная/еженедельная проверка Apple Search Ads кампании: анализ ключей, корректировка ставок, поисковые запросы.

## Когда использовать

Ежедневная проверка кампании или оптимизация ставок/ключей.

## Что нужно от пользователя

- Папка проекта (содержит `./ASA/` и `./unit-economics/`)

## Пути и креды проекта

Пути в этом файле (`./ASA/asa-monitoring/`, `./ASA/asa_changelog.md`) — раскладка по умолчанию.
**Сначала прочитай `README.md` проекта**: если он задаёт свою раскладку, рабочий кабинет
(orgId, clientId, keyId) или команду экспорта переменных — действует README, а не этот файл
и не `~/.config/aso-tools/api_keys.env`. Пример: проект, где `asa-monitoring/` и
`asa_changelog.md` лежат в корне, а в `api_keys.env` прописан другой рекламный аккаунт —
перед каждым вызовом скриптов нужен `export ASA_ORG_ID=… ASA_CLIENT_ID=… ASA_KEY_ID=…` из README.

Если README молчит — раскладка по умолчанию и креды из `api_keys.env`.

## Первоначальная настройка (один раз)

Credentials — в `~/.config/aso-tools/api_keys.env`, скрипты читают их сами (`scripts/env_setup.py`).
Шаблон — `config/api_keys.env.example` в репозитории: `cp config/api_keys.env.example ~/.config/aso-tools/api_keys.env`.

Нужны: `ASA_ORG_ID`, `ASA_CLIENT_ID`, `ASA_KEY_ID` + PEM-пара в `~/.config/aso-tools/keys/`;
`APPLE_SA_COOKIE` + `APPLE_SA_XSRF` для `keyword_popularity.py` (живут ~24 часа).
Amplitude подключается как MCP-сервер, отдельного ключа в этом файле не требует.

Если чего-то не хватает — не угадывать значения, а сказать пользователю, какой переменной нет
и куда её взять (описано в `config/api_keys.env.example` в репозитории скиллов).

**Интерпретатор.** Скрипты нужно запускать тем `python3`, где стоят пакеты из
`requirements.txt` репозитория (requests, python-dotenv, authlib, pycryptodomex, PyJWT).
Какой это — печатает `./install.sh --check` в репозитории. На macOS `python3` в PATH часто
оказывается Homebrew-python без пакетов (`ModuleNotFoundError: dotenv`), а системный
`/usr/bin/python3` с пакетами работает — тогда все команды ниже вызывай через `/usr/bin/python3`.
Ставить пакеты в чужой интерпретатор без спроса не надо: скажи пользователю команду из
`requirements.txt`.

## Структура данных

Данные хранятся в накопительных файлах — каждый вызов **дополняет**, не перезаписывает.

```
./ASA/asa-monitoring/data/
├── asa_metrics.csv              ← keyword-level метрики, все кампании, все гео
├── asa_searchterms.csv          ← search terms, все кампании
├── asc_downloads_YYYYMMDD.csv   ← ASC: загрузки по стране/источнику
└── asc_discovery_YYYYMMDD.csv   ← ASC: impressions/page views/taps

./ASA/asa_changelog.md           ← история всех изменений (bid raises, паузы, запуски)
```

**Схема `asa_metrics.csv`:**
`fetch_date, period_start, period_end, campaign_id, campaign_name, country, status, keyword, bid, impressions, taps, installs, spend, ttr, cr, avg_cpt, avg_cpa, ipm, kw_status`

`keyword`: `[текст]` — EXACT, `текст` без скобок — BROAD, `~ <адгруппа> (Search Match)` / `~ <адгруппа> (без ключа)` —
остаток адгруппы сверх её ключей (Discovery и трафик, который Apple не привязал к ключу).
`status` — статус кампании, `kw_status` — статус ключа (у строки-остатка — адгруппы).

Дедупликация по `(fetch_date, period_start, period_end)`: повторный запуск за тот же период **заменяет все его строки**.
Поэтому прогон без `--keywords` и с `--keywords` за один период затирают друг друга — использовать только один режим (шаг 1).

ASC-конфиг: `./ASO/config/asc_config.env` (ASC_KEY_ID, ASC_ISSUER_ID, ASC_APP_ID).
Ключ: `./ASO/config/asc_keys/AuthKey_{KEY_ID}.p8`.

## Начало сессии

Прочитай все knowledge-файлы **до начала анализа**:
- `~/.claude/skills/asa-monitoring/knowledge/decision_gates.md` — **⚠️ ОБЯЗАТЕЛЬНО: три gate-проверки перед любой рекомендацией**
- `~/.claude/skills/asa-monitoring/knowledge/api_snippets.md` — сниппеты для шага 5
- `~/.claude/skills/asa-monitoring/knowledge/asa_campaign_architecture.md` — budget starvation, thematic clusters, bid discovery
- `~/.claude/skills/asa-monitoring/knowledge/aso_metrics_iteration.md` — organic multiplier, каннибализация

Прочитай последние записи в `./ASA/asa_changelog.md` для контекста предыдущих изменений.

### Сверка кабинета с учётом проекта (каждую сессию, до шага 1)

```bash
python3 ~/.claude/skills/asa-monitoring/scripts/asa/reconcile.py --project {папка проекта}
```

Только чтение. Конфиг проекта (`config/campaigns_v2.json`) и README видят не всё, что
есть в кабинете. Скрипт показывает три вещи:

1. **Все кампании аккаунта** с отметкой `НЕ УЧТЕНА` у тех, чьих id/имени нет ни в
   конфиге, ни в README. ENABLED неучтённая кампания тратит деньги мимо анализа —
   спроси пользователя, чья она, и внеси в README/конфиг (пример: «Songria Competitors —
   Global» и «Songria Brazil» на проекте Songria).
2. **ENABLED-адгруппы, у которых все ключи PAUSED.** В интерфейсе они выглядят
   работающими, а показов нет. Предложи паузу адгруппы или включение ключа.
3. **Изменения после последней записи changelog** (`modificationTime` кампаний,
   адгрупп, ключей). Правки того же дня выводятся отдельно — сверь их с записью;
   более поздние — правки руками в кабинете или незаписанная сессия: выясни и запиши.
   Своя дата — `--since YYYY-MM-DD`.

Найденное покажи пользователю вместе с данными Этапа 1; сам ничего не меняй.

## Принцип оценки ключей

Нет деления на «тестовые» и «боевые». Три вопроса на каждый ключ:
1. Есть ли impressions? (ключ попадает в аукцион)
2. Есть ли installs? (трафик конвертируется)
3. Есть ли триалы? (сегмент монетизируется)

---

## Алгоритм — два этапа

**Алгоритм фиксированный. Не импровизировать. Не переходить к Этапу 2 без подтверждения пользователя.**

---

### ЭТАП 1 — Сбор данных и аналитика

Выполни шаги 1–4, затем **жди подтверждения** перед переходом к Этапу 2.

#### Шаг 1 — Fetch ASA данных (7 полных дней)

```bash
# since = today − 7, end = вчера → 7 полных дней (обе даты включительно)
python3 ~/.claude/skills/asa-monitoring/scripts/asa/asa_fetch.py \
  --project ./ASA/asa-monitoring \
  --app-id {our_app_id} \
  --since {today−7} --end {yesterday} \
  --keywords --searchterms
```

Результат: строки на ключ в `asa_metrics.csv` с `period_start={today−7}`, `period_end={yesterday}`,
плюс строки-остатки Search Match по адгруппам. Сумма строк кампании = campaign-level расход;
если нет — скрипт печатает `WARN … строки $X ≠ кампания $Y`, и это надо чинить, а не обходить.

⚠️ `--end` включителен: `--since {today−7} --end {today}` — это 8 дней, последний неполный.
`--days 1` и `--since {date}` без `--end` тоже дают период до сегодня включительно.

⚠️ Отчёты считаются в UTC — так же, как кабинет. Если выручку сверяют по Apphud или
другому источнику, **период ASA должен совпадать с его периодом день в день**: сдвиг
на один день меняет расход на 20–25% и ROAS вслед за ним. Спроси у пользователя даты,
если он приносит выручку.

#### Шаг 2 — Триалы из Amplitude

**Только для подписочных приложений.** Если монетизация — разовые покупки (IAP) и
`trial_started` не трекается (так написано в `unit-economics/asa_pause_strategy.md`
или README проекта) — шаг пропустить, `--amplitude` в шаге 4 не передавать.
Выручку по кампаниям/адгруппам тогда даёт пользователь из Apphud (proceeds net,
тот же период, что в шаге 1).

Один запрос — все campaign_id за те же 7 дней. Сниппет — см. `api_snippets.md`.

```python
# Через mcp__Amplitude__query_dataset
# projectId="{amplitude_project_id}", groupByLimit=300, timeSeriesLimit=0
# range: "Last 7 Days", event: trial_started, groupBy: gp:asa_campaign_id
```

После получения ответа — сохранить в файл (сниппет в `api_snippets.md`):
```bash
./ASA/asa-monitoring/data/amplitude_trials.csv
```

#### Шаг 3 — IS-отчёт (если есть кандидаты на bid raise)

Запускать **одним вызовом** для всех ключей с impressions > 0. Сниппет — см. `api_snippets.md`.

```bash
./ASA/asa-monitoring/data/is_report_latest.csv
```

Если ключа нет в IS-отчёте → объём мал, Apple не раскрывает IS → +$0.20 без IS допустимо.
В нишах с малым объёмом так будет почти со всеми ключами — это нормально, правило выше и есть рабочий путь.

**IS-отчёт — источник негативов для Discovery.** То, что в нём остаётся, — обычно
запросы, на которые нас показывает Search Match (`apple music`, `yt music`, `spotify`,
названия плееров и сервисов). Каждый такой запрос сверить с search terms Discovery:
показы без установок или чужой интент → кандидат в кампанийные EXACT-негативы (шаг 5).

#### Шаг 4 — Метрики через asa_analyze.py

```bash
python3 ~/.claude/skills/asa-monitoring/scripts/asa/asa_analyze.py \
  --metrics ./ASA/asa-monitoring/data/asa_metrics.csv \
  --unit-economics ./unit-economics/asa_pause_strategy.md \
  --since {today−7} --end {yesterday} \
  [--amplitude ./ASA/asa-monitoring/data/amplitude_trials.csv] \
  [--is-report ./ASA/asa-monitoring/data/is_report_latest.csv] \
  [--fetch-date {today}]
```

`--since/--end` — те же даты, что в шаге 1: без них скрипт ищет период «fetch_date − 7 … fetch_date»
и может взять другую выгрузку того же дня. `--amplitude` — только для подписочных приложений.

Скрипт выводит таблицу по кампаниям (impr, inst, spend, trials, IR%, CPI, CPTrial, IPM), а под ней — разрез по ключам внутри каждой кампании (bid, impr, taps, inst, spend, CPI, TTR%, IPM, IS%). Discovery идут отдельными строками `~ … (Search Match)`. IS% есть только у ключей: у кампании нет одного ключа, к которому его можно привязать.
**Никаких рекомендаций — только данные.**

**Если вывод неверный — чини скрипт, не анализируй вручную.**

#### Пауза после Шага 4

Показать таблицу пользователю и написать:

> **Этап 1 завершён. Вот данные — что будем делать?**

**Не предлагать никаких действий до ответа пользователя.**

---

### ЭТАП 2 — Решения и исполнение

Выполняется **только после того, как пользователь скажет что делать**.

#### Шаг 5 — Перечитать decision_gates.md и сформировать план

Перечитать `~/.claude/skills/asa-monitoring/knowledge/decision_gates.md`.
По каждой кампании из обсуждения — проверить через gates и составить список действий.

#### Шаг 6 — После подтверждения: Выполнение + Запись в changelog

1. Выполнить через API (сниппеты в `api_snippets.md`):
   - Подъём ставок пачкой — только `shared/asa/bids.py` (сначала `--dry-run`): только вверх,
     только ACTIVE-ключи, повтор после обрыва не задваивает шаг
   - ⚠️ Верифицировать adgroup_id через `api.get_adgroups(campaign_id)` перед keyword-операциями
   - После bid raise — обновить adgroup default CPT bid = максимальная keyword bid
   - У Discovery (Search Match) ставка — это default bid адгруппы. Правка адгруппы не должна
     трогать `automatedKeywordsOptIn`: в `update_adgroup` не передавать `automated_keywords_opt_in`,
     если Search Match не включается/выключается намеренно (см. `api_snippets.md`)
   - После правок перечитать из кабинета каждое изменённое поле и сверить с планом

2. Записать в `./ASA/asa_changelog.md` новую запись в конец файла:

```markdown
### {YYYY-MM-DD} — {краткое описание действия}
{Что сделано}: перечень кампаний и конкретных изменений (bid X→Y, пауза, запуск).
{Почему}: данные которые обосновали решение — spend, installs, trials, TR%, CPTrial, IS%.
```

**Обязательные поля записи:**
- Дата
- Список затронутых кампаний
- Числовые данные, обосновавшие решение (CPTrial, TR%, IS%, spend)
- Итог: что изменилось (новый bid, статус)

**Не записывать** сессии без изменений (только анализ без действий).

---

## Дополнительные проверки (раз в 7 дней)

### ASC данные — organic vs paid

```bash
python3 ~/.claude/skills/asa-monitoring/scripts/asc/asc_fetch_analytics.py \
  --project {путь}/asa-monitoring \
  --asc-config {путь}/ASO/config/asc_config.env \
  --days 7
```

ONGOING request ID отчёта скрипт находит сам: при 409 (запрос уже создан) подхватывает существующий.

```
organic = asc_ftd_total − asa_installs
multiplier = organic / asa_installs
```
Растёт → ASO работает. Flat при росте spend → аудит metadata.

### Гео-разбивка

Группируй `asa_metrics.csv` по `country`. Сигналы:
- Одна страна > 70% spend, < 30% installs → сжигает бюджет
- CPA в одной стране в 2× выше → переплата, снизить bid
- Страна даёт лучший CPA → выделить отдельную кампанию

### Расширение ключей

**Откуда брать ключи (по убыванию пользы для малых гео):**

1. **Обход автоподсказок App Store** — основной рабочий путь. Сиды — свои ключи с показами,
   слова из title/subtitle конкурентов; `--depth 2` раскрывает нишевые подсказки.
   ~2 запроса/с, ~20 минут на страну для 40+ сидов; прерванный обход продолжается из кеша.
2. **Search Popularity** по найденным термам (`platform_api.py --popularity --terms …`) —
   только голова; ниже порога — путь проверки конкретного терма ниже.
3. **Search Terms Report — НЕ источник ключей в малых гео.** В DE/AT/CH почти весь трафик
   приходит с текстом `(none)`: Apple скрывает запросы с малым числом показов. Замер
   05–11.10.2026: без текста запроса 84% показов и 54 из 55 установок в DE, 94% и 25 из 25
   в CH, 98% и 12 из 12 в AT (в BR — 62%). Search terms годятся для негативов
   (чужой интент среди названных запросов), но не для поиска новых ключей.

**Search Hints:**
```bash
python3 ~/.claude/skills/aso-collection/scripts/keyword_suggest.py \
  --term "ki scan" --country de
python3 ~/.claude/skills/aso-collection/scripts/keyword_suggest.py \
  --seeds "ki song,suno,lied erstellen" --country de --depth 2 --out hints_de.json
```
Тир HIGH по hints не информативен (суррогат по позиции, почти у всех 10000) — смотри `hits` и Search Popularity. Сбойные запросы считаются в итоге (`НЕУДАЧНЫХ N`, код выхода 3), повтор команды дозапрашивает только их.

**ASA Popularity:**
```bash
python3 ~/.claude/skills/asa-monitoring/scripts/asa/keyword_popularity.py \
  --seeds "keyword1,keyword2" --storefronts DE
```
Терм есть в hints + pop ≥ 5 → добавить по правилу новых ключей (ниже). ASA pop ≥ 20 → уверенный сигнал.
Cookie истекает ~24ч. При 401 — обновить `APPLE_SA_COOKIE` в `~/.config/aso-tools/api_keys.env`.

**Apple Ads Platform API — подсказки ключей с popularity (без cookie).**

С августа 2026 у Apple есть `/v1/suggestions/keywords/query`: отдаёт ключи с
popularity 0-100 по своему приложению. Cookie не нужен, авторизация обычная.

```bash
python3 shared/asa/platform_api.py --suggest-keywords --app-id {adam_id} \
    --seeds "ki song,suno,ai song" --country DE
```

Без `--seeds` вернёт общие головные запросы жанра (youtube, spotify) — бесполезно.
Засевать нишевыми словами обязательно.

⚠️ Фильтр `countriesOrRegions` Apple игнорирует: DE/AT/CH возвращают идентичные
списки, popularity не привязана к стране.

⚠️ **Это подсказки, а не поиск popularity по произвольному терму.** Apple возвращает
только то, что сам считает подсказкой по сидам: на Songria 184 терма-сида дали 42 строки.
Отсутствие терма в ответе = **нет данных**, а не «popularity 0». Проверка конкретного терма:
1. `platform_api.py --popularity --terms "<терм>" --countries DE` — официальная popularity
   по стране, но только голова (в DE порог ≈ 49); нет в выдаче = ниже порога;
2. ниже порога — cookie-способ `keyword_popularity.py` / JS из `aso-collection/SKILL.md`
   шаг 4В2 (длинный хвост, нужно своё приложение в нише);
3. нигде нет — терм в hints? Тогда завести ключ по правилу новых ключей и смотреть
   показы: реальные impressions — единственный точный сигнал объёма в малых гео.

Там же — официальный топ-500 запросов на жанр на страну:

```bash
# Проверить свои ключи (регистр не важен); без --month — последний опубликованный месяц
python3 shared/asa/platform_api.py --popularity --countries DE,AT --terms "schrittzähler,kalorienzähler"
# Топ жанра / запросы со словом / понедельный срез
python3 shared/asa/platform_api.py --popularity --countries DE --genre HEALTH_FITNESS --out pop.csv
python3 shared/asa/platform_api.py --popularity --countries US --contains song
python3 shared/asa/platform_api.py --popularity --week 2026-09-13 --countries DE --genre PHOTO_VIDEO
```

Не привязан к своему приложению и честно разбит по странам. Покрытие — только
голова (в DE порог ≈ 49 по `searchPopularity1to100`), поэтому нишевые ключи там
искать бесполезно: «не в топ-500» значит «ниже порога», а не «ноль». Жанров 15,
MUSIC/MEDICAL/BOOKS нет — их запросы лежат в ENTERTAINMENT/LIFESTYLE.
`ASA_ORG_ID` можно не задавать, если у ключа один рекламный аккаунт.

**Способ без cookie (предпочтительный).** Запрос выполняется изнутри залогиненной
страницы `app-ads.apple.com` — браузер сам подставляет сессию, ничего не истекает
раз в сутки и учётные данные никуда не копируются. Полный рецепт с JS-сниппетом —
в `aso-collection/SKILL.md`, шаг 4В2.

⚠️ **Предусловие для хвоста.** `getRecommendedKeywords` отдаёт данные только
для `adamId` **из твоей ASA-организации** и фильтрует выдачу по тематике этого
приложения. adamId конкурента возвращает **пустой массив с HTTP 200** — это не
протухший cookie, а отсутствие доступа. Нет своего приложения в нужной нише →
popularity хвоста не получить. Частые запросы по стране при этом доступны без своего
приложения — через официальный Search Term Popularity (`platform_api.py --popularity --terms …`).
Проверить доступные adamId: `python3 aso-collection/scripts/asa/asa_api.py --list-apps`.


### Органические позиции

```bash
python3 ~/.claude/skills/aso-collection/scripts/search_positions.py \
  --keyword "keyword" --app-ids {our_app_id} --country de
```
Позиция 11–50 → усилить ASA bid для прогрева органики (эффект через 2–4 недели).

## Структурные правила

**Это правила по умолчанию, а не догма.** Если `README.md` проекта или changelog фиксирует
другую архитектуру (решение владельца) — работай в ней и не предлагай «привести к стандарту»
без новых данных. Примеры отклонений, которые встречаются: BROAD-ключи на смысловой кластер,
Discovery-адгруппа с Search Match внутри основной кампании, много адгрупп «1 ключ = 1 адгруппа»
в одной кампании на гео. Тогда Discovery и BROAD оцениваются по тем же gates, что и EXACT,
плюс их search terms — источник новых ключей и негативов.

По умолчанию:
- Search Match (`automatedKeywordsOptIn`) выключен — Discovery-adgroup не используется
- 1 ключ = 1 кампания (бюджетная изоляция + точный CPTrial)

**Новые ключи — правило по умолчанию** (решение владельца, 2026-10; сниппет —
`api_snippets.md`, «Новые ключи: правило по умолчанию»):
- **1–2 слова → EXACT, 3+ слова → BROAD.** Короткий запрос в BROAD собирает чужой интент,
  длинный в EXACT почти не получает показов.
- **В каждую BROAD-адгруппу — EXACT-негативы текстов всех прочих активных ключей
  кампании**, чтобы их запросы уходили в свои адгруппы, а не в BROAD.
- **Тематические BROAD-негативы — на уровне адгруппы, не кампании.** Кампанийный BROAD-негатив
  блокирует и собственные ключи: `stimme` блокирует `stimme klonen`. Негатив, все слова которого
  входят в собственный ключ адгруппы, в неё не ставится.
- **Ставка: старт $0.80, +$0.20 в день** ключам без показов —
  `bids.py --step 0.20 --ramp-zero-impressions` (только после «да» пользователя).
  Потолок — ориентир, не граница (см. ниже). Пауза — по GATE 3 и фактической экономике
  (CPI, выручка, CPT против потолка), а не по достижению потолка.

Всегда, независимо от архитектуры:
- Bid raise (оптимизация): только если IS < 90% (или ключа нет в IS-отчёте — см. шаг 3)
- **Потолок ставки (`economics.by_geo.*.bid_ceiling`) — ориентир, а не граница.** Ставка выше
  потолка допустима: она даёт показы, а фактический CPT (вторая цена) остаётся у потолка или
  ниже. С потолком сравнивай фактический CPT; CPT устойчиво выше потолка (≥ 5 тапов) → GATE 3
  и пересчёт потолка. Ставку до потолка не обрезать и не понижать «потому что выше потолка».
  Подробно — `decision_gates.md` → «Потолок ставки». Отчёт «ставка / потолок / CPT»:
  `python3 shared/asa/bids.py --project {проект} --report`
- Paused кампании не удалять — данные нужны для истории
- Target IPM = 250
