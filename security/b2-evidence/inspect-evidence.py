"""Read-only inspection of B2 scope, APK packaging and executed evidence."""
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORT = ROOT / 'build/reports/b2'
BASE = '690a74af29897d43fcb9f4c58808ae6ea2e3365f'


def inspect():
    changed = subprocess.check_output(['git', 'diff', '--name-only', BASE, 'HEAD'], cwd=ROOT, text=True).splitlines()
    exact = {'security/build.gradle.kts', 'gradle/libs.versions.toml', 'gradle/verification-metadata.xml', '.github/workflows/t20-b2-argon2kt-spike.yml'}
    prefixes = ('security/src/androidTest/', 'security/src/test/', 'security/b2-evidence/')
    assert all(p in exact or p.startswith(prefixes) for p in changed), changed
    manifest = [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in changed]
    (REPORT / 'changed-files.json').write_text(json.dumps(manifest, indent=2))
    xmls = list((ROOT / 'security/build/outputs/androidTest-results').rglob('*.xml'))
    totals = dict(tests=0, failures=0, errors=0, skipped=0)
    for path in xmls:
        suite = ET.parse(path).getroot()
        if suite.tag != 'testsuite':
            continue
        for key in totals:
            totals[key] += int(suite.get(key, 0))
    assert totals == dict(tests=6, failures=0, errors=0, skipped=0), totals
    assert (REPORT / 'instrumented-exit.txt').read_text().strip() == '0'
    metrics = [json.loads(s) for s in (REPORT / 'metrics.jsonl').read_text().splitlines() if s.strip()]
    assert len(metrics) == 20, len(metrics)
    apks = list((ROOT / 'security/build/outputs/apk/androidTest').rglob('*.apk'))
    assert len(apks) == 1
    apk = apks[0]
    zipalign = pathlib.Path(os.environ['ANDROID_HOME']) / 'build-tools/37.0.0/zipalign'
    aligned = subprocess.run([str(zipalign), '-c', '-P', '16', '-v', '4', str(apk)], capture_output=True, text=True, check=False)
    (REPORT / 'zipalign.txt').write_text(aligned.stdout + aligned.stderr)
    elf = []
    with zipfile.ZipFile(apk) as archive:
        for name in archive.namelist():
            if not name.endswith('.so'):
                continue
            raw = archive.read(name)
            is64 = raw[4] == 2
            endian = '<' if raw[5] == 1 else '>'
            offset = struct.unpack_from(endian + ('Q' if is64 else 'I'), raw, 32 if is64 else 28)[0]
            size, count = struct.unpack_from(endian + 'HH', raw, 54 if is64 else 42)
            aligns = []
            for index in range(count):
                entry = offset + index * size
                if struct.unpack_from(endian + 'I', raw, entry)[0] == 1:
                    aligns.append(struct.unpack_from(endian + ('Q' if is64 else 'I'), raw, entry + (48 if is64 else 28))[0])
            elf.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'alignments': aligns})
    assert elf
    summary = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'junit': totals, 'metricRows': len(metrics), 'apk': str(apk.relative_to(ROOT)),
               'apkSha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
               'apkZip16KiB': 'PASS' if aligned.returncode == 0 else 'FAIL', 'zipalignExit': aligned.returncode,
               'elf': elf, 'pageSize': (REPORT / 'page-size.txt').read_text().strip(),
               'r8': 'NOT-VERIFIED', 'exhaustedMemory': 'NOT-VERIFIED', 'scope': 'B2_TEST_ONLY'}
    (REPORT / 'summary.json').write_text(json.dumps(summary, indent=2))
    assert aligned.returncode == 0, 'APK ZIP alignment failed; see zipalign.txt'
    assert all(a >= 16384 for item in elf for a in item['alignments']), 'ELF alignment failed'
    print(json.dumps({k: v for k, v in summary.items() if k != 'elf'}))


if __name__ == '__main__':
    inspect()
