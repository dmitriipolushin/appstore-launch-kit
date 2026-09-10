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

## Первоначальная настройка (один раз)

Credentials — в `~/.config/aso-tools/api_keys.env`, скрипты читают их сами (`scripts/env_setup.py`).
Файл создаёт `growth/install.sh` из шаблона `growth/api_keys.env.example`.

Нужны: `ASA_ORG_ID`, `ASA_CLIENT_ID`, `ASA_KEY_ID` + PEM-пара в `~/.config/aso-tools/keys/`;
`APPLE_SA_COOKIE` + `APPLE_SA_XSRF` для `keyword_popularity.py` (живут ~24 часа).
Amplitude подключается как MCP-сервер, отдельного ключа в этом файле не требует.

Если чего-то не хватает — не угадывать значения, а сказать пользователю, какой переменной нет
и куда её взять (описано в `growth/api_keys.env.example` в репозитории скиллов).

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
`fetch_date, period_start, period_end, campaign_id, campaign_name, country, keyword, bid, impressions, taps, installs, spend, ttr, cr, avg_cpt, avg_cpa, ipm`

Дедупликация по `(fetch_date, campaign_id, period_start)` — повторный запуск не дублирует строки.

ASC-конфиг: `./ASO/config/asc_config.env` (ASC_KEY_ID, ASC_ISSUER_ID, ASC_APP_ID).
Ключ: `./ASO/config/asc_keys/AuthKey_{KEY_ID}.p8`.

## Начало сессии

Прочитай все knowledge-файлы **до начала анализа**:
- `~/.claude/skills/asa-monitoring/knowledge/decision_gates.md` — **⚠️ ОБЯЗАТЕЛЬНО: три gate-проверки перед любой рекомендацией**
- `~/.claude/skills/asa-monitoring/knowledge/api_snippets.md` — сниппеты для шага 5
- `~/.claude/skills/asa-monitoring/knowledge/asa_campaign_architecture.md` — budget starvation, thematic clusters, bid discovery
- `~/.claude/skills/asa-monitoring/knowledge/aso_metrics_iteration.md` — organic multiplier, каннибализация

Прочитай последние записи в `./ASA/asa_changelog.md` для контекста предыдущих изменений.

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

#### Шаг 1 — Fetch ASA данных (7 дней)

```bash
# 7d_ago = today − 7 дней
python3 ~/.claude/skills/asa-monitoring/scripts/asa/asa_fetch.py \
  --project ./ASA/asa-monitoring \
  --app-id {our_app_id} \
  --since {7d_ago} --end {today}
```

Результат: строки в `asa_metrics.csv` с `period_start={7d_ago}`, `period_end={today}`.

⚠️ `--days 1` и `--since {date}` без `--end` дают период до сегодня (2 дня), НЕ один день.

#### Шаг 2 — Триалы из Amplitude

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

Если кампания отсутствует в IS-отчёте → объём мал, Apple не раскрывает IS → +$0.20 без IS допустимо.

#### Шаг 4 — Метрики через asa_analyze.py

```bash
python3 ~/.claude/skills/asa-monitoring/scripts/asa/asa_analyze.py \
  --metrics ./ASA/asa-monitoring/data/asa_metrics.csv \
  --unit-economics ./unit-economics/asa_pause_strategy.md \
  --amplitude ./ASA/asa-monitoring/data/amplitude_trials.csv \
  --days 7 \
  [--is-report ./ASA/asa-monitoring/data/is_report_latest.csv] \
  [--fetch-date {today}]
```

Скрипт выводит таблицу метрик: impr, inst, spend, trials, IR%, CPI, CPTrial, IPM, IS%.
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
   - ⚠️ Верифицировать adgroup_id через `api.get_adgroups(campaign_id)` перед keyword-операциями
   - После bid raise — обновить adgroup default CPT bid = максимальная keyword bid

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

ONGOING request ID для product_scanner: `6b504963-ab81-45ff-b354-d988dd9833ff`. При 409 — скрипт найдёт автоматически.

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

**Search Hints:**
```bash
python3 ~/.claude/skills/aso-collection/scripts/keyword_suggest.py \
  --term "ki scan" --country de
```
Tier HIGH = позиции 1–5 в autocomplete.

**ASA Popularity:**
```bash
python3 ~/.claude/skills/asa-monitoring/scripts/asa/keyword_popularity.py \
  --seeds "keyword1,keyword2" --storefronts DE
```
Hints HIGH + pop ≥ 5 → добавить EXACT с bid $0.80 (discovery). ASA pop ≥ 20 → уверенный сигнал.
Cookie истекает ~24ч. При 401 — обновить `APPLE_SA_COOKIE` в `~/.config/aso-tools/api_keys.env`.

### Органические позиции

```bash
python3 ~/.claude/skills/aso-collection/scripts/search_positions.py \
  --keyword "keyword" --app-ids {our_app_id} --country de
```
Позиция 11–50 → усилить ASA bid для прогрева органики (эффект через 2–4 недели).

## Структурные правила

- Только EXACT match, Search Match (`automatedKeywordsOptIn`) выключен всегда — Discovery-adgroup не используется
- 1 ключ = 1 кампания (бюджетная изоляция + точный CPTrial)
- Bid discovery: старт $0.80, +$0.20 каждые ~2 часа, пока impressions = 0
- Bid raise (оптимизация): только если IS < 90%
- Paused кампании не удалять — данные нужны для истории
- Target IPM = 250
