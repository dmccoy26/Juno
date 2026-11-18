#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
project_path="$PWD"
python_path="$project_path/.venv/bin/python"
if [[ ! -x "$python_path" ]]; then
    printf 'Set up .venv per README.md before building the app.\n' >&2
    exit 1
fi
"$python_path" -c 'import playwright, pypdf'
swift build -c release
bin_dir="$(swift build -c release --show-bin-path)"
app="$project_path/local/Concur Helper.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
install -m 755 "$bin_dir/ConcurHelper" "$app/Contents/MacOS/ConcurHelper"
install -m 644 concur_portal.py pcard_receipts.py receipt_helper.py "$app/Contents/Resources/"
printf '%s\n' "$python_path" > "$app/Contents/Resources/python-path.txt"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>CFBundleExecutable</key><string>ConcurHelper</string>
    <key>CFBundleIdentifier</key><string>local.concur-helper.mac</string>
    <key>CFBundleName</key><string>Concur Helper</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>0.1.1</string>
    <key>CFBundleVersion</key><string>2</string>
    <key>CFBundleURLTypes</key><array><dict>
        <key>CFBundleURLName</key><string>local.concur-helper.mac.job</string>
        <key>CFBundleURLSchemes</key><array><string>concur-helper</string></array>
    </dict></array>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
</dict></plist>
PLIST
codesign --force --sign - "$app"
printf '%s\n' "$app"
