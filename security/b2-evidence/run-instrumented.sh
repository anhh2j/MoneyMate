#!/usr/bin/env bash
set -uo pipefail
mkdir -p build/reports/b2
adb shell getprop > build/reports/b2/device-properties.txt
adb shell getconf PAGE_SIZE > build/reports/b2/page-size.txt
adb shell dumpsys meminfo > build/reports/b2/device-memory-before.txt
./gradlew --dependency-verification strict :security:connectedDebugAndroidTest --console=plain 2>&1 | tee build/reports/b2/instrumented.log
b2_test_exit=${PIPESTATUS[0]}
printf '%s\n' "$b2_test_exit" > build/reports/b2/instrumented-exit.txt
adb exec-out run-as com.app.moneymate.security.test cat files/b2-metrics.jsonl > build/reports/b2/metrics.jsonl
b2_metrics_exit=$?
printf '%s\n' "$b2_metrics_exit" > build/reports/b2/metrics-exit.txt
if [ "$b2_test_exit" -ne 0 ]; then exit "$b2_test_exit"; fi
exit "$b2_metrics_exit"
