"""B2-G2 isolated execution, fail-closed evidence inspection; synthetic inputs only."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / 'security/b2-g2'
REPORT = HARNESS / 'build/reports/b2-g2'
BASE = '690a74af29897d43fcb9f4c58808ae6ea2e3365f'
ACCEPTED_B2 = 'be26d275d621c4a0c64ed9dd5fb89cad42bf91b2'
P05_CATALOG_ALIAS = b'b2-errorprone-annotations = { module = "com.google.errorprone:error_prone_annotations", version = "2.36.0" }\n'
P08_CATALOG_ALIAS = b'b2-tracing = { module = "androidx.tracing:tracing", version = "1.1.0" }\n'
P08_GRAPH_HASHES = {
    'releaseAndroidTestCompileClasspath': '5fd6ba7f9c09d4ad3ce4be5ef9c44c6947d9be107920de5713c54a47ffc2c6c5',
    'releaseAndroidTestRuntimeClasspath': '08b586c85acdeed027245c7d7f1c4b600feeef16726ab45d61591c0894349f11',
    'releaseRuntimeClasspath': 'e08b8b91403b633f1f60198df3a221d51cfe40d4186628c1c9181f9e1f760d59',
}
P08_TRACE_METHODS = {'beginSection(Ljava/lang/String;)V', 'endSection()V', 'forceEnableAppTracing()V'}
P05_CLASSES = ['com.google.errorprone.annotations.CanIgnoreReturnValue', 'com.google.errorprone.annotations.MustBeClosed']
# G2-P01: Leader6354820006, official PO authorization6355498984.
# G2-P03: official PO authorization6356299057; only the final metadata record.
APPROVED_CHECKSUMS = [
    ("androidx.annotation:annotation:1.3.0", "annotation-1.3.0.module",
     "9516c2ae44284ea0bd3d0eade0ee638879b708cbe31e3af92ba96c300604ebc3"),
    ("androidx.annotation:annotation:1.6.0", "annotation-1.6.0.module",
     "6146b6138643b2ac0590df509dd51abaea769c79fd7602eb217168fe5af78cd2"),
    ("androidx.annotation:annotation-jvm:1.6.0", "annotation-jvm-1.6.0.jar",
     "60b10b5ef5769b79570172e015b8159405c92f034ba88b9391a977589c9deb4e"),
    ("androidx.annotation:annotation-jvm:1.6.0", "annotation-jvm-1.6.0.module",
     "3f5a8faa19de667e63dca9730ff8ef0e478e4bafb5feeb8258e5c086246dc90c"),
    ("org.jetbrains.kotlin:kotlin-stdlib-common:2.2.10", "kotlin-stdlib-common-2.2.10.module",
     "336afb512852028b1da5d5d07a6fb833cf9a797ee4b33519694d312f683227c9"),
    ("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.6.4", "kotlinx-coroutines-android-1.6.4.jar",
     "3fdc0eed5bc4b83ee9622774520a2db25470370eacd1581cac1e37704f095b00"),
    ("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.6.4", "kotlinx-coroutines-core-1.6.4.module",
     "a6eed4a1835588e7c84fcd7b0475fce9a7b3444c870ebc797b88ba64ccf4576b"),
    ("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.6.4", "kotlinx-coroutines-core-jvm-1.6.4.jar",
     "c24c8bb27bb320c4a93871501a7e5e0c61607638907b197aef675513d4c820be"),
    ("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.6.4", "kotlinx-coroutines-core-jvm-1.6.4.module",
     "0d94c8a41483e7c2707ebd693e1b1357a84152998ce85550ebbc54ca4321a3a7"),
    ("androidx.tracing:tracing:1.0.0", "tracing-1.0.0.aar",
     "07b8b6139665b884a162eccf97891ca50f7f56831233bf25168ae04f7b568612"),
    ("org.jetbrains.kotlin:kotlin-stdlib-common:2.4.21", "kotlin-stdlib-common-2.4.21.module",
     "aeae4f24688e1dd7ebee648ab2b12be685cbe33e9c72bc1439730a794d6e2d5b"),
]
# G2-P09: PO6360301889; preserve the previous eleven admitted additions unchanged.
P09_CHECKSUM = ('androidx.annotation:annotation:1.2.0', 'annotation-1.2.0.module',
                '2efcab81ef91b211bacd206eaacd995a51f633a2e96b57a8fc00144c5f9c56b3')
P09_METADATA_BLOCK = (
    '      <component group="androidx.annotation" name="annotation" version="1.2.0">\n'
    '         <artifact name="annotation-1.2.0.module">\n'
    '            <sha256 value="' + P09_CHECKSUM[2] + '" origin="G2-P09 verified upstream bytes"/>\n'
    '         </artifact>\n'
    '      </component>\n'
).encode()
PATHS = [
    'security/b2-g2/settings.gradle.kts',
    'security/b2-g2/build.gradle.kts',
    'security/b2-g2/gradle/libs.versions.toml',
    'security/b2-g2/gradle/verification-metadata.xml',
    'security/b2-g2/proguard-rules.pro',
    'security/b2-g2/src/main/AndroidManifest.xml',
    'security/b2-g2/src/main/res/xml/data_extraction_rules.xml',
    'security/b2-g2/src/main/kotlin/com/app/moneymate/b2g2/B2KdfProbe.kt',
    'security/b2-g2/src/androidTest/kotlin/com/app/moneymate/b2g2/B2G2RuntimeTest.kt',
    '.github/workflows/t20-b2-g2-compat.yml',
    'security/b2-evidence/B2_G2_PROTOCOL.md',
    'security/b2-evidence/b2-g2-run-and-inspect.py',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def approved_metadata():
    """Reconstruct exact 795 approved bytes, then insert the sole P09 record."""
    text = subprocess.check_output(
        ['git', 'show', ACCEPTED_B2 + ':gradle/verification-metadata.xml'], cwd=ROOT,
    ).decode()
    for coordinate in dict.fromkeys(row[0] for row in APPROVED_CHECKSUMS):
        group, name, version = coordinate.split(':')
        opening = f'      <component group="{group}" name="{name}" version="{version}">'
        entries = [row for row in APPROVED_CHECKSUMS if row[0] == coordinate]
        approval = 'G2-P03' if coordinate == 'org.jetbrains.kotlin:kotlin-stdlib-common:2.4.21' else 'G2-P01'
        block = ''.join(
            f'         <artifact name="{artifact}">\n'
            f'            <sha256 value="{digest}" origin="{approval} verified upstream bytes"/>\n'
            '         </artifact>\n'
            for _, artifact, digest in entries
        )
        if opening in text:
            end = text.index('      </component>', text.index(opening))
            text = text[:end] + block + text[end:]
        else:
            block = opening + '\n' + block + '      </component>\n'
            text = text.replace('   </components>', block + '   </components>')
    assert text.count('   </components>') == 1
    return text.encode().replace(b'   </components>', P09_METADATA_BLOCK + b'   </components>', 1)


def verify_metadata(raw):
    assert len(APPROVED_CHECKSUMS) == 11 and len(set(APPROVED_CHECKSUMS)) == 11
    assert raw == approved_metadata(), 'STOP: metadata differs from exact 795 approved records plus sole P09 record'


def approved_catalog():
    baseline = subprocess.check_output(['git', 'show', ACCEPTED_B2 + ':gradle/libs.versions.toml'], cwd=ROOT)
    assert baseline.count(b'[libraries]\n') == 1
    return baseline.replace(b'[libraries]\n', b'[libraries]\n' + P05_CATALOG_ALIAS + P08_CATALOG_ALIAS, 1)


def verify_catalog(raw):
    assert raw == approved_catalog(), 'STOP: catalog differs from baseline plus exact P05/P08 aliases'


def catalog_negative_controls(raw):
    verify_catalog(raw)
    controls = {
        'alias-missing': raw.replace(P05_CATALOG_ALIAS, b''),
        'alias-version-drift': raw.replace(P05_CATALOG_ALIAS, P05_CATALOG_ALIAS.replace(b'2.36.0', b'2.27.0')),
        'baseline-version-drift': raw.replace(b'agp = "9.4.1"', b'agp = "9.4.0"'),
        'extra-alias': raw + b'\nunapproved = { id = "synthetic.plugin", version = "1" }\n',
        'alias-renamed': raw.replace(b'b2-errorprone-annotations =', b'b2-unapproved-annotations ='),
        'p08-alias-missing': raw.replace(P08_CATALOG_ALIAS, b''),
        'p08-version-drift': raw.replace(P08_CATALOG_ALIAS, P08_CATALOG_ALIAS.replace(b'1.1.0', b'1.2.0')),
        'p08-alias-renamed': raw.replace(b'b2-tracing =', b'b2-unapproved-tracing ='),
        'p08-alias-duplicate': raw + P08_CATALOG_ALIAS,
    }
    results = []
    for name, value in controls.items():
        assert value != raw
        try:
            verify_catalog(value)
        except AssertionError:
            results.append({'case': name, 'result': 'REJECTED'})
        else:
            raise AssertionError('Catalog accepted negative control: ' + name)
    write_json('p05-catalog-negative-controls.json', {'status': 'PASS', 'controls': results, 'sourceFilesMutated': False})


def write_json(name, value):
    (REPORT / name).write_text(json.dumps(value, indent=2) + '\n')


def command(label, args, required=True, split_streams=False):
    print('RUN', label, flush=True)
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE if split_streams else subprocess.STDOUT, text=True, check=False)
    if split_streams:
        (REPORT / (label + '.stdout.log')).write_text(result.stdout)
        (REPORT / (label + '.stderr.log')).write_text(result.stderr)
        result.stdout += result.stderr
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
                           '--console=plain', *tasks], split_streams=label == 'instrumented')


def verify_scope(changes):
    assert len(PATHS) == 12 and len(set(PATHS)) == 12, 'STOP: expected exact P04 twelve-path allowlist'
    assert sorted(changes) == sorted('A\t' + p for p in PATHS), changes


def guard_negative_controls(metadata):
    verify_metadata(metadata)
    rows = ['A\t' + path for path in PATHS]
    verify_scope(rows)
    checks = [
        ('missing-path', verify_scope, rows[:-1]),
        ('thirteenth-path', verify_scope, rows + ['A\tsynthetic-unapproved.txt']),
        ('modified-baseline-path', verify_scope, ['M\t' + PATHS[0]] + rows[1:]),
        ('metadata-byte-change', verify_metadata, metadata + b' '),
        ('verification-config-change', verify_metadata,
         metadata.replace(b'<verify-metadata>true</verify-metadata>', b'<verify-metadata>false</verify-metadata>')),
        ('p03-hash-change', verify_metadata, metadata.replace(APPROVED_CHECKSUMS[-1][2].encode(), b'0' * 64)),
        ('p01-hash-change', verify_metadata, metadata.replace(APPROVED_CHECKSUMS[0][2].encode(), b'0' * 64)),
        ('unapproved-component', verify_metadata,
         metadata.replace(b'   </components>', b'      <component group="synthetic" name="unapproved" version="1"/>\n   </components>')),
        ('p09-missing', verify_metadata, metadata.replace(P09_METADATA_BLOCK, b'')),
        ('p09-hash-change', verify_metadata, metadata.replace(P09_CHECKSUM[2].encode(), b'0' * 64)),
        ('p09-artifact-renamed', verify_metadata, metadata.replace(b'annotation-1.2.0.module', b'annotation-1.2.0.jar')),
        ('p09-coordinate-version', verify_metadata, metadata.replace(
            b'name="annotation" version="1.2.0"', b'name="annotation" version="1.2.1"')),
        ('p09-duplicate', verify_metadata, metadata.replace(P09_METADATA_BLOCK, P09_METADATA_BLOCK * 2)),
        ('p09-extra-hash', verify_metadata, metadata.replace(
            P09_METADATA_BLOCK, P09_METADATA_BLOCK.replace(b'         </artifact>',
                b'            <sha256 value="' + b'0' * 64 + b'"/>\n         </artifact>'))),
    ]
    results = []
    for name, guard, value in checks:
        try:
            guard(value)
        except AssertionError:
            results.append({'case': name, 'result': 'REJECTED'})
        else:
            raise AssertionError('Guard accepted negative control: ' + name)
    write_json('p04-negative-controls.json', {'status': 'PASS', 'controls': results, 'sourceFilesMutated': False,
                                            'positiveMetadata': 'ACCEPTED_EXACT_796', 'p09Authority': 'Issue16 comment6360301889'})


def preflight():
    REPORT.mkdir(parents=True, exist_ok=True)
    changes = subprocess.check_output(['git', 'diff', '--name-status', BASE, 'HEAD'], cwd=ROOT, text=True).splitlines()
    verify_scope(changes)
    write_json('changed-files.json', [{'path': p, 'sha256': sha((ROOT / p).read_bytes())} for p in PATHS])
    identity = subprocess.check_output(['git', 'rev-parse', 'HEAD', 'HEAD^{tree}'], cwd=ROOT, text=True).splitlines()
    write_json('source.json', {'base': BASE, 'head': identity[0], 'tree': identity[1], 'acceptedB2': ACCEPTED_B2})
    reference = subprocess.check_output(['git', 'show', ACCEPTED_B2 + ':gradle/libs.versions.toml'], cwd=ROOT)
    catalog = (HARNESS / 'gradle/libs.versions.toml').read_bytes()
    verify_catalog(catalog)
    catalog_negative_controls(catalog)
    write_json('catalog-policy.json', {'authority': 'Issue16 comment6359936855', 'acceptedB2': ACCEPTED_B2,
                                       'baselineSha256': sha(reference), 'catalogSha256': sha(catalog),
                                       'approvedInsertions': [P05_CATALOG_ALIAS.decode().strip(), P08_CATALOG_ALIAS.decode().strip()]})
    metadata = (HARNESS / 'gradle/verification-metadata.xml').read_bytes()
    verify_metadata(metadata)
    guard_negative_controls(metadata)
    p08_negative_controls()
    write_json('checksum-policy.json', {'baselineArtifactRecords': 784, 'approvedAdditions': APPROVED_CHECKSUMS + [P09_CHECKSUM],
                                       'p01Additions': 10, 'p03Additions': 1, 'p09Additions': 1, 'totalArtifactRecords': 796,
                                       'p09Authority': 'Issue16 comment6360301889',
                                       'metadataSha256': sha(metadata), 'strictVerification': True})
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
                'connectedReleaseAndroidTest', 'lintRelease', 'exportB2G2Inventory', 'exportB2G2Toolchain']
    assert all(re.search(r'^' + name + r'(?:\s|$)', tasks, re.M) for name in expected), 'STOP: task graph mismatch'
    gradle('toolchain', ':exportB2G2Toolchain')
    verify_toolchain()
    observer = write_p06_observer()
    try:
        gradle('build', '--init-script', str(observer), ':minifyReleaseWithR8', ':assembleRelease', ':assembleReleaseAndroidTest',
               ':lintRelease', ':exportB2G2Inventory', ':build-logic:exportBuildDependencies')
    finally:
        if (REPORT / 'p06-r8-inputs.json').exists():
            verify_test_resolution()
        if (REPORT / 'p08-classpaths.json').exists():
            verify_p08_graphs()
    verify_p08_apks()
    gradle('target-dependencies', ':dependencies', '--configuration', 'releaseRuntimeClasspath')
    gradle('test-dependencies', ':dependencies', '--configuration', 'releaseAndroidTestRuntimeClasspath')
    gradle('test-errorprone-insight', ':dependencyInsight', '--dependency', 'com.google.errorprone:error_prone_annotations',
           '--configuration', 'releaseAndroidTestCompileClasspath')
    verify_test_resolution()
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
        license_inventory(inventory, tools)
    p07_safe('license', p07_license_diagnostics)
    p07_safe('p10-build', lambda: p10_closure('build'))


def write_p06_observer():
    """Generated evidence-only init script; reads task inputs without changing their wiring."""
    path = REPORT / 'p06-observe-inputs.init.gradle'
    path.write_text(r'''
import groovy.json.JsonOutput
import java.security.MessageDigest
import java.util.zip.ZipFile

def digest = { byte[] bytes -> MessageDigest.getInstance('SHA-256').digest(bytes).encodeHex().toString() }
def annotations = ['com/google/errorprone/annotations/CanIgnoreReturnValue.class',
                   'com/google/errorprone/annotations/MustBeClosed.class']
def describe = { File file ->
    def found = []
    if (file.isDirectory()) {
        file.eachFileRecurse { child ->
            if (child.isFile()) {
                def relative = file.toPath().relativize(child.toPath()).toString().replace('\\', '/')
                if (relative.startsWith('com/google/errorprone/annotations/') && relative.endsWith('.class')) found.add(relative)
            }
        }
    } else if (file.isFile() && file.name.endsWith('.jar')) {
        def archive = new ZipFile(file)
        try {
            archive.entries().each { entry ->
                if (entry.name.startsWith('com/google/errorprone/annotations/') && entry.name.endsWith('.class')) found.add(entry.name)
            }
        } finally { archive.close() }
    }
    [path: file.absolutePath, kind: file.isDirectory() ? 'directory' : 'file', exists: file.exists(),
     sha256: file.isFile() ? digest(file.bytes) : null, errorProneClasses: found.sort()]
}
def readInputFiles = { task, String getter ->
    def type = task.class
    def method = null
    while (type != null && method == null) {
        method = type.declaredMethods.find { it.parameterCount == 0 && (it.name == getter || it.name.startsWith(getter + '$')) }
        type = type.superclass
    }
    if (method == null) throw new IllegalStateException('Cannot observe R8 getter: ' + getter)
    method.accessible = true
    def value = method.invoke(task)
    if (!(value instanceof Iterable)) throw new IllegalStateException('R8 input is not iterable: ' + getter)
    value.collect { File file -> describe(file) }
}
gradle.taskGraph.beforeTask { task ->
    if (task.project.rootProject.name != 'MoneyMate-B2-G2-Test-Only' || task.path != ':minifyReleaseAndroidTestWithR8') return
    def output = new File(task.project.rootProject.projectDir, 'build/reports/b2-g2')
    output.mkdirs()
    def scopes = ['releaseAndroidTestCompileClasspath', 'releaseAndroidTestRuntimeClasspath', 'releaseRuntimeClasspath',
                  'releaseCompileClasspath']
    def graphs = scopes.collect { scope ->
        def configuration = task.project.configurations.getByName(scope)
        def result = configuration.incoming.resolutionResult
        [scope: scope, components: result.allComponents.findAll { it.moduleVersion != null }.collect {
            [group: it.moduleVersion.group, name: it.moduleVersion.name, version: it.moduleVersion.version]
        }, selectionReasons: result.allComponents.collect {
            [id: it.id.displayName, reasons: it.selectionReason.descriptions.collect { reason -> reason.description }]
        }, edges: result.allDependencies.collect {
            [from: it.from.id.displayName, requested: it.requested.displayName, selected: it.selected.id.displayName]
        }]
    }
    new File(output, 'p06-classpaths.json').text = JsonOutput.toJson([
        graphs: graphs.findAll { it.scope != 'releaseCompileClasspath' }, capturedBeforeTask: task.path])
    new File(output, 'p08-classpaths.json').text = JsonOutput.toJson([graphs: graphs, capturedBeforeTask: task.path])
    def evidence = [task: task.path, taskType: task.class.name, stage: 'BEFORE_TEST_R8', status: 'NOT-VERIFIED',
                    mutatesTaskInputs: false]
    try {
        evidence.referencedClasses = readInputFiles(task, 'getReferencedClasses')
        evidence.programClasses = readInputFiles(task, 'getProgramClasses')
        evidence.bootClasspath = readInputFiles(task, 'getBootClasspath')
        evidence.status = 'OBSERVED'
    } catch (Exception failure) {
        evidence.observationError = failure.toString()
    }
    new File(output, 'p06-r8-inputs.json').text = JsonOutput.toJson(evidence)
    def libraries = evidence.referencedClasses ?: []
    def programs = evidence.programClasses ?: []
    def provided = libraries.any { row -> annotations.every { row.errorProneClasses.contains(it) } }
    if (evidence.status != 'OBSERVED' || !provided || programs.any { !it.errorProneClasses.isEmpty() }) {
        throw new IllegalStateException('STOP P06: Error Prone R8 referenced/library input not verified or leaked into program classes')
    }
}
'''.lstrip())
    return path


def validate_p06_inputs(graphs, inputs):
    expected = {'releaseAndroidTestCompileClasspath': {'2.36.0'},
                'releaseAndroidTestRuntimeClasspath': set(), 'releaseRuntimeClasspath': set()}
    assert len(graphs) == 3 and {g['scope'] for g in graphs} == set(expected)
    for graph in graphs:
        versions = {c['version'] for c in graph['components'] if c['group'] == 'com.google.errorprone'
                    and c['name'] == 'error_prone_annotations'}
        assert versions == expected[graph['scope']], f"STOP P06: {graph['scope']} selected {versions}"
    assert inputs['status'] == 'OBSERVED' and inputs['stage'] == 'BEFORE_TEST_R8'
    assert inputs['task'] == ':minifyReleaseAndroidTestWithR8' and inputs['mutatesTaskInputs'] is False
    assert not any(row['errorProneClasses'] for row in inputs['programClasses']), 'Error Prone in test R8 program inputs'
    library_rows = [row for row in inputs['referencedClasses'] if row['errorProneClasses']]
    assert any(row['sha256'] == '77440e270b0bc9a249903c5a076c36a722c4886ca4f42675f2903a1c53ed61a5'
               and all(name.replace('.', '/') + '.class' in row['errorProneClasses'] for name in P05_CLASSES)
               for row in library_rows), 'Pinned Error Prone JAR not observed as R8 library input'


def validate_p08_graphs(graphs):
    expected = set(P08_GRAPH_HASHES) | {'releaseCompileClasspath'}
    assert len(graphs) == 4 and {g['scope'] for g in graphs} == expected, 'STOP P08: incomplete compile/runtime graphs'
    rows_by_scope = {}
    for graph in graphs:
        versions = {c['version'] for c in graph['components']
                    if c['group'] == 'androidx.tracing' and c['name'] == 'tracing'}
        assert versions == {'1.1.0'}, f"STOP P08: {graph['scope']} tracing {versions}"
        rows = sorted(':'.join(c[k] for k in ['group', 'name', 'version']) for c in graph['components']
                      if c['group'] != 'androidx.tracing' or c['name'] != 'tracing')
        rows_by_scope[graph['scope']] = set(rows)
        if graph['scope'] in P08_GRAPH_HASHES:
            assert sha('\n'.join(rows).encode()) == P08_GRAPH_HASHES[graph['scope']], 'STOP P08: non-tracing graph drift'
    admitted = set().union(*(rows_by_scope[scope] for scope in P08_GRAPH_HASHES))
    assert rows_by_scope['releaseCompileClasspath'] <= admitted, 'STOP P08: unexpected target compile component'


def verify_p08_graphs():
    graphs = json.loads((REPORT / 'p08-classpaths.json').read_text())['graphs']
    validate_p08_graphs(graphs)
    controls = {}
    for case in ['runtime-downgrade', 'test-compile-missing', 'target-compile-missing', 'non-tracing-drift']:
        modified = json.loads(json.dumps(graphs))
        scope = 'releaseAndroidTestRuntimeClasspath' if case == 'runtime-downgrade' else 'releaseAndroidTestCompileClasspath'
        graph = next(g for g in modified if g['scope'] == scope)
        if case == 'runtime-downgrade':
            next(c for c in graph['components'] if c['group'] == 'androidx.tracing')['version'] = '1.0.0'
        elif case == 'test-compile-missing':
            graph['components'] = [c for c in graph['components'] if c['group'] != 'androidx.tracing']
        elif case == 'target-compile-missing':
            modified = [g for g in modified if g['scope'] != 'releaseCompileClasspath']
        else:
            graph['components'].append({'group': 'synthetic.unapproved', 'name': 'drift', 'version': '0'})
        try:
            validate_p08_graphs(modified)
        except AssertionError:
            controls[case] = 'REJECTED'
        else:
            raise AssertionError('P08 graph negative control accepted: ' + case)
    write_json('p08-resolution.json', {
        'authority': 'Issue16 comment6359936855', 'status': 'PASS', 'tracingVersion': '1.1.0',
        'scopes': [g['scope'] for g in graphs], 'graphSha256': sha((REPORT / 'p08-classpaths.json').read_bytes()),
        'p07NonTracingComponentHashes': P08_GRAPH_HASHES, 'negativeControls': controls,
        'note': 'Target compile is additionally observed; three pre-existing scope component sets match P07 excluding tracing.',
    })


def validate_p08_apk_facts(facts):
    assert facts['traceTargetDefinition'] is True, 'STOP P08: no stable Trace target DEX definition'
    assert facts['traceTestDefinition'] is False, 'STOP P08: duplicate Trace test definition'
    assert set(facts['targetPublicStaticMethods']) >= P08_TRACE_METHODS, 'STOP P08: missing shared Trace API definition'
    assert facts['canaryRemoved'] is True and facts['r8Executed'] is True, 'STOP P08: R8/canary not verified'


def p08_negative_controls():
    valid = {'traceTargetDefinition': True, 'traceTestDefinition': False,
             'targetPublicStaticMethods': sorted(P08_TRACE_METHODS), 'canaryRemoved': True, 'r8Executed': True}
    validate_p08_apk_facts(valid)
    mutations = {
        'missing-target-trace': dict(valid, traceTargetDefinition=False),
        'duplicate-test-trace': dict(valid, traceTestDefinition=True),
        'missing-force-enable-api': dict(valid, targetPublicStaticMethods=['beginSection(Ljava/lang/String;)V', 'endSection()V']),
        'canary-retained': dict(valid, canaryRemoved=False),
        'r8-not-executed': dict(valid, r8Executed=False),
    }
    rows = []
    for case, facts in mutations.items():
        try:
            validate_p08_apk_facts(facts)
        except AssertionError:
            rows.append({'case': case, 'result': 'REJECTED'})
        else:
            raise AssertionError('P08 APK negative control accepted: ' + case)
    write_json('p08-negative-controls.json', {'status': 'PASS', 'controls': rows, 'sourceFilesMutated': False})


def verify_test_resolution():
    coordinate = 'com.google.errorprone:error_prone_annotations:2.36.0'
    graph_path, input_path = REPORT / 'p06-classpaths.json', REPORT / 'p06-r8-inputs.json'
    graphs = json.loads(graph_path.read_text())['graphs']
    inputs = json.loads(input_path.read_text())
    validate_p06_inputs(graphs, inputs)
    cache = pathlib.Path(os.environ.get('GRADLE_USER_HOME', pathlib.Path.home() / '.gradle')) / 'caches/modules-2/files-2.1'
    jars = list((cache / 'com.google.errorprone/error_prone_annotations/2.36.0').glob('*/error_prone_annotations-2.36.0.jar'))
    assert jars, 'No resolved P05 JAR'
    hashes = []
    for jar in jars:
        digest = sha(jar.read_bytes())
        assert digest == '77440e270b0bc9a249903c5a076c36a722c4886ca4f42675f2903a1c53ed61a5'
        with zipfile.ZipFile(jar) as archive:
            assert all(name.replace('.', '/') + '.class' in archive.namelist() for name in P05_CLASSES)
        hashes.append({'file': jar.name, 'sha256': digest, 'classesPresent': P05_CLASSES})
    write_json('p06-test-resolution.json', {
        'authority': 'Issue16 comment6358851194', 'status': 'PASS', 'coordinate': coordinate,
        'targetRuntimeAbsent': True, 'testCompilePresent': True, 'testRuntimeAbsent': True,
        'testR8ReferencedInputPresent': True, 'testR8ProgramInputAbsent': True, 'jarArtifacts': hashes,
        'graphSha256': sha(graph_path.read_bytes()), 'r8InputSha256': sha(input_path.read_bytes()),
    })


def license_inventory(inventory, tools):
    """Collect declared POM licenses with provenance; retain UNKNOWN for independent QA."""
    document = json.loads(inventory.read_text())
    cache = pathlib.Path(os.environ.get('GRADLE_USER_HOME', pathlib.Path.home() / '.gradle')) / 'caches/modules-2/files-2.1'
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

    def collect(component):
        coordinate = tuple(component[key] for key in ['group', 'name', 'version'])
        provenance, seen = [], set()
        licenses, error = [], None
        for _ in range(6):
            if coordinate in seen or not all(coordinate):
                break
            seen.add(coordinate)
            group, name, version = coordinate
            filename = f'{name}-{version}.pom'
            local = list((cache / group / name / version).glob('*/' + filename))
            if local:
                raw, source = local[0].read_bytes(), 'gradle-cache:' + ':'.join(coordinate) + '/' + filename
            else:
                relative = '/'.join([group.replace('.', '/'), name, version, filename])
                repositories = ['https://repo.maven.apache.org/maven2/', 'https://dl.google.com/dl/android/maven2/']
                if group.startswith(('androidx.', 'com.android')):
                    repositories.reverse()
                raw = None
                for repository in repositories:
                    try:
                        source = repository + relative
                        with urllib.request.urlopen(source, timeout=8) as response:
                            raw = response.read(2 * 1024 * 1024)
                        break
                    except Exception as failure:
                        error = type(failure).__name__
                if raw is None:
                    break
            provenance.append({'coordinate': ':'.join(coordinate), 'source': source, 'sha256': sha(raw)})
            try:
                root = ET.fromstring(raw)
                licenses = [dict(name=entry.findtext('m:name', default='', namespaces=ns),
                                 url=entry.findtext('m:url', default='', namespaces=ns))
                            for entry in root.findall('m:licenses/m:license', ns)]
                licenses = [entry for entry in licenses if entry['name'] or entry['url']]
                if licenses:
                    break
                parent = root.find('m:parent', ns)
                if parent is None:
                    break
                coordinate = tuple(parent.findtext('m:' + key, namespaces=ns) for key in ['groupId', 'artifactId', 'version'])
                if any(value and '${' in value for value in coordinate):
                    break
            except ET.ParseError as failure:
                error = type(failure).__name__
                break
        return {'component': component['purl'], 'licenses': licenses, 'provenance': provenance,
                'status': 'DECLARED' if licenses else 'NOT-VERIFIED', 'fetchError': error if not licenses else None}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        rows = list(executor.map(collect, document['components']))
    by_purl = {row['component']: row for row in rows}
    for component in document['components']:
        declarations = by_purl[component['purl']]['licenses']
        component['licenses'] = [{'license': entry} for entry in declarations] or [{'license': {'name': 'UNKNOWN'}}]
    stem = inventory.name.removesuffix('.json')
    enriched = REPORT / (stem + '-licenses.cdx.json')
    enriched.write_text(json.dumps(document, indent=2) + '\n')
    write_json(stem + '-license-provenance.json', {
        'inventorySha256': sha(inventory.read_bytes()), 'enrichedSha256': sha(enriched.read_bytes()),
        'components': rows, 'declared': sum(row['status'] == 'DECLARED' for row in rows),
        'unverified': sum(row['status'] == 'NOT-VERIFIED' for row in rows),
        'assessment': 'DECLARATIONS_AND_SCANNER_CLASSIFICATION_ONLY_REQUIRES_QA_REVIEW',
    })
    # Preserve every classification; no license exception, ignore list or legal PASS is inferred.
    command(stem + '-license-scan', [str(tools / 'trivy'), 'sbom', '--scanners', 'license', '--format', 'json',
                                   '--output', str(REPORT / (stem + '-licenses.json')), str(enriched)])


def verify_toolchain():
    """G2-P02 B: require observed baseline selections and exact admitted artifact hashes."""
    graph_path = REPORT / 'toolchain-graph.json'
    artifact_path = REPORT / 'toolchain-artifacts.json'
    graphs = json.loads(graph_path.read_text())['graphs']
    artifacts = json.loads(artifact_path.read_text())
    expected = {
        'buildscript:classpath': {'kotlin-gradle-plugin', 'kotlin-build-tools-api'},
        'module:kotlinCompilerClasspath': {'kotlin-build-tools-impl', 'kotlin-compiler-embeddable', 'kotlin-build-tools-api'},
        'module:kotlinBuildToolsApiClasspath': {'kotlin-build-tools-impl', 'kotlin-compiler-embeddable', 'kotlin-build-tools-api'},
    }
    assert len(graphs) == len(expected) and {g['scope'] for g in graphs} == set(expected)
    for graph in graphs:
        components = graph['components']
        for name in expected[graph['scope']]:
            versions = {c['version'] for c in components if c['group'] == 'org.jetbrains.kotlin' and c['name'] == name}
            assert versions == {'2.4.21'}, f"STOP: {graph['scope']} {name} selected {versions}, expected 2.4.21"
        if graph['scope'] == 'buildscript:classpath':
            assert {c['version'] for c in components if c['group'] == 'com.android.tools.build'
                    and c['name'] == 'gradle'} == {'9.4.1'}, 'STOP: AGP drift'
        assert graph['edges'] and graph['selectionReasons'], 'Missing resolution evidence'
        for component in components:
            if component['group'] == 'org.jetbrains.kotlin' and component['name'] in {
                'kotlin-gradle-plugin', 'kotlin-compiler-embeddable', 'kotlin-build-tools-api', 'kotlin-build-tools-impl',
            }:
                assert component['version'] == '2.4.21', 'STOP: mixed toolchain'
    metadata = (HARNESS / 'gradle/verification-metadata.xml').read_bytes()
    verify_metadata(metadata)
    ns = {'v': 'https://schema.gradle.org/dependency-verification'}
    admitted = {}
    for component in ET.fromstring(metadata).findall('v:components/v:component', ns):
        coordinate = ':'.join(component.get(key) for key in ['group', 'name', 'version'])
        for artifact in component.findall('v:artifact', ns):
            admitted[(coordinate, artifact.get('name'))] = {h.get('value') for h in artifact.findall('v:sha256', ns)}
    assert artifacts and {a['scope'] for a in artifacts} == set(expected), 'Incomplete artifact manifest'
    for scope, names in expected.items():
        for name in names:
            assert any(a['scope'] == scope and a['component'] == f'org.jetbrains.kotlin:{name}:2.4.21'
                       for a in artifacts), f'Missing critical artifact: {scope} {name}'
    for artifact in artifacts:
        assert artifact['sha256'] in admitted.get((artifact['component'], artifact['file']), set()), artifact
    write_json('toolchain-parity.json', {
        'authority': 'Issue16 comment6356080091', 'status': 'PASS',
        'expectedKgpCompilerBta': '2.4.21', 'expectedAgp': '9.4.1',
        'graphSha256': sha(graph_path.read_bytes()), 'artifactManifestSha256': sha(artifact_path.read_bytes()),
        'artifactCount': len(artifacts), 'metadataSha256': sha(metadata),
    })


def p07_command(label, args, timeout=12):
    """Read-only diagnostic, separate from acceptance and never a PASS oracle."""
    directory = REPORT / 'p07'
    directory.mkdir(exist_ok=True)
    row = {'label': label, 'argv': args, 'kind': 'READ_ONLY_DIAGNOSTIC', 'startedUnix': time.time()}
    try:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=timeout, check=False)
        stdout, stderr = result.stdout, result.stderr
        row.update(exit=result.returncode, status='OBSERVED' if result.returncode == 0 else 'NOT-VERIFIED')
    except subprocess.TimeoutExpired as failure:
        stdout, stderr = failure.stdout or b'', failure.stderr or b''
        row.update(exit=None, status='NOT-VERIFIED', error='TIMEOUT')
    except OSError as failure:
        stdout, stderr = b'', str(failure).encode()
        row.update(exit=None, status='NOT-VERIFIED', error=type(failure).__name__)
    row['finishedUnix'] = time.time()
    for stream, raw in [('stdout', stdout), ('stderr', stderr)]:
        path = directory / (label + '.' + stream + '.log')
        path.write_bytes(raw)
        row[stream] = {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}
    index = directory / 'commands.json'
    rows = json.loads(index.read_text()) if index.exists() else []
    rows.append(row)
    index.write_text(json.dumps(rows, indent=2) + '\n')
    return stdout.decode('utf-8', errors='replace')


def p07_safe(phase, action):
    """Diagnostic failure cannot replace an acceptance failure or waive a gate."""
    try:
        action()
    except Exception as failure:
        write_json('p07-' + phase + '-collection-error.json', {
            'status': 'NOT-VERIFIED', 'error': type(failure).__name__, 'detail': str(failure),
            'acceptanceUnchanged': True,
        })


def p07_snapshot(phase):
    queries = {
        'instrumentation': ['shell', 'pm', 'list', 'instrumentation', '-f'],
        'running-instrumentation': ['shell', 'dumpsys', 'activity', 'instrumentation'],
        'device': ['shell', 'getprop'],
        'processes': ['shell', 'ps', '-A'],
        'log-buffers': ['logcat', '-g'],
        'runner-logcat': ['logcat', '-d', '-v', 'threadtime', 'AndroidJUnitRunner:V', 'TestRunner:V',
                          'MonitoringInstr:V', 'AndroidRuntime:V', 'ActivityManager:I', 'PackageManager:I',
                          'System.err:V', 'art:D', 'dalvikvm:D', 'B2_G2_METRIC:I', '*:S'],
        'crash-logcat': ['logcat', '-d', '-b', 'crash', '-v', 'threadtime'],
    }
    for package in ['com.app.moneymate.b2g2', 'com.app.moneymate.b2g2.test']:
        queries[package + '-path'] = ['shell', 'pm', 'path', package]
        queries[package + '-package'] = ['shell', 'dumpsys', 'package', package]
    for label, args in queries.items():
        p07_command(phase + '-' + label, ['adb', *args])
    # Observe installed APKs only; do not install/reinstall/run a second instrumentation.
    installed = []
    for package in ['com.app.moneymate.b2g2', 'com.app.moneymate.b2g2.test']:
        raw = (REPORT / 'p07' / (phase + '-' + package + '-path.stdout.log')).read_text()
        paths = [line.removeprefix('package:') for line in raw.splitlines() if line.startswith('package:')]
        item = {'package': package, 'paths': paths, 'classification': 'OBSERVED_INSTALLED' if paths else 'NOT-VERIFIED_NOT_OBSERVED'}
        item['note'] = 'UTP may install/uninstall between snapshots; absence does not prove it was never installed.'
        installed.append(item)
        for index, remote in enumerate(paths):
            if not remote.startswith('/data/app/') or not remote.endswith('.apk'):
                continue
            local = REPORT / 'p07' / (phase + '-' + package + '-' + str(index) + '.apk')
            p07_command(phase + '-' + package + '-pull-' + str(index), ['adb', 'pull', remote, str(local)])
            if local.exists():
                sdk = pathlib.Path(os.environ['ANDROID_HOME']) / 'build-tools/37.0.0'
                item.setdefault('apks', []).append({'path': str(local.relative_to(ROOT)), 'sha256': sha(local.read_bytes())})
                p07_command(phase + '-' + package + '-signature-' + str(index),
                            [str(sdk / 'apksigner'), 'verify', '--print-certs', str(local)])
    write_json('p07-' + phase + '-installed.json', installed)


def p07_apk_diagnostics():
    sdk = pathlib.Path(os.environ['ANDROID_HOME']) / 'build-tools/37.0.0'
    rows = []
    for kind, pattern in [('target', 'release/*.apk'), ('test', 'androidTest/release/*.apk')]:
        for apk in (HARNESS / 'build/outputs/apk').glob(pattern):
            row = {'kind': kind, 'path': str(apk.relative_to(ROOT)), 'sha256': sha(apk.read_bytes())}
            p07_command(kind + '-badging', [str(sdk / 'aapt'), 'dump', 'badging', str(apk)])
            p07_command(kind + '-manifest', [str(sdk / 'aapt'), 'dump', 'xmltree', str(apk), 'AndroidManifest.xml'])
            p07_command(kind + '-signature', [str(sdk / 'apksigner'), 'verify', '--print-certs', str(apk)])
            classes = sorted(apk_classes(apk))
            row['diagnosticClasses'] = [c for c in classes if any(
                s in c for s in ['B2G2RuntimeTest', 'AndroidJUnitRunner', 'AndroidJUnit4', 'org/junit/', 'jna/'])]
            row['classCount'] = len(classes)
            with zipfile.ZipFile(apk) as archive:
                row['licenseEntries'] = [n for n in archive.namelist() if re.search(r'license|notice|jna', n, re.I)]
                for name in archive.namelist():
                    if re.fullmatch(r'classes\d*\.dex', name):
                        dex = REPORT / 'p07' / (kind + '-' + name)
                        dex.write_bytes(archive.read(name))
                        # No -d disassembly: preserve class/method/annotation metadata for discovery review.
                        p07_command(kind + '-' + name + '-metadata', [str(sdk / 'dexdump'), '-a', '-f', str(dex)], timeout=30)
            rows.append(row)
    write_json('p07-apks.json', rows)


def p07_result_index():
    rows = []
    build_root = HARNESS / 'build'
    for directory in ['outputs/androidTest-results', 'reports/androidTests', 'outputs/logs']:
        for path in (build_root / directory).rglob('*'):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            rows.append({'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)})
            if directory == 'outputs/logs':
                destination = REPORT / 'p07' / ('gradle-' + path.name)
                destination.write_bytes(raw)
    write_json('p07-connected-results-index.json', {
        'files': rows, 'note': 'Original XML/PROTO retained by workflow; no generated or substituted test result.',
        'acceptanceCommand': ':connectedReleaseAndroidTest', 'extraInstrumentationInvocation': False,
        'discoveryStatus': 'NOT-VERIFIED_UNTIL_RUNNER_AND_DEX_EVIDENCE_REVIEW',
    })


def p07_license_diagnostics():
    cache = pathlib.Path(os.environ.get('GRADLE_USER_HOME', pathlib.Path.home() / '.gradle')) / 'caches/modules-2/files-2.1'
    graphs = []
    for name in ['p06-classpaths.json', 'toolchain-graph.json']:
        graphs.extend(json.loads((REPORT / name).read_text())['graphs'])
    rows = []
    for inventory in ['dependencies.cdx', 'build-logic.cdx']:
        source = json.loads((REPORT / (inventory + '-license-provenance.json')).read_text())
        for entry in source['components']:
            if 'net.java.dev.jna/' not in entry['component'] and entry['status'] != 'NOT-VERIFIED':
                continue
            row = {'inventory': inventory, 'original': entry, 'graphMembership': [], 'rawPom': []}
            for graph in graphs:
                for component in graph['components']:
                    purl = 'pkg:maven/' + component['group'] + '/' + component['name'] + '@' + component['version']
                    if purl == entry['component']:
                        row['graphMembership'].append(graph['scope'])
            coordinate = entry['component'].removeprefix('pkg:maven/').replace('@', '/').split('/')
            if len(coordinate) == 3:
                group, name, version = coordinate
                for path in (cache / group / name / version).glob('*/*.pom'):
                    raw = path.read_bytes()
                    destination = REPORT / 'p07' / (inventory + '-' + name + '-' + version + '.pom')
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(raw)
                    root = ET.fromstring(raw)
                    declarations = []
                    for node in root.iter():
                        if node.tag.rsplit('}', 1)[-1] == 'license':
                            declarations.append({child.tag.rsplit('}', 1)[-1]: child.text for child in node})
                    row['rawPom'].append({'path': str(destination.relative_to(ROOT)), 'sha256': sha(raw),
                                          'rootTag': root.tag, 'allNamespaceLicenseDeclarations': declarations})
            row['assessment'] = 'READ_ONLY_DECLARATIONS_NOT_LEGAL_APPROVAL_NO_INVENTORY_REWRITE'
            rows.append(row)
    write_json('p07-license-review.json', rows)


def instrument():
    p07_safe('apk', p07_apk_diagnostics)
    p07_safe('before', lambda: p07_snapshot('before'))
    command('device-properties', ['adb', 'shell', 'getprop'])
    command('page-size', ['adb', 'shell', 'getconf', 'PAGE_SIZE'], required=False)
    command('device-memory-before', ['adb', 'shell', 'dumpsys', 'meminfo'])
    command('kernel', ['adb', 'shell', 'uname', '-a'])
    emulator = str(pathlib.Path(os.environ['ANDROID_HOME']) / 'emulator/emulator')
    command('emulator-version', [emulator, '-no-window', '-version'])
    command('acceleration', [emulator, '-accel-check'])
    try:
        command('clear-logcat', ['adb', 'logcat', '-c'], split_streams=True)
    except Exception:
        p07_safe('clear-failed', lambda: p07_snapshot('clear-failed'))
        raise
    try:
        gradle('instrumented', ':connectedReleaseAndroidTest')
    finally:
        stream = command('metric-stream', ['adb', 'logcat', '-d', '-v', 'raw', '-s', 'B2_G2_METRIC:I', '*:S'],
                         required=False).stdout
        rows = [json.loads(line) for line in stream.splitlines() if line.startswith('{')]
        (REPORT / 'metrics.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
        command('device-memory-after', ['adb', 'shell', 'dumpsys', 'meminfo'], required=False)
        p07_safe('after', lambda: p07_snapshot('after'))
        p07_safe('results', p07_result_index)
        p08_runtime_observation()
        p07_safe('p10-runtime', lambda: p10_closure('runtime'))


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


def dex_public_static_definitions(raw, descriptor):
    """Read encoded class_data definitions, not merely method_ids references."""
    assert raw[:4] == b'dex\n'
    u32 = lambda offset: struct.unpack_from('<I', raw, offset)[0]

    def uleb(offset):
        value, shift = 0, 0
        while True:
            byte = raw[offset]
            offset += 1
            value |= (byte & 127) << shift
            if not byte & 128:
                return value, offset
            shift += 7
            assert shift < 35, 'Invalid DEX ULEB128'

    strings = []
    for index in range(u32(56)):
        offset = u32(u32(60) + index * 4)
        _, offset = uleb(offset)
        strings.append(raw[offset:raw.index(b'\x00', offset)].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68) + index * 4)] for index in range(u32(64))]
    found = set()
    for index in range(u32(96)):
        entry = u32(100) + index * 32
        if types[u32(entry)] != descriptor:
            continue
        offset = u32(entry + 24)
        if not offset:
            continue
        sizes = []
        for _ in range(4):
            value, offset = uleb(offset)
            sizes.append(value)
        for _ in range(sizes[0] + sizes[1]):
            _, offset = uleb(offset)
            _, offset = uleb(offset)
        for count in sizes[2:]:
            method_index = 0
            for _ in range(count):
                delta, offset = uleb(offset)
                flags, offset = uleb(offset)
                _, offset = uleb(offset)
                method_index += delta
                owner, prototype, name = struct.unpack_from('<HHI', raw, u32(92) + method_index * 8)
                assert types[owner] == descriptor
                if flags & 9 != 9:
                    continue
                _, result, parameters = struct.unpack_from('<III', raw, u32(76) + prototype * 12)
                arguments = '' if not parameters else ''.join(
                    types[struct.unpack_from('<H', raw, parameters + 4 + parameter * 2)[0]]
                    for parameter in range(u32(parameters)))
                found.add(strings[name] + '(' + arguments + ')' + types[result])
    return found


def verify_p08_apks():
    targets = list((HARNESS / 'build/outputs/apk/release').glob('*.apk'))
    tests = list((HARNESS / 'build/outputs/apk/androidTest/release').glob('*.apk'))
    assert len(targets) == len(tests) == 1, 'STOP P08: missing/ambiguous APK pair'
    target, test = targets[0], tests[0]
    target_classes, test_classes = apk_classes(target), apk_classes(test)
    definitions = set()
    with zipfile.ZipFile(target) as archive:
        for name in archive.namelist():
            if re.fullmatch(r'classes\d*\.dex', name):
                definitions |= dex_public_static_definitions(archive.read(name), 'Landroidx/tracing/Trace;')
    usage = (HARNESS / 'build/outputs/mapping/release/usage.txt').read_text()
    lines = (REPORT / 'build.log').read_text().splitlines()
    tasks = [line for line in lines if line.startswith('> Task :minifyReleaseWithR8')
             or line.startswith('> Task :minifyReleaseAndroidTestWithR8')]
    facts = {
        'traceTargetDefinition': 'Landroidx/tracing/Trace;' in target_classes,
        'traceTestDefinition': 'Landroidx/tracing/Trace;' in test_classes,
        'targetPublicStaticMethods': sorted(definitions),
        'canaryRemoved': 'B2G2UnreachableCanary' in usage and not any('B2G2UnreachableCanary' in c for c in target_classes),
        'r8Executed': len(tasks) == 2 and not any(any(flag in line for flag in ['SKIPPED', 'NO-SOURCE', 'UP-TO-DATE', 'FROM-CACHE'])
                                              for line in tasks),
    }
    # Persist actual facts before assertion, including a failed R8/class/member oracle.
    write_json('p08-trace-apks.json', {
        'authority': 'Issue16 comment6359936855', 'facts': facts, 'r8TaskLog': tasks,
        'targetApkSha256': sha(target.read_bytes()), 'testApkSha256': sha(test.read_bytes()),
        'classification': 'OBSERVED_NOT_RUNTIME_ACCEPTANCE',
    })
    validate_p08_apk_facts(facts)


def p08_runtime_observation():
    totals = dict(tests=0, failures=0, errors=0, skipped=0)
    for path in (HARNESS / 'build/outputs/androidTest-results').rglob('*.xml'):
        for suite in ET.parse(path).getroot().iter('testsuite'):
            for key in totals:
                totals[key] += int(suite.get(key, 0))
    metrics = (REPORT / 'metrics.jsonl').read_text().splitlines()
    crash = REPORT / 'p07/after-crash-logcat.stdout.log'
    raw = crash.read_text(errors='replace') if crash.exists() else ''
    trace_crash = bool(re.search(r'(?:NoClassDefFoundError|ClassNotFoundException|NoSuchMethodError).*?(?:androidx[/.]tracing|forceEnableAppTracing)', raw))
    passed = totals == dict(tests=5, failures=0, errors=0, skipped=0) and len(metrics) == 20 and not trace_crash
    write_json('p08-runtime-observation.json', {
        'status': 'PASS' if passed and crash.exists() else 'FAIL', 'junit': totals, 'metricsRows': len(metrics),
        'traceCrashObserved': trace_crash, 'crashEvidencePresent': crash.exists(),
        'crashLogSha256': sha(crash.read_bytes()) if crash.exists() else None,
        'note': 'Runtime observation only; all original JNI/KAT/metrics/environment/security/signature gates remain mandatory.',
    })


# Diagnostic-only decoder. Instruction widths follow AOSP dex_instruction_list.h;
# provenance and limits are recorded in B2_G2_PROTOCOL.md, never fetched during CI.
P10_WIDTHS = '1123123123111111111232235223211221223331123332222222222222222200000022222222222222222222222222222222222222222233333033333001111111111111111111112222222222222222222222222222222211111111111111111111111111111111222222222222222222200000000000000000000000443322'


def p10_types(descriptor):
    # Member identifiers are not descriptors: getClassLoader()/LEVEL must not create
    # fictitious types beginning at the 'L' in the identifier.
    if '(' in descriptor:
        descriptor = descriptor[descriptor.index('('):]
    elif ':' in descriptor:
        descriptor = descriptor.split(':', 1)[1]
    found = re.findall(r'L[^;]+;', descriptor)
    assert all(re.fullmatch(r'L[^;():\[\]]+;', name) for name in found), 'Invalid diagnostic descriptor'
    return found


def p10_dex(raw, source):
    """Definitions and actual instruction/annotation sites; no execution or APK changes."""
    assert raw[:4] == b'dex\n' and len(P10_WIDTHS) == 256
    u16 = lambda o: struct.unpack_from('<H', raw, o)[0]
    u32 = lambda o: struct.unpack_from('<I', raw, o)[0]
    assert u32(36) == 112 and u32(40) == 0x12345678, 'Unsupported DEX header/container/endian'

    def leb(o, signed=False):
        value, shift = 0, 0
        while True:
            byte = raw[o]; o += 1
            value |= (byte & 127) << shift; shift += 7
            assert shift <= 35
            if not byte & 128:
                return value - (1 << shift) if signed and byte & 64 else value, o

    strings = []
    for i in range(u32(56)):
        _, o = leb(u32(u32(60) + i * 4))
        strings.append(raw[o:raw.index(b'\x00', o)].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68) + i * 4)] for i in range(u32(64))]
    known_types = {t.lstrip('[') for t in types}

    def typelist(o):
        return [] if not o else [types[u16(o + 4 + i * 2)] for i in range(u32(o))]

    protos = []
    for i in range(u32(72)):
        _, ret, params = struct.unpack_from('<III', raw, u32(76) + i * 12)
        protos.append('(' + ''.join(typelist(params)) + ')' + types[ret])
    fields, methods = [], []
    for i in range(u32(80)):
        c, t, n = struct.unpack_from('<HHI', raw, u32(84) + i * 8)
        fields.append((types[c], strings[n] + ':' + types[t]))
    for i in range(u32(88)):
        c, p, n = struct.unpack_from('<HHI', raw, u32(92) + i * 8)
        methods.append((types[c], strings[n] + protos[p]))
    maps = {}
    if u32(52):
        for i in range(u32(u32(52))):
            kind, _, count, offset = struct.unpack_from('<HHII', raw, u32(52) + 4 + i * 12)
            maps[kind] = (count, offset)
    refs, definitions, errors = [], {}, []

    def add(type_name, kind, owner, member='', target_member='', pc=None, line=None, detail=''):
        for base in p10_types(type_name):
            assert base in known_types, 'P10 reference is not an actual DEX type: ' + base
            refs.append(dict(type=base, kind=kind, owner=owner, member=member, referencedMember=target_member,
                             dexPc=pc, dexLine=line, detail=detail))

    def symbol(table, index, kind, owner, member, pc=None, line=None):
        target, signature = table[index]
        add(target, kind, owner, member, signature, pc, line)
        add(signature, kind + '_SIGNATURE', owner, member, signature, pc, line)
        return target + '->' + signature

    def handle(index, kind, owner, member, pc=None, line=None):
        count, base = maps.get(8, (0, 0)); assert index < count
        category, _, index, _ = struct.unpack_from('<HHHH', raw, base + index * 8)
        symbol(fields if category <= 3 else methods, index, kind, owner, member, pc, line)

    def annotation(o, owner, member, kind):
        index, o = leb(o); add(types[index], kind, owner, member)
        size, o = leb(o)
        for _ in range(size):
            _, o = leb(o); o = encoded(o, owner, member, kind)
        return o

    def encoded(o, owner, member, kind):
        tag = raw[o]; o += 1; value_type, width = tag & 31, (tag >> 5) + 1
        if value_type == 0x1c:
            count, o = leb(o)
            for _ in range(count): o = encoded(o, owner, member, kind)
        elif value_type == 0x1d:
            o = annotation(o, owner, member, kind)
        elif value_type not in [0x1e, 0x1f]:
            value = int.from_bytes(raw[o:o + width], 'little'); o += width
            if value_type == 0x18: add(types[value], kind, owner, member)
            elif value_type in [0x19, 0x1b]: symbol(fields, value, kind, owner, member)
            elif value_type == 0x1a: symbol(methods, value, kind, owner, member)
            elif value_type == 0x15: add(protos[value], kind, owner, member)
            elif value_type == 0x16: handle(value, kind, owner, member)
        return o

    def annotations(o, owner, member):
        if not o: return
        for i in range(u32(o)):
            at = u32(o + 4 + i * 4)
            annotation(at + 1, owner, member, 'ANNOTATION_' + str(raw[at]))

    def debug_positions(o, owner, member):
        positions = []
        if not o: return positions
        line, o = leb(o); count, o = leb(o)
        for _ in range(count): _, o = leb(o)
        pc = 0
        while True:
            op = raw[o]; o += 1
            if op == 0: break
            if op == 1:
                delta, o = leb(o); pc += delta
            elif op == 2:
                delta, o = leb(o, True); line += delta
            elif op in [3, 4]:
                _, o = leb(o); _, o = leb(o); type_index, o = leb(o)
                if type_index: add(types[type_index - 1], 'DEBUG_METADATA', owner, member)
                if op == 4: _, o = leb(o)
            elif op in [5, 6, 9]: _, o = leb(o)
            elif op >= 10:
                pc += (op - 10) // 15; line += -4 + (op - 10) % 15
                positions.append((pc, line))
        return positions

    def code(o, owner, member):
        size, tries, debug = u32(o + 12), u16(o + 6), u32(o + 8)
        positions = debug_positions(debug, owner, member)
        units = [u16(o + 16 + i * 2) for i in range(size)]
        pc, position_index, line = 0, 0, None
        while pc < size:
            while position_index < len(positions) and positions[position_index][0] <= pc:
                line = positions[position_index][1]; position_index += 1
            word = units[pc]; op = word & 255
            if op == 0 and word:
                if word == 0x100: width = 4 + units[pc + 1] * 2
                elif word == 0x200: width = 2 + units[pc + 1] * 4
                elif word == 0x300: width = 4 + (units[pc + 1] * (units[pc + 2] | units[pc + 3] << 16) + 1) // 2
                else: raise ValueError('Unknown DEX payload ' + str(word))
            else:
                width = int(P10_WIDTHS[op]); assert width > 0 and pc + width <= size, ('Unsupported opcode', op, pc)
                if op in [0x1c, 0x1f, 0x20, 0x22, 0x23, 0x24, 0x25]:
                    kind = 'NEW_INSTANCE' if op == 0x22 else 'TYPE_INSTRUCTION'
                    add(types[units[pc + 1]], kind, owner, member, pc=pc, line=line, detail=hex(op))
                elif 0x52 <= op <= 0x6d:
                    symbol(fields, units[pc + 1], 'FIELD_ACCESS_' + hex(op), owner, member, pc, line)
                elif 0x6e <= op <= 0x72 or 0x74 <= op <= 0x78 or op in [0xfa, 0xfb]:
                    symbol(methods, units[pc + 1], 'INVOKE_' + hex(op), owner, member, pc, line)
                    if op in [0xfa, 0xfb]: add(protos[units[pc + 3]], 'DYNAMIC_PROTO', owner, member, pc=pc, line=line)
                elif op in [0xfc, 0xfd]:
                    count, at = maps.get(7, (0, 0)); index = units[pc + 1]; assert index < count
                    at = u32(at + index * 4); count, at = leb(at)
                    for _ in range(count): at = encoded(at, owner, member, 'DYNAMIC_CALL_SITE')
                elif op == 0xfe: handle(units[pc + 1], 'METHOD_HANDLE', owner, member, pc, line)
                elif op == 0xff: add(protos[units[pc + 1]], 'METHOD_TYPE', owner, member, pc=pc, line=line)
            pc += width
        assert pc == size
        if tries:
            at = o + 16 + size * 2 + (2 if size % 2 else 0) + tries * 8
            count, at = leb(at)
            for _ in range(count):
                number, at = leb(at, True)
                for _ in range(abs(number)):
                    index, at = leb(at); address, at = leb(at)
                    add(types[index], 'CATCH_TYPE', owner, member, pc=address)
                if number <= 0: _, at = leb(at)

    for i in range(u32(96)):
        at = u32(100) + i * 32
        c, flags, parent, interfaces, _, ann, data, values = struct.unpack_from('<IIIIIIII', raw, at)
        owner = types[c]
        info = dict(flags=flags, superclass=None if parent == 0xffffffff else types[parent],
                    interfaces=typelist(interfaces), methods={}, fields={})
        definitions[owner] = info
        for t in [info['superclass'], *info['interfaces']]:
            if t: add(t, 'SUPERCLASS' if t == info['superclass'] else 'INTERFACE', owner)
        if data:
            sizes = []
            for _ in range(4): value, data = leb(data); sizes.append(value)
            for count in sizes[:2]:
                index = 0
                for _ in range(count):
                    delta, data = leb(data); access, data = leb(data); index += delta
                    field_owner, member = fields[index]; assert field_owner == owner
                    info['fields'][member] = access; add(member, 'FIELD_SIGNATURE', owner, member)
            for count in sizes[2:]:
                index = 0
                for _ in range(count):
                    delta, data = leb(data); access, data = leb(data); code_offset, data = leb(data); index += delta
                    method_owner, member = methods[index]; assert method_owner == owner
                    info['methods'][member] = dict(flags=access, codeOffset=code_offset)
                    add(member, 'METHOD_SIGNATURE', owner, member)
                    if code_offset:
                        try: code(code_offset, owner, member)
                        except (AssertionError, IndexError, ValueError, struct.error) as error:
                            errors.append(dict(owner=owner, member=member, codeOffset=code_offset, error=str(error)))
        if values:
            count, values = leb(values)
            for _ in range(count): values = encoded(values, owner, '', 'STATIC_ENCODED_VALUE')
        if ann:
            annotations(u32(ann), owner, '')
            at = ann + 16
            for table, count in [(fields, u32(ann + 4)), (methods, u32(ann + 8))]:
                for _ in range(count):
                    index, offset = struct.unpack_from('<II', raw, at); at += 8
                    annotations(offset, owner, table[index][1])
            for _ in range(u32(ann + 12)):
                index, offset = struct.unpack_from('<II', raw, at); at += 8
                for parameter in range(u32(offset)):
                    annotations(u32(offset + 4 + parameter * 4), owner, methods[index][1] + ':parameter' + str(parameter))
    mentioned = {r['type'] for r in refs}
    for t in types:
        for base in p10_types(t):
            if base not in mentioned: add(base, 'TYPE_IDS_ONLY', '', detail='No decoded use site; not a requirement')
    return dict(source=source, dexSha256=sha(raw), definitions=definitions, references=refs, decodeErrors=errors)


def p10_classfile(raw):
    """Read declared ABI/hierarchy and CP symbols only; CP is not execution evidence."""
    assert raw[:4] == b'\xca\xfe\xba\xbe'
    u2 = lambda o: struct.unpack_from('>H', raw, o)[0]
    u4 = lambda o: struct.unpack_from('>I', raw, o)[0]
    pool, at, index, count = {}, 10, 1, u2(8)
    while index < count:
        tag = raw[at]; at += 1
        if tag == 1:
            size = u2(at); at += 2; pool[index] = (tag, raw[at:at + size].decode('utf-8', errors='replace')); at += size
        elif tag in [3, 4]: pool[index] = (tag, None); at += 4
        elif tag in [5, 6]: pool[index] = (tag, None); at += 8; index += 1
        elif tag in [7, 8, 16, 19, 20]: pool[index] = (tag, u2(at)); at += 2
        elif tag in [9, 10, 11, 12, 17, 18]: pool[index] = (tag, (u2(at), u2(at + 2))); at += 4
        elif tag == 15: pool[index] = (tag, (raw[at], u2(at + 1))); at += 3
        else: raise ValueError('Unknown class constant pool tag ' + str(tag))
        index += 1
    text = lambda i: pool[i][1]
    typename = lambda i: 'L' + text(pool[i][1]) + ';' if i else None
    flags, owner, parent = u2(at), typename(u2(at + 2)), typename(u2(at + 4)); at += 6
    count = u2(at); at += 2; interfaces = [typename(u2(at + i * 2)) for i in range(count)]; at += count * 2
    members = {}
    for category in ['fields', 'methods']:
        count = u2(at); at += 2; declarations = []
        for _ in range(count):
            access, name, descriptor, attrs = struct.unpack_from('>HHHH', raw, at); at += 8
            declarations.append(dict(name=text(name), descriptor=text(descriptor), flags=access))
            for _ in range(attrs): at += 6 + u4(at + 2)
        members[category] = declarations
    symbols = []
    for tag, value in pool.values():
        if tag in [9, 10, 11]:
            c, signature = value; name, descriptor = pool[signature][1]
            symbols.append(dict(owner=typename(c), name=text(name), descriptor=text(descriptor),
                                kind='FIELD_CP' if tag == 9 else 'METHOD_CP'))
    return dict(owner=owner, flags=flags, superclass=parent, interfaces=interfaces, **members,
                symbols=symbols, classSha256=sha(raw), symbolsAre='CONSTANT_POOL_NOT_PER_METHOD_EXECUTION')


def p10_classification(type_name, sites, observed, structural, provider_known):
    if type_name in observed: return 'REQUIRED', 'OBSERVED_RUNTIME_MISSING_CLASS'
    if type_name in structural: return 'REQUIRED', 'SUPERCLASS_OR_INTERFACE_OF_OBSERVED_REQUIRED_TYPE'
    if sites and all(s['kind'].startswith(('ANNOTATION_', 'DEBUG_METADATA')) for s in sites):
        return 'ANNOTATION-METADATA', 'ONLY_TYPED_ANNOTATION_DEBUG_SITES_NOT_PROOF_OF_RUNTIME_NEED'
    if not provider_known or not sites or all(s['kind'] == 'TYPE_IDS_ONLY' for s in sites):
        return 'UNKNOWN', 'NO_PROVIDER_OR_NO_DECODED_USE_SITE'
    return 'CONDITIONAL', 'STATIC_REFERENCE_WITHOUT_EXECUTION_OR_BRANCH_PROOF'


def p10_negative_controls():
    site = lambda kind: [{'kind': kind}]
    cases = [
        ('observed', p10_classification('LX;', site('TYPE_IDS_ONLY'), {'LX;'}, set(), True)[0], 'REQUIRED'),
        ('structural', p10_classification('LX;', [], set(), {'LX;'}, True)[0], 'REQUIRED'),
        ('invoke-not-observed', p10_classification('LX;', site('INVOKE_0x70'), set(), set(), True)[0], 'CONDITIONAL'),
        ('annotation-only', p10_classification('LX;', site('ANNOTATION_1'), set(), set(), True)[0], 'ANNOTATION-METADATA'),
        ('mixed-annotation-invoke', p10_classification('LX;', site('ANNOTATION_1') + site('INVOKE_0x70'), set(), set(), True)[0], 'CONDITIONAL'),
        ('type-pool-only', p10_classification('LX;', site('TYPE_IDS_ONLY'), set(), set(), True)[0], 'UNKNOWN'),
        ('provider-unknown', p10_classification('LX;', site('FIELD_SIGNATURE'), set(), set(), False)[0], 'UNKNOWN'),
        ('signature-not-executed', p10_classification('LX;', site('METHOD_SIGNATURE'), set(), set(), True)[0], 'CONDITIONAL'),
        ('debug-only', p10_classification('LX;', site('DEBUG_METADATA'), set(), set(), True)[0], 'ANNOTATION-METADATA'),
        ('method-name-L', p10_types('getClassLoader()Ljava/lang/ClassLoader;'), ['Ljava/lang/ClassLoader;']),
        ('field-name-L', p10_types('LEVEL:Ljava/lang/String;'), ['Ljava/lang/String;']),
        ('primitive-method-name-L', p10_types('nativeLoad()V'), []),
        ('array-parameter-return', p10_types('load(Ljava/lang/String;[Lfoo/Bar;)Lkotlin/Unit;'),
         ['Ljava/lang/String;', 'Lfoo/Bar;', 'Lkotlin/Unit;']),
    ]
    for case, reader in [('reject-non-dex', lambda: p10_dex(b'not-a-dex', {})),
                         ('reject-non-classfile', lambda: p10_classfile(b'not-a-classfile'))]:
        try:
            reader()
        except AssertionError:
            cases.append((case, 'REJECTED', 'REJECTED'))
        else:
            raise AssertionError('P10 invalid diagnostic input accepted: ' + case)
    for case, actual, expected in cases: assert actual == expected, (case, actual, expected)
    return dict(status='PASS', cases=[dict(case=c, result='PASS', expected=e) for c, _, e in cases],
                acceptanceChanged=False, note='Classification controls, not runtime tests')


def p10_closure(phase):
    controls = p10_negative_controls()
    output = REPORT / ('p10-' + phase); output.mkdir(exist_ok=True)
    documents, manifest = [], []
    for kind, directory in [('target', 'release'), ('test', 'androidTest/release')]:
        apks = list((HARNESS / 'build/outputs/apk' / directory).glob('*.apk')); assert len(apks) == 1
        apk = apks[0]; apk_hash = sha(apk.read_bytes())
        with zipfile.ZipFile(apk) as archive:
            for entry in archive.namelist():
                if not re.fullmatch(r'classes\d*\.dex', entry): continue
                source = dict(apk=kind, path=str(apk.relative_to(ROOT)), apkSha256=apk_hash, entry=entry)
                document = p10_dex(archive.read(entry), source); documents.append(document)
                file = output / (kind + '-' + entry + '.json'); file.write_text(json.dumps(document, indent=2) + '\n')
                manifest.append(dict(path=str(file.relative_to(ROOT)), sha256=sha(file.read_bytes())))
    definitions, sites = {}, {}
    for document in documents:
        for name, info in document['definitions'].items():
            definitions.setdefault(name, []).append(dict(source=document['source'], dexSha256=document['dexSha256'], **info))
        for ref in document['references']:
            sites.setdefault(ref['type'], []).append(dict(source=document['source'], dexSha256=document['dexSha256'], **ref))
    inputs_path = REPORT / 'p06-r8-inputs.json'; inputs = json.loads(inputs_path.read_text())
    resolution = json.loads((REPORT / 'p08-classpaths.json').read_text())['graphs']
    jars, library_index, boot, unindexed = {}, {}, set(), []
    for role in ['referencedClasses', 'programClasses', 'bootClasspath']:
        for row in inputs[role]:
            path = pathlib.Path(row['path'])
            if not path.is_file() or path.suffix != '.jar':
                unindexed.append(dict(role=role, path=str(path), reason='NOT_JAR_NOT_INDEXED; actual program DEX still decoded'))
                continue
            assert sha(path.read_bytes()) == row['sha256'], 'P10 input hash changed after R8 observation'
            jars[str(path)] = row
            with zipfile.ZipFile(path) as archive:
                for entry in archive.namelist():
                    if not entry.endswith('.class') or entry.startswith('META-INF/versions/'): continue
                    name = 'L' + entry[:-6] + ';'
                    if role == 'bootClasspath': boot.add(name)
                    else:
                        coordinate = re.search(r'/files-2\.1/([^/]+)/([^/]+)/([^/]+)/', str(path))
                        component = ':'.join(coordinate.groups()) if coordinate else None
                        scopes = [g['scope'] for g in resolution if component and any(
                            ':'.join(c[k] for k in ['group', 'name', 'version']) == component for c in g['components'])]
                        library_index.setdefault(name, []).append(dict(role=role, path=str(path), jarSha256=row['sha256'], entry=entry,
                            componentFromCachePath=component, resolvedScopes=scopes,
                            componentOrigin='MAVEN_CACHE_PATH' if component else 'TRANSFORM_COORDINATE_NOT_VERIFIED'))
    observed, frames, crash_files = set(), [], []
    for filename in ['p07/after-crash-logcat.stdout.log', 'p07/after-runner-logcat.stdout.log']:
        path = REPORT / filename
        if not path.exists(): continue
        raw = path.read_bytes(); text = raw.decode('utf-8', errors='replace')
        crash_files.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(raw)))
        pids = set(re.findall(r'Process: com\.app\.moneymate\.b2g2, PID: (\d+)', text))
        # Filter exception evidence by the actual harness PID; unrelated system crashes cannot seed REQUIRED.
        text = '\n'.join(line for line in text.splitlines() if re.match(
            r'^\S+\s+\S+\s+(' + '|'.join(sorted(pids)) + r')\s', line)) if pids else ''
        observed.update(re.findall(r'Failed resolution of: (L[^;]+;)', text))
        observed.update('L' + name.replace('.', '/') + ';' for name in re.findall(r'ClassNotFoundException: ([\w.$]+)', text))
        frames.extend(dict(owner='L' + c.replace('.', '/') + ';', name=n, line=int(line))
                      for c, n, line in re.findall(r'\bat ([\w.$]+)\.([\w$<>]+)\([^\n():]+:(\d+)\)', text))
    frames = [dict(owner=o, name=n, line=l) for o, n, l in sorted({(f['owner'], f['name'], f['line']) for f in frames})]
    required = set(observed); structural, required_reasons, headers = set(), {}, {}
    def header(name):
        if name in headers: return headers[name]
        providers = library_index.get(name, [])
        bodies = []
        for provider in providers:
            with zipfile.ZipFile(provider['path']) as archive: body = p10_classfile(archive.read(provider['entry']))
            bodies.append(dict(source=provider, **body))
        headers[name] = bodies; return bodies
    def member_definitions(name, signature):
        queue, seen, found = [name], set(), []
        while queue:
            current = queue.pop(0)
            if current in seen: continue
            seen.add(current)
            for body in header(current):
                for category in ['methods', 'fields']:
                    for declaration in body[category]:
                        candidate = declaration['name'] + (':' if category == 'fields' else '') + declaration['descriptor']
                        if candidate == signature:
                            found.append(dict(declaringClass=current, declaration=declaration,
                                              source=body['source'], classSha256=body['classSha256']))
                if body['superclass']: queue.append(body['superclass'])
                queue.extend(body['interfaces'])
        return found
    # Only unambiguous selected classfile hierarchies seed REQUIRED closure.
    queue = list(required)
    while queue:
        name = queue.pop(0); bodies = header(name)
        shapes = {(b['superclass'], tuple(b['interfaces'])) for b in bodies}
        if len(shapes) != 1: continue
        parent, interfaces = next(iter(shapes))
        for dependency in [parent, *interfaces]:
            if dependency and dependency not in definitions and dependency not in boot and dependency not in required:
                required.add(dependency); structural.add(dependency); queue.append(dependency)
                required_reasons[dependency] = dict(fromClass=name, kind='SELECTED_CLASSFILE_HIERARCHY')
    # Crash line + unique new-instance of a class with the failed superclass is additional evidence,
    # not a generic claim that every allocation/branch in a stack-frame method executed.
    allocation_evidence = []
    for frame in frames:
        matching = [r for group in sites.values() for r in group if r['owner'] == frame['owner']
                    and r['member'].split('(')[0] == ('<init>' if frame['name'] == '<init>' else frame['name'])
                    and r['dexLine'] == frame['line'] and r['kind'] == 'NEW_INSTANCE']
        unique = {r['type'] for r in matching}
        if len(unique) != 1: continue
        allocated = next(iter(unique)); infos = definitions.get(allocated, [])
        if len(infos) != 1 or infos[0]['superclass'] not in observed: continue
        allocation_evidence.append(dict(frame=frame, allocatedClass=allocated, sites=matching))
        for dependency in infos[0]['interfaces']:
            if dependency not in definitions and dependency not in boot:
                structural.add(dependency); required_reasons[dependency] = dict(fromClass=allocated, kind='UNIQUE_CRASH_LINE_ALLOCATION_INTERFACE')
    # Static program invoke graph: paths are potential paths, not executed traces.
    nodes = {owner + '->' + method for owner, infos in definitions.items() for info in infos for method in info['methods']}
    edges = {}
    for group in sites.values():
        for ref in group:
            if not ref['kind'].startswith('INVOKE_') or ref['kind'].endswith('_SIGNATURE'): continue
            source = ref['owner'] + '->' + ref['member']; target = ref['type'] + '->' + ref['referencedMember']
            if target in nodes: edges.setdefault(source, set()).add(target)
    roots = sorted(n for n in nodes if n.startswith('Landroidx/test/runner/AndroidJUnitRunner;->onCreate('))
    paths = {root: [root] for root in roots}; queue = list(roots)
    while queue:
        node = queue.pop(0)
        for target in sorted(edges.get(node, [])):
            if target not in paths: paths[target] = paths[node] + [target]; queue.append(target)
    candidates = sorted((set(sites) - set(definitions) - boot) | observed | structural)
    mappings = {}
    for kind, variant in [('target', 'release'), ('test', 'releaseAndroidTest')]:
        root = HARNESS / 'build/outputs/mapping' / variant
        mapping = (root / 'mapping.txt').read_text(); usage = (root / 'usage.txt').read_text()
        mappings[kind] = dict(mapping=mapping, usage=usage,
            files=[dict(path=str((root / f).relative_to(ROOT)), sha256=sha((root / f).read_bytes())) for f in ['mapping.txt', 'usage.txt']])
    rows = []
    for name in candidates:
        refs = sites.get(name, []); providers = library_index.get(name, [])
        category, reason = p10_classification(name, refs, observed, structural, bool(providers))
        body = header(name) if providers else []
        references = []
        for ref in refs:
            node = ref['owner'] + '->' + ref['member']
            primary_member = ref['kind'].startswith(('INVOKE_', 'FIELD_ACCESS_')) and not ref['kind'].endswith('_SIGNATURE')
            references.append(dict(**ref, potentialRunnerPath=paths.get(node), pathKind='STATIC_DIRECT_INVOKES_NOT_EXECUTION_PROOF',
                selectedLibraryMemberDefinitions=member_definitions(name, ref['referencedMember']) if primary_member else []))
        r8 = {}
        original = name[1:-1].replace('/', '.')
        for kind, evidence in mappings.items():
            match = re.search(r'^' + re.escape(original) + r' -> ([^\s]+):$', evidence['mapping'], re.M)
            r8[kind] = dict(mappingName=match.group(1) if match else None,
                            mappedDefinitionPresent=('L' + match.group(1).replace('.', '/') + ';' in definitions) if match else False,
                            usageLines=[l for l in evidence['usage'].splitlines() if l == original or l == original + ':'],
                            sources=evidence['files'])
        rows.append(dict(type=name, classification=category, reason=reason, requirementEvidence=required_reasons.get(name),
                         programDefinitions=definitions.get(name, []), references=references,
                         r8=r8, inputProviders=providers, selectedClassfileABI=body,
                         providerAmbiguous=len({b['classSha256'] for b in body}) > 1,
                         missingMemberProof='CLASS_MISSING; library declarations/CP symbols are expectations, not execution'))
    # javap disassembles selected JARs read-only, preserving per-library-method code evidence.
    # Classfile CP symbols above remain explicitly non-execution evidence.
    javap_groups = {}
    for row in rows:
        if row['classification'] == 'REQUIRED' or any(r['potentialRunnerPath'] for r in row['references']):
            providers = row['inputProviders']
            if len({p['jarSha256'] for p in providers}) == 1 and providers:
                javap_groups.setdefault(providers[0]['path'], set()).add(row['type'][1:-1].replace('/', '.'))
            for ref in row['references']:
                if not ref['potentialRunnerPath'] and row['classification'] != 'REQUIRED': continue
                for declaration in ref['selectedLibraryMemberDefinitions']:
                    javap_groups.setdefault(declaration['source']['path'], set()).add(
                        declaration['declaringClass'][1:-1].replace('/', '.'))
    javap = []
    for index, (jar, names) in enumerate(sorted(javap_groups.items())):
        label = 'p10-' + phase + '-javap-' + str(index)
        java_tool = str(pathlib.Path(os.environ['JAVA_HOME']) / 'bin/javap') if os.environ.get('JAVA_HOME') else 'javap'
        p07_command(label, [java_tool, '-p', '-s', '-c', '-classpath', jar, *sorted(names)], timeout=30)
        result = json.loads((REPORT / 'p07/commands.json').read_text())[-1]
        javap.append(dict(jar=jar, jarSha256=sha(pathlib.Path(jar).read_bytes()), classes=sorted(names),
                          commandsManifest=str((REPORT / 'p07/commands.json').relative_to(ROOT)), label=label,
                          status=result['status'], exit=result['exit']))
    graph = REPORT / 'p08-classpaths.json'
    errors = [dict(source=d['source'], **e) for d in documents for e in d['decodeErrors']]
    report = dict(authority='Issue16 comment6360661190', phase=phase, diagnosticOnly=True,
                  acceptanceChanged=False, status='COLLECTED' if not errors and all(j['status'] == 'OBSERVED' for j in javap) else 'PARTIAL_NOT_VERIFIED',
                  source=json.loads((REPORT / 'source.json').read_text()), negativeControls=controls,
                  dexReports=manifest, decodeErrors=errors, crashEvidence=crash_files,
                  observedMissingClasses=sorted(observed), crashFrames=frames, allocationEvidence=allocation_evidence,
                  selectedLibraryDisassembly=javap, unindexedR8Inputs=unindexed,
                  crossApkClassCollisions={n: ds for n, ds in definitions.items() if len(ds) > 1},
                  runnerRoots=roots, reachableProgramMethods=len(paths),
                  callGraphKind='DIRECT_INVOKE_TARGETS_ONLY_NO_VIRTUAL_DISPATCH_OR_BRANCH_PROOF',
                  programClassCounts={d['source']['apk']: len(d['definitions']) for d in documents},
                  bootDefinitionScope='COMPILE_SDK_BOOT_JAR_NOT_DEVICE_RUNTIME_PROOF',
                  resolvedGraph=dict(path=str(graph.relative_to(ROOT)), sha256=sha(graph.read_bytes())),
                  r8Inputs=dict(path=str(inputs_path.relative_to(ROOT)), sha256=sha(inputs_path.read_bytes())),
                  candidates=rows, counts={c: sum(r['classification'] == c for r in rows)
                      for c in ['REQUIRED', 'CONDITIONAL', 'ANNOTATION-METADATA', 'UNKNOWN']},
                  note='No keep/dependency proposal is applied. Conditional/metadata/unknown are not blanket runtime requirements.')
    path = output / 'closure.json'; path.write_text(json.dumps(report, indent=2) + '\n')
    lines = ['| Class | Classification | Reference sites | Runner path sites | Library providers |', '|---|---|---:|---:|---:|']
    for row in rows:
        lines.append('| ' + row['type'] + ' | ' + row['classification'] + ' | ' + str(len(row['references'])) + ' | '
                     + str(sum(bool(r['potentialRunnerPath']) for r in row['references'])) + ' | ' + str(len(row['inputProviders'])) + ' |')
    (output / 'closure.md').write_text('\n'.join(lines) + '\n\nFull per-member/source/hash evidence: closure.json and DEX reports. Static paths are not execution traces.\n')



def inspect():
    verify_toolchain()
    verify_catalog((HARNESS / 'gradle/libs.versions.toml').read_bytes())
    verify_test_resolution()
    verify_p08_graphs()
    verify_p08_apks()
    assert json.loads((REPORT / 'p08-runtime-observation.json').read_text())['status'] == 'PASS', 'P08 runtime observation failed'
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
    test_r8 = [line for line in (REPORT / 'build.log').read_text().splitlines()
               if line.startswith('> Task :minifyReleaseAndroidTestWithR8')]
    test_maps = [path for path in (HARNESS / 'build/outputs/mapping').rglob('mapping.txt')
                 if path.parent != mapping_root]
    assert not any(name.startswith('Lcom/google/errorprone/annotations/') for name in target_classes)
    assert not re.search(r'^com\.google\.errorprone\.annotations\.', mapping, re.M), 'P05 dependency in target mapping'
    test_mapping = '\n'.join(path.read_text() for path in test_maps)
    test_usage_paths = [path.parent / 'usage.txt' for path in test_maps if (path.parent / 'usage.txt').exists()]
    test_usage = '\n'.join(path.read_text() for path in test_usage_paths)
    annotation_classes = []
    for original in P05_CLASSES:
        match = re.search(r'^' + re.escape(original) + r' -> ([^\s]+):$', test_mapping, re.M)
        renamed = match.group(1) if match else original
        present = 'L' + renamed.replace('.', '/') + ';' in test_classes
        assert not present, 'P06 compile-only annotation packaged in test DEX'
        annotation_classes.append({
            'original': original, 'mappedName': renamed, 'presentInTestDex': present,
            'listedInTestUsage': original in test_usage,
            'classification': 'ABSENT_COMPILE_ONLY',
        })
    test_minification = {
        'taskLog': test_r8,
        'mappingFiles': [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())} for path in test_maps],
        'classification': 'R8_TASK_EXECUTED' if any(
            not any(flag in line for flag in ['SKIPPED', 'NO-SOURCE']) for line in test_r8
        ) else 'NOT-VERIFIED',
    }
    assert test_minification['classification'] == 'R8_TASK_EXECUTED', 'Test APK R8 not verified'
    assert not any(name.startswith('Lcom/google/errorprone/annotations/') for name in test_classes)
    assert not re.search(r'^com\.google\.errorprone\.annotations\.', test_mapping, re.M)
    write_json('p06-apk-isolation.json', {
        'testResolution': json.loads((REPORT / 'p06-test-resolution.json').read_text()),
        'targetErrorProneDependencyAbsent': True, 'annotationClasses': annotation_classes,
        'testUsageFiles': [{'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())}
                           for path in test_usage_paths],
        'targetApkSha256': sha(target.read_bytes()), 'testApkSha256': sha(test.read_bytes()),
        'testApkR8': test_minification,
        'note': 'P06: compile/library-only annotations absent from runtime graphs and both program DEX; JNI/KAT checked separately.',
    })
    write_json('summary.json', {
        'source': json.loads((REPORT / 'source.json').read_text()), 'cell': os.environ['G2_CELL'],
        'junit': totals, 'junitFiles': junit, 'metricsRows': len(metrics), 'metricsSha256': sha((REPORT / 'metrics.jsonl').read_bytes()),
        'r8Target': 'PASS', 'providerInTargetDex': 'PASS', 'providerAbsentFromTestDex': 'PASS',
        'canaryRemoved': 'PASS', 'providerClassMapping': provider, 'apkZip16KiB': 'PASS', 'elf': elf,
        'pageSize': expected_page, 'abi': 'x86_64', 'api': expected_api, 'hashes': hashes,
        'testApkMinification': test_minification,
        'arm64Runtime': 'ENV-BLOCKED', 'arm64Kernel16KiB': 'ENV-BLOCKED', 'nativeOom': 'NOT-VERIFIED',
        'page16KiBKind': 'SIMULATED_X86_USERSPACE' if expected_page == 16384 else '4_KiB',
    })
    print('PASS: isolated minified target, actual JNI/KAT/negative tests, DEX/mapping/canary and measured environment')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'build', 'instrument', 'inspect'])
    mode = parser.parse_args().mode
    globals()[mode]()
