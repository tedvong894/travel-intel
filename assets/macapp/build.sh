#!/bin/bash
# 构建「全国旅游情报」原生 macOS App（可重复执行）
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="/Users/tedwong/Applications/全国旅游情报.app"
ICNS="$HERE/../app-icon.icns"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# 1. 编译二进制
xcrun swiftc -O -o "$APP/Contents/MacOS/travelintel" "$HERE/main.swift" \
  -framework Cocoa -framework WebKit

# 2. Info.plist
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>全国旅游情报</string>
  <key>CFBundleDisplayName</key><string>全国旅游情报</string>
  <key>CFBundleExecutable</key><string>travelintel</string>
  <key>CFBundleIdentifier</key><string>com.tedwong.travel-intel</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
PLIST

# 3. 图标
cp "$ICNS" "$APP/Contents/Resources/AppIcon.icns"

# 3b. 刷新脚本（供 App 内「立即刷新」调用）
cp "$HERE/../../refresh_via_actions.sh" "$APP/Contents/Resources/refresh_via_actions.sh"
chmod +x "$APP/Contents/Resources/refresh_via_actions.sh"

# 4. 签名 + 注册
codesign --force --deep --sign - "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP"
echo "[ok] 已构建: $APP"
