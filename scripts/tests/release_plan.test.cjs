const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {plan,rawCandidate,code,entries,VERSION,ACTION_SHA} = require('../release_plan.cjs');
const root = path.resolve(__dirname,'../..');
const original = {
  config:JSON.parse(fs.readFileSync(path.join(root,'release-please-config.json'))),
  manifest:{}, latestRelease:null, requestedVersion:'0.1.0-alpha.1', date:'2026-10-21',
  files:Object.fromEntries(['CHANGELOG.md','version.properties'].map(f=>[f,fs.readFileSync(path.join(root,f),'utf8')])),
  commits:[{sha:'1'.repeat(40),message:'ci(release): initial M0 pipeline',files:['.github/workflows/ci.yml']}],
};
const copy = () => structuredClone(original);
function next(version, message='fix(app): correct visible behavior', files=['app/src/main/Example.kt']) {
  const x=copy();x.latestRelease={tagName:'v'+version,sha:'2'.repeat(40)};x.manifest={'.':version};
  x.files['version.properties']=x.files['version.properties'].replace('0.1.0-alpha.1',version);
  x.files['CHANGELOG.md']=x.files['CHANGELOG.md'].replace('0.1.0-alpha.1',version).replace('Pending release','2026-10-20');
  x.commits=[{sha:'3'.repeat(40),message,files}];return x;
}
test('exact runtime and reference action SHA; first release has one entry and intact M0',async()=>{
  assert.equal(VERSION,'17.6.0');assert.equal(ACTION_SHA,'45996ed1f6d02564a971a2fa1b5860e934307cf7');
  const reference=JSON.parse(fs.readFileSync(path.join(root,'scripts/release-runtime.json')));
  const lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json')));
  assert.equal(lock.packages['node_modules/release-please'].integrity,reference.package_integrity);
  const p=await plan(copy());assert.equal(p.version,'0.1.0-alpha.1');assert.equal(p.versionCode,10001);
  assert.equal(p.title,'chore(release): release 0.1.0-alpha.1');assert(p.draft);
  const log=p.files['CHANGELOG.md'];assert.deepEqual(entries(log).map(e=>e.key),['Unreleased','0.1.0-alpha.1']);
  assert(!log.includes('v0.1.0-alpha.1...v0.1.0-alpha.1'));assert(log.includes('T00:'));assert(log.includes('T00b:'));
  for(const heading of ['Added','Changed','Fixed','Security','Breaking'])assert.equal(log.split('### '+heading+'\n').length-1,1);
  assert.equal(p.files['version.properties'],original.files['version.properties']);assert.deepEqual(JSON.parse(p.files['.release-please-manifest.json']),{'.':p.version});
});
test('real Manifest empty bootstrap and manifest updater on GET-only fake SCM',async()=>{
  const {Manifest}=require('release-please');
  const scm={repository:{owner:'anhh2j',repo:'MoneyMate'},
    async *releaseIterator(){},async *tagIterator(){},
    async *mergeCommitIterator(){yield original.commits[0];},async *pullRequestIterator(){},
  };
  const cfg={'.':{releaseType:'go',packageName:'MoneyMate',includeComponentInTag:false,includeVInTag:true,
    initialVersion:'0.1.0-alpha.1',extraFiles:[{type:'generic',path:'version.properties'}],
    versioning:'prerelease',prerelease:true,prereleaseType:'alpha.1',bumpMinorPreMajor:true,
    changelogSections:[{type:'ci',section:'Changed',hidden:false}],
    pullRequestTitlePattern:'chore(release): release ${version}'}};
  const manifest=new Manifest(scm,'main',cfg,{}, {logger:{info(){},debug(){},warn(){},error(){}}});
  const candidates=await manifest.buildPullRequests();assert.equal(candidates.length,1);
  const pr=candidates[0];assert.equal(pr.version.toString(),'0.1.0-alpha.1');
  const update=pr.updates.find(u=>u.path==='.release-please-manifest.json');
  assert.deepEqual(JSON.parse(update.updater.updateContent('{}')),{'.':'0.1.0-alpha.1'});
  assert(!pr.body.releaseData[0].notes.includes('v0.1.0-alpha.1...v0.1.0-alpha.1'));
});
test('reproduces old release-as self-comparison using actual 17.6.0 strategy',async()=>{
  const x=next('0.1.0-alpha.1');const raw=await rawCandidate(x,{releaseAs:'0.1.0-alpha.1'});
  assert(raw.body.releaseData[0].notes.includes('v0.1.0-alpha.1...v0.1.0-alpha.1'));
});
test('reject fake previous release state and persistent release-as',async()=>{
  const x=copy();x.manifest={'.':'0.1.0-alpha.1'};await assert.rejects(plan(x),/manifest must be empty/);
  const y=copy();y.config['release-as']='0.1.0-alpha.1';await assert.rejects(plan(y),/release-as/);
});
for(const stage of ['alpha','beta','rc'])test('next '+stage+' release increments and Generic updater preserves markers',async()=>{
  const x=next('0.1.0-'+stage+'.1');x.requestedVersion='0.1.0-'+stage+'.2';x.config.packages['.']['prerelease-type']=stage+'.1';
  const p=await plan(x);assert.equal(p.version,x.requestedVersion);assert(p.files['version.properties'].includes('VERSION_NAME='+x.requestedVersion));
  assert(p.files['version.properties'].includes('# x-release-please-end'));assert.equal(entries(p.files['CHANGELOG.md']).length,3);
});
test('pre-major breaking advances MINOR on stable profile',async()=>{
  const x=next('0.1.0','feat(app)!: incompatible product behavior');x.config.prerelease=false;x.requestedVersion='0.2.0';
  const p=await plan(x);assert.equal(p.version,'0.2.0');assert.equal(p.versionCode,20099);
});
for(const [name,msg,paths] of [
  ['tooling','fix(ci): correct QA tool',['qa/tools/verify_review_package.py']],
  ['docs','docs(docs): update guide',['README.md']],
  ['dependency','chore(deps): update action',['.github/workflows/ci.yml']],
  ['test','fix(app): test only',['app/src/test/Example.kt']],
  ['misleading scope','fix(app): docs only',['README.md']],
])test('no release for '+name,async()=>{
  const x=next('0.1.0-alpha.1',msg,paths);x.requestedVersion='0.1.0-alpha.2';await assert.rejects(plan(x),/No product changes/);
});
test('product plus tooling only uses product changes to bump',async()=>{
  const x=next('0.1.0-alpha.1');x.requestedVersion='0.1.0-alpha.2';x.commits.push({sha:'4'.repeat(40),message:'feat(ci)!: tooling-only breaking',files:['scripts/tool.py']});
  assert.equal((await plan(x)).version,'0.1.0-alpha.2');
});
test('reject requested bump, duplicate history, invalid updater and prerelease overflow',async()=>{
  const x=copy();x.requestedVersion='0.1.0-alpha.2';await assert.rejects(plan(x),/Requested version|strictly equal/);
  const y=copy();y.files['CHANGELOG.md']+='\n## [0.1.0-alpha.1] - duplicate\n';await assert.rejects(plan(y),/Duplicate/);
  const z=copy();z.files['version.properties']='VERSION_NAME=0.1.0-alpha.1\n';await assert.rejects(plan(z));
  const n=next('0.1.0-alpha.29');n.requestedVersion='0.1.0-alpha.30';await assert.rejects(plan(n),/bounds/);
  assert.throws(()=>code('0.100.0'));assert.throws(()=>code('99999.1.0'));
});
test('workflow boundaries: manual only, no push/tag triggers or signing in candidate',()=>{
  const yaml=require('yaml');const c=yaml.parse(fs.readFileSync(path.join(root,'.github/workflows/release.yml'),'utf8'));
  const p=yaml.parse(fs.readFileSync(path.join(root,'.github/workflows/publication.yml'),'utf8'));
  for(const wf of [c,p]){assert.deepEqual(Object.keys(wf.on),['workflow_dispatch']);assert.deepEqual(wf.permissions,{});}
  assert.equal(c.jobs.plan.permissions.contents,'read');assert.equal(c.jobs['create-pr'].environment,'moneymate-candidate');
  assert(!JSON.stringify(c).includes('KEYSTORE'));assert(!JSON.stringify(c).includes('release_created'));
  assert.equal(p.jobs.preflight.permissions.contents,'read');assert.equal(p.jobs['build-signed'].permissions.contents,'read');
  assert.equal(p.jobs.publish.permissions.contents,'write');assert.equal(p.jobs.publish.environment,'moneymate-publication');
  assert(p.jobs.publish.if.includes('PUBLICATION_ENABLED'));assert.equal(p.jobs.publish.needs,'build-signed');
  assert(!JSON.stringify(p.jobs.publish).includes('KEYSTORE'));assert(!JSON.stringify(p.jobs.preflight).includes('KEYSTORE'));
  assert.deepEqual(p.jobs['build-signed'].steps.filter(s=>s.env?.KEYSTORE_BASE64).map(s=>s.name),['Sign only after PO environment approval']);
});
