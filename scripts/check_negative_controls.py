"""Local/CI negative controls; synthetic isolated fixtures, exact source restoration."""
import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tools', required=True, type=__import__('pathlib').Path)
args = parser.parse_args()
from pathlib import Path
import tempfile,subprocess,json,shutil,secrets,string,os
r=Path(__file__).resolve().parents[1];repo=r;out=r/'build/reports/negative-controls';out.mkdir(parents=True,exist_ok=True);tools=args.tools.resolve()
with (out/'docs-pass.log').open('w') as f:
 p=subprocess.run(['python3','scripts/check_docs.py'],cwd=repo,stdout=f,stderr=subprocess.STDOUT);assert p.returncode==0;f.write('\nEXIT_CODE: 0\n')
with tempfile.TemporaryDirectory(prefix='moneymate-docs-negative-') as d:
 d=Path(d)
 for p in (repo/'docs').glob('*.docx'):shutil.copyfile(p,d/p.name)
 next(d.glob('*.docx')).rename(d/'bad.docx')
 with (out/'docs-negative.log').open('w') as f:
  p=subprocess.run(['python3','scripts/check_docs.py','--docs',str(d)],cwd=repo,stdout=f,stderr=subprocess.STDOUT);assert p.returncode==1;f.write('\nEXPECTED_EXIT_CODE: 1\n')
 print('PASS: document checker rejects malformed filename',flush=True)
with tempfile.TemporaryDirectory(prefix='moneymate-secret-negative-') as d:
 d=Path(d);subprocess.run(['git','init','-q',str(d)],check=True)
 token='ghp_'+''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(36))
 (d/'probe.txt').write_text('token='+token+'\n');subprocess.run(['git','add','.'],cwd=d,check=True)
 identity=['git','-c','user.name=Security Probe','-c','user.email=probe@example.invalid']
 subprocess.run(identity+['commit','-qm','test: isolated detection probe'],cwd=d,check=True)
 (d/'probe.txt').unlink();subprocess.run(['git','add','-u'],cwd=d,check=True);subprocess.run(identity+['commit','-qm','test: remove probe from tree'],cwd=d,check=True)
 with (out/'secret-negative.log').open('w') as f:
  p=subprocess.run([str(tools/'gitleaks'),'git','--redact=100','--no-banner','--log-opts=--all','--report-format=json','--report-path='+str(out/'secret-negative.json'),str(d)],stdout=f,stderr=subprocess.STDOUT)
  assert p.returncode==1;findings=json.loads((out/'secret-negative.json').read_text());assert findings;assert all(token not in str(x) for x in findings);f.write('\nEXPECTED_EXIT_CODE: 1; historical probe detected after deletion from current tree\n')
 print('PASS: real gitleaks rejects synthetic secret in deleted historical file; report redacted',flush=True)

with tempfile.TemporaryDirectory(prefix='moneymate-vulnerability-negative-') as d:
 d=Path(d);bom={'bomFormat':'CycloneDX','specVersion':'1.5','version':1,'components':[{'type':'library','group':'org.apache.logging.log4j','name':'log4j-core','version':'2.14.1','purl':'pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1'}]};(d/'probe.cdx.json').write_text(json.dumps(bom))
 with (out/'vulnerability-negative.log').open('w') as f:
  p=subprocess.run([str(tools/'trivy'),'sbom','--severity','HIGH,CRITICAL','--exit-code','1','--format','json','--output',str(out/'vulnerability-negative.json'),str(d/'probe.cdx.json')],stdout=f,stderr=subprocess.STDOUT)
  f.write('\nEXIT_CODE: '+str(p.returncode)+'\n')
  findings=json.loads((out/'vulnerability-negative.json').read_text()) if (out/'vulnerability-negative.json').exists() else {}
  assert p.returncode==1 and any(x.get('Vulnerabilities') for x in findings.get('Results',[])), 'BLOCKER: scanner did not produce expected vulnerability evidence'
 print('PASS: real Trivy rejects HIGH/CRITICAL vulnerable dependency probe',flush=True)

from pathlib import Path
import subprocess,sys,xml.etree.ElementTree as E,json
root=Path(__file__).resolve().parents[1];out=root/'build/reports/negative-controls';metadata=root/'gradle/verification-metadata.xml';ns={'v':'https://schema.gradle.org/dependency-verification'}
original=metadata.read_bytes();xml=E.fromstring(original)
assert xml.findtext('v:configuration/v:verify-metadata',namespaces=ns)=='true'
assert not xml.findall('.//v:trusted-artifact',ns)
component=xml.find("v:components/v:component[@group='com.android.tools.build'][@name='gradle'][@version='9.4.1']",ns);assert component is not None
artifact=component.find("v:artifact[@name='gradle-9.4.1.jar']",ns);assert artifact is not None
checksum=artifact.find('v:sha256',ns).get('value');assert len(checksum)==64
args=['./gradlew','help','--dependency-verification','strict','-Dorg.gradle.dependency.verification.console=verbose','--no-configuration-cache','--no-daemon','--console=plain']
def run(name,expected):
 with (out/name).open('w') as f:
  f.write('COMMAND: '+' '.join(args)+'\n');f.flush();r=subprocess.run(args,cwd=root,stdout=f,stderr=subprocess.STDOUT);f.write(f'\nEXIT_CODE: {r.returncode}\nEXPECTED_EXIT_CODE: {expected}\n')
 assert r.returncode==expected,(name,r.returncode)
 return (out/name).read_text()
try:
 wrong=original.replace(('value="'+checksum+'"').encode(),('value="'+'0'*64+'"').encode(),1);assert wrong!=original;metadata.write_bytes(wrong)
 text=run('checksum-negative.log',1)
 assert 'Dependency verification failed' in text and 'gradle-9.4.1.jar' in text and ('checksum' in text.lower() or 'expected' in text.lower()),text[-8000:]
 print('PASS wrong SHA256 rejected by Gradle verification, exit 1',flush=True)
finally:
 metadata.write_bytes(original)
 assert metadata.read_bytes()==original
run('checksum-restored.log',0);print('PASS restored exact XML bytes, strict build help exit 0',flush=True)
(out/'verification-xml-audit.json').write_text(json.dumps(dict(verify_metadata=True,trusted_artifacts=0,components=len(xml.findall('v:components/v:component',ns)),artifacts=len(xml.findall('v:components/v:component/v:artifact',ns)),sha256=len(xml.findall('.//v:sha256',ns)),negative_component='com.android.tools.build:gradle:9.4.1',negative_artifact='gradle-9.4.1.jar',checksum_restored=True),indent=2))

from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1];out=root/'build/reports/negative-controls'
def run(args,name,expected,stdin=None):
 with (out/name).open('w') as f:
  f.write('COMMAND: '+' '.join(args)+'\n');f.flush();r=subprocess.run(args,cwd=root,input=stdin,text=True,stdout=f,stderr=subprocess.STDOUT);f.write(f'\nEXIT_CODE: {r.returncode}\nEXPECTED_EXIT_CODE: {expected}\n')
 assert r.returncode==expected,(name,r.returncode);print('PASS',name,expected,flush=True)
v=root/'version.properties';original=v.read_bytes()
try:
 v.write_text('VERSION_NAME=not-semver\n');run(['./gradlew','help','--dependency-verification','strict','--console=plain','--no-daemon'],'version-negative.log',1)
 assert 'Invalid or unsupported SemVer' in (out/'version-negative.log').read_text()
finally:v.write_bytes(original)
run(['./gradlew','help','--dependency-verification','strict','--console=plain','--no-daemon'],'version-restored.log',0)
commitlint=str(root/'node_modules/.bin/commitlint')
run([commitlint,'--config',str(root/'commitlint.config.cjs')],'commit-negative.log',1,'invalid message\n')
assert 'type-empty' in (out/'commit-negative.log').read_text()
run([commitlint,'--config',str(root/'commitlint.config.cjs'),'--from','30056b7','--to','HEAD','--verbose'],'commitlint-all.log',0)
