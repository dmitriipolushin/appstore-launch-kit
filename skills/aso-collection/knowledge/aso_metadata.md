# ASO Metadata — Components, Optimization, Localization

## Summary

Метаданные — текстовый слой ASO, определяющий индексацию (попадёт ли приложение в поисковую выдачу по запросу). Для iOS App Store это иерархия полей с убывающим весом: Title → Subtitle → Keyword Field → What's New → In-App Events / Screenshot Captions (с 2025). Description напрямую не индексируется поиском, но критична для конверсии. Ключевой принцип: каждое слово встречается только в одном поле — дублирование не усиливает позицию, а тратит бюджет символов.

---

## Key Principles

- **iTunes Lookup API НЕ возвращает subtitle**: поле `subtitle` в ответе iTunes API всегда отсутствует или равно `null`. Для получения subtitle конкурентов использовать **AppStoreSpy API** (`/v1/ios/apps/{id}` → поле `short`). Это касается как собственного приложения, так и анализа конкурентов.
- **Иерархия весов**: Title > Subtitle > Keyword Field. Слово из title не нужно повторять в keyword field — Apple индексирует его единожды [1, 3]
- **Дублирование = расточительство**: повторение ключей между полями не даёт дополнительного веса и сокращает охват [2]
- **First 167 chars в description** — всё что пользователь видит до "Read More"; это главное конверсионное окно [4]
- **Description не индексируется поиском на iOS** (в отличие от Google Play, где full description индексируется) [1, 2]
- **Promotional Text — единственное поле без ребилда**: можно обновлять без нового релиза, но не индексируется [2]
- **What's New индексируется**: обновляется с каждым релизом; сигнал активной разработки [4]
- **Последнее слово в 30-char subtitle может не индексироваться**: некоторые девелоперы сообщают об этом баге — размещать критические ключи ближе к началу [3]
- **Локализация ≠ перевод**: каждый рынок требует отдельного keyword research на локальном языке — прямой перевод даёт неверные ключи [5, 6]

---

## Data / Models

### Metadata Fields — iOS App Store (полная карта)

| Поле | Лимит | Индексируется | Видно пользователю | Обновление |
|---|---|---|---|---|
| App Name (Title) | 30 chars | Да (макс. вес) | Да — в поиске и на странице | С новым билдом |
| Subtitle | 30 chars | Да (высокий вес) | Да — под названием | С новым билдом |
| Keyword Field | 100 chars | Да (средний вес) | Нет | С новым билдом |
| Description | 4000 chars | Нет (iOS) | Да — первые 167 chars без клика | С новым билдом |
| Promotional Text | 170 chars | Нет | Да — над описанием | Без билда (в любой момент) |
| What's New | ~4000 chars | Да | Да — в секции "Updates" | С новым билдом |
| In-App Event title | 30 chars | Да (с 2022) | Да — карточка события | Через ASC |
| In-App Event short desc | 45 chars | Да | Да | Через ASC |
| Screenshot Captions | — | Да (с июня 2025) | Да — под скриншотами | С новым билдом |
| Developer Name | — | Да (средний вес) | Да | Через ASC |

### Title — оптимизационные правила

```
[Brand Name] — [Primary Keyword]  (рекомендуемая структура)
```

| Правило | Обоснование |
|---|---|
| Размещать primary keyword в title | Максимальный вес в алгоритме |
| Бренд + ключевое слово | Сохраняет узнаваемость + индексацию |
| Без стоп-слов (the/and/your/with) | Топ-приложения: <3.2% стоп-слов; ranked 150-250 — в 4× чаще используют [7] |
| Без "App" в названии | Только 1.1% топ-приложений используют "app" в title [7] |
| Без "Free" как standalone | 0.6% приложений; воспринимается как spam [7] |
| Читаемость для пользователя | Keyword stuffing снижает CVR даже при индексации |

### Subtitle — оптимизационные правила

- 30 символов — каждый символ важен; неиспользованное пространство = упущенная возможность [3]
- Цель: value proposition + secondary keywords в читаемой форме
- **Хорошо**: "transcribe voice to text quick" — индексирует несколько фраз, читается как tagline [3]
- **Плохо**: "books audiobook narrate reader" — keyword stuffing, вредит CVR [3]
- Ключевые слова размещать ближе к началу (последнее слово в 30-char subtitle может не индексироваться) [3]

### Keyword Field — правила заполнения

| Правило | Деталь |
|---|---|
| Разделитель — запятая, не пробел | "health,tracker" — правильно; "health tracker" — тоже работает (Apple split по пробелу) |
| Не дублировать title/subtitle/developer name | Уже проиндексированы |
| Без пробелов вокруг запятых | Экономия символов |
| Без кавычек и спец. символов | Не индексируются |
| Использовать цифры вместо слов | "7" вместо "seven" — короче |
| Не использовать "best", "top", "free" | Apple фильтрует superlatives |
| Алфавит не важен | Порядок слов не влияет на вес |
| Long-tail термины | Незанятые ниши с достижимым рангом |

### Description — структура (conversion-focused)

```
[1] Hook — первые 167 chars (до "Read More")
    → Чёткое УТП: что делает приложение + главная выгода
    → Самый высокий конверсионный вес

[2] Features — bullet points с action-глаголами
    → Track, Learn, Scan, Watch — не существительные
    → 3-5 ключевых функций

[3] Social proof
    → Рейтинги, награды, упоминания в прессе, кол-во пользователей

[4] Call-to-action
    → "Download now" / "Try free for 7 days"
```

**iOS vs. Google Play**:

| Аспект | iOS App Store | Google Play |
|---|---|---|
| Индексация description | Нет | Да (full description) |
| Оптимизация | Только конверсия | Конверсия + ключи (density 2-3%) |
| Short description | Нет поля | 80 chars, индексируется |
| Promotional Text | 170 chars (без ребилда) | Нет аналога |

---

## Localization Framework

### Cross-Localization — расширение keyword real estate

Ключевой инсайт: Apple индексирует metadata из **нескольких языковых локалей** в одном сторефронте [5].

**US App Store индексирует 10 языков** (подтверждено экспериментально MobileAction, AppTweak, aso.dev; официально Apple не документирует):

| Язык | Locale code | Доп. символов |
|---|---|---|
| English (US) | en-US | базовый |
| Spanish (Mexico) | es-MX | +160 chars (30+30+100) |
| Arabic | ar | +160 chars |
| Chinese Simplified | zh-Hans | +160 chars |
| Chinese Traditional | zh-Hant | +160 chars |
| French | fr-FR | +160 chars |
| Korean | ko | +160 chars |
| Portuguese (Brazil) | pt-BR | +160 chars |
| Russian | ru | +160 chars |
| Vietnamese | vi | +160 chars |

**Стратегия для US-focused приложений**: заполнять все вторичные локали английскими ключами (не переводом). Подтверждено кейсом Amma Pregnancy Tracker (AppFollow): +49% US visibility, +1221 индексированных запросов за 1 месяц при заполнении ar и zh-Hans английскими словами. Apple индексирует текст как есть, не проверяя соответствие языка локали.

**Ограничение**: ключевые фразы должны быть целиком внутри одной локали. Слова из en-US и es-MX не комбинируются в одну фразу [5].

**Практика**: заполнить es-MX другими ключами (не переводом en-US) — увеличивает общий keyword coverage без изменения основного listing.

**RU App Store индексирует 3 локали** (не US-набор из 9!):

| Язык | Locale code | Стратегия заполнения |
|---|---|---|
| Russian | ru | Основные RU-термины (primary) |
| Ukrainian | uk | Дополнительные RU-термины — Кириллица общая, русские слова покрываются |
| English (GB) | en-GB | English-термины (⚠️ en-US **не** индексируется в RU-сторе!) |

**⚠️ Частая ошибка**: заполнять en-US локаль для RU рынка — она не индексируется в RU App Store. Использовать en-GB.

**Стратегия uk-локали для RU**: заполнять русскоязычными терминами, которых нет в ru-локали. Кириллица одинаковая, Apple индексирует русские запросы из uk metadata в RU сторефронте. Не переводить на украинский язык — это потеря keyword budget.

### Translation vs. Transcreation

| Подход | Что делает | Когда применять |
|---|---|---|
| Translation | Прямой перевод metadata | Никогда для keyword field |
| Localization | Адаптация текста под культуру | Description, screenshots |
| Transcreation | Полное переосмысление под рынок | Новый рынок с другим поведением |
| Keyword re-research | Отдельный keyword research на локальном языке | Всегда для title/subtitle/keyword field |

**Принцип**: пользователи в разных странах ищут разными словами даже для одного и того же приложения. Прямой перевод English keywords в Spanish даёт нерелевантные запросы [6].

### Рынки с культурными ограничениями [6]

| Рынок | Особенности |
|---|---|
| Китай | Online Game Ethics Committee; строгие требования к контенту и naming |
| Арабские страны | Нет алкоголя/азартных игр в visuals; скромный контент |
| Германия | Строгая регуляция насилия |
| Япония | 4 системы письма (English/Kanji/Hiragana/Katakana); грамматические частицы критичны для natural indexing |

### Задокументированный impact локализации [6]

| Кейс | Результат |
|---|---|
| Robocar Poli → Франция | Рост загрузок после локализации |
| Kid-E-Cats → Вьетнам | Третье место в чарте |
| Kid-E-Cats → Испаноязычные рынки | Органический рост |
| Скандинавские рынки (subscription) | +13-38% конверсии после native speaker review |
| Indonesia (Robocar Poli) | #1 Android market после локализации |

---

## Evolution / Trends

| Период | Изменение |
|---|---|
| До 2017 | Title — 50 chars |
| 2017 (iOS 11) | Title сокращён до 30 chars; добавлен Subtitle 30 chars; редизайн App Store |
| 2018 | Keyword field — подтверждено отсутствие веса у description для поиска iOS |
| 2022 | In-App Events title/subtitle индексируются (30 + 45 chars доп. real estate) |
| Июнь 2025 | Screenshot captions активно индексируются [4] |
| 2025-2026 | NLP-сдвиг: "цель — матчить intent, а не слова"; keyword stuffing наказывается сильнее [4] |

---

## Open Questions & Gaps

- **What's New индексация**: подтверждена некоторыми источниками [4], но не официально Apple; глубина — unknown
- **Последнее слово subtitle не индексируется**: наблюдение сообщества, не подтверждено Apple официально [3]
- **Description iOS**: большинство источников говорят "не индексируется"; Apple documentation оставляет формулировку размытой ("well-written description can improve discoverability")
- **AI-generated review summaries**: влияние на конверсию растёт [4], но механизм неизвестен
- **Promotional Text**: не индексируется — подтверждено; можно ли использовать для сезонного A/B теста без ребилда — практически да, но данных по impact мало

---

## Sources

1. ASOMobile — "How to optimize app metadata for the App Store" — asomobile.net/en/blog/how-to-optimize-your-app-metadata-for-the-app-store/ (2025)
2. Adalo — "Complete Guide to iOS App Store ASO in 2026" — adalo.com/posts/complete-guide-ios-app-store-aso-2026 (2026)
3. Gummicube — "App Store Subtitle Character Limit: Saying a Lot in a Few Words" — gummicube.com/blog/app-store-subtitle-character-limit (2025)
4. Adalo — "Complete Guide to iOS App Store ASO in 2026" — adalo.com (2026)
5. ASO.dev — "App Store Cross-Localization Guide: Double Your Keywords" — aso.dev/metadata/cross-localization/ (2025)
6. ASODesk — "ASO and App Localization: The Essential Strategy to Grow User Base" — asodesk.com/blog (2025)
7. ConsultMyApp — "App Store Keywords: Full Data & Analysis of 7,500 Apps" — consultmyapp.com/blog (Nov 2025)

---

## Reuse Hooks

- **Аудит метаданных**: проверить дублирование слов между title/subtitle/keyword field → удалить дубли, заменить новыми ключами
- **Character budget**: `title(30) + subtitle(30) + keyword_field(100)` = 160 chars основного бюджета. Cross-localization: ×9 языков в US store = до 1440 chars потенциально
- **Description hook**: первые 167 символов — приоритет конверсионного копирайтинга; остальное второстепенно
- **Promotional Text** для сезонных акций: обновлять без ребилда, но не рассчитывать на индексацию
- **Локализация keyword field**: всегда делать отдельный keyword research на языке рынка, не переводить с английского
- **Japan/China**: требуют специального внимания к writing system и cultural restrictions перед запуском

---

_Update log: 2026-03-06 — initial version, sources: ASOMobile (2025), Adalo (2026), Gummicube (2025), ASO.dev (2025), ASODesk (2025), ConsultMyApp (Nov 2025)_
