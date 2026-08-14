# Скиллы

Четыре набора инструкций. Полная маршрутизация — в [`../AGENTS.md`](../AGENTS.md).

| Скилл | Задача | Нужны ключи |
|---|---|---|
| [`aso-collection`](aso-collection/) | Конкуренты → ключевые слова → метаданные → description. Основной рабочий процесс | Частично |
| [`app-store-screenshots`](app-store-screenshots/) | Методология и код генератора скриншотов | Нет |
| [`asc-metadata`](asc-metadata/) | Заливка метаданных через App Store Connect API | Да (`.p8`) |
| [`app-store-optimization`](app-store-optimization/) | ASO-скор, A/B-планер, анализ отзывов, чеклист запуска | Нет |

---

## Пути внутри SKILL.md

Файлы `SKILL.md` написаны для установленных скиллов и содержат абсолютные пути вида `~/.claude/skills/aso-collection/scripts/...`.

**Читаешь из клона репозитория без установки** — подставляй `<репозиторий>/skills/` вместо `~/.claude/skills/`.

**Установить** (тогда пути станут верными):

```bash
for s in aso-collection app-store-optimization app-store-screenshots asc-metadata; do
  ln -sfn "$PWD/$s" ~/.claude/skills/$s
done
```

Запускать из этой директории. Симлинки, а не копии — правки в репозитории подхватываются сразу.

---

## Зависимости

```bash
pip install requests python-dotenv PyJWT cryptography
```

`PyJWT` и `cryptography` нужны только для `asc-metadata` (JWT ES256 для App Store Connect API).

Ключи: `cp ../config/api_keys.env.example ~/.config/aso-tools/api_keys.env` и заполнить. Что работает без ключей — в [`../AGENTS.md`](../AGENTS.md#ключи-и-внешние-сервисы).

---

## Актуальность

`aso-collection/knowledge/` — данные 2025–2026 с источниками и датами в каждом файле, это самый свежий слой.

`app-store-optimization/` — более старый набор (ноябрь 2025). Лимиты полей корректны, но требования к скриншотам и размерам могли устареть. При конфликте верить `aso-collection/knowledge/`.
