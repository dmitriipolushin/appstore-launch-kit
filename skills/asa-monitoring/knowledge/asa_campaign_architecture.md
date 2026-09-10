# ASA Campaign Architecture — Budget Isolation, Thematic Clusters, Bid Discovery

## Summary

Однокампанийная архитектура Apple Search Ads создаёт скрытую проблему — **budget starvation**: при ограниченном дневном бюджете Apple распределяет показы непропорционально, отдавая всё ключам с наибольшей ожидаемой win rate, оставляя остальные с нулевыми impressions. Ключ с 0 impressions — не доказательство отсутствия спроса, а симптом голодания бюджета. Решение: **тематическая кластеризация** — каждый семантический кластер получает собственную кампанию с изолированным бюджетом. Параллельно: **bid discovery strategy** — старт с $0.10 и пошаговое повышение находит реальный clearing price без переплат. Подтверждено на практике: product_scanner v1→v2 migration, 2026-04-07.

---

## Key Principles

- **Budget starvation ≠ no demand**: 0 impressions в кампании не означает отсутствие спроса по ключу — он мог не получить шанса из-за конкуренции за общий бюджет
- **Изоляция бюджета = честный эксперимент**: каждый кластер в отдельной кампании получает свой бюджет → можно сравнивать кластеры по реальным данным, не по артефактам распределения
- **Paused keyword ≠ dead keyword**: если ключ паузировали без накопленных impressions — нельзя делать вывод об отсутствии спроса. Только изолированный эксперимент с собственным бюджетом даст ответ
- **Second-price auction**: фактический CPT часто в 2–5× ниже установленного бида → $0.10 bid может давать реальные impressions если clearing price $0.05–$0.08
- **Clearing price = экспериментальная находка**: нет смысла гадать — начать с $0.10 и поднимать на $0.20 каждые ~2 часа, пока не появятся impressions
- **Равный стартовый бюджет**: все кластеры Phase 1 получают одинаковый бюджет — это исключает предвзятость в сравнении результатов
- **Phase 1 / Phase 2 rollout**: не запускать все кластеры сразу — сначала топ-7 с наибольшим приоритетом, Phase 2 через 14 дней на основе реальных данных

---

## Data / Models

### Budget Starvation — Механизм

В одной кампании с N ключами и бюджетом $B/день Apple распределяет impressions по ключам неравномерно:

```
Факторы, влияющие на получение impressions:
  → Ожидаемая auction win rate (bid vs. конкурентов)
  → Оценочный quality score (исторический CTR, релевантность)
  → Объём аукционных opportunities (спрос по ключу)

Ключи с наибольшей win rate → получают большинство impressions
Ключи с низкой win rate или без истории → оказываются вне окна распределения
```

| Ситуация | Наблюдение | Реальная причина |
|---|---|---|
| Ключ A: 200 impressions/день | Много данных, можно оптимизировать | Apple даёт ему большую долю бюджета |
| Ключ B: 0 impressions/день | Кажется — "нет спроса" | Возможно — голодание бюджета, не отсутствие спроса |
| Ключ B в отдельной кампании | 50+ impressions/день | Спрос был, просто не распределялся |

**Вывод**: данные из смешанной кампании — **selection bias**. Для честной оценки каждый кластер должен иметь собственный бюджет.

### Thematic Clustering — Принципы

Семантические кластеры для ASA формируются по **intent + аудитории**, не по форме ключа:

| Тип кластера | Примеры | Аудитория |
|---|---|---|
| Competitor | competitor brand, competitor app | Аудитория конкурентов — высокий commercial intent |
| Dietary vertical | halal checker, vegan scanner | Специфическая диетическая потребность |
| Core category | lebensmittel scanner, food scanner | Широкий категорийный спрос |
| Tech/AI | ki food scanner, ai ingredients | Tech-aware аудитория |
| Allergen / Intolerance | allergie scanner, gluten check | Медицинская/диетическая проблема |
| Long-tail | e nummern app, zusatzstoffe check | Специфический проблемный язык |

**Правило кластеризации**: если два ключа обращаются к разным аудиториям или решают разные проблемы — они должны быть в разных кластерах с независимым бюджетом. Одна аудитория = один кластер = одна кампания.

### Single vs. Multi-Campaign — Когда что использовать

| Ситуация | Архитектура | Почему |
|---|---|---|
| ≤ 8 ключей, один intent | Single campaign, одна adgroup (EXACT, Search Match OFF) | Дробить бюджет нет смысла |
| > 8 ключей, разные аудитории | Multi-campaign thematic | Budget starvation слишком вероятен |
| Тестирование новых кластеров | Отдельная кампания | Изолированный эксперимент, не мешает действующим |
| Разные geo с разным поведением | Отдельная кампания per geo | Бюджет не перетекает между рынками |
| Уже активная кампания + новые кластеры | Добавить новые кампании, старую не трогать | Сохранить историю, изолировать новые данные |

### Search Match / Discovery-adgroup — почему не используется

Схема «AG1 Keywords + AG2 Discovery» отменена. Discovery-adgroup с `automatedKeywordsOptIn=True` не работает ни на одной ставке:

| Ставка | Что происходит |
|---|---|
| Низкая ($0.15–0.20) | Показов мало, поисковые запросы единичные, статистики нет — переносить в EXACT нечего |
| Высокая | Apple подбирает всё, что похоже на метаданные; растёт доля нерелевантных запросов |

**Замер на живой кампании** (оба подхода в одном аккаунте):

| Показатель | EXACT | Discovery |
|---|---|---|
| CPT | $1.52 | $0.98 (−35%) |
| Tap → install CR | 51.5% | 27.2% (в 1.9 раза хуже) |
| CPI | $2.95 | $3.60 (+22%) |
| Installs на $100 | 33.9 | 27.8 |

Скидка на тап 35% не покрывает провал конверсии 47%. Break-even для Discovery при CR 27.2% — CPT $0.80.

**Вывод**: источник новых ключей — исследование до запуска (ASA popularity, search hints, метаданные конкурентов), а не Search Match. Проверка нового ключа — отдельная кампания на минимальной ставке.

### Bid Discovery Strategy

**Ключевой принцип**: при правильном биде Apple показывает impressions почти сразу — обычно в течение первого часа после запуска. Ждать сутки, а тем более 3 дня, не нужно. Нулевые impressions означают, что ставка не проходит в аукцион, и само это состояние не изменится: ждать здесь нечего, нужно двигать ставку.

```
Час 0:      Запустить все кластеры с bid = $0.10
            (EXACT match, automatedKeywordsOptIn=False)

+1–2 часа:  Проверка impressions
            impressions > 0  → bid прошёл в аукцион, фиксируем как clearing price
            impressions = 0  → поднять bid на $0.20 (до $0.30)

каждые
+2 часа:    Повторять, пока impressions не появятся
            ($0.30 → $0.50 → $0.70 → ...)

После первых impressions:
            bid не трогать 3–5 дней — набирается статистика по TTR, installs, trials.
            Это единственный этап, где ждём днями, а не часами.

Стоп-условия:
  bid достиг $2.00 + impressions = 0  → проверить hints API: есть ли объём вообще?
  CPA превысил target ($4–5)          → снизить bid до уровня где CPA < target
```

Поиск clearing price при часовом цикле занимает один рабочий день вместо двух недель.

**Разграничение причин нулевых impressions:**
- Bid ниже clearing price → поднять bid на $0.20
- Bid выше clearing price, но нет impressions → низкий спрос по ключу в данном сторфронте → проверить hints API или паузировать ключ
- Дневной бюджет на уровне единиц установок → сначала поднять бюджет (см. GATE 1 в `decision_gates.md`)

**Почему $0.10 start работает (second-price auction)**:
- Bid = максимальная готовность платить; фактический CPT = второй bid + $0.01
- При низкой конкуренции аукцион очищается по минимальной цене
- Поднятие bid не удвоит расходы — только увеличит win rate в аукционах

**Контраст с высокобидовым стартом**:
- Высокий bid ($2–5) → быстро расходует бюджет на первых ключах → starvation остальных сохраняется
- Низкий bid + частые проверки → находим реальный clearing price → экономим на ключах где конкуренция низкая

### campaigns_v2.json — Config Format для Multi-Campaign

Для multi-campaign архитектуры используется `campaigns_v2.json` вместо `campaign.json`:

```json
{
  "app_name": "App Name",
  "app_id": 0000000000,
  "launch_date": "YYYY-MM-DD",
  "countries": ["DE"],
  "daily_budget_per_campaign": 7.00,
  "total_daily_budget": 49.00,
  "default_bid": 0.10,
  "bid_strategy": "start at $0.10, raise $0.20 every 3 days until impressions appear",

  "v1_campaign_id": 2143544578,
  "v1_status": "PAUSED",
  "v1_paused_date": "YYYY-MM-DD",

  "campaigns": [
    {
      "id": 0000000001,
      "adgroup_id": 0000000002,
      "name": "PS — ClusterName",
      "status": "ACTIVE",
      "keywords": [
        {"text": "keyword one", "bid": 0.10, "status": "ACTIVE"},
        {"text": "keyword two", "bid": 0.10, "status": "ACTIVE"}
      ]
    }
  ],

  "phase_2_campaigns": [
    {
      "name": "PS — NextCluster",
      "keywords": ["keyword a", "keyword b"]
    }
  ],

  "negative_keywords": ["competitor brand", "wrong niche"],

  "change_log": [
    {
      "date": "YYYY-MM-DD",
      "action": "description of change",
      "reason": "why it was made"
    }
  ]
}
```

**Ключевые отличия от `campaign.json`** (single-campaign format):
- `campaigns[]` — массив, каждый элемент = отдельная кампания со своим `id` и `adgroup_id`
- `phase_2_campaigns[]` — запланированные, ещё не запущенные кластеры
- `daily_budget_per_campaign` + `total_daily_budget` вместо одного `daily_budget`
- `v1_campaign_id` + `v1_status` — ссылка на заморозку предыдущей версии
- `negative_keywords` — общие для всех кампаний, применяются на campaign level через API

### Phase Rollout Model

```
Phase 1 — Запуск (Топ-7 кластеров)
│
├── Отбор: наибольший ожидаемый объём + стратегическая важность
│    (competitor, core category, сильные dietary verticals)
├── Равный бюджет на каждую кампанию
├── Стартовый bid $0.10
└── Длительность наблюдения: 14 дней

                ↓ после 14 дней

Phase 1 → Phase 2 Decision Gate
│
├── CPA < $4 + impressions > 0   → увеличить бюджет кластера
├── impressions > 0, 0 installs (7+ дней) → пауза кластера
├── 0 impressions, bid уже $1.00+ → проверить hints API → пауза если нет объёма
└── Кластеры Phase 2 → запускать

Phase 2 — Расширение (+6 кластеров)
│
├── Long-tail и нишевые вертикали
├── Бюджет = перераспределить от слабых Phase 1 кластеров
└── Повторить Decision Gate через 14 дней
```

### Monitoring Multi-Campaign — Изменение Workflow

> **Принцип**: все кампании в `campaigns_v2.json` равнозначны — нет деления на «боевые» и «тестовые». Каждая оценивается по своим метрикам. Решение о паузе или масштабировании принимается по данным (IPM, CPA), а не по истории создания кампании.

При наличии `campaigns_v2.json` изменяется работа `asa-monitoring`:

**Загрузка контекста**: читать `campaigns_v2.json` → извлечь все `campaign.id` и `adgroup_id` у кампаний со статусом ACTIVE (включая DE/AT/CH)

**Сбор данных**: запустить `asa_fetch_raw.py` для каждого campaign_id в цикле:
```bash
for campaign_id in (все ACTIVE ID из campaigns_v2.json):
    python3 asa_fetch_raw.py --campaign-id {campaign_id} --days 7
```

**Ключевой артефакт сессии** — сравнительная таблица кластеров:

```
IPM = (installs / impressions) × 1000
```

```
| Кластер          | Spend | Impr | Inst | IPM  | CPA   | TTR  | Действие |
|------------------|-------|------|------|------|-------|------|----------|
| Competitors      | $5.20 | 120  | 3    | 25.0 | $1.73 | 3.5% | ✓ hold   |
| Halal            | $4.80 | 80   | 2    | 25.0 | $2.40 | 2.5% | ✓ hold   |
| Vegan            | $0.00 | 0    | 0    | —    | —     | —    | bid↑     |
| Gluten           | $7.00 | 200  | 8    | 40.0 | $0.88 | 4.0% | ✓✓ scale |
| Scanner/Allergie | $2.10 | 45   | 1    | 22.2 | $2.10 | 2.2% | ✓ hold   |
| German Core      | $6.50 | 180  | 5    | 27.8 | $1.30 | 2.8% | ✓ hold   |
| KI/Tech          | $0.00 | 0    | 0    | —    | —     | —    | bid↑     |
```

**IPM — ключевая метрика для сравнения кластеров и CPP:**
- Показывает эффективность всей воронки (показ → тап → инсталл) в одном числе
- При запуске Custom Product Pages: сравнивать IPM по кластеру до и после CPP
- IPM растёт → CPP работает; IPM не меняется → дело не в странице (проблема в CR или relevance ключей)

| IPM | Интерпретация |
|---|---|
| > 15 | Отлично |
| 8–15 | Хорошо |
| 3–8 | Средне |
| < 3 | Проблема в CTR или CR |

**Правила принятия решений на уровне кластера**:

| Статус | Условие | Действие |
|---|---|---|
| ✓✓ Scale | CPA < $1.50 + impressions > 50/день | Увеличить бюджет кластера |
| ✓ Hold | CPA $1.50–$4.00 + есть impressions | Держать, точечно оптимизировать ключи |
| bid↑ | 0 impressions, bid ≤ $1.00 | Поднять bid на $0.20, проверить через ~2 часа |
| Пауза кластера | impressions есть, 0 installs 7+ дней | Весь кластер на паузу |
| Пауза кластера | 0 impressions при bid $1.00+, hints API подтвердил нет объёма | Весь кластер на паузу |

---

## Open Questions & Gaps

- **Оптимальный размер кластера**: нет данных — работает ли подход "1 ключ = 1 кампания" или это слишком дробно?
- **Self-competition**: если несколько наших кампаний бидят на похожие запросы (например "halal check" и "halal checker") — конкурируем ли мы сами с собой? Apple должен объединять bidder identity, но неизвестно как именно
- **Clearing price variance**: насколько clearing price отличается по дням недели и сезонности — нет данных для DE
- **Phase 2 threshold**: через сколько дней данных достаточно для запуска Phase 2 — 14 дней эмпирическое предположение, не подтверждённая норма

---

## Sources

- Empirical observation: product_scanner campaign v1→v2 migration, 2026-04-07. 7 тематических кампаний запущены; ключи, показавшие 0 impressions в v1 (single campaign), получили impressions в изолированных кампаниях
- Second-price auction mechanics: Apple Search Ads best practices (Apple Developer Documentation)
- Budget allocation: Apple Search Ads Help — "How budget is distributed across keywords"

---

## Reuse Hooks

- **При 0 impressions**: не делать вывод "нет спроса" — сначала проверить не голодание ли бюджета. Изолировать в отдельную кампанию, ставку поднимать каждые ~2 часа
- **При старте**: bid = $0.10, не $1–3. Clearing price — экспериментальная находка, +$0.20 каждые ~2 часа, пока нет показов
- **При > 8 ключей + разные аудитории**: разбить на тематические кампании с равным бюджетом
- **Config**: `campaigns_v2.json` для multi-campaign; `campaign.json` для single-campaign
- **Phase rollout**: Phase 1 (7 кластеров) → 14 дней данных → Decision Gate → Phase 2
- **Paused v1**: всегда сохранять v1 campaign на паузе — не удалять, чтобы можно было вернуться

---

_Update log: 2026-04-07 — initial version, based on product_scanner v1→v2 migration experiment_
