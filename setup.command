#!/bin/zsh
set -e
cd "${0:A:h}"
python3 -m venv .venv
.venv/bin/python -m pip install -e .
[[ -f config.json ]] || cp config.example.json config.json
echo "安装完成。下一步双击 login.command。"
read "?按 Enter 关闭窗口。"

