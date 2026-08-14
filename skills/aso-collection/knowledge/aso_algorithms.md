# ASO Algorithms & Store Updates — Evolution, Black Box, Prediction Proxies

## Summary

Алгоритмы App Store (Apple) и Google Play — закрытые системы без официальной документации весов факторов. Apple раскрыл часть механики под давлением DMA (ЕС, 2025), но раскрытие носит compliance-характер, а не технический. Детекция изменений производится косвенно: через аномалии в keyword rankings на широкой выборке приложений. 2025–2026 — период наибольшего числа подтверждённых изменений за всё время: screenshot captions, CPP в органике, AI-теги, Gemini в Google Play, battery vital, расширение рекламы.

---

## Key Principles

- **Black box**: ни Apple, ни Google не публикуют веса факторов. Все данные — inference из наблюдаемых корреляций [1, 2]
- **Два уровня алгоритма (Apple)**: детерминированный слой (metadata → indexation: yes/no) + стохастический слой (behavioral signals → position) [1]
- **Google Play более прозрачен**: полная индексация description, Android Vitals с публичными порогами, но веса также не раскрыты [5]
- **DMA-давление (ЕС)**: Apple оштрафован на €500M (апрель 2025) и обязан раскрывать ranking parameters; первые раскрытия появились, но содержат tier-структуру, не веса факторов [3]
- **Изменения не анонсируются**: и Apple, и Google вводят изменения без уведомления. Детекция возможна только через мониторинг аномалий [2, 6]
- **Аномальный score**: AppTweak/aso.dev отслеживают отклонения в keyword rankings; score ≥3 = вероятное изменение; score 6 (июнь 2025, Google Play) = крупнейшее обнаруженное изменение за период [2]
- **Battery optimization (март 2026)**: новый технический фактор на Google Play — несоответствие исключает из recommendation surfaces [4]

---

## Data / Models

### Apple App Store — Известные vs. Неизвестные сигналы

| Статус | Сигнал | Источник знания |
|---|---|---|
| **Подтверждено Apple** | Metadata: title, subtitle, keyword field | Apple Developer docs |
| **Подтверждено Apple** | App quality, ratings, engagement compliance | DMA disclosure 2025 [3] |
| **Подтверждено Apple** | Developer tier level влияет на visibility | DMA disclosure 2025 [3] |
| **Подтверждено индустрией** | Download velocity | Корреляционные исследования |
| **Подтверждено индустрией** | CVR (install rate из поиска) | A/B test observations |
| **Подтверждено индустрией** | D7/D30 retention | Множество источников, 2025-2026 |
| **Подтверждено индустрией** | Uninstall rate (штраф) | Industry consensus |
| **Подтверждено индустрией** | Crash rate (штраф) | Apple Developer guidelines |
| **Подтверждено 2025** | Screenshot captions → индексация | June 2025 detection [SplitMetrics] |
| **Подтверждено 2025** | CPP → органическая выдача | July 2025 Apple announcement |
| **Подтверждено 2025** | In-App Events → индексация | Apple WWDC 2022, закреплено |
| **Beta 2025** | AI-generated tags (iOS 26) | Apple WWDC 2025 beta |
| **Неизвестно** | Точные веса каждого фактора | — |
| **Неизвестно** | Персонализация vs. универсальный ранк | — |
| **Неизвестно** | Semantic matching глубина | — |

### Google Play — Алгоритм vs. App Store

| Параметр | Apple App Store | Google Play |
|---|---|---|
| Индексация description | Нет (iOS) | Да — full description (SEO-like) |
| Keyword field | Да (100 chars, скрытое) | Нет отдельного поля |
| Short description | Нет | Да (80 chars, индексируется) |
| Android Vitals | Нет аналога | Публичный порог: crash/ANR < 8% |
| Battery vital (2026) | Нет | Да — excessive wake locks < 5% [4] |
| AI summary | Apple AI summaries (WWDC25) | Gemini "Ask Play" (Jan 2026) [4] |
| Algorithm transparency | Частичное (DMA, 2025) | Минимальное |
| A/B testing официальное | PPO (iOS 15+) | Store Listing Experiments |
| Guided Search | Нет | Да (2025) — refinement queries |

### Android Vitals — Пороги (Google Play, 2025-2026)

| Метрика | Порог нарушения | Последствие |
|---|---|---|
| Crash rate | > 8% сессий | Исключение из featured surfaces |
| ANR rate | > 8% сессий | Исключение из featured surfaces |
| Excessive partial wake locks | > 5% батареи (с 01.03.2026) | Исключение из recommendations [4] |

### Хронология подтверждённых изменений алгоритма (2021–2026)

| Дата | Платформа | Изменение | Подтверждение |
|---|---|---|---|
| 2021, iOS 15 | Apple | PPO запущен; engagement signals официально | Apple WWDC21 |
| 2022 | Apple | In-App Events индексируются | Apple WWDC22 |
| 2023, iOS 17 | Apple | PPO тест не прерывается при обновлении приложения | Apple changelog |
| 2024 | Apple | Semantic matching mature; plurals/singulars авто | Industry observation |
| Июнь 2025 | Google Play | Крупнейшее keyword volatility: аномальный score 6/6; ≥40 стран; keyword density weight up [2] | AppTweak detector |
| Июнь 2025 | Apple | Screenshot captions начали индексироваться | SplitMetrics detection |
| Июль 2025 | Apple | CPP в органических результатах поиска | Apple announcement |
| Ноябрь 2025 | Apple | CPP doubled: 35 → 70; ручное назначение keyword per CPP | Apple ASC update |
| Ноябрь 2025 | Google Play | Battery vital анонсирован (вступает в силу 01.03.2026) | Google Play Console |
| Январь 2026 | Google Play | "Ask Play" (Gemini): AI-ответы из metadata + reviews | Play Store v49.3 |
| Март 2026 | Apple | Расширение рекламных позиций в поиске (beyond top) | Apple announcement [4] |
| 2025, iOS 26 beta | Apple | AI-generated tags | Apple beta |
| 2025 | Apple/DMA | Первое частичное раскрытие ranking parameters (EU DMA) | EC decision [3] |

---

## Black Box — Структура неизвестности

```
ИЗВЕСТНО (детерминировано)
├── Keyword field → binary: indexed / not indexed
├── Title/subtitle → indexed с наибольшим весом
└── Android Vitals пороги (Google Play, публичные)

ИЗВЕСТНО КОРРЕЛЯЦИОННО (не подтверждено официально)
├── Download velocity → position
├── CVR → position
├── D7/D30 retention → position
├── Uninstall rate → demotion
└── Rating avg → visibility threshold

НЕИЗВЕСТНО
├── Точные веса каждого фактора
├── Персонализация: universal rank vs. user-specific rank
├── Semantic matching depth
├── Как AI-теги влияют на rank (beta, 2025)
└── DMA tier structure → как именно "tier" влияет на visibility
```

---

## Proxies для Prediction

### Детекция изменений алгоритма

| Метод | Как работает | Инструменты |
|---|---|---|
| Anomaly score tracking | Мониторинг аномальных отклонений rankings на широкой выборке | AppTweak Algorithm Change Detector, aso.dev/detector |
| Keyword volatility index | % ключей, сменивших позицию за период > threshold | ASO tools daily snapshots |
| Visibility score delta | Резкое изменение органического share of voice без metadata изменений | ConsultMyApp Visibility Index® |
| Competitor rank correlation | Если все конкуренты в категории двигаются одновременно → алгоритм, не ты | Ручной мониторинг |
| Category-wide movement | Изменение в одной категории = нишевой сигнал; в 40+ странах = глобальный апдейт [2] | ASO platforms |

### Practitioner Framework: "Изменение алгоритма или мои действия?"

```
Падение/рост позиции обнаружено
          ↓
Проверить: двигаются ли конкуренты в той же категории?
    Да → вероятно алгоритм (или сезонность)
    Нет → вероятно мои metadata/behavioral изменения
          ↓
Проверить: аномальный score у детекторов за период?
    Score ≥ 3 → подтверждён апдейт
    Score < 3 → нет глобального события
          ↓
Проверить: было ли изменение в нескольких странах одновременно?
    40+ стран → глобальный апдейт (Google Play June 2025 pattern)
    1-3 страны → тест или нишевое изменение
```

### Google Play June 2025 — Winning Profile

Приложения, выигравшие от апдейта [2]:

| Характеристика | Значение |
|---|---|
| Длина description | ~4,000 chars (максимум) |
| Keyword repetitions в description | 6-15 раз |
| Средний рейтинг | 4.5+ |
| Total installs | 100,000+ |

**Вывод**: апдейт усилил вес keyword density в long description и доверие к established apps.

---

## DMA и Transparency (EU, 2025)

| Событие | Дата | Детали |
|---|---|---|
| EC finds Apple in breach of DMA | Апрель 2025 | Anti-steering restrictions нарушают DMA |
| Apple оштрафован | Апрель 2025 | €500M финальный штраф |
| Частичное раскрытие ranking parameters | 2025 | Apple раскрыл tier-структуру и quality signals; точные веса не опубликованы [3] |
| Разработчики сообщают о продолжении нарушений | Декабрь 2025 | Coalition for App Fairness: Apple продолжает non-compliance [The Register] |

**Практическое значение для ASO**: DMA-раскрытие подтвердило что "developer tier" и "app quality" влияют на visibility — новый официально подтверждённый фактор. Веса по-прежнему не раскрыты.

---

## Open Questions & Gaps

- **AI-теги (iOS 26 beta)**: механизм влияния на ранг не раскрыт; в production не вышли на момент написания
- **"Ask Play" (Gemini, Jan 2026)**: как оптимизировать metadata под AI-интерпретацию — новая неизвестная
- **DMA tier structure**: что именно означает "tier" и как developer tier определяется — не раскрыто Apple
- **Expanded ads (March 2026)**: насколько расширение платных позиций вытеснит органику — в процессе rollout
- **CPP в органике (July 2025)**: долгосрочное влияние на organic traffic distribution — данных ещё мало
- **Battery vital Google Play (01.03.2026)**: сколько приложений реально окажутся под порогом — неизвестно

---

## Sources

1. ConsultMyApp — "Understanding the App Store Algorithm 2025: Challenges and Best Practices" — consultmyapp.com/blog (2025)
2. ARPU Brothers — "ASO Google Play Algorithm Changes – Keyword Movements June 2025" — arpubrothers.com/blog (2025)
3. Red Blink — "App Store Algorithm Updates: Strategies for Success in 2025" — redblink.com (2025)
4. AppTweak — "ASO news & app store updates 2026" — apptweak.com/en/aso-blog/app-store-optimization-news-app-store-updates (2026)
5. AppTweak — "What are the top Google Play ranking factors in 2026?" — apptweak.com/en/aso-blog/google-play-ranking-factors (2026)
6. aso.dev — "ASO Anomaly Detector: Track App Store Algorithm Changes" — aso.dev/aso/detector/ (2025)
7. The ASO Project — "Inside Apple's App Store Algorithm" — theasoproject.com/blog (2025)

---

## Reuse Hooks

- **При необъяснимом падении позиций**: сначала проверить anomaly detectors (AppTweak / aso.dev) — алгоритмический апдейт, не твоя ошибка
- **Google Play description**: ~4,000 chars + keyword repetition 6-15× → winning profile (June 2025 update)
- **Android Vitals**: crash/ANR < 8%; с 01.03.2026 battery wake locks < 5% — несоответствие = exclusion from discovery surfaces
- **DMA-раскрытие**: официально подтверждены quality, engagement, developer tier — обоснование для stakeholders
- **Gemini "Ask Play"**: description должен содержать чёткие, однозначные формулировки — AI генерирует ответы из metadata
- **Алгоритм detection cadence**: еженедельный мониторинг anomaly score; если score ≥ 3 и движение в 3+ конкурентов — wait 2 недели перед внесением metadata изменений

---

_Update log: 2026-03-06 — initial version, sources: ConsultMyApp (2025), ARPU Brothers (2025), AppTweak (2026), aso.dev (2025), The ASO Project (2025), Red Blink (2025)_
