#!/bin/bash
set -e
cd "$(dirname "$0")"

APP_NAME="CodexSwitch"
SWIFT_DIR="Swift"
SOURCES="$SWIFT_DIR/Sources"
BUILD_OUT="/tmp/CodexSwitch_build"
DIST_APP="dist/$APP_NAME.app"
DIST_DMG="dist/$APP_NAME.dmg"

echo "==> 编译 Swift 源码（Universal Binary: arm64 + x86_64）..."
mkdir -p "$BUILD_OUT"

SRCS="$SOURCES/AppDelegate.swift $SOURCES/ContentView.swift $SOURCES/Manager.swift $SOURCES/VisualEffectView.swift"

swiftc -O -parse-as-library \
    -target arm64-apple-macos12.0 \
    -framework AppKit -framework SwiftUI \
    $SRCS \
    -o "$BUILD_OUT/${APP_NAME}_arm64"

swiftc -O -parse-as-library \
    -target x86_64-apple-macos12.0 \
    -framework AppKit -framework SwiftUI \
    $SRCS \
    -o "$BUILD_OUT/${APP_NAME}_x86_64"

lipo -create \
    "$BUILD_OUT/${APP_NAME}_arm64" \
    "$BUILD_OUT/${APP_NAME}_x86_64" \
    -output "$BUILD_OUT/$APP_NAME"

echo "    $(lipo -info "$BUILD_OUT/$APP_NAME")"

echo "==> 构建 .app 包结构..."
rm -rf "$DIST_APP"
mkdir -p "$DIST_APP/Contents/MacOS"
mkdir -p "$DIST_APP/Contents/Resources"

cp "$BUILD_OUT/$APP_NAME"     "$DIST_APP/Contents/MacOS/$APP_NAME"
cp "$SWIFT_DIR/Info.plist"    "$DIST_APP/Contents/Info.plist"
cp "assets/moonbridge"        "$DIST_APP/Contents/Resources/moonbridge"

# Icon
if [ -f "assets/icon.icns" ]; then
    cp "assets/icon.icns" "$DIST_APP/Contents/Resources/AppIcon.icns"
fi

chmod +x "$DIST_APP/Contents/MacOS/$APP_NAME"
chmod +x "$DIST_APP/Contents/Resources/moonbridge"

echo "==> Ad-hoc 签名..."
codesign --deep --force --sign - --options runtime "$DIST_APP" 2>&1
echo "    $(codesign -dv "$DIST_APP" 2>&1 | grep Signature)"

echo "==> 打包 .dmg..."
rm -f "$DIST_DMG"
mkdir -p dist
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DIST_APP" \
    -ov -format UDZO \
    "$DIST_DMG"

echo ""
echo "✓ 构建完成！"
echo "  .app  →  $DIST_APP"
echo "  .dmg  →  $DIST_DMG"
echo ""
echo "测试运行："
echo "  open $DIST_APP"
