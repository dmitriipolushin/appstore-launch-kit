# ASO Visual Assets — Icon, Screenshots, Preview Video: Psychology, A/B Logic, Compliance

## Summary

Визуальные ассеты — основной конверсионный слой ASO. Только 1% пользователей читает описание; решение об установке принимается за ~7 секунд на основе иконки и первых 2-3 скриншотов. Icon/screenshots/video не влияют напрямую на поисковую индексацию, но критически воздействуют на CVR (install rate), который сам является поведенческим сигналом ранжирования. A/B тестирование через PPO (Product Page Optimization) — официальный инструмент Apple с iOS 15. В 2025 добавлена поддержка Liquid Glass icons и расширена роль CPP в органике.

---

## Key Principles

- **7 секунд** — среднее время на странице приложения; только **13% пользователей** скроллят скриншоты [3]
- **1% читает описание** — визуальные ассеты = основной инструмент конверсии [3]
- **Первые 2 скриншота видны в поиске без клика** — они решают большинство installs [1]
- **90% не скроллят дальше третьего скриншота** — первые три экрана несут ~90% конверсионного веса [1]
- **Video: 8% досматривают до конца** — первые 7 секунд video = единственное что имеет значение [3]
- **CVR → ranking сигнал**: высокий install rate из поиска — подтверждённый фактор ранжирования [foundations]
- **PPO ≠ CPP**: PPO тестирует default страницу для всего трафика; CPP создаёт отдельные страницы для сегментов [4, 5]
- **Тестировать одну переменную за раз**: иначе невозможно атрибутировать lift [2, 4]

---

## Data / Models

### Impact по типу ассета

| Ассет | Конверсионный вес | Ranking влияние | Примечание |
|---|---|---|---|
| Icon | Высокий (first impression) | Косвенное через CVR | Виден в поиске, топ-чартах, рекомендациях |
| Screenshot 1-2 | Очень высокий | Косвенное через CVR | Видны в поиске без клика на страницу |
| Screenshot 3 | Высокий | Косвенное | ~90% не скроллят дальше |
| Screenshot 4-10 | Низкий | Минимальное | Для вовлечённых пользователей |
| Preview Video | Средний | Косвенное | 8% досматривают; первые 7с — критичны |
| Текст на скриншотах | Средний | Косвенное | Встроен в изображение; отдельного поля нет |

### Empirical Data — Конверсионный lift

| Изменение | Lift CVR | Источник |
|---|---|---|
| Добавление Preview Video + улучшение скриншотов | +10-30% | [1] |
| Успешный A/B тест (median) | +10-25% | [1] |
| Улучшение CVR на 3-5% (без доп. трафика) | Материальный рост органики | [foundations] |

### AppAgent A/B Testing Budget Allocation [3]

| Тип эксперимента | Доля от бюджета тестов |
|---|---|
| Major design changes (новые скриншоты, redesign иконки, новая концепция video) | 60% |
| Communication refinements (copy, headlines, branding prominence) | 20% |
| Layout experiments (порядок скриншотов, ориентация, позиционирование элементов) | 20% |

---

## Icon — Психология и требования

### Психология дизайна

- **Функция**: первая точка касания; отличительность в переполненном сторе
- Яркие, насыщенные цвета → быстрое распознавание на маленьких экранах [3]
- Чёткое отражение назначения приложения без текста
- Простота → узнаваемость при размере 29×29px (Settings icon)
- Консистентность с внутренним UI → снижение когнитивного диссонанса

### Технические требования iOS 2026 [6]

| Параметр | Требование |
|---|---|
| Master размер | 1024×1024 px |
| Формат | PNG |
| Прозрачность | Запрещена — 100% opaque, без alpha channel |
| Rounded corners | Не добавлять вручную — Apple применяет маску автоматически |
| Тени/глосс | Не добавлять — система применяет сама |
| Apple devices в иконке | Запрещено |
| App Store скриншоты в иконке | Запрещено |
| Notification badges в иконке | Запрещено |
| Placeholder/beta индикаторы | Запрещено |
| Текст | Только если essential branding |

### Размеры по платформам [6]

| Платформа | Размер | Форма после маски |
|---|---|---|
| iPhone / iPad / macOS | 1024×1024 px | Rounded rectangle |
| Apple Watch | 1088×1088 px | Circular |
| tvOS | 800×480 px | Rectangular |
| visionOS | 1024×1024 px | Circular (3D) |

### 2025 WWDC Update [6]

- **Icon Composer** tool в Xcode 16: автоматическая адаптация под Light/Dark mode без отдельных дизайнов
- **Liquid Glass icons** (2025): Apple's modern design standard — слоистые, консистентные, адаптируются к light/dark. Рекомендуется как направление для A/B тестирования [4]
- Visual consistency теперь влияет на App Store ranking (официальное заявление Apple) [6]

---

## Screenshots — Психология и структура

### Поведенческие паттерны пользователя

```
Поиск → [Icon + название + рейтинг + Screenshot 1-2] → Клик или нет
           ↑ всё это видно без перехода на страницу

Страница → [Screenshot 1 → 2 → 3] → 90% пользователей здесь принимают решение
                                         ↑ только 13% скроллят дальше
```

### Value–Usage–Trust Framework

Рекомендуемая последовательность скриншотов [1, 3]:

| Позиция | Фрейм | Что показывать |
|---|---|---|
| 1-2 | **Value** | Главное УТП — что пользователь получает; видно в поиске без клика |
| 3-4 | **Usage** | Ключевой сценарий использования; одно чёткое действие |
| 5-6 | **Trust** | Социальное доказательство, награды, рейтинги, количество пользователей |
| 7-10 | **Features** | Дополнительные функции для вовлечённых пользователей |

### 8 принципов дизайна скриншотов [3]

1. Логическая структура — иерархия ассетов диктуется стратегией, не дизайнером
2. Сильный visual language — сообщение без текста
3. Демонстрация живого приложения (не концепт-арт)
4. Один месседж на один ассет
5. Увеличивать ключевые UI элементы (mobile экраны малы)
6. Упрощать UI сохраняя clarity
7. Яркие, привлекающие внимание цветовые палитры
8. Эмоциональный резонанс через visuals и messaging

### Текст на скриншотах

- При загрузке скриншотов в App Store Connect **нет отдельного текстового поля** — только файл изображения
- Весь текст встраивается в дизайн самого скриншота
- Включать target keywords в текст на скриншоте (headline + subtext) — влияет на NLP-индексацию через визуальный контент страницы
- Один headline на скриншот; subtext — до 40-50 символов для читаемости на малых экранах

### Технические требования [5]

- Минимум 5 скриншотов (рекомендуется использовать все 10 слотов)
- Обязателен набор под самый большой iPhone (6.9", 1320×2868). Отдельные наборы под 6.5" и 5.5" больше не требуются — Apple масштабирует сама
- Portrait или Landscape — выбор влияет на отображение в поиске (landscape занимает больше экрана)

---

## Preview Video — Психология и стратегия

### Ключевые данные [3]

- Среднее время внимания: **7 секунд**
- Досматривают до конца: **8%**
- **Вывод**: видео должно открываться core value немедленно — не intro, не брендинг, не загрузочный экран

### Структура эффективного preview

```
[0-3 сек] Hook — самая compelling функция / визуальный момент
[3-10 сек] Core mechanic — как это работает (одно действие)
[10-30 сек] Supporting features — для досмотревших
```

### Технические ограничения (PPO через App Store Connect) [4, 5]

- До 3 видео на устройство
- Максимальная длина: **30 секунд**
- Требует прохождения App Review независимо от билда

### Video vs. No Video

| Сценарий | Рекомендация |
|---|---|
| Приложение с сильной визуальной механикой | Video обязателен |
| Утилита / простой workflow | Тестировать — иногда скриншоты конвертят лучше |
| Игра | Video критичен — gameplay > всего |
| Медитация/wellbeing | Атмосферное video > демонстрация функций |

---

## A/B Testing — PPO vs. CPP

### PPO (Product Page Optimization)

Официальный инструмент Apple (с iOS 15) для тестирования default product page [2, 4, 5].

| Параметр | Значение |
|---|---|
| Variants | До 3 одновременно (+ original) |
| Testable elements | Icons, Screenshots, Preview Videos |
| Нельзя тестировать | Название, subtitle, description, keywords |
| Max duration | 90 дней |
| Confidence level | 90% |
| Traffic | Только iOS 15+ пользователи |
| Параллельные тесты | Только 1 PPO за раз на default page |
| Icon тестирование | Требует включения в app binary + App Review |
| Screenshots/Video | Независимый App Review (без нового билда) |

**Результаты**: "Performing Better" / "Performing Worse" / "No Clear Result" — при достижении 90% confidence.

### CPP (Custom Product Pages)

| Параметр | Значение |
|---|---|
| Количество | До 70 CPP на приложение |
| Аудитория | Специфические сегменты (через ASA, deep links, внешние кампании) |
| С июля 2025 | CPP отображаются в органических результатах поиска |
| Тестирование | PPO недоступен для CPP — отдельный инструмент |

### PPO vs. Google Play Store Listing Experiments

| Фактор | PPO (iOS) | Store Listing Experiments (Android) |
|---|---|---|
| Testable elements | Icons, screenshots, videos | + short/long descriptions |
| Review required | Да | Нет |
| Icon testing | Требует обновления binary | Без обновления |
| Max duration | 90 дней | Unlimited |

### Методология A/B теста [2, 4, 5]

1. **Формулировать гипотезу** до запуска теста (предсказать результат)
2. **Одна переменная за раз** — изолировать причинность
3. **Минимум 1 неделя** — тесты в 7-дневных инкрементах
4. **Не останавливать досрочно** — fake positives при низкой confidence
5. **Равное распределение трафика** (50/50 или 33/33/33) — для сравнения apples-to-apples
6. **Контролировать внешние факторы**: маркетинговые кампании, сезонность искажают результаты
7. **По локалям раздельно**: тесты в топ-рынках, не глобально — разное поведение аудитории
8. **Целевая ясность**: store page — 90% clarity (vs. 60% для paid ads) [3]

---

## Compliance — Ключевые правила

### App Icon [6]

| Нарушение | Следствие |
|---|---|
| Прозрачность / alpha channel | Rejection |
| Неправильный размер (даже 1px) | Rejection |
| Pre-applied rounded corners | Двойная маска → обрезанный вид |
| Apple devices / UI elements в иконке | Rejection (Guideline 4.1) |
| Чужой brand/icon без разрешения | Rejection (Guideline 4.1c) |
| Placeholder/beta indicators | Rejection |
| Shadows/gloss эффекты | Нежелательно (система применяет сама) |

### Screenshots / Video

- Скриншоты должны отражать актуальный UI приложения
- Нельзя использовать реальные Apple device images без разрешения (использовать device frames)
- Preview video: максимум 30 секунд; контент должен соответствовать реальному опыту приложения
- Misleading visuals → rejection + возможный ban аккаунта

### Metadata в creatives

- Guideline 4.1c: нельзя использовать иконку, бренд или название другого девелопера в metadata без разрешения [search results]
- Superlatives ("Best", "#1") в скриншотах — допустимы если подкреплены данными

---

## Evolution / Trends

| Период | Изменение |
|---|---|
| До 2017 (iOS 11) | Нет subtitle; longer title; меньше скриншотов |
| 2021 (iOS 15) | PPO запущен; Custom Product Pages (до 35 CPP) |
| 2022 | CPP расширены до 70; In-App Events с visual assets |
| 2023 | iOS 17: обновление PPO не прерывается при публикации нового app version |
| Июнь 2025 | Screenshot captions индексируются поиском |
| Июль 2025 | CPP в органических результатах поиска |
| 2025 WWDC | Icon Composer в Xcode 16; Liquid Glass design standard; light/dark auto-adaptation |

---

## Open Questions & Gaps

- **Screenshot captions ranking weight**: подтверждено индексирование (июнь 2025), но величина эффекта на ранг неизвестна
- **Video vs. no video**: нет масштабных контролируемых исследований по категориям — данные носят анекдотальный характер
- **Icon ranking signal**: Apple заявило что "visual consistency impacts ranking" (2025), но механизм непрозрачен
- **CPP в органике**: появились в июле 2025 — долгосрочный impact на органический трафик не изучен
- **Liquid Glass**: новый стандарт в beta — как алгоритм учитывает соответствие дизайну системы, неизвестно

---

## Sources

1. ASOMobile — "Visual ASO for Mobile Apps in 2025" / "Screenshots Guide 2025" — asomobile.net (2025)
2. AppTweak — "Product Page Optimization: A Guide to App Store A/B Testing" — apptweak.com/en/aso-blog/product-page-optimization (2024-2025)
3. AppAgent — "ASO Creative Best Practices" — appagent.com/blog (2025)
4. MobileAction — "App Store product page optimization: how to run A/B tests (2026)" — mobileaction.co/blog/product-page-optimization/ (2026)
5. Apple Developer — "Overview of product page optimization" — developer.apple.com/help/app-store-connect (official, 2025)
6. The App Launchpad — "iOS App Icon Sizes, Requirements & Guidelines for App Store Approval (2026)" — theapplaunchpad.com (2026)

---

## Reuse Hooks

- **Screenshot audit**: первые 2 скриншота — UТП без скролла; screenshot 3 — closing argument; остальные вторичны
- **Caption strategy**: с июня 2025 — включать target keywords в подписи к скриншотам
- **PPO setup**: одна переменная, equal traffic split, минимум 7 дней, ждать 90% confidence
- **Icon compliance checklist**: PNG 1024×1024, без alpha, без rounded corners, без Apple devices
- **Video hook**: ценность за первые 3 секунды — не intro, не splashscreen
- **A/B budget**: 60% на major redesign, 20% на copy, 20% на layout
- **CPP post-July 2025**: создавать keyword-specific CPP для органического поиска без paid трафика

---

_Update log: 2026-03-06 — initial version, sources: ASOMobile (2025), AppTweak (2024-2025), AppAgent (2025), MobileAction (2026), Apple Developer (official 2025), The App Launchpad (2026)_
