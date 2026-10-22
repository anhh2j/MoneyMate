"""T02 synthetic contract validation. No bank parsing, networking or mutation executor."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKERS = ('com.example.moneymate.fixture', 'SYNTHETIC_')
RULES = ['INVENTORY', 'STRICT_JSON', 'SCHEMA', 'ORACLE', 'INTEGRITY', 'PATH', 'PRIVACY',
         'PRIVACY_NORMALIZED', 'EXCEPTION', 'PROVENANCE', 'SCENARIO', 'ENCODING',
         'CONSENT', 'EVIDENCE', 'JUNIT', 'ENVELOPE', 'ORDER', 'MARKER']
BANKS = ('BIDV', 'MSB', 'MB')
TYPES = ('txn_in_01', 'txn_out_01', 'invalid_missing_amount_01', 'noise_notice_01', 'noise_promotion_01')
OPS = ('omit', 'null', 'empty', 'lineEnding', 'unicodeNfd', 'substitute', 'truncate', 'repeat', 'update', 'deltaTime')
DEFINITIONS = {
    'manifest': ['schemaVersion', 'corpusClass', 'cases', 'privacyExceptions'],
    'case': ['id', 'bankCode', 'caseType', 'inputPath', 'expectedPath', 'inputSha256', 'expectedSha256', 'provenance', 'formatVerification', 'eligibleForRealBankGolden', 'observedPackage', 'layoutVerification', 'envelope', 'extras', 'oracleScope', 'coverageTags', 'approval'],
    'provenance': ['kind', 'sourceRef', 'variant', 'rationale'],
    'approval': ['poPrivacy', 'qaPrivacy', 'evidenceRef'],
    'envelope': ['source', 'packageName', 'postTime', 'receivedAt', 'notificationId', 'groupKey', 'isGroupSummary'],
    'scenario': ['id', 'seedIds', 'operation', 'parameters', 'consumerTask', 'oracleMode', 'decisionId', 'eligibleForRealBankGolden', 'provenanceKind', 'coverageTags', 'facts', 'token'],
    'scenarioDocument': ['schemaVersion', 'scenarios'],
}
SCOPES = [
    {'bankCode': 'BIDV', 'caseType': 'txn_in_01', 'direction': 'IN', 'sourceRef': 'PO_BIDV_STRUCTURE'},
    {'bankCode': 'BIDV', 'caseType': 'txn_out_01', 'direction': 'OUT', 'sourceRef': 'PO_BIDV_STRUCTURE'},
    {'bankCode': 'MSB', 'caseType': 'txn_out_01', 'direction': 'OUT', 'sourceRef': 'SPEC_5_2'},
]
META = {'README.md', 'manifest.json', 'schema.json', 'scenarios.json'}


class Invalid(Exception):
    def __init__(self, rule, case='CORPUS'):
        self.rule = rule
        self.case = case if re.fullmatch(r'[A-Za-z0-9_-]{1,90}', str(case)) else 'CORPUS'
        super().__init__(rule)


def require(condition, rule, case='CORPUS'):
    if not condition:
        raise Invalid(rule, case)


def keys(value, expected, case='CORPUS'):
    require(isinstance(value, dict) and set(value) == set(expected), 'SCHEMA', case)


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'STRICT_JSON')
            result[key] = value
        return result
    try:
        return json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid('STRICT_JSON')))
    except (UnicodeError, ValueError, OSError):
        raise Invalid('STRICT_JSON') from None


def digest(path):
    raw = hashlib.sha256(path.read_bytes()).hexdigest()
    return ':'.join(raw[n:n + 4] for n in range(0, len(raw), 4))


def file_path(root, relative):
    require(isinstance(relative, str), 'PATH')
    p = pathlib.PurePosixPath(relative)
    require(not p.is_absolute() and '\\' not in relative and '..' not in p.parts and ':' not in relative, 'PATH')
    candidate = root / p
    require(not any((root / pathlib.Path(*p.parts[:n])).is_symlink() for n in range(1, len(p.parts) + 1)), 'PATH')
    require(candidate.resolve().is_relative_to(root.resolve()), 'PATH')
    require(candidate.is_file(), 'INVENTORY')
    return candidate


def detect(text):
    def found(value):
        return bool(re.search(r'\d{8,}|[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)(?:0|\+84)\d{9,10}(?!\d)', value))
    for line in text.splitlines():
        if found(line):
            return 'PRIVACY'
        normalized = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c
                             for c in line if unicodedata.category(c) != 'Cf')
        normalized = re.sub(r'(?<=\d)[ \t.,\u00a0]+(?=\d)', '', normalized)
        if found(normalized):
            return 'PRIVACY_NORMALIZED'
    return None


def leaves(value, pointer=''):
    if isinstance(value, dict):
        for k, v in value.items():
            yield pointer + '/' + k, k
            yield from leaves(v, pointer + '/' + k.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for n, v in enumerate(value):
            yield from leaves(v, pointer + '/' + str(n))
    else:
        yield pointer, str(value)


def parse_text(path):
    try:
        raw = path.read_bytes()
        text = raw.decode('utf-8')
    except (OSError, UnicodeError):
        raise Invalid('ENCODING') from None
    match = re.fullmatch(r'# package: ([^\r\n]+)\r?\n# title: ([^\r\n]*)\r?\n---\r?\n([\s\S]*)', text)
    require(match is not None, 'ENCODING')
    return match.group(1), match.group(2), match.group(3), raw


def schema_check(schema):
    keys(schema, ['schemaVersion', 'corpusClass', 'rules', 'sourceScopes', 'banks', 'caseTypes', 'operations', 'definitions', 'limits', 'numericExceptionFields'])
    require(schema['schemaVersion'] == 1 and schema['corpusClass'] == 'SYNTHETIC_CONTRACT', 'SCHEMA')
    require(schema['rules'] == RULES and schema['sourceScopes'] == SCOPES, 'SCHEMA')
    require(schema['definitions'] == DEFINITIONS and schema['banks'] == list(BANKS)
            and schema['caseTypes'] == list(TYPES) and schema['operations'] == list(OPS), 'SCHEMA')
    require(schema['limits'] == {'maxCodePoints': 100000, 'maxRepeat': 3, 'maxDeltaMs': 121000}, 'SCHEMA')
    require(schema['numericExceptionFields'] == ['amount', 'balanceAfter', 'postTime', 'receivedAt', 'value'], 'SCHEMA')


def oracle_check(expected, ident):
    require(isinstance(expected, dict) and 'parse' in expected, 'ORACLE', ident)
    state = expected['parse']
    require(state is None or type(state) is bool, 'ORACLE', ident)
    if state is True:
        require(set(expected) <= {'parse', 'direction', 'amount', 'balanceAfter', 'description', 'accountMask', 'refCode', 'occurredAt'}, 'ORACLE', ident)
        require(expected.get('direction') in ('IN', 'OUT') and type(expected.get('amount')) is int, 'ORACLE', ident)
        require(0 <= expected['amount'] <= 9223372036854775807, 'ORACLE', ident)
        if 'balanceAfter' in expected:
            require(type(expected['balanceAfter']) is int and 0 <= expected['balanceAfter'] <= 9223372036854775807, 'ORACLE', ident)
        for field in ('description', 'accountMask', 'refCode', 'occurredAt'):
            require(field not in expected or expected[field] is None or isinstance(expected[field], str), 'ORACLE', ident)
    elif state is False:
        require(expected == {'parse': False}, 'ORACLE', ident)
    else:
        require(set(expected) == {'parse', 'decisionId', 'reasonCode'} and all(isinstance(expected.get(k), str) and expected[k] for k in ('decisionId', 'reasonCode')), 'ORACLE', ident)


def provenance_check(case, expected):
    ident = case['id']
    p = case['provenance']
    keys(p, DEFINITIONS['provenance'], ident)
    require(case['eligibleForRealBankGolden'] is False and case['oracleScope'] == 'CONTRACT_ONLY', 'PROVENANCE', ident)
    require(case['formatVerification'] in ('UNVERIFIED', 'STRUCTURE_ONLY') and case['layoutVerification'] == 'UNKNOWN', 'PROVENANCE', ident)
    require(p['variant'] == case['caseType'] and p['rationale'] == 'SYNTHETIC_VALUES_ONLY', 'PROVENANCE', ident)
    if p['kind'] == 'synthetic_from_observed_structure':
        entry = dict(bankCode=case['bankCode'], caseType=case['caseType'], direction=expected.get('direction'), sourceRef=p['sourceRef'])
        require(entry in SCOPES and case['formatVerification'] == 'STRUCTURE_ONLY', 'PROVENANCE', ident)
    else:
        require(p['kind'] == 'synthetic_contract' and p['sourceRef'] == 'CONTRACT_ONLY'
                and case['formatVerification'] == 'UNVERIFIED', 'PROVENANCE', ident)


def envelope_check(case, package, title, body):
    ident = case['id']
    env = case['envelope']
    keys(env, DEFINITIONS['envelope'], ident)
    require(env['packageName'] == package == MARKERS[0] + '.' + case['bankCode'].lower()
            and case['observedPackage'] is None, 'ENVELOPE', ident)
    require(env['source'] == 'NOTIF' and type(env['isGroupSummary']) is bool, 'ENVELOPE', ident)
    for field in ('postTime', 'receivedAt'):
        require(isinstance(env[field], str) and re.fullmatch(r'2000-01-01T00:00:0[01]\+07:00', env[field]), 'ENVELOPE', ident)
    require(isinstance(env['notificationId'], str) and env['notificationId'].startswith('SYNTHETIC_')
            and (env['groupKey'] is None or isinstance(env['groupKey'], str)), 'ENVELOPE', ident)
    keys(case['extras'], ['title', 'text', 'bigText', 'subText'], ident)
    for name, extra in case['extras'].items():
        require(isinstance(extra, dict) and extra.get('state') in ('missing', 'null', 'string'), 'ENVELOPE', ident)
        if extra['state'] != 'string':
            keys(extra, ['state'], ident)
            if name == 'title':
                require(title == 'UNRESOLVED', 'ENVELOPE', ident)
        else:
            require(extra.get('source') in ('txtTitle', 'txtBody', 'literal'), 'ENVELOPE', ident)
            keys(extra, ['state', 'source', 'value'] if extra['source'] == 'literal' else ['state', 'source'], ident)
            resolved = extra.get('value') if extra['source'] == 'literal' else title if extra['source'] == 'txtTitle' else body
            require(isinstance(resolved, str), 'ENVELOPE', ident)
            if name == 'title':
                require(resolved == title, 'ENVELOPE', ident)


def approval_check(approval, ident):
    keys(approval, DEFINITIONS['approval'], ident)
    require(all(approval[k] in ('PENDING', 'APPROVED') for k in ('poPrivacy', 'qaPrivacy')), 'PROVENANCE', ident)
    if any(approval[k] == 'APPROVED' for k in ('poPrivacy', 'qaPrivacy')):
        require(isinstance(approval['evidenceRef'], str) and approval['evidenceRef'].startswith('REVIEW_'), 'PROVENANCE', ident)
    return all(approval[k] == 'APPROVED' for k in ('poPrivacy', 'qaPrivacy'))


def exceptions_check(entries, documents, schema):
    require(isinstance(entries, list), 'EXCEPTION')
    accepted = set()
    for e in entries:
        keys(e, ['file', 'pointer', 'value', 'rationale', 'poReview', 'qaReview', 'evidenceRef'])
        require(e['file'].endswith('.json') and e['file'] in documents and e['file'] != 'manifest.json', 'EXCEPTION')
        require(e['pointer'].split('/')[-1] in schema['numericExceptionFields'], 'EXCEPTION')
        require(e['poReview'] == e['qaReview'] == 'APPROVED' and e['evidenceRef'].startswith('REVIEW_')
                and e['rationale'] == 'SYNTHETIC_NUMERIC_ONLY', 'EXCEPTION')
        require(isinstance(e['value'], (str, int)) and not isinstance(e['value'], bool) and re.fullmatch(r'[0-9., +:T\-]+', str(e['value'])), 'EXCEPTION')
        leaf = dict(leaves(documents[e['file']]))
        require(leaf.get(e['pointer']) == str(e['value']) and detect(str(e['value'])) is not None, 'EXCEPTION')
        token = (e['file'], e['pointer'], str(e['value']))
        require(token not in accepted, 'EXCEPTION')
        accepted.add(token)
    return accepted


def scenarios_check(doc, case_map, expected_map):
    keys(doc, DEFINITIONS['scenarioDocument'])
    require(doc['schemaVersion'] == 1 and isinstance(doc['scenarios'], list) and doc['scenarios'], 'SCENARIO')
    ids = set()
    for s in doc['scenarios']:
        keys(s, DEFINITIONS['scenario'])
        ident = s['id']
        require(isinstance(ident, str) and ident not in ids, 'SCENARIO')
        ids.add(ident)
        require(isinstance(s['seedIds'], list) and s['seedIds'] and len(s['seedIds']) == len(set(s['seedIds']))
                and all(k in case_map for k in s['seedIds']), 'SCENARIO', ident)
        require(s['operation'] in OPS and s['provenanceKind'] == 'synthetic_contract'
                and s['eligibleForRealBankGolden'] is False, 'SCENARIO', ident)
        require(s['oracleMode'] in ('CONTRACT', 'UNRESOLVED', 'GOLDEN'), 'SCENARIO', ident)
        require(all(isinstance(t, str) and re.fullmatch(r'FX-(0[1-9]|1[0-9]|2[0-4])', t) for t in s['coverageTags']), 'SCENARIO', ident)
        if s['oracleMode'] == 'GOLDEN':
            require(all(expected_map[k]['parse'] is not None for k in s['seedIds']), 'SCENARIO', ident)
        if s['oracleMode'] == 'UNRESOLVED':
            require(isinstance(s['decisionId'], str) and s['decisionId'], 'SCENARIO', ident)
        else:
            require(s['decisionId'] is None, 'SCENARIO', ident)
        require(s['token'] == 'SYNTHETIC_SCENARIO' and isinstance(s['facts'], list) and s['facts']
                and isinstance(s['coverageTags'], list) and s['coverageTags'], 'MARKER', ident)
        require(s['consumerTask'] in ('T04_T05', 'T06', 'T01_T07'), 'SCENARIO', ident)
        p = s['parameters']
        require(isinstance(p, dict) and set(p) <= {'field', 'value', 'count', 'codePoints', 'values', 'groupKey', 'isGroupSummary', 'notificationId', 'packageName', 'consent', 'expectedDelivery'}, 'SCENARIO', ident)
        for field, maximum in (('count', 3), ('codePoints', 100000)):
            require(field not in p or type(p[field]) is int and 1 <= p[field] <= maximum, 'SCENARIO', ident)
        if 'values' in p:
            require(isinstance(p['values'], list) and p['values'] and all(type(v) is int and 0 <= v <= 121000 for v in p['values']), 'SCENARIO', ident)
        if p.get('consent') in ('DENIED', 'DISCOVERY_ONLY'):
            require(p.get('expectedDelivery') == 'METADATA_ONLY' and 'value' not in p and 'field' not in p, 'CONSENT', ident)


def validate(root=ROOT / 'fixtures', require_approved=False):
    root = pathlib.Path(root)
    manifest = strict_json(file_path(root, 'manifest.json'))
    schema = strict_json(file_path(root, 'schema.json'))
    scenarios = strict_json(file_path(root, 'scenarios.json'))
    schema_check(schema)
    keys(manifest, DEFINITIONS['manifest'])
    require(manifest['schemaVersion'] == 1 and manifest['corpusClass'] == 'SYNTHETIC_CONTRACT', 'PROVENANCE')
    require(isinstance(manifest['cases'], list) and len(manifest['cases']) == 15, 'INVENTORY')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    expected_files = set(META)
    documents = {'manifest.json': manifest, 'schema.json': schema, 'scenarios.json': scenarios}
    case_map, expected_map, pending, unresolved = {}, {}, [], []
    inventory = []
    for c in manifest['cases']:
        keys(c, DEFINITIONS['case'])
        ident = c['id']
        require(isinstance(ident, str) and ident not in case_map and c['bankCode'] in BANKS and c['caseType'] in TYPES, 'INVENTORY')
        require(ident == c['bankCode'].lower() + '_' + c['caseType'], 'INVENTORY', ident)
        case_map[ident] = c
        require(isinstance(c['coverageTags'], list) and c['coverageTags'] and all(isinstance(t, str) and re.fullmatch(r'FX-(0[1-9]|1[0-9]|2[0-4])', t) for t in c['coverageTags']), 'SCHEMA', ident)
        for key, extension in (('inputPath', '.txt'), ('expectedPath', '.expected.json')):
            file_path(root, c[key])
            require(c[key] == c['bankCode'].lower() + '/' + c['caseType'] + extension, 'INVENTORY', ident)
            require(c[key] not in expected_files, 'INVENTORY', ident)
            expected_files.add(c[key])
        input_path, expected_path = file_path(root, c['inputPath']), file_path(root, c['expectedPath'])
        package, title, body, raw = parse_text(input_path)
        expected = strict_json(expected_path)
        documents[c['expectedPath']] = expected
        expected_map[ident] = expected
        oracle_check(expected, ident)
        provenance_check(c, expected)
        envelope_check(c, package, title, body)
        require('SYNTHETIC_' in body and len(body) <= 100000, 'MARKER', ident)
        if not approval_check(c['approval'], ident):
            pending.append(ident)
        if expected['parse'] is None:
            unresolved.append(ident)
        require(c['inputSha256'] == digest(input_path) and c['expectedSha256'] == digest(expected_path), 'INTEGRITY', ident)
        issue = detect(raw.decode('utf-8'))
        require(issue is None, issue or 'PRIVACY', ident)
        inventory.append({'id': ident, 'inputSha256': c['inputSha256'], 'expectedSha256': c['expectedSha256'], 'provenance': c['provenance']['kind']})
    require(actual == expected_files, 'INVENTORY')
    require(len(case_map) == 15 and all(sum(c['bankCode'] == b for c in case_map.values()) == 5 for b in BANKS), 'INVENTORY')
    scenarios_check(scenarios, case_map, expected_map)
    allowed = exceptions_check(manifest['privacyExceptions'], documents, schema)
    for filename, doc in documents.items():
        for pointer, text in leaves(doc):
            # Exception-record values are independently bound to an approved target above.
            in_record = filename == 'manifest.json' and re.fullmatch(r'/privacyExceptions/\d+/value', pointer)
            if in_record:
                continue
            issue = detect(text)
            require(issue is None or (filename, pointer, text) in allowed, issue or 'PRIVACY')
    readme = file_path(root, 'README.md').read_text()
    require(readme.startswith('# SYNTHETIC_CONTRACT') and 'không case nào' in readme.lower(), 'PROVENANCE')
    require(detect(readme) is None, 'PRIVACY')
    scenario_unresolved = [s['id'] for s in scenarios['scenarios'] if s['oracleMode'] == 'UNRESOLVED']
    result = {'validation': 'PASS', 'corpusClass': manifest['corpusClass'], 'acceptedCorpus': not pending,
              'pendingApprovals': pending, 'unresolvedOracles': unresolved, 'unresolvedScenarios': scenario_unresolved,
              'largeNumericStress': 'BLOCKED_PENDING_EXACT_VALUE_APPROVAL', 'realCorpus': 'BLOCKED',
              'inventory': inventory, 'scenarioCount': len(scenarios['scenarios']), 'privacyExceptions': len(allowed)}
    require(not require_approved or not pending, 'PROVENANCE')
    return result


def scan_apk(path, fixture_root=ROOT / 'fixtures'):
    path = pathlib.Path(path)
    require(path.is_file(), 'EVIDENCE')
    manifest = strict_json(file_path(pathlib.Path(fixture_root), 'manifest.json'))
    names = META | {pathlib.PurePosixPath(c[k]).name for c in manifest['cases'] for k in ('inputPath', 'expectedPath')}
    markers = [s.encode(e) for s in MARKERS for e in ('utf-8', 'utf-16le', 'utf-16be')]
    hits, entries, bad_entries = [], [], []
    try:
        with zipfile.ZipFile(path) as z:
            require(z.namelist() and len(z.namelist()) == len(set(z.namelist())), 'EVIDENCE')
            for n in z.namelist():
                entries.append(n)
                p = pathlib.PurePosixPath(n)
                if 'fixtures' in p.parts or (p.parts and p.parts[0] in ('assets', 'res') and p.name in names):
                    bad_entries.append(n)
                if not n.endswith('/'):
                    data = z.read(n)
                    for num, marker in enumerate(markers):
                        if marker in data:
                            hits.append({'entry': n, 'markerIndex': num, 'count': data.count(marker)})
    except (OSError, zipfile.BadZipFile, RuntimeError):
        raise Invalid('EVIDENCE') from None
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'entries': entries,
            'expectedMarkerCount': 0, 'observedMarkerCount': sum(x['count'] for x in hits),
            'markerHits': hits, 'forbiddenEntries': bad_entries,
            'contentScan': 'FAIL' if hits else 'PASS', 'entryScan': 'FAIL' if bad_entries else 'PASS'}


def qa_c09(root):
    spec = importlib.util.spec_from_file_location('t02_readonly_qa', ROOT / 'qa/tools/verify_review_package.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.c09(str(root))
    result = module.R[-1]
    require(result['id'] == 'C09', 'EVIDENCE')
    return result


def verify_control_evidence(rows):
    require(isinstance(rows, list), 'EVIDENCE')
    require({r.get('control') for r in rows} == {f'NC-{n:02d}' for n in range(1, 16)}, 'EVIDENCE')
    require(all(r.get('result') == 'PASS' and r.get('expected') == r.get('observed')
                and r.get('originalUnchanged') is True for r in rows), 'EVIDENCE')


def verify_junit_evidence(xml_path, expected_names):
    try:
        suite = ET.parse(xml_path).getroot()
        names = [(c.get('classname'), c.get('name')) for c in suite.iter('testcase')]
        require(names and len(names) == len(set(names)) and set(names) == set(expected_names), 'JUNIT')
        require(int(suite.get('tests', 0)) == len(names), 'JUNIT')
        require(all(int(suite.get(k, 0)) == 0 for k in ('failures', 'errors', 'skipped')), 'JUNIT')
        require(not any(c.find(tag) is not None for c in suite.iter('testcase') for tag in ('failure', 'error', 'skipped')), 'JUNIT')
    except (ET.ParseError, ValueError, OSError):
        raise Invalid('JUNIT') from None


def write_report(path, result):
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures', type=pathlib.Path, default=ROOT / 'fixtures')
    p.add_argument('--require-approved', action='store_true')
    p.add_argument('--apk', type=pathlib.Path, action='append', default=[])
    p.add_argument('--report', type=pathlib.Path)
    args = p.parse_args()
    try:
        result = validate(args.fixtures, args.require_approved)
        require(result == validate(args.fixtures, args.require_approved), 'ORDER')
        result['c09'] = qa_c09(args.fixtures.parent)
        require(result['c09']['result'] == 'PASS', 'PRIVACY')
        result['qaToolBlob'] = subprocess.check_output(['git', 'hash-object', 'qa/tools/verify_review_package.py'], cwd=ROOT, text=True).strip()
        if args.apk:
            require(len(args.apk) == 2, 'EVIDENCE')
            result['apks'] = [scan_apk(a, args.fixtures) for a in args.apk]
            write_report(args.report, result)
            require(all(a['contentScan'] == a['entryScan'] == 'PASS' for a in result['apks']), 'MARKER')
        write_report(args.report, result)
        print(json.dumps({'validation': result['validation'], 'acceptedCorpus': result['acceptedCorpus'], 'pendingApprovals': len(result['pendingApprovals']), 'unresolvedOracles': len(result['unresolvedOracles']), 'scenarios': result['scenarioCount'], 'C09': result['c09']['result']}))
    except Invalid as e:
        write_report(args.report, {'validation': 'FAIL', 'rule': e.rule, 'case': e.case})
        print(json.dumps({'validation': 'FAIL', 'rule': e.rule, 'case': e.case}))
        return 1
    except Exception:
        write_report(args.report, {'validation': 'FAIL', 'rule': 'EVIDENCE', 'case': 'CORPUS'})
        print('{"validation":"FAIL","rule":"EVIDENCE","case":"CORPUS"}')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
