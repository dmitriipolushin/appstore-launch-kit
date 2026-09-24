# Скиллы

Семь наборов инструкций в двух направлениях. Полная маршрутизация — в [`../AGENTS.md`](../AGENTS.md).

### ASO — органический поиск

| Скилл | Задача | Нужны ключи |
|---|---|---|
| [`aso-collection`](aso-collection/) | Конкуренты → ключевые слова → метаданные → description. Основной рабочий процесс | Частично |
| [`app-store-screenshots`](app-store-screenshots/) | Методология и код генератора скриншотов | Нет |
| [`asc-metadata`](asc-metadata/) | Заливка метаданных через App Store Connect API | Да (`.p8`) |
| [`aso-monitoring`](aso-monitoring/) | Раз в 2–4 недели: позиции, keyword discovery, конкурентность, сверка с ASA, A/B-тесты скриншотов | Частично |
| [`app-store-optimization`](app-store-optimization/) | ASO-скор, A/B-планер, анализ отзывов, чеклист запуска | Нет |

### Apple Ads (Apple Search Ads) — реклама в поиске App Store

| Скилл | Задача | Нужны ключи |
|---|---|---|
| [`asa-launch`](asa-launch/) | Новая кампания через API: ключи, тематические кластеры, ставки, негативы, organic baseline | Да (Apple Ads API) |
| [`asa-monitoring`](asa-monitoring/) | Оптимизация работающих кампаний: метрики, триалы, Impression Share, gate-проверки, ставки и паузы, paid vs organic | Да (Apple Ads API, Amplitude MCP, ASC) |

Оба ASA-скилла используют общий тулкит [`../shared/asa/`](../shared/asa/). Они меняют
живые кампании и тратят бюджет, поэтому каждое действие в API выполняется только после
явного «да» пользователя.

---

## Пути внутри SKILL.md

Файлы `SKILL.md` написаны для установленных скиллов и содержат абсолютные пути вида `~/.claude/skills/aso-collection/scripts/...`.

**Читаешь из клона репозитория без установки** — подставляй `<репозиторий>/skills/` вместо `~/.claude/skills/`.

**Установить** (тогда пути станут верными):

```bash
../install.sh          # все семь скиллов, симлинками
../install.sh --check  # что установлено сейчас
```

Симлинки, а не копии — правки в репозитории подхватываются сразу.

---

## Зависимости

```bash
pip install requests python-dotenv PyJWT cryptography authlib pycryptodomex
```

`PyJWT` и `cryptography` — для `asc-metadata` (JWT ES256 для App Store Connect API); `authlib` и `pycryptodomex` — для Apple Ads API в ASA-скиллах.

Ключи: `cp ../config/api_keys.env.example ~/.config/aso-tools/api_keys.env` и заполнить. Что работает без ключей — в [`../AGENTS.md`](../AGENTS.md#ключи-и-внешние-сервисы).

---

## Актуальность

`aso-collection/knowledge/` — данные 2025–2026 с источниками и датами в каждом файле, это самый свежий слой.

`app-store-optimization/` — более старый набор (ноябрь 2025). Лимиты полей корректны, но требования к скриншотам и размерам могли устареть. При конфликте верить `aso-collection/knowledge/`.
