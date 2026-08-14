# ASO Foundations — Definitions, Lifecycle Role, Ranking Algorithm, KPI Funnel

## Summary

ASO (App Store Optimization) — непрерывный процесс улучшения видимости и конверсии приложения в сторах (App Store, Google Play) через оптимизацию метаданных, визуальных ассетов и поведенческих сигналов. Охватывает весь lifecycle от pre-launch до retention. Алгоритм Apple ранжирует по двум уровням: метаданные определяют индексацию (попадаешь ли в выдачу), поведенческие сигналы определяют позицию (насколько высоко).

---

## Key Principles

- **65% загрузок из App Store происходят после keyword search** — поиск является основным каналом discovery [1]
- **ASO — не разовая задача**: алгоритм постоянно меняется, конкуренты обновляют метаданные, поведение пользователей эволюционирует
- **Два уровня алгоритма**: метаданные → индексация (eligibility); поведенческие сигналы → ранжирование (position) [2, 5]
- **Конверсия влияет на ранг**: App Store учитывает install rate из результатов поиска как сигнал качества [2]
- **Uninstall rate — штрафной сигнал**: алгоритм трактует высокий uninstall как несоответствие app↔query [2]
- **CPP в органике с июля 2025**: Custom Product Pages теперь отображаются в органических результатах поиска [3, 4]
- **AI-теги Apple (iOS 26 beta)**: Apple автогенерирует теги через ML на основе метаданных — новый слой discovery [4, 5]

---

## Data / Models

### ASO Component Map (MECE)

| Компонент | Что оптимизируем | Влияет на |
|---|---|---|
| Метаданные | Title, Subtitle, Keyword field, Description | Индексация, ранжирование |
| Визуальные ассеты | Icon, Screenshots (+ captions с 2025), Preview video | CVR, ранжирование (косвенно) |
| Поведенческие сигналы | Installs velocity, Retention, Session depth, Uninstalls | Ранжирование |
| Пользовательские сигналы | Ratings (avg + count), Reviews, Sentiment | Ранжирование, CVR |
| Контент | In-App Events, Custom Product Pages | Индексация (с 2025), CVR |

### Ranking Factors — иерархия (App Store iOS)

| Фактор | Категория | Вес | Примечание |
|---|---|---|---|
| App Title | Metadata | Критический | Максимальный вес среди текстовых полей |
| Subtitle | Metadata | Критический | 30 chars; второй по весу |
| Keyword Field | Metadata | Критический | 100 chars; не дублировать title/subtitle |
| Screenshot Captions | Metadata | Средний | С июня 2025 — активно индексируются [3] |
| In-App Events | Content | Средний | Индексируются и матчатся к поисковым запросам [3] |
| Custom Product Pages | Content | Средний | С июля 2025 в органике [2, 3] |
| Download Volume & Velocity | Behavioral | Высокий | Всплеск установок = сигнал релевантности |
| Conversion Rate (Install Rate) | Behavioral | Высокий | Прямо влияет на видимость |
| Retention & Engagement | Behavioral | Высокий | Session length, DAU, D1/D7/D30 retention |
| Uninstall Rate | Behavioral | Штраф | Высокий uninstall → понижение позиции |
| Ratings (avg score) | User Signal | Высокий | <3.5 звезды → снижение видимости; 4.5+ = 3× больше установок [5] |
| Rating Count | User Signal | Средний | Recency важна |
| Update Frequency | Quality | Средний-высокий | Топ-приложения: 1-4 апдейта/мес, медиана ~18 дней [5] |
| Crash Rate | Quality | Средний | Активно штрафуется |
| Description | Metadata | Низкий | Влияет на CVR, не на индексацию напрямую |

### KPI Funnel: Impressions → Downloads (5 категорий) [MobileAction, 2026]

```
IMPRESSIONS / Store-listing visitors
        ↓  CTR (tap-through rate)
PRODUCT PAGE VIEWS
        ↓  CVR (conversion rate / install rate)
DOWNLOADS (Installs)
        ↓  Activation / Onboarding
ACTIVE USERS (DAU/MAU)
        ↓  Retention / Monetization
LTV / Revenue
```

| KPI-категория | Метрики |
|---|---|
| Visibility | Keyword rankings, Top-chart position, Impressions, Visibility score |
| Conversion | CTR (impressions→page), CVR (page→install), Install Rate |
| Growth | Install volume, Install velocity, Organic vs. paid split, eCPI |
| User Feedback | Avg rating, Rating count, Review sentiment, Response rate |
| Monetization | Revenue, ARPU, LTV |

**Platform разница**: App Store считает *impressions* (каждый показ в Today/Games/Apps/Search); Google Play считает *store-listing visitors* (уникальные визиты на страницу). Формулы CVR не совпадают — не сравнивать напрямую [MobileAction].

### Benchmarks (AppTweak ASO Report 2025)

| Метрика | Данные |
|---|---|
| Lift CVR от ASO-оптимизации | +3-5% → материальный рост органики без допрасходов |
| Games CVR lift (2025) | +3.5% |
| Non-games CVR lift (2025) | +5.9% |
| Рейтинг 4.5+ | 3× больше установок vs. ниже 4.5 [5] |
| Рейтинг <3.5 | Видимость значительно снижается [2] |

---

## Evolution / Trends

| Период | Изменение |
|---|---|
| До 2016 | Метаданные доминируют; достаточно keyword stuffing в title |
| 2016 | Keyword field ограничен до 100 chars; поведенческие сигналы начинают учитываться |
| 2017-2019 | Semantic matching, NLP; description de-indexed |
| 2021 (iOS 15) | Custom Product Pages, A/B тестирование. Engagement/retention — подтверждённые сигналы |
| 2022 | In-App Events индексируются для поиска |
| 2023-2024 | Semantic search improvements; синонимы без точного match |
| Июнь 2025 | Screenshot captions активно индексируются [3] |
| Июль 2025 | CPPs отображаются в органических результатах поиска [2, 3] |
| 2025 (iOS 26 beta) | AI-generated tags от Apple — автогенерация меток через ML [4, 5] |

---

## Open Questions & Gaps

- **Точные веса сигналов** не публикуются Apple — все данные косвенные (industry observation)
- **AI-теги iOS 26**: в beta, неизвестно когда станут production и как точно влияют на ранг
- **Глубина semantic matching**: подтверждено для plurals/singulars; multi-hop synonyms — unknown
- **Персонализация vs. универсальный ранк**: в какой мере каждый пользователь видит разный порядок — неизвестно
- **Screenshot captions**: новый сигнал (июнь 2025), нет надёжных кейсов с замером delta

---

## Sources

1. AppTweak — "What is app store optimization and why is ASO important" — apptweak.com/en/aso-blog/what-is-app-store-optimization-and-why-is-aso-important (2026)
2. AppTweak — "What are the top ranking factors on the App Store in 2026?" — apptweak.com/en/aso-blog/app-store-ranking-factors (2026)
3. SplitMetrics — "App Store Ranking Factors: How to Grow Your iOS App (Updated With 2025 News)" — splitmetrics.com/blog/apple-app-store-ranking-factors/ (2025)
4. MobileAction — "App Store ranking factors: How to boost app visibility in 2026" — mobileaction.co/blog/app-store-ranking-factors/ (2026)
5. MobileAction — "ASO KPIs: Measuring what matters to drive app growth in 2026" — mobileaction.co/blog/aso-kpis/ (2026)

---

## Reuse Hooks

- **Перед стартом любого ASO-проекта**: проверить все 5 KPI-категорий — какие данные есть, каких нет.
- **При оценке keyword**: метаданные = eligibility; поведенческие сигналы = position. Нет индексации → ранг невозможен.
- **При падении позиций**: разделить причину — изменилась индексация (metadata) или поведенческие сигналы (retention/CVR/uninstalls)?
- **Screenshot captions**: с июня 2025 — обязательно включать target keywords в подписи к скриншотам.
- **CPP стратегия**: с июля 2025 CPPs в органике → можно создавать keyword-specific страницы без платного трафика.
- **AI-теги**: проверять в App Store Connect и удалять нерелевантные.

---

_Update log: 2026-03-06 — initial version, sources: AppTweak (2026), SplitMetrics (2025), MobileAction (2026)_
