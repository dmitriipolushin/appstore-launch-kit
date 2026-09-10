---
name: aso-monitoring
description: Регулярный ASO-мониторинг (раз в 2-4 недели): органические позиции по ключам, keyword discovery по активным локалям, конкурентность ключей, сверка с ASA-данными, планирование A/B тестов скриншотов. Вызывай когда нужно проверить позиции, найти новые ключи или оценить эффект от изменения метаданных.
---

# aso-monitoring

Регулярный ASO-мониторинг: позиции, исследование новых ключей по всем активным локалям, конкурентность ключей, сверка с данными ASA-кампании.

Частота: раз в 2–4 недели.

## Что нужно от пользователя

- App ID приложения
- Активные ASO-локали (например: US en, US es, DE, GB)
- Текущие metadata по каждой локали (title, subtitle, keyword field)

## Первоначальная настройка (один раз)

Ключи — в `~/.config/aso-tools/api_keys.env`, скрипты читают их сами (`scripts/env_setup.py`).
Файл создаёт `growth/install.sh` из шаблона `growth/api_keys.env.example`.

Нужны: `APPSTORESPY_API_KEY`; `APPLE_SA_COOKIE` + `APPLE_SA_XSRF` для Search Popularity (живут ~24 часа);
`ASC_KEY_ID` + `ASC_ISSUER_ID` + `.p8` в `~/.config/aso-tools/keys/` для метрик App Store Connect.

Если чего-то не хватает — не угадывать значения, а сказать пользователю, какой переменной нет
и куда её взять (описано в `growth/api_keys.env.example` в репозитории скиллов).

## Структура данных

```
./ASO/
├── config/
│   ├── competitors.txt              # App IDs конкурентов
│   └── keywords.txt                 # отслеживаемые ключи
└── aso-monitoring/
    └── data/
        ├── keyword_signals.csv      # наши позиции по ключу (история)
        ├── competitor_positions.csv # полный SERP-снапшот (история)
        ├── metadata_changes.csv     # лог изменений metadata
        ├── keywords/                # popularity CSVs
        └── raw/                     # profiles и reviews конкурентов

ASA/asa-monitoring/data/
├── asa_metrics.csv                  # ASA метрики по ключам
└── asa_searchterms.csv              # search terms
```

**Принцип: только CSV-append, никаких timestamped файлов, никаких JSON для позиций.**

`keyword_signals.csv` — `keyword, locale, app_id, date, organic_position, metadata_source`  
`competitor_positions.csv` — `keyword, locale, date, app_id, app_name, position`  
`metadata_changes.csv` — `locale, field, was, becomes, status, date_recommended, date_submitted, date_live, positions_verified`

## Начало сессии

Прочитай knowledge-файлы:
- `~/.claude/skills/aso-monitoring/knowledge/aso_keyword_research.md` — семантический сдвиг 2025
- `~/.claude/skills/aso-monitoring/knowledge/aso_metadata.md` — правила keyword field, cross-localization
- `~/.claude/skills/aso-monitoring/knowledge/aso_algorithms.md` — алгоритмические апдейты
- `~/.claude/skills/aso-monitoring/knowledge/aso_creatives.md` — A/B тестирование через PPO

## Шаги

### 1. Загрузи контекст

```python
import pandas as pd

keywords = open('./ASO/config/keywords.txt').read()
sig = pd.read_csv('./ASO/aso-monitoring/data/keyword_signals.csv')
last_date = sig['date'].max()
latest = sig[sig['date'] == last_date]
print(f"Предыдущая проверка: {last_date}, {len(latest)} записей")
print(latest[['keyword', 'locale', 'organic_position']].to_string(index=False))
```

Если `keyword_signals.csv` не существует — создать с заголовком `keyword,locale,app_id,date,organic_position,metadata_source` и попросить у пользователя текущие metadata.

### 2. Загрузи ASA-данные

ASA-кампания является главным источником сигналов о ключах. Загрузи оба накопительных файла:

```python
import pandas as pd

asa = pd.read_csv('./ASA/asa-monitoring/data/asa_metrics.csv')
st  = pd.read_csv('./ASA/asa-monitoring/data/asa_searchterms.csv')

# Последние 14 дней (или с даты последнего мониторинга)
recent = asa[asa['fetch_date'] >= '{last_check_date}']
```

Поля `asa_metrics.csv`: `fetch_date, period_start, period_end, campaign_id, campaign_name, country, keyword, bid, impressions, taps, installs, spend, ttr, cr, avg_cpt, avg_cpa, ipm`

Поля `asa_searchterms.csv`: `searchTerm, keyword, impressions, taps, installs, ttr(%), cr(%), avgCPA, spend`

Построй сводную таблицу **по каждому ключу** (только с impressions > 0):

```
| Keyword           | ASA impr | ASA CR | IPM  | Spend | Organic pos | Сигнал |
|-------------------|----------|--------|------|-------|-------------|--------|
```

**Как читать:**

| ASA impr | ASA CR | Organic pos | Вывод |
|----------|--------|-------------|-------|
| > 50, CR > 3% | — | #1–10 | Снизить ASA bid — органика справляется |
| > 50, CR > 3% | — | #11–50 | Усилить ASA (прогрев) + добавить в KF |
| > 50, CR > 3% | — | #51+ | Добавить в KF + усилить ASA bid |
| > 50, CR < 2% | — | любая | **Не добавлять в title** — semantic mismatch |
| < 10 | — | любая | Мало данных — проверить popularity перед добавлением |

**Search terms — скрытые кандидаты:**
- Запрос с installs > 0, которого нет в ASA ключах → добавить в KF + как EXACT в ASA (доказан спрос)
- Запрос с TTR > 3%, которого нет в ASA → добавить как EXACT в ASA
- Нерелевантный запрос с taps > 0 → negative keyword

### 3. Проверь позиции по текущим ключам

Один вызов скрипта → пишет сразу в `keyword_signals.csv` (наша позиция) и `competitor_positions.csv` (полный SERP). Никаких промежуточных файлов.

```bash
APP_ID="YOUR_APP_ID"
for kw in "lebensmittel scanner" "halalcheck" "vegan check" "gluten free scanner" "produkt scanner" "allergie scanner"; do
  python3 ~/.claude/skills/aso-monitoring/scripts/search_positions.py \
    --keyword "$kw" --app-id $APP_ID --country de --project ./ASO/aso-monitoring
done
# повторить для fr, at, ch
```

После прогона — сравни с прошлой сессией:

```python
import pandas as pd
sig = pd.read_csv('./ASO/aso-monitoring/data/keyword_signals.csv')
dates = sorted(sig['date'].unique())
prev, today = dates[-2], dates[-1]
merged = (
    sig[sig['date']==today][['keyword','locale','organic_position']].rename(columns={'organic_position':'now'})
    .merge(sig[sig['date']==prev][['keyword','locale','organic_position']].rename(columns={'organic_position':'prev'}),
           on=['keyword','locale'], how='outer')
)
merged['delta'] = merged['prev'] - merged['now']
print(merged[merged['locale']=='de'].sort_values('now').to_string(index=False))
```

Что смотреть:
- Ключи с `delta < -5` (упали) — проверить конкурентов в `competitor_positions.csv`
- Ключи `now == null` (выпали из топ-50) — нужен ASA-прогрев
- Конкуренты, занявшие места: `competitor_positions.csv` где `keyword == X AND date == today AND position <= 10`

**Если позиции упали** — сначала проверить конкурентов: если все двигаются → алгоритмический апдейт; только мы → причина в metadata или behavioral сигналах.

### 4. Оцени конкурентность ключа (Competition Score)

Для каждого кандидата на добавление в metadata — оцени сложность ранжирования. Используй inline Python после получения позиций:

```python
import requests, json, math

def competition_score(keyword: str, country: str = 'us') -> dict:
    """Returns competition level based on rating counts of top-5 apps."""
    resp = requests.get(
        'https://itunes.apple.com/search',
        params={'term': keyword, 'entity': 'software', 'limit': 10, 'country': country},
        timeout=10
    )
    results = resp.json().get('results', [])[:5]
    if not results:
        return {'score': 0, 'level': 'unknown'}
    counts = [r.get('userRatingCount', 0) for r in results]
    avg_log = sum(math.log10(c + 1) for c in counts) / len(counts)
    # avg_log: <2 = LOW, 2–3 = MEDIUM, >3 = HIGH
    level = 'LOW' if avg_log < 2 else ('MEDIUM' if avg_log < 3 else 'HIGH')
    return {
        'keyword': keyword, 'country': country,
        'avg_log_ratings': round(avg_log, 2),
        'top5_ratings': counts,
        'level': level,
        'top5_names': [r.get('trackName', '') for r in results]
    }

# Пример
print(competition_score('food scanner', 'us'))
```

| avg_log | Level | Интерпретация |
|---------|-------|---------------|
| < 2 | LOW | Топ-5 малоизвестны (< 100 отзывов avg) — конкурировать реально |
| 2–3 | MEDIUM | Топ-5 умеренные (100–1000 отзывов) — нужен quality signal |
| > 3 | HIGH | Топ-5 сильные (> 1000 отзывов) — без накопленных поведенческих сигналов не пробиться |

Дополнительный сигнал: **если в топ-5 есть бренды конкурентов** — keyword branded, органический ранк без brand equity крайне сложен.

**Итоговая оценка ключа:**

```
| Keyword       | Popularity | Competition | ASA CR | Приоритет |
|---------------|-----------|-------------|--------|-----------|
| gluten scan   | 35        | LOW         | 4.2%   | HIGH      |
| food scanner  | 55        | HIGH        | 1.8%   | LOW       |
| e numbers     | 22        | MEDIUM      | 3.5%   | MEDIUM    |
```

Приоритет = HIGH когда: popularity ≥ 20 + Competition LOW/MEDIUM + ASA CR > 2%.

### 5. Обязательный keyword discovery для каждой активной локали

При каждом вызове скилла — исследуй новые ключи. Не полагайся только на `keywords.txt`.

**Шаг 5.1 — Apple Search Hints (гео-точный, без авторизации)**

Запускать для каждой локали отдельно. Подавать ПРЕФИКС, не полное слово.

```bash
# US (основная локаль)
python3 ~/.claude/skills/aso-monitoring/scripts/keyword_suggest.py \
  --term "food scan" --country us

# DE (если активна немецкая локаль)
python3 ~/.claude/skills/aso-monitoring/scripts/keyword_suggest.py \
  --term "lebens scan" --country de

# Несколько сидов сразу
python3 ~/.claude/skills/aso-monitoring/scripts/keyword_suggest.py \
  --seeds "food check,ingredient scan,allergy" --country us
```

Tier HIGH = позиция 1–5 в autocomplete. Чем выше тир — тем чаще вводят в данном сторефронте.

**Источники сидов для discovery (по порядку):**
1. Текущие токены title/subtitle нашего приложения
2. Title и subtitle конкурентов из `competitors.txt`
3. Search terms из ASA с installs > 0 (шаг 2)
4. Смежные ниши и глаголы-механики приложения

**Шаг 5.2 — ASA Popularity (требует kuки)**

```bash
python3 ~/.claude/skills/aso-monitoring/scripts/asa/keyword_popularity.py \
  --seeds "keyword1,keyword2,keyword3" \
  --storefronts US,GB,DE \
  --out ./ASO/aso-monitoring/data/keywords/popularity_{date}.csv
```

Cookie истекает ~24ч. При 401 → обновить `APPLE_SA_COOKIE` в `~/.config/aso-tools/api_keys.env`.

**Пороги popularity:**

⚠️ `searchPopularity` из ASA API ненадёжен для non-US рынков — не использовать как основной фильтр. Ориентир для keyword field / title — присутствие в hints и ASA impressions из реальной кампании. Popularity-score использовать только как вспомогательный сигнал при US-стор.

**⚠️ Ограничения:**

| Инструмент | Что измеряет | Ограничение |
|-----------|-------------|-------------|
| Hints | Относительную частоту в данном сторефронте | Нет абсолютного объёма |
| ASA Popularity | Глобальный объём | Не учитывает гео; pop=5 в DE может быть реальным |

Единственный достоверный сигнал объёма — impressions в реальной кампании с правильным бидом.

**Шаг 5.3 — Отсев кандидатов**

⚠️ `searchPopularity` из ASA API **не использовать как фильтр**: метрика сломана — не передаёт параметр страны, возвращает глобальные/US-biased данные для всех рынков. Для DE/AT/CH/GB показывает одинаковые `2–3` у всех ключей.

Реальный сигнал объёма — наличие ключа в hints/autocomplete:
- Ключ появляется в autocomplete при вводе первых 3-4 символов в нужном сторфронте → есть реальный органический спрос
- Ключа нет в hints → органический объём < 5-10 запросов в день; ASA может давать impressions (paid), но органики не будет

Финальная фильтрация каждого нового ключа:
1. **Hints: ключ присутствует** в autocomplete нужного сторфронта (это первичный фильтр объёма)
2. Competition ≤ MEDIUM
3. ASA CR > 2% (если уже тестировался), или нет ASA-данных
4. Нет дубля с существующими токенами title + subtitle
5. Релевантен: результаты autocomplete по этому префиксу совпадают с нашей нишей

**Обнови `./ASO/config/keywords.txt`** — добавь новые кандидаты с пометкой `# candidate {date}`.

### 6. Проверь изменения у конкурентов

```bash
python3 ~/.claude/skills/aso-monitoring/scripts/collect_profiles.py \
  --project ./ASO/aso-monitoring \
  --app-ids $(grep -v '#' ./ASO/config/competitors.txt | awk '{print $1}' | tr '\n' ' ')
```

Фиксируй **только изменения** относительно предыдущей сессии:
- Кто обновил title или subtitle?
- Новые токены в title конкурентов → кандидаты для нашего KF (если в нашей нише)
- Аномальный рост рейтингов = активная рекламная кампания

### 7. Собери метрики App Store Connect (раз в 7 дней)

```bash
python3 ~/.claude/skills/aso-monitoring/scripts/asc_fetch_metrics.py \
  --project ./ASO/aso-monitoring \
  --since {дата_последнего_мониторинга}
```

Что смотреть:
- impressions → pageViews → installs: снижение на любом этапе = проблема с иконкой/title/скриншотами
- Органические установки = appUnits минус ASA installs

Рейтинг приложения:
```bash
curl "https://itunes.apple.com/lookup?id={app_id}&country={cc}&entity=software" | \
  python3 -c "import json,sys; d=json.load(sys.stdin)['results'][0]; print(d['userRatingCount'], d['averageUserRating'])"
```

Если avg rating < 3.7 → review prompting — приоритет перед изменением metadata.

### 8. Сформируй рекомендации

Каждая рекомендация по metadata — с обязательным обоснованием:

```
Текущий title:    "Food Screener: AI Ingredient Check"
Предлагаемый:     "Food Scanner: AI Ingredient & Allergy"
Добавляем:        "allergy" — popularity 28, Competition LOW, Hints HIGH/US, нет в KF конкурентов
ASA-сигнал:       нет данных, но search terms: "allergy scanner" — 2 installs органически
```

Каждая рекомендация должна иметь маркер:
- ✓ Подтверждён ASA (impressions > 50, CR > 3%)
- ✓ Подтверждён search terms (реальные запросы с installs)
- ~ Нет ASA-данных, popularity ≥ 20, Competition LOW
- ✗ Не добавлять: ASA CR < 2% при > 50 impressions (semantic mismatch)

**Принцип составления keyword field:**

Apple индексирует фразы из комбинаций токенов разных полей.

1. Фиксировать токены title + subtitle
2. Для каждой ценной фразы — найти минимальный токен для KF (не дублировать то, что уже есть)
3. Проверить через Hints что токен релевантен нише
4. Проверить ASA CR или search terms
5. Убедиться: нет дублей с title/subtitle

**Не применять изменения без подтверждения пользователя.**

После согласования — добавь строку в `./ASO/aso-monitoring/data/metadata_changes.csv`:

```python
import csv, os
from datetime import date

ROW = {
    'locale': 'de',
    'field': 'title',          # title / subtitle / keywords
    'was': 'старое значение',
    'becomes': 'новое значение',
    'status': 'recommended',   # recommended → submitted → live → verified
    'date_recommended': date.today().isoformat(),
    'date_submitted': '',
    'date_live': '',
    'positions_verified': '',
}

path = './ASO/aso-monitoring/data/metadata_changes.csv'
write_header = not os.path.exists(path)
with open(path, 'a', newline='') as f:
    w = csv.DictWriter(f, fieldnames=ROW.keys())
    if write_header:
        w.writeheader()
    w.writerow(ROW)
```

Статусы: `recommended` → `submitted` → `live` → `verified`

### 9. Сохрани popularity кандидатов в CSV

После каждого discovery — сохрани результаты как append в накопительный файл:

```bash
# --out дописывает в существующий файл или создаёт новый с header
python3 ~/.claude/skills/aso-monitoring/scripts/asa/keyword_popularity.py \
  --seeds "keyword1,keyword2" \
  --storefronts DE \
  --out ./ASO/aso-monitoring/data/keywords/popularity_de.csv
```

Формат: `keyword, popularity, storefront, collected_date` — дата в каждой строке, файл накапливается.

### 10. Планируй A/B тест если меняешь скриншоты

A/B тест через PPO: одна переменная, 50/50 трафик, минимум 7 дней, ждать 90% confidence.
Тестировать нельзя: title, subtitle, keywords — только icon, screenshots, preview video.

## Правила анализа

- Позиция меняется медленно — значимое движение за 2–4 недели
- После обновления metadata ждать 1–2 недели до переиндексации
- Keyword field: без пробелов после запятых, без дублей из title/subtitle
- Apple Search Hints: подавать PREFIX ("food scan", не "food scanner")
- При необъяснимом падении позиций: сначала проверить конкурентов
- Если < 2 недель с момента "в сторе" — позиции ещё меняются, не делать выводов
