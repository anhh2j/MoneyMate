"""B2-G2 isolated execution, fail-closed evidence inspection; synthetic inputs only."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / 'security/b2-g2'
REPORT = HARNESS / 'build/reports/b2-g2'
BASE = '690a74af29897d43fcb9f4c58808ae6ea2e3365f'
ACCEPTED_B2 = 'be26d275d621c4a0c64ed9dd5fb89cad42bf91b2'
PATHS = [
    'security/b2-g2/settings.gradle.kts',
    'security/b2-g2/build.gradle.kts',
    'security/b2-g2/gradle/libs.versions.toml',
    'security/b2-g2/gradle/verification-metadata.xml',
    'security/b2-g2/proguard-rules.pro',
    'security/b2-g2/src/main/AndroidManifest.xml',
    'security/b2-g2/src/main/kotlin/com/app/moneymate/b2g2/B2KdfProbe.kt',
    'security/b2-g2/src/androidTest/kotlin/com/app/moneymate/b2g2/B2G2RuntimeTest.kt',
    '.github/workflows/t20-b2-g2-compat.yml',
    'security/b2-evidence/B2_G2_PROTOCOL.md',
    'security/b2-evidence/b2-g2-run-and-inspect.py',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(name, value):
    (REPORT / name).write_text(json.dumps(value, indent=2) + '\n')


def command(label, args, required=True):
    print('RUN', label, flush=True)
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    (REPORT / (label + '.log')).write_text(result.stdout)
    print(result.stdout, end='', flush=True)
    path = REPORT / 'commands.json'
    rows = json.loads(path.read_text()) if path.exists() else []
    rows.append({'label': label, 'argv': args, 'exit': result.returncode, 'required': required})
    write_json('commands.json', rows)
    if required and result.returncode:
        raise RuntimeError(f'{label}: exit {result.returncode}; STOP, no policy/task workaround authorized')
    return result


def gradle(label, *tasks):
    return command(label, [str(ROOT / 'gradlew'), '-p', str(HARNESS), '--dependency-verification', 'strict',
                           '-Pandroid.useAndroidX=true', '-Dorg.gradle.jvmargs=-Xmx3g -Dfile.encoding=UTF-8',
                           '--console=plain', *tasks])


def preflight():
    REPORT.mkdir(parents=True, exist_ok=True)
    changes = subprocess.check_output(['git', 'diff', '--name-status', BASE, 'HEAD'], cwd=ROOT, text=True).splitlines()
    assert sorted(changes) == sorted('A\t' + p for p in PATHS), changes
    write_json('changed-files.json', [{'path': p, 'sha256': sha((ROOT / p).read_bytes())} for p in PATHS])
    identity = subprocess.check_output(['git', 'rev-parse', 'HEAD', 'HEAD^{tree}'], cwd=ROOT, text=True).splitlines()
    write_json('source.json', {'base': BASE, 'head': identity[0], 'tree': identity[1], 'acceptedB2': ACCEPTED_B2})
    for path in ['gradle/libs.versions.toml', 'gradle/verification-metadata.xml']:
        reference = subprocess.check_output(['git', 'show', ACCEPTED_B2 + ':' + path], cwd=ROOT)
        assert (HARNESS / path).read_bytes() == reference, 'Only exact accepted B2 copies are authorized'
    assert 'verify-metadata>true' in (HARNESS / 'gradle/verification-metadata.xml').read_text()
    command('java', ['java', '-version'])
    catalog = command('sdk-list', ['sdkmanager', '--list']).stdout
    requested = f"system-images;android-{os.environ['G2_API']};{os.environ['G2_TARGET']};x86_64"
    write_json('requested-environment.json', {
        'cell': os.environ['G2_CELL'], 'api': int(os.environ['G2_API']), 'systemImage': requested,
        'ramMiB': int(os.environ['G2_RAM']), 'heapMiB': int(os.environ['G2_HEAP']),
        'arm64': 'ENV-BLOCKED', 'arm64Kernel16KiB': 'ENV-BLOCKED', 'nativeOom': 'NOT-VERIFIED',
    })
    if requested not in catalog:
        (REPORT / 'environment.txt').write_text('ENV-BLOCKED: requested image unavailable\n')
        raise RuntimeError('ENV-BLOCKED: requested image unavailable')


def build():
    tasks = gradle('tasks', 'tasks', '--all').stdout
    expected = ['minifyReleaseWithR8', 'assembleRelease', 'assembleReleaseAndroidTest',
                'connectedReleaseAndroidTest', 'lintRelease', 'exportB2G2Inventory']
    assert all(re.search(r'^' + name + r'(?:\s|$)', tasks, re.M) for name in expected), 'STOP: task graph mismatch'
    gradle('build', ':minifyReleaseWithR8', ':assembleRelease', ':assembleReleaseAndroidTest',
           ':lintRelease', ':exportB2G2Inventory', ':build-logic:exportBuildDependencies')
    gradle('target-dependencies', ':dependencies', '--configuration', 'releaseRuntimeClasspath')
    gradle('test-dependencies', ':dependencies', '--configuration', 'releaseAndroidTestRuntimeClasspath')
    tools = pathlib.Path(os.environ['G2_TOOLS'])
    command('install-scanners', ['python3', 'scripts/install_security_tools.py', str(tools)])
    command('secrets-history', [str(tools / 'gitleaks'), 'git', '--redact=100', '--no-banner',
                              '--log-opts=--all', '--report-format=json',
                              '--report-path=' + str(REPORT / 'secrets-history.json'), str(ROOT)])
    command('secrets-harness', [str(tools / 'gitleaks'), 'dir', '--redact=100', '--no-banner',
                              '--report-format=json', '--report-path=' + str(REPORT / 'secrets-harness.json'),
                              str(HARNESS / 'src')])
    included = ROOT / 'build-logic/build/reports/security/build-logic.cdx.json'
    shutil.copyfile(included, REPORT / 'build-logic.cdx.json')
    for name in ['dependencies.cdx', 'build-logic.cdx']:
        inventory = REPORT / (name + '.json')
        assert json.loads(inventory.read_text()).get('components')
        command(name + '-scan', [str(tools / 'trivy'), 'sbom', '--severity', 'HIGH,CRITICAL', '--exit-code', '1',
                                 '--format', 'json', '--output', str(REPORT / (name + '-vulnerabilities.json')),
                                 str(inventory)])


def instrument():
    command('device-properties', ['adb', 'shell', 'getprop'])
    command('page-size', ['adb', 'shell', 'getconf', 'PAGE_SIZE'], required=False)
    command('device-memory-before', ['adb', 'shell', 'dumpsys', 'meminfo'])
    command('kernel', ['adb', 'shell', 'uname', '-a'])
    command('emulator-version', ['emulator', '-version'])
    command('acceleration', ['emulator', '-accel-check'])
    command('clear-logcat', ['adb', 'logcat', '-c'])
    try:
        gradle('instrumented', ':connectedReleaseAndroidTest')
    finally:
        stream = command('metric-stream', ['adb', 'logcat', '-d', '-v', 'raw', '-s', 'B2_G2_METRIC:I', '*:S'],
                         required=False).stdout
        rows = [json.loads(line) for line in stream.splitlines() if line.startswith('{')]
        (REPORT / 'metrics.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
        command('device-memory-after', ['adb', 'shell', 'dumpsys', 'meminfo'], required=False)


def dex_classes(raw):
    assert raw[:4] == b'dex\n'
    string_count, string_offset = struct.unpack_from('<II', raw, 56)
    type_count, type_offset = struct.unpack_from('<II', raw, 64)
    class_count, class_offset = struct.unpack_from('<II', raw, 96)
    strings = []
    for index in range(string_count):
        offset = struct.unpack_from('<I', raw, string_offset + index * 4)[0]
        while raw[offset] & 0x80:
            offset += 1
        offset += 1
        strings.append(raw[offset:raw.index(b'\x00', offset)].decode('utf-8', errors='replace'))
    types = [strings[struct.unpack_from('<I', raw, type_offset + index * 4)[0]] for index in range(type_count)]
    return {types[struct.unpack_from('<I', raw, class_offset + index * 32)[0]] for index in range(class_count)}


def apk_classes(path):
    with zipfile.ZipFile(path) as archive:
        return set().union(*(dex_classes(archive.read(n)) for n in archive.namelist() if n.endswith('.dex')))


def inspect():
    commands = json.loads((REPORT / 'commands.json').read_text())
    assert all(row['exit'] == 0 for row in commands if row['required'])
    assert any(row['label'] == 'instrumented' and row['exit'] == 0 for row in commands)
    totals = dict(tests=0, failures=0, errors=0, skipped=0)
    xmls = list((HARNESS / 'build/outputs/androidTest-results').rglob('*.xml'))
    junit = []
    for path in xmls:
        junit.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())})
        for suite in ET.parse(path).getroot().iter('testsuite'):
            for key in totals:
                totals[key] += int(suite.get(key, 0))
    assert totals == dict(tests=5, failures=0, errors=0, skipped=0), totals
    metrics = [json.loads(line) for line in (REPORT / 'metrics.jsonl').read_text().splitlines()]
    assert len(metrics) == 20
    expected_api = int(os.environ['G2_API'])
    expected_page = 16384 if os.environ['G2_TARGET'] == 'google_apis_ps16k' else 4096
    for row in metrics:
        assert row['scope'] == 'B2_G2_TEST_ONLY' and row['api'] == expected_api
        assert row['abis'].split(',')[0] == 'x86_64' and row['process64Bit'] is True
        assert row['pageSize'] == expected_page and row['targetPackage'] == 'com.app.moneymate.b2g2'
        assert 'com.app.moneymate.b2g2' in row['targetSourceDir']
    if expected_page == 16384:
        assert (REPORT / 'page-size.log').read_text().strip() == '16384'
    for case in ['KAT_256_KiB', 'KAT_65536_KiB', 'VERIFIER_AND_SENSITIVITY',
                 'MALFORMED_REJECTED', 'BOUNDED_PRESSURE_16_MiB']:
        selected = [row for row in metrics if row['case'] == case]
        assert len(selected) == 1 and selected[0]['result'] == 'PASS'
    for memory in [1024, 8192, 65536]:
        selected = [row for row in metrics if row['case'] == 'BENCHMARK_TEST_ONLY' and row['mKiB'] == memory]
        assert len(selected) == 5 and {row['run'] for row in selected} == set(range(5))
        for row in selected:
            assert row['t'] == 2 and row['p'] == 1 and row['elapsedNs'] > 0
            if os.environ['G2_CELL'] == 'memory35':
                assert row['before']['javaMaxBytes'] <= 128 * 1024 * 1024, 'Requested heap limit not effective'
                total = row['before']['totalMemBytes']
                assert 0.7 * 1536 * 1024 * 1024 <= total <= 1536 * 1024 * 1024, 'RAM envelope not effective'
    apk_root = HARNESS / 'build/outputs/apk'
    targets = list((apk_root / 'release').glob('*.apk'))
    tests = list((apk_root / 'androidTest/release').glob('*.apk'))
    assert len(targets) == 1 and len(tests) == 1
    target, test = targets[0], tests[0]
    mapping_root = HARNESS / 'build/outputs/mapping/release'
    mapping = (mapping_root / 'mapping.txt').read_text()
    usage = (mapping_root / 'usage.txt').read_text()
    configuration = (mapping_root / 'configuration.txt').read_text()
    provider = {}
    for original, renamed in re.findall(r'^([^\s#][^\s]*) -> ([^\s]+):$', mapping, re.M):
        if original.startswith('com.lambdapioneer.argon2kt.'):
            provider[original] = 'L' + renamed.replace('.', '/') + ';'
    assert provider, 'No provider classes in R8 mapping'
    target_classes, test_classes = apk_classes(target), apk_classes(test)
    assert any(name in target_classes for name in provider.values()), 'No mapped provider in target DEX'
    assert not set(provider.values()) & test_classes, 'Provider duplicate in test APK'
    assert not any(name.startswith('Lcom/lambdapioneer/argon2kt/') for name in test_classes)
    assert 'Lcom/app/moneymate/b2g2/B2KdfProbe;' in target_classes
    assert 'B2G2UnreachableCanary' in usage
    assert not any('B2G2UnreachableCanary' in name for name in target_classes)
    assert not re.search(r'^-dont(?:shrink|optimize|obfuscate)\s*$', configuration, re.M)
    assert not re.search(r'^-keep[^\n]*com\.lambdapioneer\.argon2kt\.\*\*', configuration, re.M)
    assert '> Task :minifyReleaseWithR8' in (REPORT / 'build.log').read_text()
    sdk = pathlib.Path(os.environ['ANDROID_HOME']) / 'build-tools/37.0.0'
    target_sig = command('target-signature', [str(sdk / 'apksigner'), 'verify', '--print-certs', str(target)]).stdout
    test_sig = command('test-signature', [str(sdk / 'apksigner'), 'verify', '--print-certs', str(test)]).stdout
    cert_pattern = r'Signer #1 certificate SHA-256 digest: (\S+)'
    assert re.search(cert_pattern, target_sig).group(1) == re.search(cert_pattern, test_sig).group(1)
    badging = command('target-manifest', [str(sdk / 'aapt'), 'dump', 'badging', str(target)]).stdout
    assert 'application-debuggable' not in badging and 'uses-permission:' not in badging
    command('target-zipalign', [str(sdk / 'zipalign'), '-c', '-P', '16', '-v', '4', str(target)])
    elf = []
    with zipfile.ZipFile(target) as archive:
        for name in archive.namelist():
            if not name.endswith('.so'):
                continue
            raw = archive.read(name)
            is64 = raw[4] == 2
            endian = '<' if raw[5] == 1 else '>'
            offset = struct.unpack_from(endian + ('Q' if is64 else 'I'), raw, 32 if is64 else 28)[0]
            size, count = struct.unpack_from(endian + 'HH', raw, 54 if is64 else 42)
            alignments = []
            for index in range(count):
                entry = offset + index * size
                if struct.unpack_from(endian + 'I', raw, entry)[0] == 1:
                    alignments.append(struct.unpack_from(endian + ('Q' if is64 else 'I'), raw,
                                                         entry + (48 if is64 else 28))[0])
            assert alignments and min(alignments) >= 16384
            elf.append({'path': name, 'sha256': sha(raw), 'alignments': alignments})
    assert elf and any('/x86_64/' in entry['path'] for entry in elf)
    with zipfile.ZipFile(test) as archive:
        assert not any('argon2' in name.lower() and name.endswith('.so') for name in archive.namelist())
    files = [target, test, *xmls, *(mapping_root / name for name in ['mapping.txt', 'usage.txt', 'configuration.txt'])]
    hashes = [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())} for path in files]
    write_json('summary.json', {
        'source': json.loads((REPORT / 'source.json').read_text()), 'cell': os.environ['G2_CELL'],
        'junit': totals, 'junitFiles': junit, 'metricsRows': len(metrics), 'metricsSha256': sha((REPORT / 'metrics.jsonl').read_bytes()),
        'r8Target': 'PASS', 'providerInTargetDex': 'PASS', 'providerAbsentFromTestDex': 'PASS',
        'canaryRemoved': 'PASS', 'providerClassMapping': provider, 'apkZip16KiB': 'PASS', 'elf': elf,
        'pageSize': expected_page, 'abi': 'x86_64', 'api': expected_api, 'hashes': hashes,
        'arm64Runtime': 'ENV-BLOCKED', 'arm64Kernel16KiB': 'ENV-BLOCKED', 'nativeOom': 'NOT-VERIFIED',
        'page16KiBKind': 'SIMULATED_X86_USERSPACE' if expected_page == 16384 else '4_KiB',
    })
    print('PASS: isolated minified target, actual JNI/KAT/negative tests, DEX/mapping/canary and measured environment')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'build', 'instrument', 'inspect'])
    mode = parser.parse_args().mode
    globals()[mode]()
