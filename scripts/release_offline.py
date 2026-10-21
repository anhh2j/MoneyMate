"""Dry-run the checked-out bootstrap tree and real git history; no remote API."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/reports/t00c'


def main():
    manifest = json.loads((ROOT/'.release-please-manifest.json').read_text())
    if manifest:
        # Later releases are covered by synthetic previous-release regression;
        # a local checkout cannot authenticate published GitHub release state.
        print('Offline bootstrap snapshot not applicable after first candidate; regression still required')
        return
    shas = subprocess.check_output(['git','rev-list','HEAD'],cwd=ROOT,text=True).splitlines()
    if len(shas)>500:
        raise ValueError('Offline history exceeds reviewed bound')
    commits=[]
    for sha in shas:
        message=subprocess.check_output(['git','show','-s','--format=%B',sha],cwd=ROOT,text=True).strip()
        paths=subprocess.check_output(['git','diff-tree','--root','--no-commit-id','--name-only','-r',sha],cwd=ROOT,text=True).splitlines()
        commits.append({'sha':sha,'message':message,'files':paths})
    source={'config':json.loads((ROOT/'release-please-config.json').read_text()),'manifest':manifest,
        'files':{name:(ROOT/name).read_text() for name in ['CHANGELOG.md','version.properties']},
        'commits':commits,'latestRelease':None,'requestedVersion':'0.1.0-alpha.1'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'bootstrap-input.json').write_text(json.dumps(source,indent=2)+'\n')
    subprocess.run(['node',str(ROOT/'scripts/release_plan.cjs'),str(OUT/'bootstrap-input.json'),str(OUT/'bootstrap-plan.json')],check=True,cwd=ROOT)


if __name__=='__main__':
    main()
