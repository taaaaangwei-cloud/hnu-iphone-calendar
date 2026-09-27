#!/bin/zsh
set -e
cd "${0:A:h}"
.venv/bin/hnu-calendar install-automation
echo "自动同步已启用。"
read "?按 Enter 关闭窗口。"

