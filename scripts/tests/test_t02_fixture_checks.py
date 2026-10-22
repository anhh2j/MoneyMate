"""Independent mutations of the safe corpus; no real bank input and no production tests."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import zipfile

SPEC = importlib.util.spec_from_file_location('t02_checks', pathlib.Path(__file__).resolve().parents[1] / 't02_fixture_checks.py')
t02 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(t02)
ROWS = []


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class FixtureChecksTest(unittest.TestCase):
    def control(self, control, subcase, rule, mutate, refresh=True):
        before = hashes(t02.ROOT / 'fixtures')
        with tempfile.TemporaryDirectory(prefix='t02-safe-') as tmp:
            root = pathlib.Path(tmp) / 'fixtures'
            shutil.copytree(t02.ROOT / 'fixtures', root)
            m = t02.strict_json(root / 'manifest.json')
            scenarios = t02.strict_json(root / 'scenarios.json')
            mutate(root, m, scenarios)
            if refresh:
                for c in m['cases']:
                    for path_key, hash_key in (('inputPath', 'inputSha256'), ('expectedPath', 'expectedSha256')):
                        path = root / c[path_key]
                        if path.is_file() and not path.is_symlink():
                            c[hash_key] = t02.digest(path)
            dump(root / 'manifest.json', m)
            dump(root / 'scenarios.json', scenarios)
            with self.assertRaises(t02.Invalid) as raised:
                t02.validate(root)
            self.assertEqual(rule, raised.exception.rule, subcase)
        self.assertEqual(before, hashes(t02.ROOT / 'fixtures'))
        ROWS.append(dict(control=control, subcase=subcase, result='PASS', expected=rule, observed=raised.exception.rule, originalUnchanged=True))

    def test_clean_deterministic_pending_and_c09(self):
        first = t02.validate()
        self.assertEqual(first, t02.validate())
        self.assertFalse(first['acceptedCorpus'])
        self.assertEqual(15, len(first['pendingApprovals']))
        self.assertEqual(3, len(first['unresolvedOracles']))
        self.assertEqual(72, first['scenarioCount'])
        self.assertEqual('PASS', t02.qa_c09(t02.ROOT)['result'])
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual('NA', t02.qa_c09(pathlib.Path(empty))['result'])
        with self.assertRaises(t02.Invalid):
            t02.validate(require_approved=True)

    def test_approved_content_plan_and_preserved_bytes(self):
        import subprocess
        result = t02.validate()
        self.assertEqual({'transactions': 6, 'noise': 6, 'missingAmount': 3}, result['contentCounts'])
        self.assertEqual(15, len(result['contentInventory']))
        manifest = t02.strict_json(t02.ROOT / 'fixtures/manifest.json')
        prior = json.loads(subprocess.check_output(['git', 'show', 'c5a67c2:fixtures/manifest.json'], cwd=t02.ROOT))
        edited = {'bidv_noise_promotion_01', 'msb_txn_in_01', 'mb_txn_in_01', 'mb_txn_out_01', 'mb_invalid_missing_amount_01', 'mb_noise_notice_01', 'mb_noise_promotion_01'}
        for case, old in zip(manifest['cases'], prior['cases']):
            self.assertEqual(old['id'], case['id'])
            for key in case:
                if key not in ('inputSha256', 'approval'):
                    self.assertEqual(old[key], case[key])
            for field in ('inputPath', 'expectedPath'):
                if field == 'expectedPath' or case['id'] not in edited:
                    before = subprocess.check_output(['git', 'show', 'c5a67c2:fixtures/' + case[field]], cwd=t02.ROOT)
                    self.assertEqual(before, (t02.ROOT / 'fixtures' / case[field]).read_bytes())
        for bank in ('bidv', 'mb'):
            _, title, _, _ = t02.parse_text(t02.ROOT / 'fixtures' / bank / 'noise_promotion_01.txt')
            self.assertTrue(title.startswith('🎁 '))

    def test_po_privacy_recording_preserves_source_and_qa_gate(self):
        import subprocess
        source = '547bc6c05d3655fd8d02635e038d9f0292b75118'
        reference = 'REVIEW_PO_T02_PRIVACY_SIGNOFF_A'
        manifest = t02.strict_json(t02.ROOT / 'fixtures/manifest.json')
        prior = json.loads(subprocess.check_output(['git', 'show', source + ':fixtures/manifest.json'], cwd=t02.ROOT))
        evidence = (t02.ROOT / 'docs/fixtures/T02-evidence.md').read_text()
        self.assertIn('## ' + reference, evidence)
        self.assertIn('https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6336501800', evidence)
        self.assertIn(source, evidence)
        expected = copy.deepcopy(prior)
        for case in expected['cases']:
            self.assertEqual({'poPrivacy': 'PENDING', 'qaPrivacy': 'PENDING', 'evidenceRef': None}, case['approval'])
            case['approval'] = {'poPrivacy': 'APPROVED', 'qaPrivacy': 'PENDING', 'evidenceRef': reference}
            self.assertFalse(t02.approval_check(case['approval'], case['id']))
            source_hashes = []
            for field in ('inputPath', 'expectedPath'):
                raw = subprocess.check_output(['git', 'show', source + ':fixtures/' + case[field]], cwd=t02.ROOT)
                self.assertEqual(raw, (t02.ROOT / 'fixtures' / case[field]).read_bytes())
                source_hashes.append(hashlib.sha256(raw).hexdigest())
            self.assertIn('| `' + case['id'] + '` | `' + source_hashes[0] + '` | `' + source_hashes[1] + '` |', evidence)
        self.assertEqual(expected, manifest)
        self.assertFalse(t02.validate()['acceptedCorpus'])
        with self.assertRaises(t02.Invalid) as raised:
            t02.validate(require_approved=True)
        self.assertEqual('PROVENANCE', raised.exception.rule)

    def test_content_oracle_mutations_after_matching_hashes(self):
        def expected_mutation(index, field, value):
            def mutate(root, manifest, _):
                p = root / manifest['cases'][index]['expectedPath']
                expected = t02.strict_json(p); expected[field] = value; dump(p, expected)
            return mutate
        self.control('NC-04', 'content-mb-amount', 'ORACLE', expected_mutation(10, 'amount', 125001))
        self.control('NC-04', 'content-bidv-balance', 'ORACLE', expected_mutation(0, 'balanceAfter', 875001))
        self.control('NC-04', 'content-mb-memo', 'ORACLE', expected_mutation(11, 'description', 'SYNTHETIC_OTHER'))
        def text_mutation(index, old, new):
            def mutate(root, manifest, _):
                p = root / manifest['cases'][index]['inputPath']; p.write_text(p.read_text().replace(old, new))
            return mutate
        self.control('NC-04', 'content-msb-sign', 'ORACLE', text_mutation(5, '+125,000', '-125,000'))
        self.control('NC-04', 'content-mb-missing-restored', 'ORACLE', text_mutation(12, '| +VND', '| +25,000VND'))
        self.control('NC-04', 'content-mb-title', 'ORACLE', text_mutation(13, '# title: MB Bank - Xác thực giao dịch', '# title: SYNTHETIC_WRONG_TITLE'))
        def marketing_tx(root, manifest, _):
            dump(root / manifest['cases'][4]['expectedPath'], {'parse': True, 'direction': 'IN', 'amount': 30000, 'balanceAfter': 875000, 'description': 'SYNTHETIC_MEMO_A'})
        self.control('NC-04', 'marketing-not-transaction', 'ORACLE', marketing_tx)
        def otp_sent(root, manifest, _):
            p = root / manifest['cases'][13]['inputPath']; p.write_text(p.read_text() + 'SYNTHETIC_SENTINEL: 12345678')
        self.control('NC-07', 'mb-digital-otp-no-digits', 'PRIVACY', otp_sent)

    def test_nc01_pairing(self):
        self.control('NC-01', 'missing-pair', 'INVENTORY', lambda r, m, s: (r / m['cases'][0]['expectedPath']).unlink())
        self.control('NC-01', 'extra-pair', 'INVENTORY', lambda r, m, s: (r / 'extra.txt').write_text('SYNTHETIC_EXTRA'))

    def test_nc02_duplicates(self):
        self.control('NC-02', 'duplicate-id', 'INVENTORY', lambda r, m, s: m['cases'].__setitem__(1, copy.deepcopy(m['cases'][0])))
        self.control('NC-02', 'duplicate-json-key', 'STRICT_JSON', lambda r, m, s: (r / m['cases'][0]['expectedPath']).write_text('{"parse":false,"parse":true}'))

    def test_nc03_schema_and_envelope(self):
        self.control('NC-03', 'unknown-key', 'SCHEMA', lambda r, m, s: m['cases'][0].update(extra=True))
        self.control('NC-03', 'package-header-conflict', 'ENVELOPE', lambda r, m, s: m['cases'][0]['envelope'].update(packageName='com.example.moneymate.fixture.wrong'))
        self.control('NC-03', 'title-conflict', 'ENVELOPE', lambda r, m, s: m['cases'][0]['extras'].update(title={'state': 'string', 'source': 'literal', 'value': 'SYNTHETIC_OTHER'}))
        self.control('NC-03', 'title-missing-header-present', 'ENVELOPE', lambda r, m, s: m['cases'][0]['extras'].update(title={'state': 'missing'}))
        self.control('NC-03', 'observed-package-synthetic', 'ENVELOPE', lambda r, m, s: m['cases'][0].update(observedPackage='com.example.real'))
        self.control('NC-03', 'schema-parity', 'SCHEMA', lambda r, m, s: (r / 'schema.json').write_text('{}'))

    def test_nc04_oracles(self):
        for label, value in [('missing-amount', {'parse': True, 'direction': 'IN'}), ('false-with-amount', {'parse': False, 'amount': 1}), ('null-without-decision', {'parse': None})]:
            self.control('NC-04', label, 'ORACLE', lambda r, m, s, v=value: dump(r / m['cases'][0]['expectedPath'], v))

    def test_nc05_integrity(self):
        self.control('NC-05', 'changed-input-byte', 'INTEGRITY', lambda r, m, s: (r / m['cases'][0]['inputPath']).write_text((r / m['cases'][0]['inputPath']).read_text() + 'SYNTHETIC_CHANGED'), False)
        self.control('NC-05', 'bank-path-conflict', 'INVENTORY', lambda r, m, s: m['cases'][0].update(bankCode='MB'))

    def test_nc06_paths(self):
        for label, value in [('absolute', '/etc/passwd'), ('parent', '../other'), ('remote', 'https://example.invalid/file')]:
            self.control('NC-06', label, 'PATH', lambda r, m, s, v=value: m['cases'][0].update(inputPath=v), False)
        def symlink(root, manifest, _):
            path = root / manifest['cases'][0]['inputPath']
            path.unlink()
            path.symlink_to(root.parent / 'outside')
        self.control('NC-06', 'symlink', 'PATH', symlink, False)

    def test_nc07_privacy(self):
        for label, value in [('digits', '12345678'), ('email', 'synthetic@example.invalid'), ('phone', '0901234567')]:
            self.control('NC-07', label, 'PRIVACY', lambda r, m, s, v=value: m['cases'][0]['provenance'].update(rationale=v)) if False else self.privacy_mutation('NC-07', label, value, 'PRIVACY')

    def privacy_mutation(self, control, label, value, rule):
        def mutation(root, manifest, _):
            path = root / manifest['cases'][0]['inputPath']
            path.write_text(path.read_text() + '\nSYNTHETIC_SENTINEL: ' + value)
        self.control(control, label, rule, mutation)

    def test_nc08_normalization(self):
        for label, value in [('space', '1234 5678'), ('tab', '1234\t5678'), ('dot', '1234.5678'), ('comma', '1234,5678'), ('nbsp', '1234\u00a05678'), ('mixed', '12 34.56,78'), ('unicode', '１２３４ ５６７８'), ('zero-width', '1234\u200b5678')]:
            self.privacy_mutation('NC-08', label, value, 'PRIVACY_NORMALIZED')
        def escaped(root, manifest, _):
            path = root / manifest['cases'][0]['expectedPath']
            original = path.read_text()
            path.write_text(original.replace('SYNTHETIC_MEMO_A', r'\u0031\u0032\u0033\u0034\u0035\u0036\u0037\u0038'))
        self.control('NC-08', 'json-escape', 'PRIVACY', escaped)

    def test_nc09_exceptions(self):
        for label, entry in [('broad', {'file': '*.txt'}), ('text-exception', {'file': 'bidv/txn_in_01.txt', 'pointer': '/amount', 'value': 12345678, 'rationale': 'SYNTHETIC_NUMERIC_ONLY', 'poReview': 'APPROVED', 'qaReview': 'APPROVED', 'evidenceRef': 'REVIEW_FAKE'})]:
            self.control('NC-09', label, 'SCHEMA' if label == 'broad' else 'EXCEPTION', lambda r, m, s, e=entry: m['privacyExceptions'].append(e))

    def test_nc10_provenance(self):
        self.control('NC-10', 'wrong-corpus', 'PROVENANCE', lambda r, m, s: m.update(corpusClass='OBSERVED'))
        self.control('NC-10', 'synthetic-golden', 'PROVENANCE', lambda r, m, s: m['cases'][0].update(eligibleForRealBankGolden=True))
        self.control('NC-10', 'approval-no-evidence', 'PROVENANCE', lambda r, m, s: m['cases'][0]['approval'].update(poPrivacy='APPROVED', evidenceRef=None))
        for index in (5, 10, 3):
            self.control('NC-10', 'unobserved-source-' + str(index), 'PROVENANCE', lambda r, m, s, i=index: m['cases'][i]['provenance'].update(kind='synthetic_from_observed_structure', sourceRef='PO_BIDV_STRUCTURE'))

    def test_nc11_scenarios(self):
        self.control('NC-11', 'missing-seed', 'SCENARIO', lambda r, m, s: s['scenarios'][0].update(seedIds=['missing']))
        self.control('NC-11', 'unresolved-golden', 'SCENARIO', lambda r, m, s: s['scenarios'][2].update(oracleMode='GOLDEN', decisionId=None))
        self.control('NC-11', 'unbounded-count', 'SCENARIO', lambda r, m, s: s['scenarios'][0]['parameters'].update(count=4))

    def test_nc12_encoding_and_order(self):
        self.control('NC-12', 'bad-header', 'ENCODING', lambda r, m, s: (r / m['cases'][0]['inputPath']).write_text('SYNTHETIC_NO_HEADER'))
        self.control('NC-12', 'invalid-utf8', 'ENCODING', lambda r, m, s: (r / m['cases'][0]['inputPath']).write_bytes(b'\xff'))
        original = pathlib.Path.rglob
        before = t02.validate()
        with mock.patch.object(pathlib.Path, 'rglob', lambda path, pattern: iter(reversed(list(original(path, pattern))))):
            self.assertEqual(before, t02.validate())

    def test_nc13_consent(self):
        self.control('NC-13', 'denied-with-payload', 'CONSENT', lambda r, m, s: s['scenarios'][20]['parameters'].update(value='SYNTHETIC_PAYLOAD'))

    def test_nc14_evidence_and_crash(self):
        for value in ([], [{'control': 'NC-01', 'result': 'PASS'}]):
            with self.assertRaises(t02.Invalid) as raised:
                t02.verify_control_evidence(value)
            self.assertEqual('EVIDENCE', raised.exception.rule)
        ROWS.append(dict(control='NC-14', subcase='missing-report-controls', result='PASS', expected='EVIDENCE', observed='EVIDENCE', originalUnchanged=True))
        with mock.patch.object(t02, 'validate', side_effect=RuntimeError('SYNTHETIC_CRASH_SENTINEL')):
            with mock.patch('sys.argv', ['t02']):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(2, t02.main())
                self.assertNotIn('SYNTHETIC_CRASH_SENTINEL', output.getvalue())

    def test_nc15_junit(self):
        names = [('SyntheticTest', 'sample')]
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'suite.xml'
            for flag in ('failure', 'error', 'skipped', 'missing', 'extra', 'duplicate'):
                suite = ET.Element('testsuite', tests='1', failures='0', errors='0', skipped='0')
                case = ET.SubElement(suite, 'testcase', classname='SyntheticTest', name='sample')
                if flag in ('failure', 'error', 'skipped'):
                    ET.SubElement(case, flag)
                elif flag == 'missing':
                    suite.remove(case)
                elif flag == 'extra':
                    ET.SubElement(suite, 'testcase', classname='SyntheticTest', name='other')
                else:
                    ET.SubElement(suite, 'testcase', classname='SyntheticTest', name='sample')
                ET.ElementTree(suite).write(path)
                with self.assertRaises(t02.Invalid) as raised:
                    t02.verify_junit_evidence(path, names)
                self.assertEqual('JUNIT', raised.exception.rule)
                ROWS.append(dict(control='NC-15', subcase=flag, result='PASS', expected='JUNIT', observed='JUNIT', originalUnchanged=True))

    def test_apk_markers_and_zip_entries(self):
        before = hashes(t02.ROOT / 'fixtures')
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / 'canary.zip'
            for encoding in ('utf-8', 'utf-16le', 'utf-16be'):
                for marker in t02.MARKERS:
                    with zipfile.ZipFile(p, 'w') as z:
                        z.writestr('classes.dex', marker.encode(encoding))
                    self.assertEqual('FAIL', t02.scan_apk(p)['contentScan'])
            for entry in ('assets/fixtures/a', 'res/raw/txn_in_01.txt', 'assets/manifest.json'):
                with zipfile.ZipFile(p, 'w') as z:
                    z.writestr(entry, 'safe')
                self.assertEqual('FAIL', t02.scan_apk(p)['entryScan'])
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('classes.dex', b'no fixtures')
            report = t02.scan_apk(p)
            self.assertEqual('PASS', report['contentScan'])
            self.assertEqual('PASS', report['entryScan'])
        self.assertEqual(before, hashes(t02.ROOT / 'fixtures'))


PACKAGER_SPEC = importlib.util.spec_from_file_location(
    't02_packager', pathlib.Path(__file__).resolve().parents[1] / 't00b_review_evidence.py')
packager = importlib.util.module_from_spec(PACKAGER_SPEC)
PACKAGER_SPEC.loader.exec_module(packager)
PACKAGER_ROWS = []


class PackagerIdentityTest(unittest.TestCase):
    def snapshot(self, target, ref):
        import subprocess
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ref], cwd=t02.ROOT, text=True).splitlines()
        for name in names:
            if name.endswith('.kt') or name.endswith('/build.gradle.kts'):
                destination = target / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(subprocess.check_output(['git', 'show', ref + ':' + name], cwd=t02.ROOT))

    def xml_from_inventory(self, source, artifacts):
        groups = {}
        for key in packager.junit_source_inventory(source):
            groups.setdefault(key[:4], []).append(key[4])
        for (module, task, variant, classname), methods in groups.items():
            suite = ET.Element('testsuite', name=classname, tests=str(len(methods)), failures='0', errors='0', skipped='0')
            for name in methods:
                ET.SubElement(suite, 'testcase', classname=classname, name=name)
            path = artifacts / module / 'build/test-results' / task / ('TEST-' + classname + '.xml')
            path.parent.mkdir(parents=True, exist_ok=True)
            ET.ElementTree(suite).write(path)

    def test_baseline_twenty_and_current_twenty_two(self):
        for label, ref, count in [('baseline', '4570e4e3cece382e5a69fa277046628c05f0aa07', 20), ('T02', '63f5e18ffb3fb0d472539825fd23d887598905bc', 22)]:
            with tempfile.TemporaryDirectory(prefix='t02-junit-source-') as tmp:
                source, artifacts = pathlib.Path(tmp) / 'source', pathlib.Path(tmp) / 'artifacts'
                self.snapshot(source, ref)
                self.xml_from_inventory(source, artifacts)
                totals, evidence = packager.verify_junit_inventory(source, artifacts)
                self.assertEqual(count, totals['tests'])
                self.assertEqual(count, len(evidence['inventory']))
                self.assertEqual(len(evidence['inventory']), len({(x['module'], x['task'], x['variant'], x['class'], x['method']) for x in evidence['inventory']}))
                PACKAGER_ROWS.append({'case': label, 'expectedTests': count, 'actualTests': totals['tests'], 'result': 'PASS'})

    def test_identity_negative_controls(self):
        cases = ['missing', 'extra', 'duplicate', 'module', 'variant', 'classname', 'malformed', 'summary', 'failure', 'error', 'skipped', 'source-set', 'source-method']
        for label in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix='t02-junit-mutation-') as tmp:
                source, artifacts = pathlib.Path(tmp) / 'source', pathlib.Path(tmp) / 'artifacts'
                self.snapshot(source, '63f5e18ffb3fb0d472539825fd23d887598905bc')
                self.xml_from_inventory(source, artifacts)
                before = hashes(artifacts)
                path = next((artifacts / 'parser').rglob('*FixtureLoaderTest.xml'))
                suite = ET.parse(path).getroot()
                if label == 'missing':
                    suite.remove(suite.find('testcase')); suite.set('tests', str(len(suite.findall('testcase'))))
                elif label == 'extra':
                    ET.SubElement(suite, 'testcase', classname=suite.get('name'), name='SYNTHETIC_EXTRA'); suite.set('tests', '3')
                elif label == 'duplicate':
                    suite.append(copy.deepcopy(suite.find('testcase'))); suite.set('tests', '3')
                elif label in ('module', 'variant'):
                    destination = artifacts / ('dedup' if label == 'module' else 'parser') / 'build/test-results' / ('test' if label == 'module' else 'testReleaseUnitTest') / path.name
                    destination.parent.mkdir(parents=True, exist_ok=True); path.rename(destination)
                elif label == 'classname':
                    suite.find('testcase').set('classname', 'SYNTHETIC_WRONG_CLASS')
                elif label == 'malformed':
                    path.write_text('<broken')
                elif label == 'summary':
                    suite.set('tests', '999')
                elif label in ('failure', 'error', 'skipped'):
                    ET.SubElement(suite.find('testcase'), label)
                elif label == 'source-set':
                    directory = source / 'parser/src/test'
                    directory.rename(directory.with_name('testDebug'))
                else:
                    path_source = source / 'parser/src/test/kotlin/com/app/moneymate/parser/fixtures/FixtureLoaderTest.kt'
                    path_source.write_text(path_source.read_text().replace('manifestOrderAndDoubleLoadPreserveEveryByte', 'SYNTHETIC_CHANGED_METHOD'))
                if label not in ('module', 'variant', 'malformed'):
                    ET.ElementTree(suite).write(path)
                expected_reason = {'missing': 'XML_MISSING', 'extra': 'XML_EXTRA', 'duplicate': 'XML_DUPLICATE', 'module': 'XML_EXTRA', 'variant': 'XML_VARIANT', 'classname': 'XML_CLASS', 'malformed': 'XML_MALFORMED', 'summary': 'XML_COUNTS', 'failure': 'XML_OUTCOME', 'error': 'XML_OUTCOME', 'skipped': 'XML_OUTCOME', 'source-set': 'SOURCE_SET', 'source-method': 'XML_EXTRA'}[label]
                with self.assertRaises(packager.JunitEvidenceError) as error:
                    packager.verify_junit_inventory(source, artifacts)
                self.assertEqual(expected_reason, str(error.exception))
                PACKAGER_ROWS.append({'case': label, 'expected': expected_reason, 'observed': str(error.exception), 'result': 'PASS', 'temporaryOnly': True})
                self.assertTrue(before)

    def test_android_debug_sources_and_annotation_literals(self):
        with tempfile.TemporaryDirectory(prefix='t02-junit-variant-') as tmp:
            source, artifacts = pathlib.Path(tmp) / 'source', pathlib.Path(tmp) / 'artifacts'
            self.snapshot(source, '63f5e18ffb3fb0d472539825fd23d887598905bc')
            new_source = source / 'capture/src/testDebug/kotlin/synthetic/VariantTest.kt'
            new_source.parent.mkdir(parents=True, exist_ok=True)
            new_source.write_text('package synthetic\nimport org.junit.Test\nclass VariantTest {\n@Test fun syntheticDebugCase() {}\nval literal = "@Test fun fake()"\n/* @Test fun ignoredComment() {} */\n}\n')
            self.xml_from_inventory(source, artifacts)
            totals, evidence = packager.verify_junit_inventory(source, artifacts)
            entry = next(x for x in evidence['inventory'] if x['method'] == 'syntheticDebugCase')
            self.assertEqual(('capture', 'testDebugUnitTest', 'debugUnitTest', 'testDebug'), (entry['module'], entry['task'], entry['variant'], entry['sourceSet']))
            self.assertEqual(23, totals['tests'])
            PACKAGER_ROWS.append({'case': 'android-testDebug-plus-base', 'result': 'PASS', 'temporaryOnly': True})


def tearDownModule():
    # Missing, skipped, crashed or unrecorded controls make the whole selftest fail.
    t02.verify_control_evidence(ROWS)
    output = t02.ROOT / 'build/reports/t02/negative-controls.json'
    t02.write_report(output, {'result': 'PASS', 'controls': ROWS, 'originalCorpusUnchanged': True})
    if len(PACKAGER_ROWS) != 16 or any(r['result'] != 'PASS' for r in PACKAGER_ROWS):
        raise AssertionError('PACKAGER_EVIDENCE_MISSING')
    t02.write_report(t02.ROOT / 'build/reports/t02/packager-negative-controls.json', {'result': 'PASS', 'cases': PACKAGER_ROWS})
