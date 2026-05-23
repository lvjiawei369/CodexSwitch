#!/bin/bash
# build_dmg.sh — 制作带背景图、Applications 快捷方式和使用指南的安装 DMG
# 用法：
#   bash build_dmg.sh            → 菜单栏版 CodexSwitch.dmg
#   bash build_dmg.sh Window     → 窗口版   CodexSwitch-Window.dmg
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST="$SCRIPT_DIR/dist"
ASSETS="$SCRIPT_DIR/assets"

# 支持可选的变体后缀（如 "Window"）
VARIANT="${1:-}"
if [ -n "$VARIANT" ]; then
  APP_NAME="CodexSwitch-$VARIANT"
  BUILD_HINT="build_swift_window.sh"
else
  APP_NAME="CodexSwitch"
  BUILD_HINT="build_swift.sh"
fi

APP="$DIST/$APP_NAME.app"
DMG_FINAL="$DIST/$APP_NAME.dmg"
DMG_TMP="$DIST/${APP_NAME}_rw.dmg"

# ── 检查素材 ──────────────────────────────────────────────────────────────────
if [ ! -d "$APP" ]; then
  echo "ERROR: $APP not found. Run $BUILD_HINT first."
  exit 1
fi
if [ ! -f "$ASSETS/dmg_background.png" ]; then
  echo "Generating DMG assets..."
  python3 "$SCRIPT_DIR/make_dmg_assets.py"
fi

echo "==> Building installer DMG for $APP_NAME"

# ── 清理旧文件和残留挂载卷 ──────────────────────────────────────────────────
rm -f "$DMG_FINAL" "$DMG_TMP"
# 挂载点必须与最终卷名一致，否则 .DS_Store 里的背景图路径在用户机器上对不上
MOUNT_POINT="/Volumes/$APP_NAME"
# 清理可能残留的同名卷
hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
sleep 0.5

# ── 1. 创建可读写 DMG（足够大的临时盘） ──────────────────────────────────────
echo "--> Creating writable DMG..."
hdiutil create \
  -size 60m \
  -fs HFS+ \
  -volname "$APP_NAME" \
  -o "$DMG_TMP"

# ── 2. 挂载（用唯一挂载点，避免命名冲突） ──────────────────────────────────
echo "--> Mounting..."
hdiutil attach "$DMG_TMP" -readwrite -noverify -noautoopen -mountpoint "$MOUNT_POINT" > /dev/null
echo "    Mounted at: $MOUNT_POINT"

# ── 3. 复制内容 ───────────────────────────────────────────────────────────────
echo "--> Copying files..."
cp -R "$APP" "$MOUNT_POINT/"
cp "$ASSETS/使用指南.txt" "$MOUNT_POINT/"

# /Applications 快捷方式
ln -s /Applications "$MOUNT_POINT/Applications"

# 隐藏背景图文件夹
mkdir -p "$MOUNT_POINT/.background"
cp "$ASSETS/dmg_background.png" "$MOUNT_POINT/.background/background.png"

# ── 4. AppleScript 设置 Finder 窗口外观 ─────────────────────────────────────
echo "--> Configuring Finder window..."
# 逻辑坐标（1x）：窗口 600×400，图标区域上下留白
# 背景图 1142x780 @144dpi → 逻辑尺寸 571x390
# App icon 左侧 (130, 170)，Applications 右侧 (430, 170)，使用指南右下 (430, 310)
osascript - "$APP_NAME" << 'APPLESCRIPT'
on run argv
  set diskName to item 1 of argv   -- 卷名 = APP_NAME，与挂载点一致
  set bgFile to POSIX file ("/Volumes/" & diskName & "/.background/background.png")

  tell application "Finder"
    tell disk diskName
      open
      set current view of container window to icon view
      set toolbar visible of container window to false
      set statusbar visible of container window to false
      set the bounds of container window to {200, 120, 771, 510}

      set viewOptions to the icon view options of container window
      set arrangement of viewOptions to not arranged
      set icon size of viewOptions to 110
      set text size of viewOptions to 11
      set background picture of viewOptions to bgFile

      set position of item (diskName & ".app") to {130, 170}
      set position of item "Applications" to {430, 170}
      set position of item "使用指南.txt" to {430, 310}

      close
      open
      update without registering applications
      delay 3
      close
    end tell
  end tell
end run
APPLESCRIPT

echo "--> Finder window configured."

# ── 5. 隐藏 .background 文件夹（chflags 在 HFS+ 上可靠） ────────────────────
chflags hidden "$MOUNT_POINT/.background" 2>/dev/null || true

# DS_Store sync & 卸载
sync
sleep 2
# 先让 Finder 主动弹出，再 hdiutil detach；全失败也继续（convert 可在只读挂载下运行）
osascript -e "tell application \"Finder\" to try" \
           -e "  eject disk \"$APP_NAME\"" \
           -e "end try" 2>/dev/null || true
sleep 1
hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null \
  || hdiutil detach "$MOUNT_POINT" -force -quiet 2>/dev/null \
  || true
rmdir "$MOUNT_POINT" 2>/dev/null || true

# ── 6. 压缩为最终 UDZO DMG ───────────────────────────────────────────────────
echo "--> Compressing to final DMG..."
hdiutil convert "$DMG_TMP" \
  -format UDZO \
  -imagekey zlib-level=9 \
  -o "$DMG_FINAL"

# 再尝试一次 detach，然后删除临时 rw DMG（即使还挂载也可以删除文件）
hdiutil detach "$MOUNT_POINT" -force -quiet 2>/dev/null || true
rm -f "$DMG_TMP"

SIZE=$(du -sh "$DMG_FINAL" | cut -f1)
echo ""
echo "✓ Done!  $DMG_FINAL  ($SIZE)"
echo ""
echo "  Contents:"
echo "    $APP_NAME.app   — drag to Applications to install"
echo "    Applications/     — shortcut to /Applications"
echo "    使用指南.txt      — Chinese usage guide"
