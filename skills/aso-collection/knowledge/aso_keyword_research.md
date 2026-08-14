# ASO Keyword Research — Methods, Models, Semantics

## Summary

Keyword research для ASO — процесс нахождения поисковых запросов пользователей, их оценки по трём осям (volume × relevance × competition) и формирования портфеля ключей, которые максимизируют индексированный трафик при реально достижимых позициях. В 2025-2026 ключевой сдвиг: Apple Search переходит от exact match к семантическому ранжированию через NLP — кластеризация по intent стала обязательной частью методологии.

---

## Key Principles

- **70% открытий приложений происходят через поиск в сторе** [6]; keyword research — приоритет №1 в ASO
- **Три оси оценки**: Volume (Search Popularity) × Relevance × Competition. Один показатель без двух других бесполезен
- **Character budget**: keyword field iOS — 100 chars. Слова из title/subtitle не дублировать — они уже проиндексированы
- **Long-tail priority для новых приложений**: head-terms заняты топами с мощными поведенческими сигналами; long-tail — реально достижимые позиции
- **Семантика vs. exact match**: с 2025 Apple NLP матчит intent и тему, а не только строгое совпадение символов. Кластеры по теме важнее охвата отдельных слов [1]
- **Intent ≠ Semantic cluster**: одна тема (music) содержит несколько intent (streaming, offline playback, discovery). Оптимизировать нужно под оба уровня [1]
- **Reviews как источник**: пользователи в отзывах используют естественный язык поиска — лучший источник "непромпченной" семантики [1, 2]
- **Top-10 vs. 11-20**: топ-10 по ключевому слову даёт на 155% больше загрузок, чем позиции 11-20 [6]
- **Органические пользователи vs. платные**: retention органики в 3× выше чем платного трафика [6]

---

## Data / Models

### Scoring Framework (Composite)

```
Priority Score = Relevance × Volume × (1/Competition) × Conversion Potential
```

Каждый фактор нормируется к шкале 1-10, затем перемножается. AI-версия от Phiture [4] — адаптивная: веса пересчитываются динамически под контекст приложения.

| Фактор | Шкала | Источник данных | Вес (типовой) |
|---|---|---|---|
| Relevance | 0-100 (AppTweak Atlas AI) / 1-10 (ручная) | Семантический анализ + live SERP | Высокий |
| Volume (Search Popularity) | 5-100 (Apple) | **Hints/autocomplete API** (см. ниже) | Высокий |
| Competition / Difficulty | 1-100 | Top-10 apps authority + installs | Средний |
| Chance Score | % | Сила своего приложения vs. конкурентов | Средний |
| Ranking Position | 1-250+ | Tracking tools | Для quick-wins |
| Conversion Potential | 1-10 | Исторические данные install rate | Средний |

### ⚠️ searchPopularity в ASA API сломан (2026)

**Проблема:** Метрика `searchPopularity` в Apple Search Ads API (включая Impression Share отчёты) **не передаёт параметр страны** в запросе к бэкенду Apple. В результате все значения возвращаются как глобальные / US-биased, независимо от того, какой storefront запрашивается. Для не-US рынков (DE, AT, CH, GB и др.) данные **недостоверны**.

**Симптом:** В impression share отчёте поле `searchPopularity` показывает значение `2` или `3` для практически всех ключей — слишком однородно, чтобы быть корректным country-level сигналом.

**Два разных инструмента — два разных сигнала:**

**1. Apple Search Hints / autocomplete (`keyword_suggest.py`)** — гео-точный, без авторизации:
```bash
# Реальное автодополнение App Store в конкретном сторфронте
python3 ~/.claude/skills/aso-collection/scripts/keyword_suggest.py \
  --term "lebensmit" --country de
```
Показывает что реально набирают пользователи в данной стране. Tier (HIGH/MEDIUM/LOW) = относительная частота в данном сторфронте. **Это основной гео-сигнал.**

**2. ASA Popularity (`keyword_popularity.py`, `/cm/api/v2/keywords/recommendation`)** — требует куки:
```bash
python3 keyword_popularity.py --seeds "lebensmittel scanner,halal check" --storefronts DE,AT,CH
```
⚠️ **Несмотря на параметр `--storefronts`, popularity score (0–100) является глобальной метрикой** — Apple считает объём по всем рынкам вместе. Следствия:
- Score 5 в DE не означает "нет объёма в Германии" — может быть нишевый немецкий термин с хорошим локальным спросом
- Score 30 не гарантирует объём в DE — весь объём может быть сосредоточен в US
- Использовать как дополнительный фильтр, но не как единственный критерий

**Сравнительная таблица инструментов:**

| Инструмент | Гео-точность | Абсолютный объём | Авторизация |
|---|---|---|---|
| Apple Search Hints (`keyword_suggest.py`) | ✓ Высокая (по сторфронту) | ✗ Нет (только порядок) | Не нужна |
| ASA Popularity (`keyword_popularity.py`) | ⚠️ Глобальная (не гео) | ✓ Относительный (0–100) | Cookie ~24ч |
| Реальные impressions в кампании | ✓ Точная (по кампейн-гео) | ✓ Абсолютный | ASA кампания |

**Практическое правило:** Если ключ не появляется в App Store autocomplete при вводе первых 3-4 символов в нужном сторфронте — его органический объём < 5-10 запросов в день. ASA может показывать по нему impressions (paid inventory), но органический трафик будет нулевым.

**Единственный достоверный сигнал объёма для конкретного гео** — реальные impressions после запуска ключа в ASA кампании с правильным бидом.

### Keyword Difficulty — Компонентная модель

Difficulty score (1-100) — взвешенный композит [из поисковых данных, 2025]:

| Компонент | Вес |
|---|---|
| Rating volume топ-приложений | 30% |
| Доминирующие игроки (концентрация) | 20% |
| Review velocity | 10% |
| Rating quality | 10% |
| Market age | 10% |
| Publisher diversity | 10% |
| Title relevance топ-10 | 10% |

Метки: Very Easy → Easy → Medium → Hard → Very Hard → Extreme

### Keyword Tiers (по Volume × Achievability)

| Tier | Search Popularity | Стратегия |
|---|---|---|
| Head | 70-100 | Таргетировать через ASA + органика если сильные сигналы |
| Mid | 40-69 | Основная зона органики для зрелых приложений |
| Long-tail | 10-39 | Приоритет для новых приложений; заполнить keyword field |
| Niche | 1-9 | Добивка оставшегося char budget |
| Zero / No hints | 0 | Пропустить (если не бренд) |

### Метаданные — Иерархия весов

| Поле | Символов | Вес для индексации | Приоритет ключей |
|---|---|---|---|
| Title | 30 | Максимальный | 1-2 primary |
| Subtitle | 30 | Высокий | Доп. high-value + value prop |
| Keyword Field | 100 | Средний | Long-tail, без дублей с title/subtitle |
| In-App Event title | 30 | Средний (с 2022) | Intent-specific термины |
| Custom Product Page | — | Средний (органика с июля 2025) | Keyword-specific страницы |

### Semantic Clustering — Трёхуровневая структура [AppTweak, 2025]

```
SEMANTIC THEME (уровень темы)
    └── e.g. "music"
         ├── KEYWORD CLUSTER (уровень кластера)
         │    ├── "music streaming app"
         │    ├── "listen to music"
         │    └── "music player"
         └── USER INTENT (уровень мотивации)
              ├── Comparison shopping → "best music app"
              └── Specific constraint → "offline music player"
```

**Почему важно**: Apple NLP (обнаружена смена алгоритма 05.06.2025) ранжирует по соответствию теме и intent-паттернам, а не точным словам. Кластер "music streaming" покрывает все варианты фразы без явного перечисления каждой [1].

### Discovery Sources — Ранжирование по качеству сигнала

| Источник | Качество сигнала | Описание |
|---|---|---|
| **Apple Search Hints (autocomplete)** | **Критический** | **Основной источник реального объёма по стране.** Hints = реальные запросы пользователей в конкретном сторфронте. Если ключ есть в hints → есть органический спрос. |
| Apple Search Ads suggestions | Высокий | Данные самого Apple из ASA UI; более надёжны чем API searchPopularity |
| Competitor metadata (title/subtitle/keyword field) | Высокий | Что индексируют лидеры |
| Competitor paid keywords (ASA) | Высокий | За что конкуренты платят = высокий коммерческий intent |
| ASA Impression Share (search terms) | Высокий | Показывает реальные запросы, по которым мы показываемся + наш share; кандидаты для EXACT таргетинга |
| Already-ranked keywords (own app) | Средний | Quick-win: поднять позицию без смены метаданных |
| User reviews mining | Средний | Непромпченный язык пользователей → natural search terms |
| ASA searchPopularity API | ⚠️ Ненадёжен | **Сломан:** не передаёт параметр страны, возвращает глобальные/US данные. Не использовать для оценки объёма в non-US рынках. |
| Brainstorm (features/benefits/problems) | Низкий | Стартовая точка, всегда верифицировать через hints |

### Empirical Data — 7,500 App Store приложений (ConsultMyApp, Nov 2025) [5]

| Наблюдение | Данные |
|---|---|
| Stop-words в топ-приложениях | <3.2% filler words |
| Stop-words у приложений ranked 150-250 | В 4× чаще используют "the/and/your/with" |
| "App" в title топ-приложений | Только 1.1% |
| "Free" как standalone keyword | 0.6% всех приложений |
| Games: non-branded descriptors | <15% |
| Casino: keyword clustering (slots/jackpot/vegas/spin) | >50% заголовков/подзаголовков |
| Photo & Video: AI-термины | 22% |
| Health & Fitness: "track" | ~25% |
| Weather: "radar" | 28% |
| Travel: keyword diversity (ни один термин) | <9% |
| Games/Puzzle: dominant mechanic term | ~22% |

**Вывод**: Intent-глаголы (Learn, Track, Watch, Scan, Chat) работают лучше дескрипторов-существительных. Категория Travel — наибольшее разнообразие, Casino — наибольшая кластеризация.

---

## Research Process (Step-by-Step)

```mermaid
graph TD
    A[Подготовка: цели, аудитория, аудит метаданных] --> B[Discovery: сбор 1000-2000 кандидатов]
    B --> C[Scoring: Volume × Relevance × Competition]
    C --> D[Semantic Clustering: группировка по теме + intent]
    D --> E[Gap Analysis: что не покрыто текущими метаданными]
    E --> F[Prioritization: High/Mid/Low priority]
    F --> G[Placement: Title → Subtitle → Keyword field]
    G --> H[Monitoring: tracking каждые 3-4 недели]
    H --> B
```

---

## Evolution / Trends

| Период | Изменение |
|---|---|
| До 2017 | Exact match dominates; keyword stuffing работает |
| 2017-2019 | Apple внедряет базовый NLP; semantic matching начинается |
| 2021 | Custom Product Pages → keyword-level A/B тестирование |
| 2022 | In-App Events title/subtitle индексируются |
| 2024 | Semantic matching mature; plurals/singulars автоматически |
| 05.06.2025 | Подтверждённое изменение алгоритма: broader intent matching [1] |
| Июль 2025 | CPP в органике → keyword-specific страницы без paid [2] |
| 2025-2026 | AI-assisted keyword research (Phiture, AppTweak Atlas AI); адаптивные scoring models [4] |
| 2025 (Google Play) | Guided Search — refinement of broad queries toward specific intents [1] |

---

## Open Questions & Gaps

- **searchPopularity API сломан**: не передаёт страну → возвращает глобальные данные для всех рынков. Использовать только hints/autocomplete для оценки объёма по конкретному сторфронту (подтверждено на практике, 2026-04)
- **Search Popularity scale нелинейна**: Apple не публикует mapping score → volume. Score 70 vs 80 — разница неизвестна
- **Порядок слов в keyword field**: Industry consensus — не важен; Apple не подтвердил официально
- **Глубина semantic matching**: подтверждены plurals/singulars; multi-hop synonyms ("blood pressure" → "BP tracker") — threshold неизвестен
- **Cross-locale indexation**: объединяет ли Apple сигналы по ключам из разных локализаций одного приложения — unknown
- **Review text как источник индексации**: Apple намекает, но объём учитываемого контента не раскрыт
- **Decay rate**: как быстро падает позиция после удаления ключа из метаданных — нет надёжных данных

---

## Sources

1. AppTweak — "Adapt ASO to AI-driven app store search using semantic clusters" — apptweak.com/en/aso-blog/ai-reshaping-app-store-relevance (2025)
2. AppTweak — "App Store keyword research for ASO: The 2026 step-by-step guide" — apptweak.com/en/aso-blog/app-store-keyword-research-aso (2026)
3. MobileAction — "ASO keyword research in 2026: How to achieve better rankings" — mobileaction.co/blog/aso-keyword-research/ (2026)
4. Phiture — "Keyword Research with AI: Automating ASO with No-Code Tools" — phiture.com/asostack/automating-aso-keyword-research-with-ai/ (2025)
5. ConsultMyApp — "App Store Keywords: Full Data & Analysis of 7,500 Apps" — consultmyapp.com/blog (Nov 2025)
6. AppSamurai — "Strategic Keyword Research for Mastering ASO" — appsamurai.com/blog (Mar 2025)

---

## Reuse Hooks

- **Старт исследования**: Discovery → 1000-2000 кандидатов → scoring → кластеризация по теме → gap vs. текущие метаданные
- **Semantic clustering**: группировать по теме (что), потом по intent (почему) — не по форме ключа
- **Character budget audit**: `len(",".join(keywords)) ≤ 100`; удалить слова из title/subtitle; убрать stop-words
- **Achievability check**: difficulty score + смотреть кол-во reviews у топ-3 конкурентов. Новое приложение — таргетить там, где топ-3 имеет <10k reviews
- **Reviews mining**: искать повторяющиеся глаголы и проблемы → они = реальный поисковый язык пользователей
- **Intent-глаголы**: Track, Learn, Scan, Watch, Chat — работают лучше дескрипторов в metadata
- **Re-evaluation cadence**: каждые 3-4 недели или после изменений метаданных конкурентов

---

_Update log: 2026-03-06 — initial version, sources: AppTweak (2025-2026), MobileAction (2026), Phiture (2025), ConsultMyApp (Nov 2025), AppSamurai (Mar 2025)_
