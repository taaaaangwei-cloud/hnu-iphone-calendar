#!/bin/zsh
set -e
cd "${0:A:h}"
.venv/bin/hnu-calendar sync
echo "同步完成。"
read "?按 Enter 关闭窗口。"

