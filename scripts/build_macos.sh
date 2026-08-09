#!/usr/bin/env bash
# ============================================================
#  macOS 一键打包:生成 TestCaseAgent.dmg 安装镜像
#  用法:在 macOS 上执行  bash scripts/build_macos.sh
#  前置:已安装 Python 3.10+ 与项目依赖(pip install -r requirements.txt)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/5] 生成应用图标(icns)..."
mkdir -p assets
if [ ! -f assets/icon.icns ]; then
  python tools/make_icon.py
  # png -> iconset -> icns
  rm -rf assets/icon.iconset && mkdir -p assets/icon.iconset
  for s in 16 32 64 128 256 512; do
    sips -z "$s" "$s" assets/icon.png --out "assets/icon.iconset/icon_${s}x${s}.png" >/dev/null
    s2=$((s*2))
    sips -z "$s2" "$s2" assets/icon.png --out "assets/icon.iconset/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns assets/icon.iconset -o assets/icon.icns
  rm -rf assets/icon.iconset
fi

echo "[2/5] PyInstaller 打包为 .app(约 2~5 分钟)..."
python -m PyInstaller TestCaseAgent.spec --noconfirm --clean

echo "[3/5] 创建 DMG 目录..."
APP=dist/TestCaseAgent.app
DMG_DIR=dist/dmg_root
rm -rf "$DMG_DIR" && mkdir -p "$DMG_DIR"
cp -R "$APP" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications" 2>/dev/null || true

echo "[4/5] hdiutil 制作 DMG..."
DMG=dist/TestCaseAgent.dmg
rm -f "$DMG"
hdiutil create -volname "TestCaseAgent" -srcfolder "$DMG_DIR" -ov -format UDZO "$DMG" >/dev/null

echo "[5/5] 完成!"
echo "  安装镜像: dist/TestCaseAgent.dmg(双击挂载,拖入 Applications 即可安装)"
echo "  注:若需在他人 Mac 上运行,请另行执行 codesign 签名/公证"
