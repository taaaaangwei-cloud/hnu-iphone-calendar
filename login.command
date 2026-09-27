#!/bin/zsh
set -e
cd "${0:A:h}"
.venv/bin/hnu-calendar login
echo "登录完成。下一步双击 sync.command。"
read "?按 Enter 关闭窗口。"

