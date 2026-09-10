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

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/skills"
SKILLS=(aso-collection aso-monitoring asa-launch asa-monitoring
        app-store-optimization app-store-screenshots asc-metadata)

mode="${1:---link}"
mkdir -p "$DEST"

case "$mode" in
  --check)
    for s in "${SKILLS[@]}"; do
      t="$DEST/$s"
      if   [ -L "$t" ]; then printf '  симлинк  %-26s → %s\n' "$s" "$(readlink "$t")"
      elif [ -d "$t" ]; then printf '  КОПИЯ    %-26s (разъедется — переустанови)\n' "$s"
      else                   printf '  нет      %-26s\n' "$s"; fi
    done
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

echo
echo "Готово. Проверка:  ./install.sh --check"
