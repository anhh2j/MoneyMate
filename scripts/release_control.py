"""Fail-closed candidate/publication control. Live operations require explicit PO dispatch.

Planning and tests use GET-only snapshots or injected fake transports. No credentials
or signing material are read by plan generation. Never approves or merges a PR.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from versioning import parse_version, read_version

ROOT = Path(__file__).resolve().parents[1]
FILES = {'CHANGELOG.md', 'version.properties', '.release-please-manifest.json'}
REPO = 'anhh2j/MoneyMate'
PO = 'anhh2j'
ENVIRONMENT = 'moneymate-publication'


def require(ok, message):
    if not ok:
        raise ValueError(message)


class API:
    def __init__(self, mode, token=None):
        self.mode = mode
        self.token = token if token is not None else os.environ.get('GH_TOKEN')

    def __call__(self, method, path, data=None, missing=False):
        require(path.startswith('/'), 'Invalid API path')
        if method != 'GET':
            require(self.mode in ('candidate', 'publication'), 'Read-only transport')
            if self.mode == 'candidate':
                allowed = {'/git/blobs', '/git/trees', '/git/commits', '/git/refs', '/pulls'}
                require(path in allowed or re.fullmatch(r'/issues/\d+/labels', path), 'Candidate write endpoint forbidden')
                if path == '/git/refs':
                    require(data['ref'].startswith('refs/heads/release-candidates/'), 'Candidate may only create fresh candidate branches')
            else:
                require((method == 'POST' and path in {'/git/tags','/git/refs','/releases'}) or (method == 'PATCH' and re.fullmatch(r'/releases/\d+',path)), 'Publication endpoint forbidden')
                if path == '/git/refs':
                    require(data['ref'].startswith('refs/tags/v'), 'Publication ref must be a version tag')
        request = urllib.request.Request('https://api.github.com/repos/'+REPO+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization':'Bearer '+(self.token or ''), 'Accept':'application/vnd.github+json', 'Content-Type':'application/json', 'X-GitHub-Api-Version':'2022-11-28'}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                return None
            raise ValueError('GitHub API denied/failed: '+method+' '+path+' ('+str(error.code)+')') from None


def dispatch_guard(version, sha, verb):
    parse_version(version)
    require(re.fullmatch('[0-9a-f]{40}', sha), 'Full source SHA required')
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'Unexpected repository')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'Manual dispatch only')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Dispatch from main only')
    require(os.environ.get('GITHUB_ACTOR') == PO and os.environ.get('GITHUB_TRIGGERING_ACTOR', PO) == PO, 'PO operator required')
    require(os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'No publication/candidate rerun: start a new reviewed request')
    require(os.environ.get('RELEASE_CONFIRMATION') == verb+' '+version+' @ '+sha, 'Explicit version/SHA confirmation required')


def latest_release(api):
    releases = api('GET', '/releases?per_page=100')
    require(len(releases) < 100, 'Release pagination requires explicit review')
    found = []
    for release in releases:
        if release['draft']:
            continue
        tag = release['tag_name']
        if re.fullmatch(r'v\d+\.\d+\.\d+(?:-(alpha|beta|rc)\.\d+)?', tag):
            found.append((parse_version(tag[1:])[1], tag))
    if not found:
        require(not api('GET', '/git/matching-refs/tags/'), 'Tags exist without released state; investigate')
        return None
    tag = max(found)[1]
    ref = api('GET', '/git/ref/tags/'+tag)
    require(ref['object']['type'] == 'tag', 'Previous release tag must be annotated')
    annotation = api('GET', '/git/tags/'+ref['object']['sha'])
    require(annotation['object']['type'] == 'commit', 'Nested/non-commit tag forbidden')
    return {'tagName':tag, 'sha':annotation['object']['sha']}


def snapshot(api, sha, version):
    require(api('GET', '/branches/main')['commit']['sha'] == sha, 'main moved')
    require(subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip() == sha, 'Checkout SHA differs')
    previous = latest_release(api)
    if previous:
        require(subprocess.run(['git','merge-base','--is-ancestor',previous['sha'],sha],cwd=ROOT).returncode == 0, 'Previous release is not an ancestor of main')
    revision = previous['sha']+'..'+sha if previous else sha
    # Use explicit per-commit reads; no ambiguous delimiter parsing for commit messages.
    commits = []
    shas = subprocess.check_output(['git','rev-list', revision], cwd=ROOT, text=True).splitlines()
    require(len(shas) <= 500, 'History exceeds reviewed bound')
    for item in shas:
        message = subprocess.check_output(['git','show','-s','--format=%B',item], cwd=ROOT, text=True).strip()
        paths = subprocess.check_output(['git','diff-tree','--root','--no-commit-id','--name-only','-r',item], cwd=ROOT, text=True).splitlines()
        commits.append({'sha':item,'message':message,'files':paths})
    return {'config':json.loads((ROOT/'release-please-config.json').read_text()),
        'manifest':json.loads((ROOT/'.release-please-manifest.json').read_text()),
        'files':{name:(ROOT/name).read_text() for name in ['CHANGELOG.md','version.properties']},
        'commits':commits,'latestRelease':previous,'requestedVersion':version}


def generate(api, sha, version, directory):
    directory.mkdir(parents=True, exist_ok=True)
    source = directory/'input.json'
    source.write_text(json.dumps(snapshot(api, sha, version), indent=2))
    plan = directory/'candidate.json'
    subprocess.run(['node',str(ROOT/'scripts/release_plan.cjs'),str(source),str(plan)], check=True)
    return json.loads(plan.read_text())


def create_candidate(api, plan, sha):
    review_environment(api, 'moneymate-candidate')
    require(set(plan['files']) == FILES and plan['draft'] is True, 'Invalid plan scope')
    require(plan['title'] == 'chore(release): release '+plan['version'], 'Invalid PR title')
    branch = 'release-candidates/'+plan['version']+'-'+sha[:12]
    require(api('GET','/git/ref/heads/'+branch, missing=True) is None, 'Candidate branch exists: Leader must review; never overwrite')
    for label in plan['labels']:
        require(api('GET','/labels/'+urllib.parse.quote(label, safe=''), missing=True), 'PO must configure required label first')
    commit = api('GET','/git/commits/'+sha)
    entries = []
    for name, content in sorted(plan['files'].items()):
        blob = api('POST','/git/blobs',{'content':content,'encoding':'utf-8'})
        entries.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
    tree = api('POST','/git/trees',{'base_tree':commit['tree']['sha'],'tree':entries})
    new = api('POST','/git/commits',{'message':plan['title'],'tree':tree['sha'],'parents':[sha]})
    require(api('GET','/branches/main')['commit']['sha'] == sha, 'main moved before branch write')
    api('POST','/git/refs',{'ref':'refs/heads/'+branch,'sha':new['sha']})
    pr = api('POST','/pulls',{'head':branch,'base':'main','title':plan['title'],'draft':True,
        'body':'Release candidate only. Runtime 17.6.0; base '+sha+'. No tag/release/signing. PO dispatch is not publication approval. QA/Leader review and CI required.\n\nVersion '+plan['version']+'; versionCode '+str(plan['versionCode'])+'.'})
    api('POST','/issues/'+str(pr['number'])+'/labels',{'labels':plan['labels']})
    return pr['number']


def review_environment(api, name):
    environment = api('GET','/environments/'+name)
    rules = environment.get('protection_rules', [])
    reviewers = [r for rule in rules if rule['type'] == 'required_reviewers' for r in rule.get('reviewers', [])]
    require(any(r.get('type') == 'User' and r.get('reviewer',{}).get('login') == PO for r in reviewers), 'Protected environment must require PO reviewer')
    require(environment.get('deployment_branch_policy',{}).get('protected_branches') is True, 'Environment must restrict deployments to protected branches')


def publication_preflight(api, sha, version, pr_number, signer):
    require(re.fullmatch('[0-9a-fA-F]{64}', signer), 'Expected signing certificate SHA256 required')
    branch = api('GET','/branches/main')
    require(branch['commit']['sha'] == sha and branch['protected'], 'Exact protected main required')
    review_environment(api, ENVIRONMENT)
    pr = api('GET','/pulls/'+str(pr_number))
    require(pr['merged'] and pr['merge_commit_sha'] == sha and pr['base']['ref'] == 'main', 'Merged release PR must identify exact publication SHA')
    require(pr['title'] == 'chore(release): release '+version and pr['head']['ref'].startswith('release-candidates/'), 'Not a reviewed release-candidate PR')
    require(any(x['name'] == 'autorelease: pending' for x in pr['labels']), 'Missing pending release label')
    files = api('GET','/pulls/'+str(pr_number)+'/files?per_page=100')
    require(0 < len(files) <= 3 and all(x['filename'] in FILES for x in files), 'Release PR contains unexpected changes')
    runs = api('GET','/actions/workflows/ci.yml/runs?head_sha='+sha+'&event=push&per_page=100')['workflow_runs']
    runs = [r for r in runs if r['head_sha'] == sha and r['event'] == 'push' and r['head_branch'] == 'main']
    require(runs, 'Post-merge CI at exact SHA required')
    run = max(runs, key=lambda r:r['id'])
    require(run['status']=='completed' and run['conclusion']=='success', 'Latest post-merge CI must be completed/success')
    jobs = api('GET','/actions/runs/'+str(run['id'])+'/jobs?per_page=100')['jobs']
    require(all(any(j['name']==name and j['conclusion']=='success' for j in jobs) for name in ['Build, lint and test','Install and launch debug and R8 release APKs']), 'Required CI jobs missing or failed')
    require(api('GET','/git/ref/tags/v'+version, missing=True) is None, 'Tag already exists; never move/retry it')
    require(api('GET','/releases/tags/v'+version, missing=True) is None, 'Release already exists')
    return run['id']


def verify_local(version):
    require(read_version(ROOT)[0] == version, 'Canonical APK version mismatch')
    require(json.loads((ROOT/'.release-please-manifest.json').read_text()) == {'.':version}, 'Candidate manifest mismatch')
    text = (ROOT/'CHANGELOG.md').read_text()
    headings = re.findall(r'^## \[([^\]]+)\]', text, re.M)
    require(headings and headings[0]=='Unreleased' and len(headings)==len(set(headings)) and headings.count(version)==1, 'Invalid changelog headings')
    entry = re.split(r'^## ',text,flags=re.M)[headings.index(version)+1]
    require('Pending release' not in entry, 'Candidate changelog not finalized')
    require(all('### '+name in entry for name in ['Added','Changed','Fixed','Security','Breaking']) and 'Spec: DOC-SPEC v2.1.0' in entry, 'Incomplete release notes')
    require(not re.search(r'compare/([^\s)]+)\.\.\.\1(?:[)\s]|$)', entry), 'Self comparison')
    return entry[entry.index('\n')+1:]


def verify_apk(version, signer, apk):
    subprocess.run(['python3',str(ROOT/'scripts/verify_release.py'),'v'+version,str(apk),'--checksum',str(apk)+'.sha256'],check=True)
    certificate = subprocess.check_output(['apksigner','verify','--print-certs',str(apk)],text=True)
    hashes = re.findall(r'^Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)$',certificate,re.M)
    require(hashes == [signer.lower()] or [x.lower() for x in hashes]==[signer.lower()], 'APK signer does not match PO fingerprint')


def verify_checksum(apk):
    checksum = Path(str(apk)+'.sha256')
    require(apk.is_file() and checksum.is_file(), 'APK and existing checksum required')
    expected = hashlib.sha256(apk.read_bytes()).hexdigest()+'  '+apk.name+'\n'
    require(checksum.read_text() == expected, 'Transferred APK checksum mismatch')


def publish(api, sha, version, pr_number, signer, apk):
    # Called only in protected publication job after build/verification, never in tests live.
    publication_preflight(api, sha, version, pr_number, signer)
    notes = verify_local(version)
    verify_checksum(apk)  # Check transferred evidence before verify_release regenerates it.
    verify_apk(version, signer, apk)
    previous = latest_release(api)
    require(not previous or parse_version(version)[1] > parse_version(previous['tagName'][1:])[1], 'VersionCode must increase')
    annotation = api('POST','/git/tags',{'tag':'v'+version,'message':'MoneyMate '+version+'\nImplements Spec v2.1.0\nSource '+sha,'object':sha,'type':'commit'})
    api('POST','/git/refs',{'ref':'refs/tags/v'+version,'sha':annotation['sha']})
    ref = api('GET','/git/ref/tags/v'+version)
    require(ref['object']['type']=='tag' and ref['object']['sha']==annotation['sha'], 'Annotated tag verification failed')
    release = api('POST','/releases',{'tag_name':'v'+version,'target_commitish':sha,'name':'MoneyMate '+version,'draft':True,'prerelease':'-' in version,
        'body':notes+'\nImplements Spec v2.1.0\nAC-9 build metadata/signature verified. Other product AC not claimed. Device installation pending PO confirmation.\nSource: '+sha})
    subprocess.run(['gh','release','upload','v'+version,str(apk),str(apk)+'.sha256','--repo',REPO],check=True)
    assets = api('GET','/releases/'+str(release['id']))['assets']
    require({a['name'] for a in assets} == {apk.name,apk.name+'.sha256'}, 'Release asset set mismatch')
    api('PATCH','/releases/'+str(release['id']),{'draft':False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['plan','candidate','preflight','verify-apk','publish'])
    p.add_argument('--sha',required=True); p.add_argument('--version',required=True)
    p.add_argument('--pr',type=int); p.add_argument('--signer');p.add_argument('--apk',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'build/reports/release-candidate')
    args = p.parse_args()
    dispatch_guard(args.version,args.sha,'CANDIDATE' if args.mode in ('plan','candidate') else 'PUBLISH')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == args.sha, 'Checkout SHA differs')
    if args.mode in ('plan','candidate'):
        result = generate(API('read'),args.sha,args.version,args.output)
        if args.mode=='candidate':
            require(os.environ.get('CANDIDATE_CREATION_ENABLED')=='true', 'PO must explicitly enable candidate creation')
            print('Draft candidate PR:',create_candidate(API('candidate'),result,args.sha))
    else:
        require(args.pr and args.signer,'PR and signer required')
        publication_preflight(API('read'),args.sha,args.version,args.pr,args.signer)
        verify_local(args.version)
        if args.mode=='verify-apk':
            require(args.apk and args.apk.is_file(), 'APK required')
            verify_apk(args.version,args.signer,args.apk)
        if args.mode=='publish':
            require(os.environ.get('PUBLICATION_ENABLED')=='true' and args.apk and args.apk.is_file(), 'Publication disabled/missing APK')
            publish(API('publication'),args.sha,args.version,args.pr,args.signer,args.apk)
        print('PASS publication preflight; no signing secrets read by this command')


if __name__ == '__main__':
    try:
        main()
    except (ValueError,subprocess.CalledProcessError) as error:
        raise SystemExit('BLOCKED: '+str(error))
