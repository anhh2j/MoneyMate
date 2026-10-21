#!/usr/bin/env bash
set -euo pipefail
qemu="$(adb shell getprop ro.kernel.qemu | tr -d '\r')"
if [ "$qemu" != 1 ] && [ "$(adb shell getprop ro.boot.qemu | tr -d '\r')" != 1 ]; then
  echo 'FAIL: synthetic test APK is restricted to emulators' >&2
  exit 2
fi
api="$(adb shell getprop ro.build.version.sdk | tr -d '\r')"
test "$api" -eq "${EXPECTED_T01_API:-$api}"
report="build/reports/t01/api-$api"
mkdir -p "$report"
adb shell getprop ro.config.low_ram > "$report/low-ram-property.txt"
adb shell getprop ro.build.fingerprint > "$report/fingerprint.txt"
adb shell df -k /data > "$report/data-space.txt"
adb shell input keyevent 82
listener='com.app.moneymate/com.app.moneymate.capture.spike.SpikeNotificationListenerService'
cleanup() {
  if [ "$api" -eq 26 ]; then
    adb shell settings delete secure enabled_notification_listeners >/dev/null 2>&1 || true
  else
    adb shell cmd notification disallow_listener "$listener" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
adb install -r app/build/outputs/apk/debug/app-debug.apk >/dev/null
adb install -r -t app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk >/dev/null
if [ "$api" -ge 33 ]; then adb shell pm grant com.app.moneymate.test android.permission.POST_NOTIFICATIONS; fi
if [ "$api" -eq 26 ]; then
  adb shell settings put secure enabled_notification_listeners "$listener"
else
  adb shell cmd notification allow_listener "$listener"
fi
# Never persist raw diagnostic output. Scan in a private temporary directory, then remove.
private_dir="$(mktemp -d)"
on_exit() {
  status=$?
  if [ "$status" -ne 0 ]; then
    adb logcat -d -s AndroidRuntime:E > "$private_dir/crash.txt" 2>/dev/null || true
    adb shell dumpsys notification | python3 -c 'import sys; [print(line.rstrip()) for line in sys.stdin if "com.app.moneymate.capture.spike.SpikeNotificationListenerService" in line]' > "$private_dir/binding.txt" || true
    if python3 scripts/t01_spike_checks.py --scan "$private_dir/binding.txt"; then
      cp "$private_dir/binding.txt" "$report/binding-metadata.txt"
    fi
    if python3 scripts/t01_spike_checks.py --scan "$private_dir/crash.txt"; then
      cp "$private_dir/crash.txt" "$report/crash-sanitized.txt"
    fi
  fi
  cleanup
  rm -rf "$private_dir"
  exit "$status"
}
trap on_exit EXIT
instrument_status=0
adb shell am instrument -w -r com.app.moneymate.test/com.app.moneymate.spike.SpikeDeviceInstrumentation > "$private_dir/instrumentation.txt" || instrument_status=$?
python3 scripts/t01_spike_checks.py --scan "$private_dir/instrumentation.txt"
cp "$private_dir/instrumentation.txt" "$report/instrumentation.txt"
test "$instrument_status" -eq 0
grep -q 'ING-01..05 runtime assertions PASS' "$private_dir/instrumentation.txt"
grep -q 'INSTRUMENTATION_CODE: -1' "$private_dir/instrumentation.txt"
adb exec-out run-as com.app.moneymate.test cat shared_prefs/probe.xml > "$private_dir/probe.xml"
python3 scripts/t01_spike_checks.py --scan "$private_dir/probe.xml"
cp "$private_dir/probe.xml" "$report/external-uid-probe.xml"
adb logcat -d > "$private_dir/logcat.txt"
python3 scripts/t01_spike_checks.py --scan "$private_dir/logcat.txt"
adb exec-out run-as com.app.moneymate tar -cf - . > "$private_dir/storage.tar"
python3 scripts/t01_spike_checks.py --scan "$private_dir/storage.tar"
adb shell am force-stop com.app.moneymate
adb shell am instrument -w -r -e phase cold com.app.moneymate.test/com.app.moneymate.spike.SpikeDeviceInstrumentation > "$private_dir/cold.txt"
python3 scripts/t01_spike_checks.py --scan "$private_dir/cold.txt"
grep -q 'Cold process state PASS' "$private_dir/cold.txt"
grep -q 'INSTRUMENTATION_CODE: -1' "$private_dir/cold.txt"
cp "$private_dir/cold.txt" "$report/cold-process.txt"
python3 - "$api" "$report" <<'PY'
import hashlib, json, pathlib, subprocess, sys
api, report = sys.argv[1], pathlib.Path(sys.argv[2])
apks = sorted(pathlib.Path('app/build/outputs/apk').rglob('*.apk'))
result = {'api': int(api), 'fingerprint': subprocess.check_output(['adb','shell','getprop','ro.build.fingerprint'], text=True).strip(),
          'runtime': 'PASS', 'automated_shell_grant': True, 'real_bank_device': 'NOT VERIFIED',
          'apk_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in apks},
          'limitations': ['User Settings grant and OEM restrictions require manual evidence', 'API37 is verified only by an API37 job']}
(report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: synthetic system callback and external UID isolation; manual/device limits recorded')
PY
