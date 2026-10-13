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
Шаблон — `config/api_keys.env.example` в репозитории: `cp config/api_keys.env.example ~/.config/aso-tools/api_keys.env`.

Нужны: `ASA_ORG_ID`, `ASA_CLIENT_ID`, `ASA_KEY_ID` (Apple Search Ads → Account Settings → API)
и PEM-пара `apple_ads_private_key.pem` / `apple_ads_public_key.pem` в `~/.config/aso-tools/keys/`.

Если чего-то не хватает — не угадывать значения, а сказать пользователю, какой переменной нет
и куда её взять (описано в `config/api_keys.env.example` в репозитории скиллов).

## Структура данных

Скилл создаёт папку `./asa-launch/` в текущей директории:
```
./asa-launch/
├── config/
│   └── campaign.json   # campaign_id, ключи с adgroup_id, даты
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
- Только EXACT. BROAD на запуске не используется: это отдельный тест в работающей
  кампании с историей (`knowledge/asa_campaign_architecture.md` → «BROAD — только как
  отдельный тест», ведёт его asa-monitoring)
- `automatedKeywordsOptIn=False` — Apple иначе добавит свои ключи
- Исключить брендовые запросы конкурентов если нет явного конкурентного таргетинга
- Исключить смежные ниши с другим intent (уточни у пользователя)

**Новые ключи ищем до запуска** (`aso-collection`: ASA popularity, search hints, метаданные конкурентов) и проверяем отдельной кампанией на минимальной ставке.

⚠️ ASA popularity доступна только если приложение из нужной ниши уже есть в твоей ASA-организации: `getRecommendedKeywords` отдаёт пустой массив с HTTP 200 для чужих adamId. Если приложение ещё не опубликовано — ключи отбираются по search hints и фактической конкурентности выдачи, а popularity замеряется после релиза.

**Выбор архитектуры кампании** (см. `asa_campaign_architecture.md`):
- ≤ 8 ключей одного intent → одна кампания
- > 8 ключей с разными аудиториями → **thematic multi-campaign** (каждый кластер = отдельная кампания)

Внутри кампании при любой архитектуре — **1 ключ = 1 адгруппа** (EXACT, автоподбор ключей выключен). Обоснование — в шаге 3.

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

### 3. Создай адгруппы — 1 ключ = 1 адгруппа

**Каждый ключ — в своей адгруппе.** Имя адгруппы = текст ключа. EXACT, автоподбор ключей выключен.

Почему не одна адгруппа на все ключи:
- **Ставка ключа и default bid адгруппы совпадают.** Нет fallback-ставки, которая отстаёт от ключевой и режет её на уровне адгруппы.
- **Ключ управляется отдельно.** Пауза, подъём, смена CPP или таргетинга одного ключа не задевают остальные.
- **Отчёты по адгруппам = отчёты по ключам.** На этой архитектуре построены asa-monitoring
  (`asa_fetch.py --by-keyword`, `bids.py`, `reconcile.py`) и правило для новых ключей
  в `knowledge/asa_campaign_architecture.md` → «Новые ключи — EXACT по умолчанию».

Один и тот же ключ не должен стоять в двух адгруппах кампании: они конкурировали бы за один запрос.

```python
def add_keyword_adgroup(api, campaign_id, text, bid):
    """Адгруппа + один EXACT-ключ. Повторно не создаёт: имя адгруппы уникально в кампании."""
    if any(a["name"] == text for a in api.get_adgroups(campaign_id)):
        return None
    ag = api.create_adgroup(
        campaign_id=campaign_id,
        adgroup_name=text,
        currency="USD",
        cpc_bid=bid,  # default bid адгруппы = ставка ключа
        # start_time не передаём — старт «сейчас» в UTC. Своё время — только aware
        # (datetime.now(timezone.utc)); наивное datetime create_adgroup отвергает.
        automated_keywords_opt_in=False,  # автоподбор ключей Apple — всегда выключен
        device_class=["IPHONE"],  # в targetingDimensions уходят только заданные измерения
    )
    ag_id = ag["data"]["id"]
    api.add_targeting_keywords(campaign_id, ag_id, [{
        "text": text, "matchType": "EXACT",
        "bidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}}])
    return ag_id
```

Проверка «уже есть» — по кабинету, а не по локальному состоянию: Apple иногда принимает POST
и обрывает соединение без ответа, и повторный прогон должен дочинить, а не упасть
на `DUPLICATE_AD_GROUP_NAME`.

### 4. Добавь ключевые слова

Ставки — по bid discovery: без данных о clearing price все ключи стартуют с минимума.

```python
keywords = ["keyword one", "keyword two"]
adgroups = {}
for text in keywords:
    adgroups[text] = add_keyword_adgroup(api, campaign_id, text, bid=0.10)
print(f"Adgroups created: {sum(v is not None for v in adgroups.values())}/{len(keywords)}")
```

**Ставку ключа и default bid адгруппы менять вместе.** Default bid — fallback ставка адгруппы;
если он ниже ставки ключа, Apple может ограничивать через уровень адгруппы. Адгруппу правь
прямым PUT одного поля `defaultBidAmount`: `update_adgroup()` переписывает и другие поля адгруппы.

### 5. Добавь негативы

**Campaign-level** — общий мусор и конкуренты:
```python
campaign_negatives = [
    {"text": "competitor brand", "matchType": "EXACT"},
    {"text": "wrong niche",      "matchType": "BROAD"},
]
api.add_campaign_negative_keywords(campaign_id, campaign_negatives)
```

Для EXACT-адгрупп adgroup-level негативы не нужны: показы идут ровно по выбранным ключам.
Негативы BROAD-адгрупп появляются только вместе с тестом BROAD — см.
`asa-monitoring/knowledge/api_snippets.md`, «Новые ключи и тест BROAD».

### 6. Проверь что кампания запустилась

```python
campaign = api.get_campaign(campaign_id)
print(f"Status: {campaign['status']}")  # должно быть ENABLED
for ag in api.get_adgroups(campaign_id):
    kws = api.get_targeting_keywords(campaign_id, ag["id"])
    # ожидаем: 1 EXACT-ключ ACTIVE, automatedKeywordsOptIn=False, displayStatus RUNNING
    print(ag["name"], ag["displayStatus"], ag["automatedKeywordsOptIn"],
          [(k["text"], k["matchType"], k["status"], k["bidAmount"]["amount"]) for k in kws])
```

### 7. Сохрани в campaign.json

```json
{
  "app_name": "{App}",
  "app_id": 0,
  "campaign_id": 0,
  "campaign_start": "YYYY-MM-DD",
  "last_change": "YYYY-MM-DD",
  "organic_baseline_14d": 0,
  "daily_budget": 20,
  "countries": ["US", "GB", "CA"],
  "keywords": [
    {"text": "keyword", "adgroup_id": 0, "keyword_id": 0, "bid": 0.10, "status": "ENABLED"}
  ],
  "negative_keywords": ["competitor brand"],
  "change_log": [
    {"date": "YYYY-MM-DD", "action": "campaign created", "reason": "initial launch"}
  ]
}
```

Запиши в `./asa-launch/config/campaign.json`.

## Правила запуска

- **Ничего не создавать в API без явного «да».** Сначала показать пользователю план целиком: кампании и кластеры, ключи, стартовые ставки, дневной бюджет, страны, негативы. Кампания начинает тратить деньги сразу после создания
- Не запускать BROAD на старте — даёт нерелевантный трафик без истории; тест BROAD — позже, по `asa_campaign_architecture.md`
- `automatedKeywordsOptIn=False` **всегда** — автоподбор ключей Apple не включаем
- 1 ключ = 1 адгруппа; один ключ — только в одной адгруппе кампании, иначе две адгруппы конкурируют за один запрос
- Первые 3–5 дней не трогать ставки у ключей, **где impressions уже есть** — набирается статистика
- Ключи с нулевыми impressions — исключение: ставку поднимаем каждые ~2 часа, пока показы не появятся
- Первая проверка показов — через ~2 часа после запуска; полный разбор — через 3 дня по скиллу asa-monitoring
- Organic baseline важен: без него невозможно отличить каннибализацию от роста

## CPP для органики (опционально, с июля 2025)

Если планируется таргетинг разных intent-кластеров — рассмотреть создание Custom Product Pages с разными скриншотами под каждый кластер. С июля 2025 CPP отображаются в органических результатах поиска, не только в платных.
