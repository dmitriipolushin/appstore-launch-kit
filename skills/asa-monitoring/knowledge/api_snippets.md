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

## Ставка и статус Discovery (Search Match)

У Discovery нет targeting-ключей: ставка — это `defaultBidAmount` адгруппы.

```python
# Ставка Discovery — Search Match не трогается
api.update_adgroup(campaign_id, DISCOVERY_AG_ID, cpc_bid=0.70, currency="USD")

# Включить / выключить адгруппу (Discovery на паузе — расход гео может упасть до нуля)
api.api_call(f"campaigns/{campaign_id}/adgroups/{DISCOVERY_AG_ID}",
             json_data={"status": "ENABLED"}, method="PUT")
```

⚠️ `update_adgroup` шлёт PUT только с переданными полями. `automated_keywords_opt_in`
передавать **только** когда Search Match включается или выключается намеренно.
До 2026-10-07 этот параметр по умолчанию был `False`, и любая правка ставки
Discovery через обёртку молча выключала Search Match. Сейчас дефолт `None` — поле
не отправляется. Если работаешь со старой копией `asa_api.py` или пишешь PUT руками —
не клади `automatedKeywordsOptIn` в тело запроса.

После правки — перечитать адгруппу и проверить `automatedKeywordsOptIn == True` у Discovery.

### ⚠️ Массовое поднятие: цель считать от кабинета, не от конфига

Когда ставки поднимаются пачкой по десяткам адгрупп, прогон может оборваться
на середине — сеть, таймаут, 5xx от Apple. Дальше важен один вопрос: **что
произойдёт при повторном запуске?**

Если цель считается как «ставка из локального конфига + шаг», а конфиг успел
записаться частично — повторный запуск прибавит шаг ещё раз к уже поднятым
адгруппам. Шаг применится дважды, в кабинете будут ставки, которых никто не
согласовывал.

Правила, которые это закрывают:

- **Цель — от фактической ставки КЛЮЧА в кабинете**, не от конфига и не от default bid адгруппы.
- **План прогона пишется до первой записи** (было → станет по каждому ключу) и
  статус обновляется после каждого ключа. Повторный запуск продолжает ЭТОТ план:
  ключ уже на цели пропускается, на базе — применяется, иначе — конфликт (ставку
  меняли руками) и пропуск. Шаг второй раз не прибавляется.
- **Только вверх.** Массовая правка никогда не понижает ставку. Понижение — отдельное
  точечное решение по GATE 3, не побочный эффект шага.
- **Только ACTIVE-ключи** в ENABLED-адгруппах ENABLED-кампаний. Не «первый ключ
  адгруппы»: он может быть PAUSED.
- **Default bid адгруппы** подтягивается до ставки ключа, только вверх, без
  `automatedKeywordsOptIn` в теле.
- **Потолок не обрезает ставку.** `economics.by_geo.*.bid_ceiling` — ориентир
  (см. `decision_gates.md`, «Потолок ставки»): отчёт показывает его рядом с
  фактическим CPT и помечает `CPT > потолка`. Жёсткий предел — только явный `--max-bid`.

```python
# Суть — не копировать, использовать scripts/asa/bids.py
for kw in active_keywords:                     # status == ACTIVE, адгруппа ENABLED
    new = round(kw.bid + STEP, 2)
    if MAX_BID is not None:
        new = min(new, MAX_BID)                # только если пользователь задал предел
    if new <= kw.bid:                          # никогда не понижаем
        continue
    plan.append((kw, kw.bid, new))             # пишется в data/bid_runs/ ДО записи
```

Готовая реализация — `scripts/asa/bids.py` (в репозитории — `shared/asa/bids.py`), использовать её, а не писать заново:

```bash
# отчёт без изменений: ставка, потолок, фактический CPT за 7 дней, флаги
python3 ~/.claude/skills/asa-monitoring/scripts/asa/bids.py --project {путь_проекта} --report
# ежедневный подъём ключей без показов (bid discovery): +$0.20 тем, у кого 0 показов вчера
python3 ~/.claude/skills/asa-monitoring/scripts/asa/bids.py --project {путь_проекта} --step 0.20 --ramp-zero-impressions --dry-run
python3 ~/.claude/skills/asa-monitoring/scripts/asa/bids.py --project {путь_проекта} --step 0.20 --ramp-zero-impressions
# шаг всем ACTIVE-ключам гео, с явным жёстким пределом
python3 ~/.claude/skills/asa-monitoring/scripts/asa/bids.py --project {путь_проекта} --step 0.30 --geos CH --max-bid 4.00
```

`--ramp-zero-impressions --days N` поднимает только ключи с 0 показов за N полных дней
(UTC, до вчера включительно); ключи, созданные внутри окна, ждут следующего дня.
В отчёте — кандидаты на паузу: 0 показов 3+ дня при ставке ≥ потолка (или ≥ `--max-bid`).
Паузу модуль не ставит — это решение пользователя по GATE 3.

Повторный запуск в тот же день с теми же параметрами продолжает план из
`data/bid_runs/<дата>_<режим>_step<шаг>_<гео>.json`; ещё один шаг в тот же день — `--new-run`.

`api_call` в `shared/asa/utils/asa_api.py` ходит с таймаутом 60 с и повторяет только
чтение (GET, `reports/*`, `*/find`) на обрыв, таймаут, 429 и 5xx. Запись (POST/PUT/DELETE)
делается одной попыткой: таймаут записи — ошибка «запись могла примениться, перечитай
кабинет», а не слепой повтор. Клиент `bids.ASA` ретраит и записи — он сверяет цель
с кабинетом, поэтому повтор там безопасен; для своих батч-правок бери его.

> Источник правила: инцидент 2026-09-11 на реальном проекте. Обрыв соединения на
> третьей кампании из трёх; первые две успели записать конфиг, повторный прогон
> поднял им ставки второй раз — +$0.60 вместо +$0.30 по 46 адгруппам.
> Рабочая реализация — `scripts/asa/bids.py` (скриптов в папках проектов нет).

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

## Новые ключи и тест BROAD

По умолчанию — EXACT, архитектура «1 ключ = 1 адгруппа», старт $0.80, подъём ключей без
показов — `bids.py --step 0.20 --ramp-zero-impressions`, раз в день. BROAD — только как
согласованный тест (`asa_campaign_architecture.md` → «BROAD — только как отдельный тест»,
GATE 4): отдельная адгруппа рядом с EXACT, EXACT-негативы всех прочих ключей кампании
и тематические BROAD-негативы на уровне адгруппы (не кампании: кампанийный BROAD-негатив
`stimme` заблокировал бы собственный ключ `stimme klonen`). Всё — только после «да»
пользователя на конкретный список ключей, ставок и негативов.

```python
START_BID = 0.80
# Тематические BROAD-негативы для BROAD-адгрупп — список согласовать с пользователем.
# Пусто по умолчанию: это чужой интент, который BROAD-ключи начинают ловить, — свой
# у каждой ниши. Пример для музыкального приложения: ["stimme", "garageband", "fl studio"].
THEMATIC_BROAD_NEGATIVES = []


def add_keyword_adgroup(api, campaign_id, text, bid=START_BID, match_type="EXACT"):
    """Адгруппа + один ключ. EXACT по умолчанию; "BROAD" — только для согласованного теста.

    Повторно не создаёт: имя адгруппы уникально в кампании. У BROAD своё имя
    `<фраза> (broad)`, поэтому он встаёт рядом с EXACT-близнецом, а не вместо него.
    """
    assert match_type in ("EXACT", "BROAD")
    name = text if match_type == "EXACT" else f"{text} (broad)"
    if any(a["name"] == name for a in api.get_adgroups(campaign_id)):
        return None
    ag = api.create_adgroup(campaign_id=campaign_id, adgroup_name=name, currency="USD",
                            cpc_bid=bid, automated_keywords_opt_in=False,
                            device_class=["IPHONE"])          # старт — сейчас, UTC
    ag_id = ag["data"]["id"]
    api.add_targeting_keywords(campaign_id, ag_id, [{
        "text": text, "matchType": match_type,
        "bidAmount": {"amount": f"{bid:.2f}", "currency": "USD"}}])
    return ag_id


def blocks(negative, keyword):
    """BROAD-негатив блокирует запрос, содержащий все его слова (в любом порядке)."""
    return set(negative.lower().split()) <= set(keyword.lower().split())


def sync_broad_negatives(api, campaign_id, thematic=THEMATIC_BROAD_NEGATIVES, dry_run=True):
    """Идемпотентно доводит негативы всех ENABLED BROAD-адгрупп кампании до правила.

    EXACT-негативы — тексты ACTIVE-ключей всех ДРУГИХ адгрупп, включая EXACT-близнеца
    той же фразы: точный запрос должен уходить в свою EXACT-адгруппу. Запускать после
    каждого добавления ключей в кампанию. Негативы ключей, поставленных на паузу,
    не снимает — это отдельное решение. Без BROAD-адгрупп ничего не делает.
    """
    ags = [a for a in api.get_adgroups(campaign_id)
           if a["status"] == "ENABLED" and not a.get("deleted")]
    kws = {a["id"]: [k for k in api.get_targeting_keywords(campaign_id, a["id"])
                     if k["status"] == "ACTIVE" and not k.get("deleted")] for a in ags}
    plan = {}
    for a in ags:
        own = [k["text"].lower() for k in kws[a["id"]] if k["matchType"] == "BROAD"]
        if not own:
            continue
        others = {k["text"].lower() for b, ks in kws.items() if b != a["id"] for k in ks}
        have = {(n["text"].lower(), n["matchType"])
                for n in api.get_adgroup_negative_keywords(campaign_id, a["id"])["data"]
                if not n.get("deleted") and n.get("status") == "ACTIVE"}
        want = [(t, "EXACT") for t in sorted(others)]
        want += [(t.lower(), "BROAD") for t in thematic
                 if not any(blocks(t, o) for o in own)]      # свой ключ не блокируем
        add = [{"text": t, "matchType": m} for t, m in want if (t, m) not in have]
        if add:
            plan[a["name"]] = add
            if not dry_run:
                api.add_adgroup_negative_keywords(campaign_id, a["id"], add)
    return plan        # {адгруппа: [негативы к добавлению]} — показать пользователю


# Обычные новые ключи:
# for kw in new_keywords: add_keyword_adgroup(api, CAMPAIGN_ID, kw)
# print(sync_broad_negatives(api, CAMPAIGN_ID))                  # если в кампании идёт тест BROAD
#
# Тест BROAD (после «да» на план из GATE 4):
# add_keyword_adgroup(api, CAMPAIGN_ID, "<фраза из 3+ слов>", match_type="BROAD")
# print(sync_broad_negatives(api, CAMPAIGN_ID))                  # план негативов
# sync_broad_negatives(api, CAMPAIGN_ID, dry_run=False)          # после «да»
```

## Negative keyword

```python
api.add_campaign_negative_keywords(campaign_id,
    [{"text": "junk term", "matchType": "EXACT"}])
```

## Создать новую кампанию

```python
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
    cpc_bid=BID,   # start_time по умолчанию — сейчас, UTC; наивное datetime → ValueError
    automated_keywords_opt_in=False, device_class=["IPHONE", "IPAD"],
)   # targetingDimensions = только переданные измерения (здесь deviceClass)
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
