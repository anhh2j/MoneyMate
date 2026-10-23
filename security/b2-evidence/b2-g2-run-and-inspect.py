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
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / 'security/b2-g2'
REPORT = HARNESS / 'build/reports/b2-g2'
BASE = '690a74af29897d43fcb9f4c58808ae6ea2e3365f'
ACCEPTED_B2 = 'be26d275d621c4a0c64ed9dd5fb89cad42bf91b2'
P05_CATALOG_ALIAS = b'b2-errorprone-annotations = { module = "com.google.errorprone:error_prone_annotations", version = "2.36.0" }\n'
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
    """Preserve every baseline byte; insert only ten P01 and one P03 exact records."""
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
    return text.encode()


def verify_metadata(raw):
    assert len(APPROVED_CHECKSUMS) == 11 and len(set(APPROVED_CHECKSUMS)) == 11
    assert raw == approved_metadata(), 'STOP: metadata differs from baseline plus exact ten P01 and one P03 additions'


def approved_catalog():
    baseline = subprocess.check_output(['git', 'show', ACCEPTED_B2 + ':gradle/libs.versions.toml'], cwd=ROOT)
    assert baseline.count(b'[libraries]\n') == 1
    return baseline.replace(b'[libraries]\n', b'[libraries]\n' + P05_CATALOG_ALIAS, 1)


def verify_catalog(raw):
    assert raw == approved_catalog(), 'STOP: catalog differs from baseline plus exact P05 alias'


def catalog_negative_controls(raw):
    verify_catalog(raw)
    controls = {
        'alias-missing': raw.replace(P05_CATALOG_ALIAS, b''),
        'alias-version-drift': raw.replace(P05_CATALOG_ALIAS, P05_CATALOG_ALIAS.replace(b'2.36.0', b'2.27.0')),
        'baseline-version-drift': raw.replace(b'agp = "9.4.1"', b'agp = "9.4.0"'),
        'extra-alias': raw + b'\nunapproved = { id = "synthetic.plugin", version = "1" }\n',
        'alias-renamed': raw.replace(b'b2-errorprone-annotations =', b'b2-unapproved-annotations ='),
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


def verify_scope(changes):
    assert len(PATHS) == 12 and len(set(PATHS)) == 12, 'STOP: expected exact P04 twelve-path allowlist'
    assert sorted(changes) == sorted('A\t' + p for p in PATHS), changes


def guard_negative_controls(metadata):
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
    ]
    results = []
    for name, guard, value in checks:
        try:
            guard(value)
        except AssertionError:
            results.append({'case': name, 'result': 'REJECTED'})
        else:
            raise AssertionError('Guard accepted negative control: ' + name)
    write_json('p04-negative-controls.json', {'status': 'PASS', 'controls': results, 'sourceFilesMutated': False})


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
    write_json('catalog-policy.json', {'authority': 'Issue16 comment6357366408', 'acceptedB2': ACCEPTED_B2,
                                       'baselineSha256': sha(reference), 'catalogSha256': sha(catalog),
                                       'approvedInsertion': P05_CATALOG_ALIAS.decode().strip()})
    metadata = (HARNESS / 'gradle/verification-metadata.xml').read_bytes()
    verify_metadata(metadata)
    guard_negative_controls(metadata)
    write_json('checksum-policy.json', {'baselineArtifactRecords': 784, 'approvedAdditions': APPROVED_CHECKSUMS,
                                       'p01Additions': 10, 'p03Additions': 1, 'totalArtifactRecords': 795,
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
    def scopes = ['releaseAndroidTestCompileClasspath', 'releaseAndroidTestRuntimeClasspath', 'releaseRuntimeClasspath']
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
    new File(output, 'p06-classpaths.json').text = JsonOutput.toJson([graphs: graphs, capturedBeforeTask: task.path])
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


def instrument():
    command('device-properties', ['adb', 'shell', 'getprop'])
    command('page-size', ['adb', 'shell', 'getconf', 'PAGE_SIZE'], required=False)
    command('device-memory-before', ['adb', 'shell', 'dumpsys', 'meminfo'])
    command('kernel', ['adb', 'shell', 'uname', '-a'])
    emulator = str(pathlib.Path(os.environ['ANDROID_HOME']) / 'emulator/emulator')
    command('emulator-version', [emulator, '-no-window', '-version'])
    command('acceleration', [emulator, '-accel-check'])
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
    verify_toolchain()
    verify_catalog((HARNESS / 'gradle/libs.versions.toml').read_bytes())
    verify_test_resolution()
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
