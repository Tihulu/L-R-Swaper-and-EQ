#!/bin/zsh
set -euo pipefail

APP_NAME="L-R Swaper Mac"
DMG_NAME="L-R-Swaper-Mac-Standalone-Apple-Silicon"
VOL_NAME="L/R Swaper Mac"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/opt/homebrew/bin/python3.13"

cd "$ROOT_DIR"

echo "L/R Swaper Mac standalone DMG builder"
echo "===================================="
echo

if [ ! -x "$PYTHON" ]; then
  echo "Homebrew Python 3.13 was not found at:"
  echo "  $PYTHON"
  echo
  echo "Install build Python/Tk first:"
  echo "  brew install python@3.13 python-tk@3.13"
  exit 1
fi

echo "Checking Tkinter..."
"$PYTHON" - <<'PY'
import tkinter
root = tkinter.Tk()
root.withdraw()
root.destroy()
print("Tkinter OK")
PY

echo
echo "Creating clean build environment..."
rm -rf .venv build dist dmg_staging bundle_bin "${DMG_NAME}.dmg" "${DMG_NAME}-tmp.dmg"
"$PYTHON" -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-mac.txt pyinstaller

echo
echo "Preparing app icon..."
if [ ! -f "icons/lr-swaper-mac.icns" ]; then
  if command -v iconutil >/dev/null 2>&1 && [ -d "icons/LRSwaper.iconset" ]; then
    iconutil -c icns "icons/LRSwaper.iconset" -o "icons/lr-swaper-mac.icns"
  fi
fi

echo
echo "Preparing bundled SwitchAudioSource helper..."
mkdir -p bundle_bin
if command -v SwitchAudioSource >/dev/null 2>&1; then
  cp "$(command -v SwitchAudioSource)" bundle_bin/SwitchAudioSource
elif [ -x "/opt/homebrew/bin/SwitchAudioSource" ]; then
  cp "/opt/homebrew/bin/SwitchAudioSource" bundle_bin/SwitchAudioSource
elif [ -x "/usr/local/bin/SwitchAudioSource" ]; then
  cp "/usr/local/bin/SwitchAudioSource" bundle_bin/SwitchAudioSource
else
  cat > bundle_bin/SwitchAudioSource <<'SH'
#!/bin/zsh
echo "SwitchAudioSource helper is not installed. Run Install Required Audio Driver.command." >&2
exit 127
SH
fi
chmod +x bundle_bin/SwitchAudioSource

echo
echo "Building standalone .app..."
python -m PyInstaller \
  --windowed \
  --target-arch arm64 \
  --name "${APP_NAME}" \
  --icon "icons/lr-swaper-mac.icns" \
  --osx-bundle-identifier "com.lr-swaper.mac" \
  --add-binary "bundle_bin/SwitchAudioSource:." \
  --collect-all sounddevice \
  --collect-all numpy \
  lr_swaper_mac.py

echo
echo "Patching app privacy description..."
PLIST="dist/${APP_NAME}.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :NSMicrophoneUsageDescription" "$PLIST" >/dev/null 2>&1 || true
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string L/R Swaper Mac needs access to the BlackHole virtual audio input to process system audio locally. It does not record or upload audio." "$PLIST"

echo
echo "Ad-hoc signing app after Info.plist patch..."
codesign --force --deep --sign - "dist/${APP_NAME}.app" || true

echo
echo "Preparing DMG contents..."
mkdir -p dmg_staging
cp -R "dist/${APP_NAME}.app" dmg_staging/
cp "Install Required Audio Driver.command" dmg_staging/
cp "README-FIRST.txt" dmg_staging/
cp "PRIVACY-PERMISSION.txt" dmg_staging/
ln -s /Applications dmg_staging/Applications

echo
echo "Creating DMG..."
hdiutil create \
  -volname "${VOL_NAME}" \
  -srcfolder dmg_staging \
  -ov \
  -format UDRW \
  "${DMG_NAME}-tmp.dmg"

hdiutil convert "${DMG_NAME}-tmp.dmg" \
  -format UDZO \
  -imagekey zlib-level=9 \
  -o "${DMG_NAME}.dmg"

rm -f "${DMG_NAME}-tmp.dmg"
rm -rf dmg_staging

echo
echo "Done:"
echo "  ${ROOT_DIR}/${DMG_NAME}.dmg"
echo
echo "If macOS blocks it:"
echo "  Right-click app -> Open"
echo "or:"
echo "  System Settings -> Privacy & Security -> Open Anyway"
