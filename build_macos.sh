#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "==> 检查依赖..."
if ! command -v python3 &>/dev/null; then
    echo "✗ 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

echo "==> 生成图标..."
pip3 install pillow --quiet
python3 make_icon.py

echo "==> 安装 PyInstaller..."
pip3 install pyinstaller --quiet

echo "==> 构建 macOS .app..."
pyinstaller --clean --noconfirm CodexSwitch.spec

echo "==> 打包为 .dmg..."
rm -f dist/CodexSwitch.dmg
hdiutil create \
    -volname "CodexSwitch" \
    -srcfolder dist/CodexSwitch.app \
    -ov -format UDZO \
    dist/CodexSwitch.dmg

echo ""
echo "✓ 构建完成！"
echo "  .app  →  dist/CodexSwitch.app"
echo "  .dmg  →  dist/CodexSwitch.dmg"
echo ""
echo "分发说明："
echo "  将 dist/CodexSwitch.dmg 发给其他人"
echo "  对方打开 DMG，把 CodexSwitch.app 拖到 Applications 即可使用"
echo ""
echo "注意：其他人还需要自行安装 Go 和 Codex CLI（App 内有引导）"
