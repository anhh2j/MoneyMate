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
        self.control('NC-10', 'approval-no-evidence', 'PROVENANCE', lambda r, m, s: m['cases'][0]['approval'].update(poPrivacy='APPROVED'))
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


def tearDownModule():
    # Missing, skipped, crashed or unrecorded controls make the whole selftest fail.
    t02.verify_control_evidence(ROWS)
    output = t02.ROOT / 'build/reports/t02/negative-controls.json'
    t02.write_report(output, {'result': 'PASS', 'controls': ROWS, 'originalCorpusUnchanged': True})
