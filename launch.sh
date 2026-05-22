#!/bin/bash
# CodexSwitch 启动器
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 使用绝对路径绕过 macOS Python Launcher
PYTHON=/usr/local/bin/python3
if [ ! -x "$PYTHON" ]; then
    PYTHON=$(which python3)
fi
exec "$PYTHON" "$SCRIPT_DIR/codex_switch.py"
