# ASO Social Factors — Ratings, Reviews, Engagement Signals, Competitive Intelligence

## Summary

Социальные факторы ASO — трёхуровневая система: (1) ratings/reviews как прямые ranking inputs и конверсионные сигналы; (2) engagement signals (retention, session depth, uninstall rate) как поведенческие подтверждения качества; (3) competitive intelligence как непрерывный мониторинг рынка для нахождения gaps. В 2025-2026 Apple добавил AI-generated review summaries (WWDC25), Google интегрировал Gemini для отображения поведенческих метрик прямо на странице приложения.

---

## Key Principles

- **Рейтинг ниже 3.5 звезды → резкое снижение видимости** в поиске App Store [1, 2]
- **68% пользователей** используют только приложения с рейтингом 4+ [5]
- **4.5+ звезды = 3× больше установок** по сравнению с более низкими рейтингами [foundations]
- **Review recency важнее total count**: свежие отзывы ранжируются выше алгоритмом [1]
- **Review velocity** (скорость поступления новых отзывов) — отдельный сигнал алгоритма [1, 2]
- **Ответ на отзыв → пользователь часто обновляет оценку**: многие 1-star превращаются в 4-5 star после ответа [3]
- **AI review summaries (Apple, WWDC25)**: 100-300 символов, генерируются автоматически, появляются до индивидуальных отзывов — качество отзывов теперь влияет на первое впечатление [3, 4]
- **Uninstall rate = штрафной сигнал**: Google Gemini (2025) отображает метрики удержания прямо на странице; Apple учитывает uninstall в ранжировании [4, 6]
- **D7 и D30 retention** — подтверждённые algorithmic preference signals в 2026 [6]
- **Конкурентный анализ**: весь metadata конкурентов публичен; keyword gaps находятся через сравнение что они индексируют vs. ты [7]

---

## Data / Models

### Rating — Impact Data

| Рейтинг | Эффект |
|---|---|
| < 3.5 ★ | Резкое снижение видимости в поиске [1, 2] |
| 3.5–4.0 ★ | Нейтральная зона; не пессимизируется |
| 4.0+ ★ | Substantially higher CVR; baseline для featuring |
| 4.5+ ★ | 3× больше установок vs. ниже 4.5 [foundations] |
| 4.0+ ★ | 68% пользователей не рассмотрят ниже [5] |

**Revenue impact**: +1 звезда в среднем рейтинге → +5-9% revenue [5]
**Conversion impact**: 5+ отзывов → +270% CVR vs. 0 отзывов [5]

### Review Lifecycle Framework

```
[Trigger] Пользователь завершил positive action в приложении
       ↓
[Prompt] SKAdNetwork / StoreKit API — нативный Apple prompt
       ↓
[Review submitted] — попадает на страницу
       ↓
[Algorithm] Учитывает: sentiment, recency, velocity
       ↓
[AI Summary] Apple генерирует 100-300 char summary из паттернов [3]
       ↓
[Developer Response] — влияет на пользователя и сигнализирует алгоритму
       ↓
[Rating Update] — пользователь обновляет оценку после ответа
```

### Engagement Signals — Иерархия (2026)

| Сигнал | Тип | Вес | Источник |
|---|---|---|---|
| D7 retention | Behavioral | Высокий | [6] |
| D30 retention | Behavioral | Высокий | [6] |
| Session length | Behavioral | Средний | [6] |
| Feature adoption depth | Behavioral | Средний | [6] |
| Uninstall rate | Behavioral (штраф) | Высокий | [4, 6] |
| Crash rate | Quality (штраф) | Высокий | [foundations] |
| Review velocity | Social | Средний | [1, 2] |
| Review sentiment | Social | Средний | [1, 2] |
| Rating avg | Social | Высокий | [1, 2] |
| Response rate | Social | Косвенный | [3, 4] |

### Review Response — Framework по типу [3, 4]

| Тип отзыва | Приоритет | Timing | Тактика |
|---|---|---|---|
| Featured (visible on listing) | Критический | < 24h | Персонализированный, конкретный |
| Негативный (1-2 звезды) | Высокий | < 48h | Эмпатия → конкретные шаги → follow-up |
| Баг-репорт | Высокий | < 48h | Acknowledge → fix ETA → закрыть тикет |
| Нейтральный (3 звезды) | Средний | < 1 неделя | Уточнить боль → показать roadmap |
| Позитивный (4-5 звезды) | Низкий | < 1 неделя | Краткая благодарность, без шаблона |
| Неадресуемый ("app disgusting") | Не отвечать / минимально | — | Нет actionable insight |

**Response rate benchmarks** [5]:
- 89% пользователей с большей вероятностью выберут приложение, которое отвечает на все отзывы
- 72% ожидают ответа на негативный отзыв в течение 48 часов
- 81% считают, что ответ должен поступить в течение 1 недели

### Review Prompting — Когда просить [1, 3]

| Момент | Эффективность |
|---|---|
| После завершения positive user action | Высокая |
| После достижения milestone (уровень, цель) | Высокая |
| После успешного решения проблемы через support | Высокая |
| При первом запуске / onboarding | Низкая (нет опыта) |
| После crash / ошибки | Отрицательная |
| Повторный prompt слишком часто | Отрицательная → Apple ограничивает до 3 раз в год |

**Apple limit**: SKStoreReviewAPI позволяет показывать prompt максимум **3 раза в 365 дней** на устройство.

---

## Competitive Intelligence Framework

### 10-Step ASO Competitive Research [7]

| Шаг | Что анализируем | Приоритет |
|---|---|---|
| 1 | Category landscape — топ-чарты, market size, ключевые игроки | Критический |
| 2 | Competitor classification — direct / indirect / keyword competitors | Критический |
| 3 | Keyword gap — какие keywords конкурент индексирует, а ты нет | Критический |
| 4 | Textual metadata — title, subtitle, description конкурентов | Критический |
| 5 | Creative assets — icon, screenshots, video | Высокий |
| 6 | Ratings & reviews — sentiment, velocity, pain points | Высокий |
| 7 | Update history — частота обновлений, feature releases | Средний |
| 8 | In-App Events — promotional strategy, seasonality | Средний |
| 9 | Custom Product Pages — targeted messaging variations | Средний |
| 10 | Localization strategy — какие рынки покрыты | Средний |

### Competitor Classification

```
Direct competitors    — тот же use case, та же аудитория
Indirect competitors  — смежный use case, пересекающаяся аудитория
Keyword competitors   — ранжируются по твоим target keywords, но другой продукт
```

### Keyword Gap Analysis — Процесс

```
[Шаг 1] Собрать keywords конкурентов (title + subtitle + keyword field + ranked keywords из tools)
[Шаг 2] Сравнить с твоими indexed keywords
[Шаг 3] Gap = конкурент ранжируется → ты не индексируешь
[Шаг 4] Оценить gap-ключи по Volume × Relevance × Difficulty
[Шаг 5] Добавить высокоприоритетные в keyword field / subtitle
```

### Metadata Comparison Table (шаблон)

| Поле | Твоё приложение | Конкурент A | Конкурент B |
|---|---|---|---|
| Title (30) | … | … | … |
| Subtitle (30) | … | … | … |
| Keyword field (100) | … | … | … |
| Positioning angle | … | … | … |
| Description hook (167 chars) | … | … | … |
| IAP names | … | … | … |
| Locales | … | … | … |

### Monitoring Cadence

| Элемент | Частота |
|---|---|
| Keyword rankings (свои + конкуренты) | Еженедельно |
| Metadata конкурентов (title/subtitle) | Раз в 2 недели |
| Ratings / review velocity | Еженедельно |
| Creative updates конкурентов | Раз в месяц |
| Keyword field конкурентов | Раз в месяц |
| Category benchmarks | Ежеквартально |

---

## Evolution / Trends

| Период | Изменение |
|---|---|
| До 2020 | Рейтинг и кол-во отзывов — основные social сигналы |
| 2021-2022 | Retention и engagement signals подтверждены как ranking факторы (iOS 15) |
| 2023-2024 | Review sentiment analysis в ASO tools (AppTweak, AppFollow) |
| 2025 WWDC | **Apple AI-generated review summaries** (100-300 chars) появляются на product page [3] |
| 2025 | **Google Gemini**: отображает behavioral metrics (uninstall rate, retention) на Google Play listing [4] |
| 2025-2026 | D7/D30 retention — подтверждены как primary algorithmic preference signals [6] |
| 2026 | Review response rate становится конверсионным сигналом; featuring требует strong review profile |

---

## Open Questions & Gaps

- **Вес review velocity vs. total count**: алгоритм явно предпочитает свежие — точное соотношение неизвестно
- **AI summary алгоритм Apple**: какие отзывы входят в summary, как часто обновляется, можно ли влиять — не раскрыто
- **Google Gemini uninstall display**: с какого порога uninstall rate отображается на странице — threshold неизвестен
- **Review response → ranking**: корреляция подтверждена качественно (больше updates rating), прямой механизм влияния на ранг не задокументирован Apple официально
- **Fake review penalties**: Apple заявляет о борьбе с накрутками — алгоритм детекции и severity штрафа непрозрачны

---

## Sources

1. AppTweak — "The ultimate 2026 guide to app store reviews" — apptweak.com/en/aso-blog/app-store-reviews (2026)
2. MobileAction — "App Store ranking factors: How to boost app visibility in 2026" — mobileaction.co/blog/app-store-ranking-factors/ (2026)
3. MobileAction — "How to respond to app store reviews the right way in 2026" — mobileaction.co/guide/how-to-respond-to-app-store-reviews/ (2026)
4. AppFollow — "Advanced ASO Strategies for 2026: Webinar recap" — appfollow.io/blog/webinar-recap-advanced-aso-strategies-for-2026 (2026)
5. 1440.io — "The State of Customer Reviews in 2026" — 1440.io/blog/the-state-of-customer-reviews-in-2026/ (2026)
6. DotCom Infoway — "ASO in 2026: New Ranking Factors You Can't Ignore" — dotcominfoway.com/blog/aso-in-2026 (2026)
7. SplitMetrics — "ASO Competitive Research & Analysis: a Step-by-Step Guide" — splitmetrics.com/blog/aso-competitive-research-analysis (2025)

---

## Reuse Hooks

- **Rating triage**: avg rating < 3.7 → приоритет review prompting перед расширением keyword coverage
- **Review prompt timing**: после positive action, не при onboarding; не чаще 3 раз в год (Apple limit)
- **Response SLA**: негативные отзывы — ответ в течение 48h; отвечать на featured reviews в первую очередь
- **Engagement > installs**: высокий uninstall rate или низкий D7 retention → понижение позиций; исправить продукт до масштабирования UA
- **Competitive keyword gap**: Title+Subtitle конкурента — публичны; reverse-engineer → заполнить gaps в keyword field
- **AI summary (Apple, 2025)**: следить за тем, что попадает в AI summary — это первое что видит пользователь перед отзывами
- **Automation**: до 80% ответов на отзывы можно автоматизировать через tagging + templates; сложные — вручную

---

_Update log: 2026-03-06 — initial version, sources: AppTweak (2026), MobileAction (2026), AppFollow (2026), 1440.io (2026), DotCom Infoway (2026), SplitMetrics (2025)_
