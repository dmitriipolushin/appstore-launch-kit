---
name: ASA API — сниппеты для выполнения изменений
description: Готовые куски кода для bid raises, pauses, добавления ключей, создания кампаний. Читать перед шагом 5.
type: reference
---

# ASA API Сниппеты

## Инициализация

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / '.claude/skills/asa-monitoring/scripts'))
from env_setup import CONFIG_DIR
sys.path.insert(0, str(Path.home() / '.claude/skills/asa-monitoring/scripts/asa'))
from utils.asa_api import SearchAdsAPI

api = SearchAdsAPI.create()
```

## Верификация adgroup_id (всегда перед keyword операциями)

```python
# Для KT и AT/CH кампаний — adgroup_id в конфиге может не совпадать
real_ags = api.get_adgroups(campaign_id)
ag_id = real_ags[0]["id"]
```

## Bid raise

```python
# 1. Поднять ставку ключа
api.update_targeting_keywords(campaign_id, ag_id,
    [{"id": KW_ID, "bidAmount": {"amount": "1.50", "currency": "USD"}}])

# 2. Обновить adgroup default CPT bid = max keyword bid
api.update_adgroup(campaign_id, ag_id, cpc_bid=1.50, currency="USD")
```

### ⚠️ Массовое поднятие: цель считать от кабинета, не от конфига

Когда ставки поднимаются пачкой по десяткам адгрупп, прогон может оборваться
на середине — сеть, таймаут, 5xx от Apple. Дальше важен один вопрос: **что
произойдёт при повторном запуске?**

Если цель считается как «ставка из локального конфига + шаг», а конфиг успел
записаться частично — повторный запуск прибавит шаг ещё раз к уже поднятым
адгруппам. Шаг применится дважды, в кабинете будут ставки, которых никто не
согласовывал.

Три правила, которые это закрывают:

```python
# 1. Цель — от ФАКТИЧЕСКОЙ ставки в кабинете
live = {a["id"]: float(a["defaultBidAmount"]["amount"])
        for a in api.get_adgroups(campaign_id)}

for ag in adgroups:
    cur = live[ag["id"]]
    new = round(min(cur + STEP, BID_CEILING[geo]), 2)
    if abs(new - cur) < 1e-6:          # 2. уже применено — пропустить
        continue
    api.update_adgroup(campaign_id, ag["id"], cpc_bid=new, currency="USD")
    api.update_targeting_keywords(campaign_id, ag["id"],
        [{"id": ag["kw_id"], "bidAmount": {"amount": f"{new:.2f}", "currency": "USD"}}])
    ag["bid"] = new
    save_config(cfg)                    # 3. сохранять после КАЖДОЙ адгруппы
```

- **Цель от кабинета, а не от конфига** — повторный запуск идемпотентен.
- **Пропуск уже применённого** — сравнение с текущей ставкой, не слепой PUT.
- **Сохранение после каждой адгруппы**, а не после кампании — иначе обрыв
  теряет учёт по всей кампании и конфиг расходится с кабинетом.

Готовая реализация — `shared/asa/bids.py`, использовать её, а не писать заново:

```bash
python3 shared/asa/bids.py --project {путь_проекта} --step 0.30 --dry-run
python3 shared/asa/bids.py --project {путь_проекта} --step 0.30
```

Потолки берутся из `economics.by_geo.*.bid_ceiling` конфига проекта.

Плюс ретраи на сетевые обрывы: `api_call` в `shared/asa/utils/asa_api.py`
повторяет запрос лишь дважды и не различает типы ошибок, поэтому для батч-правок
оборачивай вызовы своим ретраем с нарастающей паузой.

> Источник правила: инцидент 2026-09-11 на проекте Songria. Обрыв соединения на
> третьей кампании из трёх; первые две успели записать конфиг, повторный прогон
> поднял им ставки второй раз — +$0.60 вместо +$0.30 по 46 адгруппам.
> Рабочая реализация: `scripts/asa_common.py` в папке того проекта.

## Пауза

```python
# Пауза кампании
api.update_campaign(campaign_id, status="PAUSED")

# Пауза ключа
api.update_targeting_keywords(campaign_id, ag_id,
    [{"id": KW_ID, "status": "PAUSED"}])
```

## Budget raise (только если spend ≥ 90% лимита)

```python
api.update_campaign(campaign_id, daily_budget=10.0, currency="USD")
```

## Добавить EXACT ключ

```python
api.add_targeting_keywords(campaign_id, ag_id,
    [{"text": "new keyword", "matchType": "EXACT",
      "bidAmount": {"amount": "1.30", "currency": "USD"}}])
# ⚠️ DUPLICATE_KEYWORD → ключ уже покрыт close variant'ом, новая кампания не нужна
```

## Negative keyword

```python
api.add_campaign_negative_keywords(campaign_id,
    [{"text": "junk term", "matchType": "EXACT"}])
```

## Создать новую кампанию

```python
from datetime import datetime

data = {
    "orgId": api.org_id,
    "name": "PS — keyword name",
    # Apple убрал lifetime/total budget для новых кампаний (июнь 2026) — только dailyBudgetAmount
    "dailyBudgetAmount": {"amount": "5.00", "currency": "USD"},
    "adamId": APP_ID,
    "countriesOrRegions": ["DE"],  # или ["AT"], ["CH"]
    "adChannelType": "SEARCH",
    "supplySources": ["APPSTORE_SEARCH_RESULTS"],
    "billingEvent": "TAPS",
}
camp = api.api_call("campaigns", json_data=data, method="POST")
camp_id = camp["data"]["id"]

ag = api.create_adgroup(
    campaign_id=camp_id, adgroup_name="Keywords", currency="USD",
    cpc_bid=BID, start_time=datetime.now(),
    automated_keywords_opt_in=False, device_class=["IPHONE", "IPAD"],
)
ag_id = ag["data"]["id"]

api.add_targeting_keywords(camp_id, ag_id,
    [{"text": "keyword", "matchType": "EXACT",
      "bidAmount": {"amount": str(BID), "currency": "USD"}}])
```

## Сохранение Amplitude trials в файл (для asa_analyze.py)

После получения ответа от mcp__Amplitude__query_dataset — сохранить в CSV:

```python
# Парсим ответ и сохраняем в amplitude_trials.csv
import csv, json

# raw_data — это data.csvResponse.data из ответа MCP
# Строки после заголовков: [campaign_id, total]
lines = []
for row in raw_data:
    if len(row) >= 2 and row[0] not in ('asa_campaign_id', '', None):
        cid = str(row[0]).strip()
        total = str(row[1]).strip() if len(row) > 1 else '0'
        if cid != '(none)':
            lines.append({'campaign_id': cid, 'trials': total})

with open('./ASA/asa-monitoring/data/amplitude_trials.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['campaign_id', 'trials'])
    w.writeheader()
    w.writerows(lines)
```

После этого `amplitude_trials.csv` готов для `asa_analyze.py`.

## IS отчёт — сохранение в файл (для asa_analyze.py)

```python
# После получения IS report — сохранить
with open('./ASA/asa-monitoring/data/is_report_latest.csv', 'w') as f:
    f.write(content)  # content — raw CSV из downloadUri
```

## Amplitude — триалы по campaign_id (обязательный шаг 3.2)

**Один вызов — все данные за 30 дней.** `project_id` — id проекта приложения в Amplitude
(его же передаём в `app`); спросить у пользователя или взять через `mcp__Amplitude__get_amplitude_context`.

```python
# Через mcp__Amplitude__query_dataset (требует подключённого MCP-сервера Amplitude)
# Если сервер не подключён — попросить пользователя выполнить /mcp в Claude Code

result = mcp__Amplitude__query_dataset(
    projectId="{amplitude_project_id}",
    groupByLimit=300,      # все campaign_id
    timeSeriesLimit=0,     # только totals, без daily разбивки
    definition={
        "type": "eventsSegmentation",
        "app": "{amplitude_project_id}",
        "name": "trial_started by asa_campaign_id — 30d",
        "params": {
            "range": "Last 30 Days",
            "events": [{"event_type": "trial_started", "filters": [], "group_by": []}],
            "metric": "totals",
            "countGroup": "User",
            "groupBy": [{"type": "user", "value": "gp:asa_campaign_id"}],
            "interval": 1,
            "segments": [{"conditions": []}]
        }
    }
)
# Ответ: CSV с колонками asa_campaign_id | Total
# Парсить: result → data.csvResponse.data → строки после заголовков
```

**Как читать результат:**
- `(none)` = органические пользователи (не из ASA)
- campaign_id → сопоставить с asa_metrics.csv по полю campaign_id
- Trials за 30d / Installs за 30d = Trial Rate (должен быть > 8%)
- Spend за 30d / Trials за 30d = CPTrial (должен быть < $20)

**⚠️ MCP не подключён** → попросить `/mcp` в Claude Code (подключается через UI).
После подключения сервер виден как `mcp__Amplitude__*` в deferred tools.

---

## IS-отчёт

```python
import urllib.request, csv, io, time

res = api.impression_share_reports(
    start_date='YYYY-MM-DD',
    end_date='YYYY-MM-DD',
    name='is_check_YYYYMMDD',
    granularity='DAILY',
)
report_id = res['id']

for _ in range(20):
    res = api.get_single_impression_share_report(report_id)
    if res['data'].get('downloadUri'):
        break
    time.sleep(5)

with urllib.request.urlopen(res['data']['downloadUri']) as f:
    content = f.read().decode('utf-8')
rows = list(csv.DictReader(io.StringIO(content)))
# Поля: date, appName, adamId, countryOrRegion, searchTerm,
#        lowImpressionShare, highImpressionShare, rank, searchPopularity
# IS avg = (low + high) / 2
# Raise bid только если IS avg < 90%
```
