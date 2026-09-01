#!/bin/bash
# Build CheckPrinter.app - a double-clickable Mac app icon that launches
# CheckPrinter from this project's local environment.
#
# Run once (and again if you move the project):  ./build_app.sh
set -e
cd "$(dirname "$0")"
PROJECT="$(pwd)"
APP="$PROJECT/CheckPrinter.app"

echo "Building icon..."
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" -c "import PIL" 2>/dev/null || "$PY" -m pip install -q pillow
"$PY" packaging/make_icon.py

echo "Assembling $APP ..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp CheckPrinter.icns "$APP/Contents/Resources/CheckPrinter.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>CheckPrinter</string>
  <key>CFBundleDisplayName</key><string>CheckPrinter</string>
  <key>CFBundleIdentifier</key><string>com.sweetwaterplumbing.checkprinter</string>
  <key>CFBundleVersion</key><string>1.0.0</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundleExecutable</key><string>CheckPrinter</string>
  <key>CFBundleIconFile</key><string>CheckPrinter</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.finance</string>
</dict>
</plist>
PLIST

# Launcher: prefer a project sitting next to the .app; else this build's path.
LAUNCHER="$APP/Contents/MacOS/CheckPrinter"
cat > "$LAUNCHER" <<LAUNCH
#!/bin/bash
PROJECT="$PROJECT"
SELF="\$(cd "\$(dirname "\$0")/../../.." && pwd)"
[ -d "\$SELF/checkprinter" ] && PROJECT="\$SELF"
cd "\$PROJECT" 2>/dev/null || { osascript -e 'display alert "CheckPrinter" message "Project folder not found. Re-run build_app.sh."'; exit 1; }

if [ ! -x ".venv/bin/python" ] || ! ./.venv/bin/python -c "import tkinter" >/dev/null 2>&1; then
    osascript -e 'display dialog "First-time setup: Terminal will open to finish installing (~30s), then re-open CheckPrinter." buttons {"OK"} default button 1' >/dev/null 2>&1 || true
    open -a Terminal "./CheckPrinter.command"
    exit 0
fi
exec ./.venv/bin/python -m checkprinter
LAUNCH
chmod +x "$LAUNCHER"

# Refresh Finder's icon cache for the bundle.
touch "$APP"
echo "Done. Double-click CheckPrinter.app, or drag it to the Dock / Applications."
