#!/usr/bin/env bash
# Установка скиллов в ~/.claude/skills.
#
# По умолчанию — симлинки: правки в репозитории подхватываются сразу,
# копии не могут разъехаться. Общая база знаний лежит в knowledge/,
# внутри скиллов на неё стоят относительные симлинки — при копировании
# их обязательно нужно разыменовывать, иначе получатся битые ссылки.
#
#   ./install.sh           симлинки (рекомендуется)
#   ./install.sh --copy    копии с разыменованием симлинков
#   ./install.sh --check   только проверить текущее состояние
#
# Каждый режим в конце проверяет Python-зависимости (requirements.txt):
# какой python3 на машине их видит. Ничего не ставит — только подсказывает.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/skills"
SKILLS=(niche-analysis aso-collection aso-monitoring asa-launch asa-monitoring
        app-store-optimization app-store-screenshots asc-metadata)

mode="${1:---link}"
mkdir -p "$DEST"

# Python-зависимости скриптов. Модули — имена для import, не пакетов pip.
PY_MODULES=(requests dotenv authlib Cryptodome jwt cryptography)
check_python() {
  echo
  echo "Python-зависимости (requirements.txt):"
  local seen="" found="" cand real missing
  for cand in "${ASO_PYTHON:-}" python3 /usr/bin/python3 /opt/homebrew/bin/python3 \
              /usr/local/bin/python3 "$HOME/.venvs/aso/bin/python3"; do
    [ -n "$cand" ] || continue
    real="$(command -v "$cand" 2>/dev/null)" || continue
    real="$(cd "$(dirname "$real")" && pwd -P)/$(basename "$real")"
    case " $seen " in *" $real "*) continue ;; esac
    seen="$seen $real"
    missing="$("$real" - "${PY_MODULES[@]}" 2>/dev/null <<'PY'
import importlib, sys, warnings
warnings.simplefilter("ignore")
bad = []
for m in sys.argv[1:]:
    try:
        importlib.import_module(m)
    except Exception:
        bad.append(m)
print(" ".join(bad))
PY
)" || missing="(не запускается)"
    if [ -z "$missing" ]; then
      printf '  ✓ %-44s %s\n' "$cand" "$("$real" -c 'import platform; print(platform.python_version())')"
      [ -n "$found" ] || found="$cand"
    else
      printf '  ✗ %-44s нет: %s\n' "$cand" "$missing"
    fi
  done
  if [ -n "$found" ]; then
    echo "  → запускай скрипты через: $found"
  else
    echo "  → ни один python3 не видит зависимости. Установить:"
    echo "      python3 -m pip install --user -r $REPO/requirements.txt"
    echo "    Homebrew-python (PEP 668) — через venv:"
    echo "      python3 -m venv ~/.venvs/aso && ~/.venvs/aso/bin/pip install -r $REPO/requirements.txt"
  fi
}

case "$mode" in
  --check)
    for s in "${SKILLS[@]}"; do
      t="$DEST/$s"
      if   [ -L "$t" ]; then printf '  симлинк  %-26s → %s\n' "$s" "$(readlink "$t")"
      elif [ -d "$t" ]; then printf '  КОПИЯ    %-26s (разъедется — переустанови)\n' "$s"
      else                   printf '  нет      %-26s\n' "$s"; fi
    done
    check_python
    exit 0 ;;

  --link)
    for s in "${SKILLS[@]}"; do
      [ -d "$REPO/skills/$s" ] || { echo "  пропуск: $s нет в репозитории"; continue; }
      if [ -d "$DEST/$s" ] && [ ! -L "$DEST/$s" ]; then
        # Бэкап кладём ВНЕ ~/.claude/skills: любой каталог внутри неё
        # подхватывается Claude Code как отдельный скилл и засоряет список.
        bakdir="$HOME/.claude/skills-backup-$(date +%Y%m%d)"
        mkdir -p "$bakdir"
        mv "$DEST/$s" "$bakdir/$s"
        echo "  старая копия $s → $bakdir/$s"
      fi
      ln -sfn "$REPO/skills/$s" "$DEST/$s"
      echo "  симлинк: $s"
    done ;;

  --copy)
    for s in "${SKILLS[@]}"; do
      [ -d "$REPO/skills/$s" ] || continue
      rm -rf "$DEST/$s"
      # -L обязателен: разыменовывает симлинки на общий knowledge/
      cp -RL "$REPO/skills/$s" "$DEST/$s"
      echo "  копия: $s"
    done
    echo
    echo "  ⚠️  Копии расходятся с репозиторием. После правок запусти install.sh снова." ;;

  *) echo "Неизвестный режим: $mode"; exit 1 ;;
esac

check_python
echo
echo "Готово. Проверка:  ./install.sh --check"
