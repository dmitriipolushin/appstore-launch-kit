---
name: aso-collection
description: Собирает первичный ASO-набор для нового приложения: конкуренты, ядро ключевых слов с Search Popularity, органические позиции, рекомендации по title/subtitle/keyword field и генерация description. Вызывай когда нужно сделать ASO с нуля, собрать ключи, проанализировать конкурентов или подготовить метаданные к публикации.
---

# aso-collection

Первичный ASO-набор для нового приложения: конкуренты, ключевые слова, Search Popularity, позиции, рекомендации по метаданным и генерация description.

## Когда использовать

Нужно собрать первичный ASO-набор: конкуренты, ключевые слова, рекомендации для title/subtitle/keyword field.

## Что нужно от пользователя

- Название или App Store ID приложения
- Категория и краткое описание (чем занимается приложение)
- Целевой рынок (страна/язык)

## Обязательный бриф перед стартом

Прежде чем писать метаданные — уточнить у пользователя:

1. **Функции приложения** — не добавлять в ключи функции, которых нет. Если ключ описывает конкретную фичу (клонирование голоса, офлайн-режим, экспорт) — сначала уточнить, потом добавлять.

2. **Монетизация** — полностью бесплатно, freemium (что именно бесплатно, что платно) или платное. Это влияет на допустимость слова «бесплатно» в видимых полях (Guideline 2.3.2).

## Правила работы

**⚠️ Не использовать `$1`, `$2` … в bash-блоках этого файла**
При вызове скилла позиционные переменные подменяются словами из аргументов пользователя
(`awk '{print $1}'` превращается в `awk '{print <второе слово запроса>}'`).
Использовать `cut -d' ' -f1`, `awk '{print substr($0,1,index($0," ")-1)}'` или именованные переменные.

**Subtitle — всегда фраза, не листинг**
Никогда не предлагать subtitle в формате перечисления через запятую («трек, кавер, лирика»). Subtitle = законченная фраза, которая сама является поисковым запросом. Структура: глагол + объект + дифференциатор.

**Subtitle конкурентов — только через AppStoreSpy**
iTunes API не возвращает subtitle. Для анализа конкурентов использовать AppStoreSpy (`/v1/ios/apps/{id}` → поле `short`) раздельно для каждой локали.

**Кросс-локали — исследовать перед работой**
Не угадывать, какие локали индексирует целевой сторефронт. Запустить отдельного агента с задачей: «исследуй, какие локали индексирует App Store сторефронт {country}» — и использовать результат.

**Читаемость всех заголовков**
После формулировки title для каждой локали — прочитать вслух. Если режет ухо — переформулировать.

## Первоначальная настройка (один раз)

Все API-ключи хранятся в `~/.config/aso-tools/api_keys.env` — скрипты загружают их оттуда сами
(через `scripts/env_setup.py`). Файл создаёт `growth/install.sh` из шаблона `growth/api_keys.env.example`.

Нужны для этого скилла: `APPSTORESPY_API_KEY`, а для Search Popularity — `APPLE_SA_COOKIE` и `APPLE_SA_XSRF`
(живут ~24 часа; `401` от `keyword_popularity.py` = пора обновить cookie из DevTools на app-ads.apple.com).

Если чего-то не хватает — не угадывать значения, а сказать пользователю, какой переменной нет
и куда её взять (описано в `growth/api_keys.env.example` в репозитории скиллов).

## Структура данных

Скилл создаёт папку `./aso-collection/` в текущей директории:
```
./aso-collection/
├── config/
│   └── competitors.txt
└── data/
    ├── raw/           # профили конкурентов, позиции
    ├── keywords/      # universe, asa_popularity
    └── reports/       # рекомендации по метаданным
```

## Начало сессии

Прочитай релевантные knowledge-файлы для контекста:
- `~/.claude/skills/aso-collection/knowledge/aso_keyword_research.md` — методология ключей
- `~/.claude/skills/aso-collection/knowledge/aso_metadata.md` — правила title/subtitle/KF
- `~/.claude/skills/aso-collection/knowledge/aso_foundations.md` — базовые концепции
- `~/.claude/skills/aso-collection/knowledge/aso_algorithms.md` — алгоритм App Store 2025-2026
- `~/.claude/skills/aso-collection/knowledge/aso_social_signals.md` — competitive intelligence

## Шаги

### 1. Создай структуру проекта

```bash
mkdir -p ./aso-collection/{config,data/{raw,keywords,reports}}
```

### 2. Составь список конкурентов

**Вариант А — пользователь даёт список**
Пользователь называет приложения или App Store ссылки. Для каждого извлеки App ID и проверь через AppStoreSpy MCP `get_detailed_app_info` — покажи таблицу с `downloads_month`, `revenue_month`, чтобы пользователь подтвердил что это нужные конкуренты.

**Вариант Б — discovery через iTunes Search (работает всегда)**

⚠️ AppStoreSpy MCP (`search_ios_apps`) есть не в каждом окружении, а REST-поиск AppStoreSpy
молча игнорирует параметр `query` и возвращает нерелевантный список. Проверь MCP; если его нет —
ищи через iTunes, он бесплатный и отдаёт ровно то, что видит пользователь в поиске App Store:

```bash
for q in "ключ 1" "ключ 2" "ключ 3"; do
  echo "== $q"
  curl -s -G "https://itunes.apple.com/search" \
    --data-urlencode "term=$q" --data-urlencode "country=us" \
    --data-urlencode "entity=software" --data-urlencode "limit=12" \
  | python3 -c "import json,sys
for a in json.load(sys.stdin)['results']:
    print(a['trackId'], a.get('userRatingCount'), a['trackName'][:55])"
done
```

Метрики (downloads/revenue) добираются потом поштучно через AppStoreSpy REST:
`GET https://api.appstorespy.com/v1/ios/apps/{id}` с заголовком `API-KEY: $APPSTORESPY_API_KEY`
(именно `API-KEY`, не `Authorization: Bearer`). Поля: `name`, `short` (subtitle), `downloads`,
`revenue`, `rating_count`, `rating_avg`, `released`.

Покажи топ результаты пользователю, пусть выберет релевантных.

После подтверждения составь `./aso-collection/config/competitors.txt`:
```
284882215  # App Name  added:2026-03-03  source:manual
123456789  # App Name  added:2026-03-03  source:discovery
```

### 3. Собери профили конкурентов

```bash
python3 ~/.claude/skills/aso-collection/scripts/collect_profiles.py \
  --project ./aso-collection \
  --app-ids $(grep -v '^#' ./aso-collection/config/competitors.txt | cut -d' ' -f1 | tr '\n' ' ')
```

Скрипт сохраняет `data/raw/profile_{app_id}_{timestamp}.json` с title, subtitle, description.
Subtitle берётся из AppStoreSpy (iTunes его не возвращает).

### 4. Собери ключевые слова

**Шаг А — извлеки seed-термины из метаданных конкурентов**

Прочитай все `./aso-collection/data/raw/profile_*.json`. Извлеки:
- Все слова и фразы из title и subtitle каждого конкурента (высокий вес)
- Часто встречающиеся фразы из description (3+ конкурентов — средний вес)
- Брендовые названия конкурентов как отдельные seeds

**Шаг Б — расширь через Apple Search Hints**

```python
import sys; sys.path.insert(0, str(__import__('pathlib').Path.home() / '.claude/skills/aso-collection/scripts'))
from keyword_suggest import expand_seeds

# Всегда подавать PREFIX, не полный термин
# "pet health t" а не "pet health tracker"
results = expand_seeds(seed_terms, "us")
# results: [{term, priority_score, tier}]
# tier: HIGH (≥5000) / MEDIUM (≥1000) / LOW
```

Сохрани результаты в `./aso-collection/data/keywords/universe_{timestamp}.json`.

**После сбора hints — просканируй список на иноязычные термины:**

Прочитай все собранные hints и найди термины не на основном языке сторефронта. Если нашлось ≥ 3 таких термина в тире HIGH/MEDIUM — запусти для них ASA popularity (шаг В). Если хотя бы один ≥ 20 → добавить отдельную локаль оправдано.

Типичные сигналы по рынкам:
- DE storefront → французские термины: франкофоны Швейцарии; арабские/турецкие: мусульмане в Германии
- GB storefront → арабские/урду: South Asian community
- US storefront → испанские термины: Hispanic community → es-MX локаль

**Шаг В — проверь Search Popularity через Apple Search Ads**

Apple Search Hints дают только *порядок* подсказок, но не реальный объём. Search Ads даёт официальный score 0–100.

| Search Popularity | Tier | Стратегия для нового приложения |
|---|---|---|
| 70–100 | Head | Title/subtitle — обязательно; органику не ждать, нужен ASA |
| 40–69 | Mid | Subtitle + KF; достижимые позиции за 3–6 мес |
| 10–39 | Long-tail | **Приоритет для нового приложения** — заполнить KF |
| 1–9 | Niche | Только добивка char budget |
| 0 | Zero | Убрать из KF; оставить в description для NLP |

**Предусловие, которое решает всё.** Запрос возвращает данные только для `adamId`
**из твоей ASA-организации**, и фильтрует выдачу по тематике этого приложения.
adamId конкурента отдаёт пустой массив. Значит:

> Если в ASA-аккаунте нет приложения из нужной ниши — **Search Popularity получить неоткуда.**
> Ни через cookie, ни через браузер, ни через официальный API. Не тратить на это время:
> сказать пользователю прямо и работать на Apple Search Hints + конкурентности выдачи,
> а popularity замерить после публикации приложения.

Сначала проверь, какие adamId доступны:
```bash
python3 ~/.claude/skills/aso-collection/scripts/asa/asa_api.py --list-apps
```

#### Способ 1 (основной) — из браузера, без cookie

Ничего не истекает раз в сутки и не нужно копировать учётные данные. Требует
Claude-in-Chrome либо встроенного браузера с активной сессией app-ads.apple.com.

1. Открыть `https://app-ads.apple.com/` и убедиться, что пользователь залогинен.
2. Выполнить запрос **изнутри страницы** — браузер сам подставит сессию:

```js
const xsrf = decodeURIComponent((document.cookie.match(/XSRF-TOKEN-CM=([^;]+)/)||[])[1]||'');
const Q = `query getRecommendedKeywordsGql($adamId: String!, $text: String, $storefronts: [String]) {
  recommendationV2 { getRecommendedKeywords(adamId: $adamId, text: $text, storefronts: $storefronts) {
    id name popularity matchType __typename } __typename } }`;
window.__q = async (adamId, text, sf=['US']) => {
  const r = await fetch('https://app-ads.apple.com/reporting/graphql', {
    method:'POST', credentials:'include',
    headers:{'content-type':'application/json','x-xsrf-token-cm':xsrf},
    body: JSON.stringify({operationName:'getRecommendedKeywordsGql',
      variables:{adamId:String(adamId), text, storefronts:sf}, query:Q})});
  const j = await r.json();
  return (j?.data?.recommendationV2?.getRecommendedKeywords)||[];
};
'ready'
```

3. Гонять пачками, **не быстрее ~1 запроса в секунду** — иначе Apple перестаёт отвечать
   (запросы виснут без статуса). Результат складывать в `window.__out`, забирать отдельным вызовом:
   долгий `await` в одном вызове упирается в таймаут инжекции.

⚠️ Cookie **не читать и никуда не записывать.** Он `HttpOnly`, из JS недоступен, и он не нужен.
⚠️ Вкладку за собой закрыть.

#### Способ 2 (запасной) — cookie в env, живёт ~24ч

1. Открой app-ads.apple.com → войди в аккаунт
2. DevTools → Network → фильтр XHR
3. Открой любую кампанию → Ad group → Keywords → вкладка Recommendations
4. Найди POST `/reporting/graphql` с `operationName: getRecommendedKeywordsGql`
5. Right-click → Copy → Copy as cURL
6. Обнови в `~/.config/aso-tools/api_keys.env`: `APPLE_SA_COOKIE`, `APPLE_SA_XSRF`, `APPLE_SA_ADAM_ID`

**Запуск:**
```bash
# Discovery — короткий seed → возвращает 10-80 связанных ключей с popularity
python3 ~/.claude/skills/aso-collection/scripts/asa/keyword_popularity.py \
  --seeds "pet health,dog tracker,cat" \
  --storefronts US,GB,CA,AU \
  --out ./aso-collection/data/keywords/asa_popularity.csv
```

**Режимы отказа — читать до того, как чинить cookie:**

| Симптом | Причина | Что делать |
|---|---|---|
| HTTP 401/403 | cookie истёк | обновить cookie, либо перейти на браузерный способ (ниже) |
| HTML вместо JSON | `APPLE_SA_COOKIE` пуст | то же |
| **HTTP 200 + пустой массив** | **`adamId` не из твоей ASA-организации, либо seed не по теме этого приложения** | подставить adamId своего приложения из нужной ниши |
| Запрос висит без ответа | троттлинг после серии запросов | пауза, затем ≤1 запрос в секунду |

⚠️ **`adamId` влияет решающе** (проверено экспериментально 09.2026, вопреки прежней записи
в этом файле). Он задаёт тематическое пространство выдачи и сам факт непустого ответа.
adamId конкурента возвращает пусто — API обслуживает только приложения твоей организации.
Следствие: **popularity по нише недоступна, пока в ASA-аккаунте нет приложения из этой ниши.**

⚠️ RU storefront всегда возвращает popularity=5 — ASA в России не работает.
⚠️ Официальный Apple Search Ads API v5 popularity **не отдаёт** — эндпоинтов нет, не искать.

**Что делать с результатами:**
1. Отсортируй CSV по popularity DESC
2. Ключи с popularity=0 — убрать из keyword field (оставь в description)
3. Расставь title/subtitle/KF по шкале выше

**Шаг Г — проверь позиции по топ-ключам**

```bash
python3 ~/.claude/skills/aso-collection/scripts/search_positions.py \
  --keyword "ключевое слово" \
  --app-ids {наше_app_id},{competitor_1},{competitor_2} \
  --country us \
  --project ./aso-collection
```

Повтори для топ 10–15 ключей по tier HIGH.

Смотри не только на позиции известных конкурентов — смотри кто вообще в топ-10. Часто обнаруживаются новые конкуренты. Профилируй их сразу.

**Шаг Д — сгруппируй ключи по теме и intent**

1. Выдели 2–4 основные темы (например: health / care / vet / tracking)
2. Внутри каждой темы раздели по intent пользователя
3. Определи: какая тема и intent — основные для title/subtitle, остальные — в keyword field

Apple ранжирует по двум целям: *behavioral relevance* (клики, загрузки) и *textual relevance*,
которую сама Apple определяет как **semantic fit** запросу — статья Apple, SIGIR 2026,
arXiv:2602.23234. Главное следствие для нового приложения:

> **Голова выигрывается поведением, хвост — смыслом.** Прирост от семантики максимален там,
> где поведенческих сигналов мало. У нового приложения их нет вообще, значит ставка —
> связные intent-кластеры на длинном хвосте, а не точные вхождения в головные запросы.

### 5. Собери отзывы конкурентов (опционально)

```bash
python3 ~/.claude/skills/aso-collection/scripts/fetch_reviews.py \
  --app-id {competitor_id} \
  --country us \
  --project ./aso-collection
```

Читай отзывы как источник поискового языка: повторяющиеся глаголы и формулировки проблем — реальные поисковые запросы пользователей.

Проверь рейтинг нашего приложения:
```bash
curl "https://itunes.apple.com/lookup?id={our_app_id}&country=us&entity=software" | \
  python3 -c "import json,sys; d=json.load(sys.stdin)['results'][0]; print(d['averageUserRating'], d['userRatingCount'])"
```
Если avg rating < 3.7 → review prompting приоритет перед расширением keyword coverage.

### 6. Keyword gap анализ

```python
import sys; sys.path.insert(0, str(__import__('pathlib').Path.home() / '.claude/skills/aso-collection/scripts'))
import json
from pathlib import Path
from competitor_analyzer import CompetitorAnalyzer, analyze_competitor_set

profiles = []
for f in Path('./aso-collection/data/raw').glob('profile_*.json'):
    p = json.loads(f.read_text())
    profiles.append({
        'app_name': p['itunes']['title'],
        'title': p['itunes']['title'] or '',
        'subtitle': p['itunes'].get('subtitle') or '',
        'description': p['itunes']['description'] or '',
        'rating': p['itunes']['rating_avg'],
        'ratings_count': p['itunes']['rating_count'],
    })

analyzer = CompetitorAnalyzer(category='{категория}', platform='apple')
gap_report = analyze_competitor_set(profiles)
```

Классификация:
- **gap** — нет ни у кого в title/subtitle/description → можно занять
- **weak** — только в description → слабая конкуренция
- **contested** — у части конкурентов в title/subtitle
- **dominated** — у большинства конкурентов в title/subtitle

### 6.5 Проверь размер ядра

После keyword gap анализа посчитай сколько уникальных слов реально войдёт в индексацию (title + subtitle + keyword field, без дублей, без стоп-слов).

```python
import re

def count_unique_words(title, subtitle, kf):
    stop = {"app","the","and","for","mit","der","die","das","und","für","von"}
    all_text = f"{title} {subtitle} {kf}".lower()
    words = set(re.findall(r"[a-zа-яёäöüß\u00c0-\u024f]+", all_text))
    return words - stop

unique = count_unique_words(title, subtitle, kf)
print(f"Уникальных слов в индексации: {len(unique)}")
```

Пороги:
| Слов | Оценка |
|---|---|
| < 20 | ⚠️ Критически мало — ядро почти пустое, расширить обязательно |
| 20–35 | ⚠️ Мало — добавить дополнительные локали или пересмотреть KF |
| 36–60 | ✓ Нормально для старта |
| > 60 | ✓ Хорошее покрытие |

Если ядро < 36 слов:
1. Проверь незаполненные локали — каждая даёт +100 символов KF = ~12–15 новых слов
2. Вернись к universe и найди low-hanging fruit: popularity 5–15, конкурент топ-3 < 500 ratings
3. Добавь intent-варианты уже используемых кластеров (глагол + существительное: "scan ingredients" → "ingredients scan", "scanning ingredients")

### 7. Сформируй рекомендации для метаданных

```python
import sys; sys.path.insert(0, str(__import__('pathlib').Path.home() / '.claude/skills/aso-collection/scripts'))
from metadata_optimizer import MetadataOptimizer

optimizer = MetadataOptimizer(platform='apple')
kw_result = optimizer.optimize_keyword_field(
    keywords=candidate_keywords,
    existing_metadata={'title': '...', 'subtitle': '...'}
)
print(kw_result['keyword_field'])  # готовая строка для App Store

validation = optimizer.validate_character_limits({
    'title': 'App Name: Main Keyword',
    'subtitle': 'Second Cluster Keywords',
    'keywords': kw_result['keyword_field'],
})
```

Предложи конкретные варианты:
- **Title** (30 символов): главный ключ + бренд
- **Subtitle** (30 символов): второй кластер ключей
- **Keyword field** (100 символов): результат `optimize_keyword_field()`

**Cross-localization — обязательный шаг, не опция**

US-сторефронт индексирует **10 локалей** (официальная таблица Apple, см. `knowledge/aso_metadata.md`):
`en-US`, `es-MX`, `ar`, `zh-Hans`, `zh-Hant`, `fr-FR`, `ko`, `pt-BR`, `ru`, `vi`.

Каждая локаль даёт **160 символов**, а не 100: title 30 + subtitle 30 + keyword field 100.
Индексируются все три поля, а не только скрытое. Итого потолок US = **1600 символов**.
Заполнять только keyword field — потерять две трети бюджета.

**Фразы собираются только внутри одной локали.** Слово из en-US и слово из es-MX не образуют
фразу (AppTweak 11.2025, Appfigures 06.2026 — проверено уже после NLP-сдвига). Отсюда правило:

> Каждая локаль = **один самодостаточный семантический кластер** со своим якорным
> существительным в title. Якорь обязан повторяться в каждой локали — без него внутри
> локали не собирается ни одной фразы. Это не дубль, а условие работы.

**Титулы вторичных локалей — риск ревью пропорционален видимости поля.** Правила «метаданные
должны быть на языке локали» у Apple нет (прочитан полный текст 2.3.7), публичных отклонений
за 2025–2026 не зафиксировано. Но 2.3.7 запрещает «irrelevant phrases just to game the system»:

| Поле | Вторичная локаль |
|---|---|
| keyword field (100) | 100% целевого языка, агрессивно. Скрыто, ревьюер в обычном флоу не видит |
| subtitle (30) | Целевой язык, но **читаемой фразой**, не набором слов |
| title (30) | `Бренд: <естественный дескриптор>`. Самое видимое поле |

⚠️ **es-MX — самая рискованная вторичная локаль, не самая безопасная.** US-пользователь
с испанским языком системы видит именно es-MX страницу в US App Store. `ar`, `vi`, `ko`,
`zh-Hant` в US-трафике пренебрежимы — там свободнее всего.

**Чем заполнять.** Для US-focused приложения — английскими ключами во всех вторичных локалях,
не переводом (кейс Amma Pregnancy Tracker: +49% US visibility за месяц). Но сначала проверь
реальный спрос на языке локали: если он есть и релевантен — бери его.

**Не применять без подтверждения.**

### 7.5 Дополнительные поверхности индексации

Метаданными в 10 локалях бюджет не исчерпывается. Эти поверхности почти никто из конкурентов
не занимает — проверь по их листингам, это дешёвое преимущество.

**IAP display names — 30 символов на каждую покупку, индексируются**
Прямо в доке Apple: «Searches use app and in-app purchase metadata from your product page».
Названия покупок — ещё одно keyword-поле. Описания покупок не индексируются.
⚠️ Цифра «64 символа», гуляющая по блогам, неверна: поле в ASC — 30.

**In-app events — name 30 + short description 50, до 10 событий**
Индексируются name и short description; long description (120) — нет.

**Keyword-linked Custom Product Pages — главный недоиспользованный рычаг**
Выкатили 30.07.2025, лимит 35 → **70** страниц с 29.10.2025.
Ключам из **уже одобренного** keyword field назначается отдельная продуктовая страница,
и она подменяет дефолтную в **органической** выдаче.

- индекс это **не расширяет** — меняется только то, какую страницу видит пользователь
- комбинация ключей уникальна для одной страницы
- нельзя брать слова, уже стоящие в title или subtitle
- CPP локализуются

Куда ставить: на ключи, где по шагу Г мы реально можем взять топ (конкурент №1 слабый),
а интент отличается от основного. Скриншоты страницы — под этот конкретный интент.

**Промо-текст (170) и описание (4000) на iOS не индексируются.** Не тратить на ключи.
Промо-текст — конверсия и новости, меняется без ревью.

---

### 8. Финальный чеклист перед публикацией

```python
import re

locales = {
    "primary": {"title": "...", "subtitle": "...", "kf": "..."},
    "en":      {"title": "...", "subtitle": "...", "kf": "..."},
}

limits = {"title": 30, "subtitle": 30, "kf": 100}
for locale, fields in locales.items():
    for field, val in fields.items():
        used, limit = len(val), limits[field]
        flag = "⚠️  НЕДОИСПОЛЬЗОВАНО" if used < limit * 0.85 else "✓"
        print(f"{flag}  {locale}.{field}: {used}/{limit}")

def words(s): return set(re.findall(r"[a-z\u00c0-\u024f]+", s.lower()))
for locale, f in locales.items():
    dupes = (words(f["title"]) | words(f["subtitle"])) & words(f["kf"])
    if dupes: print(f"⚠️  {locale} KF дублирует title/subtitle: {dupes}")
    else: print(f"✓  {locale} — нет дублей внутри локали")
```

Чеклист:
- [ ] Нет дублирования слов **внутри** локали (title / subtitle / keyword field)
- [ ] Между локалями пересекаются **только якорные слова** — они обязаны повторяться,
      иначе внутри локали не собирается фраза. Всё остальное пересечение = потеря бюджета
- [ ] Заполнены все 10 локалей US, каждая ≥85% по всем трём полям (title, subtitle, KF)
- [ ] Каждая локаль — один связный семантический кластер, а не россыпь слов
- [ ] Титулы вторичных локалей читаются как названия, а не как набор ключей
- [ ] Нет чужих торговых марок ни в одном поле (5.2.1)
- [ ] Screenshot captions написаны под конверсию. Индексация captions **не подтверждена** —
      ключи туда класть можно, строить на них стратегию нельзя
- [ ] IAP display names задействованы (30 симв. каждое, индексируются)
- [ ] Рейтинг приложения ≥ 3.7

Сохрани отчёт в `./aso-collection/data/reports/aso_recommendations_{timestamp}.md`.

### 9. Сгенерируй description

Выполняется после шагов 1–8, когда уже есть финальный набор ключей и метаданных.

**Шаг А — запроси у пользователя:**
1. Ссылку на Terms of Use / Terms of Service
2. Ссылку на Privacy Policy

Без этих ссылок description не генерировать — они обязательны в конце текста.

**Шаг Б — собери контекст для генерации:**
- Финальный title и subtitle (из шага 7)
- Топ-ключи из keyword field и keyword universe — использовать как тематические якоря
- Descriptions конкурентов из `data/raw/profile_*.json` — структура, крючки, tone of voice
- Отзывы конкурентов (если собраны) — язык и боли аудитории

**Шаг В — правила написания description:**

- Лимит: **4000 символов**
- Первые **2–3 строки критичны** — они видны без раскрытия "Подробнее". Главный value prop + призыв к действию.
- Структура:
  1. Hook — главная боль / обещание (1–2 предложения)
  2. Ключевые фичи — маркированный список (5–7 пунктов), каждый пункт начинается с глагола
  3. Для кого — целевая аудитория (1 абзац)
  4. Social proof / credibility — если есть (пресса, рейтинг, количество пользователей)
  5. CTA — призыв скачать
  6. Разделитель (`—` или пустая строка)
  7. Terms of Use: {ссылка}
  8. Privacy Policy: {ссылка}

- **Главное: описание пишется под цитирование LLM, не под индекс Apple.**
  На iOS описание поиском **не индексируется** — и это не изменилось. Но по замеру AppTweak
  (125 000 ответов ChatGPT, 9 489 промптов, US, май 2026) листинги App Store дают **38% всех
  цитирований**, вместе с Google Play — **47.5%**: больше, чем любые сайты, статьи и PR.
  Когда человек спрашивает LLM «какое приложение выбрать», модель читает именно описание.

  Из этого следует:
  - назвать аудиторию явно в первых строках, своими словами, без «for everyone»
  - **3–5 конкретных сценариев использования**, не больше — размытый список работает хуже
  - фичи через результат, а не через название фичи
  - убрать «all-in-one», «универсальное решение» и прочее позиционирование ни о чём
  - проверяемая конкретика: что именно поддерживается, что нет, какие ограничения
  - **не добивать до 4000 символов ради объёма** — сжатый текст цитируется лучше

- **NLP-оптимизация**: естественно вписать target keywords — не спамить, 1–2 вхождения кластера.
  Это вторично по отношению к пункту выше.
- Tone of voice: взять из анализа конкурентов (формальный / дружелюбный / экспертный)
- Язык description = язык основной локали (DE → немецкий, US → английский)
- Не использовать слова "лучший", "номер один", "#1" без доказательств — Apple может отклонить
- **Freemium/платный контент (обязательно)**: если приложение монетизируется через подписку или IAP — description обязан содержать явное упоминание что доступно бесплатно и что требует покупки. Без этого Apple отклоняет по Guideline 2.3.2 ("paid content not clearly identified"). Формула: одна-две фразы в конце текста (перед ссылками) — что бесплатно + что по подписке + возможность отменить. Пример: "Начни бесплатно: первые 3 вопроса и инсайт — без подписки. Полный доступ открывается по подписке, которую можно отменить в любой момент." Не нужно делать из этого отдельный раздел — достаточно органично вписать в финальный абзац.

**Шаг Г — локализация:**

Если в шаге 4 были выявлены дополнительные локали (например, DE + tr/ar для мусульманской аудитории) — предложи сгенерировать description для каждой локали отдельно. Каждая локаль получает свои ссылки ToU/PP (обычно те же, но уточни у пользователя).

**Шаг Д — сохрани результат:**

```
./aso-collection/data/reports/description_{locale}_{timestamp}.md
```

Формат файла:
```
# Description — {locale}
Символов: {N}/4000

---
{текст description}
```

**Не публиковать без подтверждения пользователя.**

## Правила анализа

- Apple Search Hints: всегда подавать PREFIX ("pet health t"), не полный термин
- Пустые hints = реально низкий объём, не баг
- **Hints ≠ Volume**: термин с Hints HIGH 10000 может иметь ASA Popularity = 5. Всегда верифицировать через ASA Popularity перед финализацией метаданных
- **Контентные термины ≠ поисковые термины**: слова важные в описании часто дают 0 hints и 0 ASA popularity. Держать в description для NLP, не в keyword field
- **Subtitle у новых конкурентов**: новые AI-приложения (2025–2026) часто выходят без subtitle. Проверять через iTunes lookup
- **Niche-термин + низкая конкуренция**: popularity=5 не всегда плохо. Если у #1 по этому ключу < 100 ratings — топ-3 достижим за 2–3 месяца
- Keyword field: без пробелов после запятых, без повторений слов из title/subtitle
- Приоритет по гео для English-рынка: US → GB → CA → AU
- Semantic clustering: группировать ключи по теме + intent, не только по volume
- Intent-глаголы (Track, Learn, Scan, Watch, Check) работают лучше дескрипторов
- Difficulty: новое приложение таргетирует ключи где топ-3 конкурент имеет < 10k reviews
