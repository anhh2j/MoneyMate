#!/usr/bin/env bash
set -euo pipefail
apk_path="${1:-apk/app-debug.apk}"
variant="${2:-debug}"
case "$variant" in debug|release-r8) ;; *) echo "Invalid variant" >&2; exit 1 ;; esac
report="build/reports/emulator/$variant"
mkdir -p "$report"
sha256sum "$apk_path" > "$report/apk-sha256.txt"
adb install -r "$apk_path" | tee "$report/install.txt"
adb shell dumpsys package com.app.moneymate > "$report/package.txt"
adb shell am start -W -n com.app.moneymate/.MainActivity | tee "$report/launch.txt"
grep -q 'Status: ok' "$report/launch.txt"
for attempt in $(seq 1 20); do
    adb shell uiautomator dump /sdcard/window.xml >/dev/null
    adb pull /sdcard/window.xml "$report/window.xml" >/dev/null
    if python3 - "$report/window.xml" <<'PYTHON'
import sys
import xml.etree.ElementTree as ET
nodes = ET.parse(sys.argv[1]).getroot().iter()
visible = any(node.get("text") == "MoneyMate" and node.get("package") == "com.app.moneymate" for node in nodes)
sys.exit(0 if visible else 1)
PYTHON
    then
        adb shell dumpsys activity activities > "$report/activities.txt"
        adb exec-out screencap -p > "$report/screen.png"
        echo 'PASS: APK installed, launcher opened, MoneyMate text visible' | tee "$report/result.txt"
        exit 0
    fi
    sleep 1
done
adb logcat -d -s AndroidRuntime:E > "$report/crash.txt"
printf '%s\n' 'FAIL: MoneyMate text not visible' >&2
exit 1
