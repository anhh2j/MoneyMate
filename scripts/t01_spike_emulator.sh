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
# Never persist raw diagnostic output. Scan in a private temporary directory, then remove.
private_dir="$(mktemp -d)"
phase=preflight
diagnostic_failed=0
run_phase() {
  phase="$1"
  shift
  local code=0
  "$@" || code=$?
  printf 'phase=%s exit=%s\n' "$phase" "$code" >> "$private_dir/phases.txt"
  return "$code"
}
platform_field() {
  local output="$1" label="$2" code=0
  shift 2
  printf '\nfield=%s\n' "$label" >> "$output"
  timeout 8s "$@" > "$private_dir/field.txt" 2>&1 || code=$?
  if [ "$(wc -c < "$private_dir/field.txt")" -le 4096 ]; then
    cat "$private_dir/field.txt" >> "$output"
  else
    printf 'output=OMITTED_OVER_LIMIT\n' >> "$output"
    diagnostic_failed=1
  fi
  printf 'exit=%s\n' "$code" >> "$output"
  # pidof=1 means absent, which is expected for the blank-emulator app PIDs.
  if [ "$code" -ne 0 ] && ! { [[ "$label" == pidof-* ]] && [ "$code" -eq 1 ]; }; then
    diagnostic_failed=1
  fi
}
platform_snapshot() {
  [ "$api" -ge 35 ] || return 0
  local label="$1" file="$private_dir/platform-$1.txt"
  printf 'phase=%s api=%s experiment=%s\n' "$label" "$api" "${T01_EXPERIMENT:-baseline}" > "$file"
  for prop in sys.boot_completed init.svc.zygote init.svc.surfaceflinger ro.build.fingerprint ro.build.version.sdk; do
    platform_field "$file" "$prop" adb shell getprop "$prop"
  done
  for process in system_server surfaceflinger com.app.moneymate com.app.moneymate.test; do
    platform_field "$file" "pidof-$process" adb shell pidof "$process"
  done
  for service in package activity notification SurfaceFlinger; do
    platform_field "$file" "service-$service" adb shell service check "$service"
  done
  if ! python3 scripts/t01_spike_checks.py --scan "$file"; then
    diagnostic_failed=1
    return 1
  fi
  cp "$file" "$report/platform-$label.txt" || { diagnostic_failed=1; return 1; }
}
on_exit() {
  local status=$? diagnostic_status=PASS final_status
  trap - EXIT
  set +e # Diagnostic collection must never overwrite an original nonzero exit.
  platform_snapshot exit || diagnostic_failed=1
  if [ "$status" -ne 0 ]; then
    adb logcat -d -s AndroidRuntime:E > "$private_dir/crash.txt" 2>/dev/null || true
    adb shell service check notification > "$private_dir/binding.txt" 2>&1 || true
    if python3 scripts/t01_spike_checks.py --scan "$private_dir/binding.txt"; then
      cp "$private_dir/binding.txt" "$report/binding-metadata.txt" || diagnostic_failed=1
    else
      diagnostic_failed=1
    fi
    if python3 scripts/t01_spike_checks.py --scan "$private_dir/crash.txt"; then
      cp "$private_dir/crash.txt" "$report/crash-sanitized.txt" || diagnostic_failed=1
    else
      diagnostic_failed=1
    fi
  fi
  if [ "$diagnostic_failed" -ne 0 ]; then diagnostic_status=FAIL; fi
  final_status="$status"
  # Preserve every original nonzero result. A new diagnostic failure fails a
  # formerly successful job separately; primary_exit still records the original.
  if [ "$status" -eq 0 ] && [ "$diagnostic_failed" -ne 0 ]; then final_status=1; fi
  printf 'phase=%s primary_exit=%s diagnostics=%s final_exit=%s\n' "$phase" "$status" "$diagnostic_status" "$final_status" >> "$private_dir/phases.txt"
  if python3 scripts/t01_spike_checks.py --scan "$private_dir/phases.txt"; then
    cp "$private_dir/phases.txt" "$report/command-status.txt" || { if [ "$status" -eq 0 ]; then final_status=1; fi; }
  else
    if [ "$status" -eq 0 ]; then final_status=1; fi
  fi
  if [ "$final_status" -ne 0 ] && [ -f "$report/result.json" ]; then
    python3 - "$report/result.json" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
result = json.loads(path.read_text())
result.update(runtime='NOT VERIFIED', diagnostics='FAIL')
path.write_text(json.dumps(result, indent=2) + '\n')
PY
  fi
  cleanup
  rm -rf "$private_dir"
  exit "$final_status"
}
trap on_exit EXIT
sha256sum app/build/outputs/apk/debug/app-debug.apk app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk > "$private_dir/apk-pair.txt"
python3 scripts/t01_spike_checks.py --scan "$private_dir/apk-pair.txt"
cp "$private_dir/apk-pair.txt" "$report/apk-pair-sha256.txt"
if [ "$api" -ge 35 ]; then
  environment="$private_dir/environment.txt"
  printf 'ImageOS=%s ImageVersion=%s\n' "${ImageOS:-unknown}" "${ImageVersion:-unknown}" > "$environment"
  platform_field "$environment" host uname -srmo
  platform_field "$environment" adb adb version
  platform_field "$environment" emulator "$ANDROID_HOME/emulator/emulator" -version
  printf 'requested_gpu=%s\n' "${T01_GPU_MODE:-unknown}" >> "$environment"
  platform_field "$environment" avd-gpu-config sed -n -E '/^(hw.gpu.enabled|hw.gpu.mode|hw.ramSize|disk.dataPartition.size)[[:space:]]*=/p' "$ANDROID_AVD_HOME/test.avd/hardware-qemu.ini"
  image_api="$api"
  if [ "$api" -eq 37 ]; then image_api=37.0; fi
  properties="$ANDROID_HOME/system-images/android-$image_api/${T01_IMAGE_TARGET:-default}/x86_64/source.properties"
  platform_field "$environment" image-properties sed -n -E '/^(Pkg.Revision|AndroidVersion.ApiLevel|AndroidVersion.CodeName|SystemImage.TagId|SystemImage.Abi)[[:space:]]*=/p' "$properties"
  if ! grep -q '^Pkg.Revision[[:space:]]*=' "$environment"; then diagnostic_failed=1; fi
  python3 scripts/t01_spike_checks.py --scan "$environment"
  cp "$environment" "$report/environment.txt"
  platform_snapshot clean-boot
  # Observe the blank emulator before any MoneyMate APK is installed.
  sleep 15
  platform_snapshot preinstall
fi
if [ "$api" -eq 37 ]; then
  ready=0
  for attempt in $(seq 1 15); do
    if adb shell cmd package list packages com.android.settings > "$private_dir/pm-ready.txt" 2>/dev/null && grep -q 'package:com.android.settings' "$private_dir/pm-ready.txt"; then
      ready=1
      break
    fi
    sleep 2
  done
  test "$ready" -eq 1
fi
phase=install-app
if [ "$api" -eq 37 ]; then
  run_phase install-app adb install --no-streaming -r app/build/outputs/apk/debug/app-debug.apk >/dev/null
  platform_snapshot post-app-install
  phase=install-test
  run_phase install-test adb install --no-streaming -r -t app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk >/dev/null
else
  run_phase install-app adb install -r app/build/outputs/apk/debug/app-debug.apk >/dev/null
  platform_snapshot post-app-install
  phase=install-test
  run_phase install-test adb install -r -t app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk >/dev/null
fi
platform_snapshot post-test-install
phase=grant-notification-permission
if [ "$api" -ge 33 ]; then run_phase grant-notification-permission adb shell pm grant com.app.moneymate.test android.permission.POST_NOTIFICATIONS; fi
# Grant only after instrumentation has started: Android 8 can retain a stale binding
# when an already-bound target is force-stopped by am instrument.
cleanup
phase=instrumentation
instrument_status=0
run_phase instrumentation adb shell am instrument -w -r com.app.moneymate.test/com.app.moneymate.spike.SpikeDeviceInstrumentation > "$private_dir/instrumentation.txt" || instrument_status=$?
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
phase=cold-process
run_phase force-stop adb shell am force-stop com.app.moneymate
run_phase cold-process adb shell am instrument -w -r -e phase cold com.app.moneymate.test/com.app.moneymate.spike.SpikeDeviceInstrumentation > "$private_dir/cold.txt"
python3 scripts/t01_spike_checks.py --scan "$private_dir/cold.txt"
grep -q 'Cold process state PASS' "$private_dir/cold.txt"
grep -q 'INSTRUMENTATION_CODE: -1' "$private_dir/cold.txt"
cp "$private_dir/cold.txt" "$report/cold-process.txt"
phase=diagnostics-validation
test "$diagnostic_failed" -eq 0
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
phase=complete
