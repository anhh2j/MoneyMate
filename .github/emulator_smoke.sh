#!/usr/bin/env bash
set -euo pipefail
mkdir -p build/reports/emulator
adb install -r apk/app-debug.apk | tee build/reports/emulator/install.txt
adb shell am start -W -n com.app.moneymate/.MainActivity | tee build/reports/emulator/launch.txt
grep -q 'Status: ok' build/reports/emulator/launch.txt
for attempt in $(seq 1 20); do
    adb shell uiautomator dump /sdcard/window.xml >/dev/null
    adb pull /sdcard/window.xml build/reports/emulator/window.xml >/dev/null
    if grep -q 'text="MoneyMate"' build/reports/emulator/window.xml; then
        adb exec-out screencap -p > build/reports/emulator/screen.png
        echo 'PASS: APK installed, launcher opened, MoneyMate text visible' | tee build/reports/emulator/result.txt
        exit 0
    fi
    sleep 1
done
adb logcat -d -s AndroidRuntime:E > build/reports/emulator/crash.txt
printf '%s\n' 'FAIL: MoneyMate text not visible' >&2
exit 1
