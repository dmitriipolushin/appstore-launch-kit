# App Store Launch Kit

Инструменты для заполнения данных приложения в App Store: метаданные, скриншоты, прохождение модерации.

Собрано из практики [Студии Along](https://t.me/alongapps) — десятки опубликованных подписочных приложений.

---

## 🤖 Если вы AI-агент

**Читайте [`AGENTS.md`](AGENTS.md)** — там маршрутизация по задачам, порядок шагов и правила, которые нельзя нарушать. Не начинайте работу, не прочитав его.

## 👤 Если вы человек

Дайте ссылку на этот репозиторий вашему AI-агенту (Claude Code, Cursor, Codex) и скажите, что нужно сделать. Например:

> Вот репозиторий с инструментами для App Store: `https://github.com/dmitriipolushin/appstore-launch-kit`. Прочитай AGENTS.md. Мне нужно собрать метаданные для нового приложения — трекер привычек, рынок США.

> Прочитай AGENTS.md в `https://github.com/dmitriipolushin/appstore-launch-kit`. Сделай скриншоты для App Store: мои скриншоты приложения лежат в `./screenshots`, иконка в `./icon.png`, стиль — тёмный минимализм.

> Прочитай `https://github.com/dmitriipolushin/appstore-launch-kit/blob/main/docs/app-store-review-guide.md`. Я получил reject по Guideline 2.3.2, вот текст письма — помоги разобраться.

---

## Что внутри

| | Что делает |
|---|---|
| **[docs/app-store-review-guide.md](docs/app-store-review-guide.md)** | Как быстро пройти модерацию: что готовить до отправки, из-за чего реджектят, что делать с реджектом, шаблон поля Notes |
| **[skills/aso-collection](skills/aso-collection/)** | Главный рабочий процесс: конкуренты → ключевые слова → Search Popularity → метаданные → description. Плюс knowledge-база из 8 файлов по алгоритму App Store |
| **[skills/app-store-screenshots](skills/app-store-screenshots/)** | Методология скриншотов: копирайтинг заголовков, структура слайдов, экспортные размеры Apple, промеренный макет iPhone |
| **[skills/asc-metadata](skills/asc-metadata/)** | Заливка метаданных в App Store Connect через официальный API — все локали, обход подводных камней |
| **[skills/app-store-optimization](skills/app-store-optimization/)** | Автономные скрипты: ASO-скор, планировщик A/B-тестов, анализ отзывов, чеклист запуска |
| **[examples/screenshots-generator](examples/screenshots-generator/)** | Рабочий генератор скриншотов на Next.js — 4 локали, экспорт в PNG под размеры Apple. Референс кода, а не заготовка |

---

## Установка как скиллы Claude Code

Скиллы можно подключить, чтобы они вызывались как `/aso-collection`, `/app-store-screenshots` и так далее:

```bash
git clone git@github.com:dmitriipolushin/appstore-launch-kit.git && cd appstore-launch-kit
for s in aso-collection app-store-optimization app-store-screenshots asc-metadata; do
  ln -sfn "$PWD/skills/$s" ~/.claude/skills/$s
done
```

Симлинки, а не копии — обновления в репозитории подхватываются сразу.

### Ключи для aso-collection

Внешние ключи нужны **только** части `aso-collection`. Всё остальное работает без них.

```bash
cp config/api_keys.env.example ~/.config/aso-tools/api_keys.env
# заполнить APPSTORESPY_API_KEY, APPLE_SA_COOKIE, APPLE_SA_XSRF
pip install requests python-dotenv PyJWT cryptography
```

Без ключей всё равно работают: профили и отзывы конкурентов через iTunes API, Apple Search Hints, позиции в поиске, вся методология и knowledge-база. Не работает: Search Popularity (0–100) и subtitle конкурентов.

---

## Порядок работы

Шаги зависят друг от друга — ключевые слова нужны и для description, и для текста на скриншотах (Apple индексирует подписи к скриншотам с июня 2025).

```
ASO-исследование → метаданные → description → скриншоты → заливка в ASC → модерация
```

Подробно — в [AGENTS.md](AGENTS.md#полный-маршрут-запуска-приложения).

---

## Оговорка

Требования Apple меняются. Данные в knowledge-базе актуальны на 2025–2026 и снабжены источниками и датами, но перед крупным запуском проверяйте текущие требования в документации Apple. Если что-то в репозитории выглядит устаревшим — так, вероятно, и есть.

`skills/app-store-screenshots` — из [ParthJadhav/app-store-screenshots](https://github.com/ParthJadhav/app-store-screenshots), MIT, лицензия сохранена в директории.
