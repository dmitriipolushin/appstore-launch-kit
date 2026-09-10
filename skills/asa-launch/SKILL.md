---
name: asa-launch
description: Создаёт и запускает новую кампанию Apple Search Ads через API: отбор ключей, архитектура кампании и adgroup-ов, ставки, негативы, organic baseline. Вызывай когда нужно запустить ASA-кампанию, создать новую кампанию или добавить кластер ключей в рекламу.
---

# asa-launch

Создание и запуск новой Apple Search Ads кампании через API.

## Когда использовать

Нужно запустить новую Search Ads кампанию для приложения. Предполагается что ASO-сбор (aso-collection) уже сделан и есть список ключевых слов.

## Что нужно от пользователя

- **App Store ID приложения** — обязательно запросить явно. Не угадывать по файлам, не брать из api_keys.env (`APPLE_SA_ADAM_ID` может быть устаревшим). Попросить пользователя открыть App Store Connect или страницу приложения и скопировать числовой ID.
- Список стартовых ключевых слов (или взять из ASO-анализа)
- Целевые страны и язык кампании
- Дневной бюджет

## Первоначальная настройка (один раз)

Credentials — в `~/.config/aso-tools/api_keys.env`, скрипты читают их сами (`scripts/env_setup.py`).
Файл создаёт `growth/install.sh` из шаблона `growth/api_keys.env.example`.

Нужны: `ASA_ORG_ID`, `ASA_CLIENT_ID`, `ASA_KEY_ID` (Apple Search Ads → Account Settings → API)
и PEM-пара `apple_ads_private_key.pem` / `apple_ads_public_key.pem` в `~/.config/aso-tools/keys/`.

Если чего-то не хватает — не угадывать значения, а сказать пользователю, какой переменной нет
и куда её взять (описано в `growth/api_keys.env.example` в репозитории скиллов).

## Структура данных

Скилл создаёт папку `./asa-launch/` в текущей директории:
```
./asa-launch/
├── config/
│   └── campaign.json   # campaign_id, adgroup_id, ключи, даты
└── data/
```

## Начало сессии

Прочитай knowledge-файлы для контекста:
- `~/.claude/skills/asa-launch/knowledge/asa_campaign_architecture.md` — budget starvation, thematic clusters, bid discovery
- `~/.claude/skills/asa-launch/knowledge/aso_keyword_research.md` — отбор ключей для ASA
- `~/.claude/skills/asa-launch/knowledge/aso_metrics_iteration.md` — organic baseline, каннибализация
- `~/.claude/skills/asa-launch/knowledge/aso_foundations.md` — основы ASA/ASO синергии

## Шаги

### 1. Подготовь список ключей

Возьми из ASO-анализа термины со статусом `gap` или `weak` и tier HIGH/MEDIUM.

Правила отбора:
- Только EXACT match — BROAD не использовать
- `automatedKeywordsOptIn=False` — Apple иначе добавит свои ключи
- Исключить брендовые запросы конкурентов если нет явного конкурентного таргетинга
- Исключить смежные ниши с другим intent (уточни у пользователя)

**Выбор архитектуры кампании** (см. `asa_campaign_architecture.md`):
- ≤ 8 ключей одного intent → одна кампания с одной adgroup (EXACT, Search Match OFF)
- > 8 ключей с разными аудиториями → **thematic multi-campaign** (каждый кластер = отдельная кампания)

**Discovery-adgroup с Search Match не создаём.** Обоснование — в разделе «Почему без Search Match».

**Стартовые ставки**:
- Новый запуск без данных о clearing price → начинать с **$0.10** (bid discovery strategy)
- Пока impressions = 0 → поднимать на **$0.20 каждые ~2 часа**. Ждать нечего: нулевые
  показы означают, что ставка не проходит в аукцион, и само это не изменится
- Как только impressions пошли → ставку не трогать 3–5 дней, набирается статистика
- Стартовые ставки $1.50–$3.00 использовать только если clearing price по рынку уже известен из предыдущих данных

### 1.5 Зафиксируй organic baseline

Перед запуском кампании запиши baseline органических установок — понадобится для cannibalization check через 7–14 дней.

Из App Store Connect:
- `first_time_downloads` за последние 14 дней до запуска
- Вычти уже существующие ASA installs (если кампании уже были)

Сохрани в `./asa-launch/config/campaign.json`:
```json
{
  "campaign_start": "YYYY-MM-DD",
  "organic_baseline_14d": 0
}
```

### 2. Создай кампанию через API

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / '.claude/skills/asa-launch/scripts'))
from env_setup import CONFIG_DIR  # загружает ~/.config/aso-tools/api_keys.env
sys.path.insert(0, str(Path.home() / '.claude/skills/asa-launch/scripts/asa'))
from utils.asa_api import SearchAdsAPI

api = SearchAdsAPI.create()

# Apple убрал lifetime/total budget для новых кампаний (июнь 2026) —
# теперь кампании только daily-budget-only, budgetAmount не передаём
campaign = api.create_campaign(
    campaign_name="{App} - Search",
    app_id=<App Store ID>,
    daily_budget="<дневной бюджет>",
    curruncy="USD",
    countries=["US", "GB", "CA"],  # целевые страны от пользователя
)
campaign_id = campaign["data"]["id"]
print(f"Campaign created: {campaign_id}")
```

### 3. Создай adgroup

**Одна adgroup на кампанию.** Search Match выключен, автоподбор ключей выключен, только ручные EXACT-ключи с индивидуальными ставками.

```python
start_time = datetime.datetime.utcnow()

adgroup = api.create_adgroup(
    campaign_id=campaign_id,
    adgroup_name="Keywords",
    currency="USD",
    cpc_bid=0.10,  # bid discovery: старт с минимума, см. раздел про ставки
    start_time=start_time,
    automated_keywords_opt_in=False,  # Search Match OFF — обязательно
)
adgroup_id = adgroup["data"]["id"]
```

#### Почему без Search Match

Discovery-adgroup с `automatedKeywordsOptIn=True` раньше использовалась как источник новых запросов. От неё отказались: у ставки нет значения, при котором инструмент полезен.

- **Низкая ставка ($0.15–0.20).** Показов мало, поисковые запросы в отчёте единичные, статистики по ним не набирается — переносить в EXACT нечего, спрос от случайности не отличить.
- **Высокая ставка.** Apple подбирает всё, что отдалённо похоже на метаданные. Растёт доля нерелевантных запросов и падает конверсия из тапа в установку.

Замер на живой кампании (два подхода в одном аккаунте):

| Показатель | EXACT | Discovery (Search Match) |
|---|---|---|
| Цена тапа | $1.52 | $0.98 — дешевле на 35% |
| Конверсия тапа в установку | 51.5% | 27.2% — хуже в 1.9 раза |
| Цена установки | $2.95 | $3.60 — дороже на 22% |

Тап дешевле на 35%, но конверсия хуже на 47% — скидка не покрывает провал, установка выходит дороже. Точка безубыточности: при конверсии 27% тап в Discovery должен стоить $0.80.

**Новые ключи ищем до запуска** (`aso-collection`: ASA popularity, search hints, метаданные конкурентов) и проверяем отдельной кампанией на минимальной ставке — не Search Match.

### 4. Добавь ключевые слова

Ставки — по bid discovery: без данных о clearing price все ключи стартуют с минимума.

```python
keywords = [
    {"text": "keyword one", "matchType": "EXACT", "bidAmount": {"amount": "0.10", "currency": "USD"}},
    {"text": "keyword two", "matchType": "EXACT", "bidAmount": {"amount": "0.10", "currency": "USD"}},
]
api.add_targeting_keywords(campaign_id, adgroup_id, keywords)
print(f"Added {len(keywords)} keywords")
```

**После добавления ключей — обновить adgroup default CPT bid:**

Adgroup default bid — это fallback для любого ключа без явной ставки. Если он ниже keyword-level ставок, Apple может ограничивать через adgroup-уровень. Всегда устанавливать равным максимальной ставке среди ключей в этой адгруппе.

```python
max_bid = max(float(kw["bidAmount"]["amount"]) for kw in keywords)
api.update_adgroup(campaign_id, adgroup_id, cpc_bid=max_bid, currency="USD")
print(f"Adgroup default CPT bid set to ${max_bid:.2f}")
```

### 5. Добавь негативы

**Campaign-level** — общий мусор и конкуренты:
```python
campaign_negatives = [
    {"text": "competitor brand", "matchType": "EXACT"},
    {"text": "wrong niche",      "matchType": "BROAD"},
]
api.add_campaign_negative_keywords(campaign_id, campaign_negatives)
```

Adgroup-level негативы при работе только на EXACT не нужны: показы идут ровно по выбранным ключам. Они понадобятся, только если когда-нибудь тестируется BROAD.

### 6. Проверь что кампания запустилась

```python
campaign = api.get_campaign(campaign_id)
print(f"Status: {campaign['status']}")  # должно быть ENABLED
kws = api.get_targeting_keywords(campaign_id, adgroup_id)
print(f"Keywords: {len(kws)}")
```

### 7. Сохрани в campaign.json

```json
{
  "app_name": "{App}",
  "app_id": 0,
  "campaign_id": 0,
  "adgroup_id": 0,
  "campaign_start": "YYYY-MM-DD",
  "last_change": "YYYY-MM-DD",
  "organic_baseline_14d": 0,
  "daily_budget": 20,
  "countries": ["US", "GB", "CA"],
  "keywords": [
    {"text": "keyword", "bid": 0.10, "status": "ENABLED"}
  ],
  "negative_keywords": ["competitor brand"],
  "change_log": [
    {"date": "YYYY-MM-DD", "action": "campaign created", "reason": "initial launch"}
  ]
}
```

Запиши в `./asa-launch/config/campaign.json`.

## Правила запуска

- Не запускать BROAD на старте — даёт нерелевантный трафик без истории
- `automatedKeywordsOptIn=False` **всегда** — Search Match не используем ни на какой ставке
- Одна adgroup на кампанию — второй группы, конкурирующей за тот же запрос, быть не должно
- Первые 3–5 дней не трогать ставки у ключей, **где impressions уже есть** — набирается статистика
- Ключи с нулевыми impressions — исключение: ставку поднимаем каждые ~2 часа, пока показы не появятся
- Первая проверка показов — через ~2 часа после запуска; полный разбор — через 3 дня по скиллу asa-monitoring
- Organic baseline важен: без него невозможно отличить каннибализацию от роста

## CPP для органики (опционально, с июля 2025)

Если планируется таргетинг разных intent-кластеров — рассмотреть создание Custom Product Pages с разными скриншотами под каждый кластер. С июля 2025 CPP отображаются в органических результатах поиска, не только в платных.
