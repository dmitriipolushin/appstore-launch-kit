# ASO Metrics & Iteration — Tracking, Attribution, ROI, Scaling

## Summary

Измерение ASO состоит из трёх слоёв: (1) трекинг метрик по воронке (visibility → conversion → growth → retention); (2) атрибуция — разделение органического и платного трафика, расчёт organic multiplier и каннибализации; (3) итерация — экспериментальный цикл с корректной статистической методологией и масштабирование через maturity model. Ключевая проблема 2025-2026: privacy изменения и рост CPI делают органический рост must-have, но его точное измерение затруднено из-за overlap с платным трафиком.

---

## Key Principles

- **Organic multiplier снижается**: доля органики падала ~20% между 2016-2019, тренд продолжается [3]
- **Paid → organic halo подтверждён**: shutoff эксперименты показывают -18-30% падение органики при отключении платного трафика [6]
- **Каннибализация реальна**: ASA может захватывать пользователей, которые нашли бы приложение органически — нужно измерять incremental rate [5]
- **CVR x keyword = dual signal**: высокий объём + низкий CVR = liability, не asset; тестировать или убирать [4]
- **61% A/B тестов не дают значимого победителя** — 43% failures из-за insufficient sample size [search results]
- **Компании с 10+ тестами в месяц растут в 2.1× быстрее** [search results]
- **Incrementality ≠ attribution**: стандартная MMP-атрибуция недооценивает истинный impact платного трафика на органику [6]
- **95% confidence** — минимальный порог для значимых тестов; 90% только для низкорисковых изменений [2]

---

## Data / Models

### ASO Метрики — Полная карта (2026)

| Категория | Метрика | Что показывает | Action trigger |
|---|---|---|---|
| **Visibility** | Keyword rankings | Позиция по target ключам | Падение > 5 позиций → аудит metadata/behavioral |
| **Visibility** | **ASA Impression Share** | % eligible impressions которые мы захватили (range: low–high) | Share > 85% + rank ONE → bid raise бесполезен, фокус на CR; share < 50% + rank > ONE → поднять bid |
| **Visibility** | Share of Voice (SOV) | % видимости в keyword set vs. конкуренты | SOV < 20% в core category → расширить coverage |
| **Visibility** | Search Ad Pollution | Плотность платных объявлений на keyword | Высокий score → сдвинуть фокус на менее конкурентные ключи |
| **Visibility** | Impressions (App Store) / Store Listing Visitors (GP) | Охват | Падение без metadata изменений → алгоритмический апдейт |
| **Conversion** | Impression → Page View ratio | CTR из поиска | Низкий → проблема с icon / title / 1-2 скриншота |
| **Conversion** | CVR (Page → Install) | Конверсия страницы | < category benchmark → A/B тест creatives |
| **Conversion** | Keyword CVR | CVR по отдельным ключам | Высокий vol + низкий CVR = убрать из title/subtitle |
| **Growth** | Install velocity | Скорость набора установок | Замедление → проверить behavioral signals |
| **Growth** | Organic Multiplier | Органика / платный трафик | Flat при росте paid → ASO неэффективен |
| **Growth** | Install Velocity by Locale | Темп роста по странам | Высокий рост в локали → приоритизировать локализацию |
| **Quality** | D1/D7/D30 retention | Удержание пользователей | D7 < 20% → алгоритм начнёт депрессировать позиции |
| **Quality** | Crash rate / ANR | Стабильность приложения | > 8% → исключение из featured surfaces (GP) |
| **Quality** | Battery wake locks | Энергопотребление (GP, 2026) | > 5% → исключение из recommendations с 01.03.2026 |
| **Social** | Avg rating + velocity | Рейтинг + темп новых отзывов | < 3.7 → приоритизировать review prompting |
| **Social** | Review sentiment delta | Изменение тональности | Рост негатива по фиче → предсказывает падение CVR |
| **Competitive** | Competitor metadata update freq. | Активность конкурентов | Лаг > 3 месяцев в реакции → потеря доли |
| **Competitive** | Keyword ranking volatility | Флуктуация позиций за 7 дней | Высокая → алгоритмический апдейт или новый конкурент |

### KPI Funnel — Полная воронка с метриками

```
IMPRESSIONS / Store-listing visitors
    ↓  [Impression → Page View ratio]  ← тестировать: icon, title, 1-2 скриншота
PAGE VIEWS
    ↓  [CVR: Page → Install]  ← тестировать: screenshots 1-3, video, description hook
INSTALLS (Organic)
    ↓  [D1 activation rate]  ← тестировать: onboarding
ACTIVATED USERS
    ↓  [D7 retention]  ← продуктовая метрика, влияет на ранг
    ↓  [D30 retention]
    ↓  [Revenue / ARPU / LTV]
```

---

## Attribution Models

### Organic vs. Paid — Проблема разделения

Стандартная MMP (Mobile Measurement Partner) атрибуция по last-click недооценивает влияние paid на органику. Исследование (arxiv, 2025) [6]:

| Платформа | Органических установок на $100 | % недооценки CPI |
|---|---|---|
| Google Ads | 0.87 органических / $100 | 3.3% |
| Facebook | 3.33 органических / $100 | 9.1% |
| Other platforms | 5.59 органических / $100 | 9.7% |

**Halo effect формула** [6]:
```
Same-day organic lift = 2.79 × (Ad spend in $100s)
Next-day spillover    = 0.92 × (Previous day spend in $100s)
Effective CPI с учётом halo = $2.50 (vs. $2.68 без учёта)
```

**Ключевой вывод**: При полном отключении платного трафика органика падает на **18-30%**. Paid и organic — комплементарные каналы, не конкурирующие.

### Organic Multiplier

```
Organic Multiplier = Organic Installs / Paid Installs
```

- Здоровый multiplier должен **расти со временем** при улучшении ASO
- Flat multiplier при росте paid spend = ASO не работает
- iOS uplift может быть **в 4× выше**, чем Android для одного приложения [3]
- Тренд: доля органики падала ~20% за 2016-2019, продолжает снижаться [3]

### Cannibalization Analysis (7-step) [5]

```
1. Baseline organic = First-time Search installs МИНУС ASA installs (до кампании)
2. Campaign period organic = First-time Search installs МИНУС ASA installs (во время)
3. Cannibalized installs = Campaign organic МИНУС Baseline organic (если < 0)
4. Incremental installs = ASA installs МИНУС Cannibalized installs
5. Incremental rate = (Incremental / ASA) × 100%
```

| Incremental rate | Интерпретация |
|---|---|
| > 80% | Низкий риск каннибализации — ASA создаёт новый спрос |
| 50-80% | Умеренная каннибализация — мониторить |
| < 50% | Высокая каннибализация — ASA замещает органику |
| Negative organic uplift | Критическая каннибализация — пересмотреть keyword targeting |

### Incrementality Analysis (AppTweak NeuralProphet) [1]

Для измерения **истинного impact** metadata/creatives изменений:

| Модель | Применение | Методология |
|---|---|---|
| Extrapolation | Долгосрочный impact (metadata updates, rebrands) | Обучение на 3 годах исторических данных → прогноз → delta |
| Interpolation | Краткосрочные события (on/off campaigns, featurings) | Before/after сравнение с контрольной группой |

**Требования к статистической значимости**:
- Confidence interval: 95%
- P-value: < 0.05
- Контроль: seasonality, holidays, market trends через NeuralProphet

**Пример**: Bitcoin.com во время election week — +79% incremental lift выявлен через extrapolation model [1].

---

## Experimentation Framework

### Phiture A/B Testing Maturity Model [2]

| Уровень | Описание | Характеристика |
|---|---|---|
| Level 0 | Нет тестирования | Только интуиция |
| Level 1 | Изолированные тесты | Разрозненные эксперименты без системы |
| Level 2 | Процесс внедрён | **Критический переход** — кросс-командная координация |
| Level 3 | Industry-leading | Facebook/Google/Netflix уровень; сотни одновременных тестов |

**> 70% команд** застревают на Level 1-2 — проблема процесса, не технологии [2].

**Duolingo benchmark**: сотни одновременных тестов → D1 retention 13% → 55% (+4.2×) [2].

### Шестишаговый цикл эксперимента [2]

```
1. IDEATION       → данные + qualitative insights + brainstorm
2. PRIORITIZE     → RRF Framework: Reach × Relevance × Frequency
3. SETUP & RUN    → одна переменная, equal traffic split, min 7 дней
4. ANALYZE        → leading metrics + core metrics
5. DECIDE         → Scale / Iterate (max 2-3×) / Kill
6. CONSOLIDATE    → задокументировать learning; обновить knowledge base
```

### Статистические требования

| Параметр | Значение |
|---|---|
| Минимальная длительность | 7 дней (усреднить day-of-week эффекты) |
| Рекомендуемая длительность | 14-28 дней |
| Confidence level | 95% (для значимых изменений) / 90% (низкорисковые) |
| Traffic split | 50/50 или 33/33/33 — равное распределение |
| Sample size пример | 10% lift от 2% CVR → ~90,000 users per variant |
| Max итераций при inconclusive | 2-3 раза, затем abandon hypothesis |

### Приоритизация гипотез — RRF Framework

```
Priority Score = Reach × Relevance × Frequency

Reach      = сколько пользователей затронет изменение
Relevance  = насколько изменение связано с core conversion moment
Frequency  = как часто пользователи сталкиваются с элементом
```

### ROI Calculation

**ASO ROI (базовая)**:
```
ROI = (Incremental Organic Installs × LTV − ASO Cost) / ASO Cost × 100%
```

**Blended ROI (с учётом halo)**:
```
Blended CPI = Total Ad Spend / (Paid Installs + Organic Halo Installs)
```

**CVR impact на paid efficiency**:
```
Если CVR растёт на 3-5% → те же деньги на ASA дают больше installs
→ Effective CPI падает без увеличения бюджета
```

---

## Scaling Framework

### Scaling ASO — Три оси

| Ось | Как масштабировать |
|---|---|
| Keyword coverage | Добавлять локали (cross-localization × 9 языков в US) |
| Test velocity | Переход Level 1 → Level 2 → Level 3; 10+ тестов/месяц |
| Geographic expansion | Install velocity by locale → приоритизировать рынки с высоким momentum |

### Cadence — Итерационный ритм

| Элемент | Частота |
|---|---|
| Keyword tracking (позиции) | Ежедневно |
| CVR monitoring | Еженедельно |
| Competitor metadata мониторинг | Раз в 2 недели |
| A/B тест запуск / анализ | Каждые 2-4 недели |
| Metadata обновление | Каждые 4-6 недель (при наличии данных) |
| Incrementality review | После каждого значимого события (campaign on/off, featuring) |
| Quarterly benchmark | Раз в квартал vs. category benchmarks |

---

## Evolution / Trends

| Период | Изменение |
|---|---|
| До 2021 | Атрибуция = last-click MMP; organic multiplier не измерялся системно |
| 2021 | iOS 14.5 ATT → paid attribution стал менее точным; organic важность растёт |
| 2022-2023 | Incrementality analysis входит в mainstream ASO tooling (AppTweak, AppsFlyer) |
| 2024-2025 | Privacy изменения + рост CPI → органический рост = must-have, не nice-to-have |
| 2025 | NeuralProphet-based incrementality становится стандартом измерения [1] |
| 2025 | Academic confirmation: paid → organic halo +7.5% эффективности [6] |
| 2025-2026 | AXO (App Experience Optimization) = ASO расширяется за пределы store page на post-install journey |

---

## Open Questions & Gaps

- **Точная формула organic multiplier по категориям**: AppsFlyer публикует агрегаты, но category-specific benchmarks закрыты
- **NeuralProphet accuracy**: модель требует 3 лет данных — у новых приложений нет этой истории
- **Halo effect by keyword type**: branded vs. generic keywords, вероятно, дают разный uplift — не исследовано
- **AXO метрики**: пост-инсталл journey как ASO сигнал — методология измерения формируется
- **Cross-platform attribution**: Facebook impressions → Google clicks (2.37 per 1000 impressions) [6] — multi-touch dynamics добавляют неизвестность

---

## Sources

1. AppTweak — "Incrementality Analysis: Measure the true impact of ASO and paid UA" — apptweak.com/en/aso-blog/incrementality-analysis (2025)
2. Phiture — "The A/B Testing Framework: How to Level Up Your A/B Experimentation" — phiture.com/mobilegrowthstack (2025)
3. AppsFlyer — "The organic uplift in app marketing: Separating fact from fiction" — appsflyer.com/blog (2025)
4. Altis — "10 Metrics Every ASO Expert Must Track in 2026" — tryaltis.com/essential-aso-metrics-to-track-2026/ (2026)
5. Moburst — "Measuring Cannibalization in ASO: The Full Guide" — moburst.com/blog/what-is-cannibalization-in-aso/ (2025)
6. arXiv — "Complementarity Between Paid and Organic Installs in Mobile App Advertising" — arxiv.org/html/2504.16151v1 (2025)

---

## ASA Impression Share Analysis

Impression Share — процент eligible impressions, которые получило приложение из всех доступных показов по данному поисковому запросу. Это **единственная метрика**, которая показывает насколько мы "заполнили" возможный paid охват по ключу.

### Как получить

Async API через `custom-reports` (не стандартный keyword report):

```python
# 1. Создать отчёт (возвращает ID)
result = api.impression_share_reports(
    start_date="2026-03-26", end_date="2026-04-07",
    granularity="DAILY",
    name="imp_share_YYYYMMDD",
    conditions=[{"field": "countryOrRegion", "operator": "IN", "values": ["DE","AT","CH"]}]
)
report_id = result["id"]  # например 64377355

# 2. Дождаться завершения (обычно ~30-60 сек)
res = api.get_single_impression_share_report(report_id)
# state: QUEUED → RUNNING → COMPLETED

# 3. Скачать CSV по downloadUri
import urllib.request
urllib.request.urlretrieve(res["data"]["downloadUri"], "imp_share.csv")
```

Поля CSV: `date, appName, adamId, countryOrRegion, searchTerm, lowImpressionShare, highImpressionShare, rank, searchPopularity`

### Интерпретация

| Impression Share | Rank | Действие |
|---|---|---|
| 85–100% | ONE | Bid raise бесполезен — потолок охвата достигнут. Фокус на CR (скриншоты, конверсия). |
| 60–85% | ONE | Есть 15–40% упущенных показов. Raise bid на 10–20% для тестирования. |
| 40–60% | ONE–TWO | Значительный upside. Raise bid агрессивнее. |
| < 40% | TWO+ | Bid сильно ниже clearing price. Либо поднять bid, либо паузировать если CPA не окупается. |
| Любой | TWO+ | Конкурент занимает rank ONE — нужно выяснить их bid диапазон и переиграть. |

### Связь с bid оптимизацией

**Главный инсайт**: высокий CPA при высоком impression share (85%+) = проблема **конверсии**, не ставки. Поднятие bid не поможет — охват уже максимален.

- Если share низкий → поднять bid → захватить больше показов → больше installs при том же CR
- Если share высокий и CR низкий → A/B тест скриншотов / иконки → без изменения bid
- Если share высокий и CR высокий → keyword уже оптимизирован, масштабировать через новые ключи

### ⚠️ searchPopularity в этом отчёте ненадёжен

Поле `searchPopularity` в impression share CSV **не передаёт параметр страны** в запросе к бэкенду Apple. Возвращает глобальные данные независимо от conditions. Для non-US рынков (DE, AT, CH) — не использовать. Источник: наблюдение на практике (2026-04).

Вместо этого использовать hints/autocomplete API для оценки объёма запросов в конкретном сторфронте.

### Cadence

- Раз в 2 недели или после значительного изменения ставок
- Обязательно после повышения/понижения бюджета
- Хранить CSV в `./asa-monitoring/data/reports/` для trend analysis

---

## Reuse Hooks

- **При оценке ASA эффективности**: использовать Blended CPI (paid + organic halo), не только attributed CPI; halo ~ +7.5% [6]
- **Cannibalization check**: запустить 7-step calculation при каждом старте новой ASA кампании на brand ключах
- **A/B тест требования**: min 7 дней, 95% confidence, 50/50 split, одна переменная
- **Тест velocity цель**: 10+ тестов в месяц = 2.1× рост; переход Level 1→2 — процесс, не инструмент
- **Incrementality**: после каждого metadata update — запустить extrapolation model (нужно 3 года данных)
- **SOV > single #1 ranking**: доля голоса в keyword set = более устойчивая метрика роста
- **Organic multiplier flat**: при росте paid spend и flat органике → ASO не работает → аудит metadata/creatives

---

_Update log: 2026-03-06 — initial version, sources: AppTweak (2025), Phiture (2025), AppsFlyer (2025), Altis (2026), Moburst (2025), arXiv (2025)_
