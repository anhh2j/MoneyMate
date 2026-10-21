// Pure release-please 17.6.0 planner: no GitHub client, token, tag or signing API.
const fs = require('node:fs');
const assert = require('node:assert/strict');
require('release-please'); // Initialize public entry point before 17.6.0 strategy internals.
const {Go} = require('release-please/build/src/strategies/go');
const {Version} = require('release-please/build/src/version');
const {TagName} = require('release-please/build/src/util/tag-name');
const {parseConventionalCommits} = require('release-please/build/src/commit');
const {PrereleaseVersioningStrategy} = require('release-please/build/src/versioning-strategies/prerelease');
const VERSION = require('release-please/package.json').version;
const ACTION_SHA = '45996ed1f6d02564a971a2fa1b5860e934307cf7';
const quiet = Object.fromEntries(['info','warn','debug','error'].map(k => [k, () => {}]));
const sections = ['Added','Changed','Fixed','Security','Breaking'];

function code(version) {
  const m = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(alpha|beta|rc)\.([1-9]\d*))?$/.exec(version);
  assert(m, 'Unsupported version');
  const [major,minor,patch] = m.slice(1,4).map(Number);
  const n = m[5] ? Number(m[5]) : 0;
  assert(minor <= 99 && patch <= 99 && n <= 29, 'DOC-VER version bounds');
  const result = major * 1000000 + minor * 10000 + patch * 100 + (m[4] ? {alpha:0,beta:30,rc:60}[m[4]] + n : 99);
  assert(Number.isSafeInteger(result) && result <= 2147483647, 'versionCode overflow');
  return result;
}

function productCommit(c) {
  // Type alone (e.g. fix(ci)) must not bump the product.
  return /^(feat|fix|perf)\((capture|parser|dedup|categorizer|data|privacy|security|app)\)!?:/.test(c.message)
    && c.files.some(p => /^(app|capture|parser|dedup|categorizer|data|privacy|security|core-model)\/src\/main\//.test(p));
}

async function rawCandidate(input, overrides = {}) {
  assert.equal(VERSION, '17.6.0', 'Release runtime drift');
  const cfg = input.config;
  const scm = {repository: {owner:'anhh2j', repo:'MoneyMate'}};
  const strategy = new Go({
    github: scm, targetBranch:'main', packageName:'MoneyMate', includeComponentInTag:false,
    includeVInTag:true, initialVersion:cfg.packages['.']['initial-version'],
    pullRequestTitlePattern:cfg['pull-request-title-pattern'],
    extraFiles:cfg.packages['.']['extra-files'], logger:quiet,
    versioningStrategy:new PrereleaseVersioningStrategy({bumpMinorPreMajor:true, prerelease:cfg.prerelease, prereleaseType:cfg.packages['.']['prerelease-type']}),
    changelogSections:[{type:'feat',section:'Added'},{type:'fix',section:'Fixed'},{type:'perf',section:'Changed'}, {type:'ci',section:'Changed',hidden:false},{type:'chore',section:'Changed',hidden:false}],
    ...overrides,
  });
  const previous = input.latestRelease ? {tag:TagName.parse(input.latestRelease.tagName), sha:input.latestRelease.sha, notes:''} : undefined;
  return strategy.buildReleasePullRequest(parseConventionalCommits(input.commits, quiet), previous, true, ['autorelease: pending']);
}

function entries(text) {
  assert(text.startsWith('# Changelog\n'), 'Invalid changelog header');
  const parts = text.split(/^## /m).slice(1).map(p => {
    const i = p.indexOf('\n');
    const heading = p.slice(0,i), key = /^\[([^\]]+)\]/.exec(heading)?.[1];
    assert(key, 'Malformed changelog heading');
    return {key, heading, body:p.slice(i+1).trim()};
  });
  assert.equal(new Set(parts.map(p=>p.key)).size, parts.length, 'Duplicate changelog heading');
  assert.equal(parts[0]?.key, 'Unreleased', 'Unreleased must be first');
  return parts;
}

function normalizedChangelog(text, notes, version, bootstrap, date) {
  const old = entries(text);
  const existing = old.find(p=>p.key===version);
  assert(!existing || bootstrap && /Pending release/.test(existing.heading), 'Refuse replacing released history');
  const carried = existing?.body || '';
  const blocks = {};
  for (const name of sections) {
    const match = new RegExp('^### '+name+'\\n([\\s\\S]*?)(?=^### |^Spec:|^This entry|$(?![\\s\\S]))','m').exec(carried);
    blocks[name] = match ? match[1].trim() : '';
  }
  // Merge generated references into the five canonical sections, once per release.
  const generated = notes.replace(/^#+[^\n]*\n/, '').trim();
  for (const part of generated.split(/^### /m).filter(Boolean)) {
    const i = part.indexOf('\n');
    const title = part.slice(0,i).trim();
    const name = sections.includes(title) ? title : /BREAKING/i.test(title) ? 'Breaking' : 'Changed';
    const content = (i >= 0 ? part.slice(i+1) : part).trim();
    if (content) blocks[name] = [blocks[name],content].filter(Boolean).join('\n');
  }
  const body = sections.map(name=>'### '+name+'\n'+(blocks[name] || '- No additional changes.')).join('\n\n')
    + '\n\nSpec: DOC-SPEC v2.1.0\n';
  const heading = '## ['+version+'] - '+date;
  const history = old.filter(p=>p.key!=='Unreleased' && p.key!==version).map(p=>'## '+p.heading+'\n\n'+p.body+'\n').join('\n');
  const output = '# Changelog\n\n## [Unreleased]\n\n'+(old[0].body ? old[0].body+'\n\n' : '')+heading+'\n\n'+body+'\n'+history;
  entries(output);
  assert(!/compare\/([^\s)]+)\.\.\.\1(?:[)\s]|$)/.test(output), 'Self comparison URL');
  return output;
}

async function plan(input) {
  assert.equal(VERSION, '17.6.0');
  assert.equal(input.config['release-type'], 'go');
  assert.equal(input.config['release-as'], undefined, 'Persistent release-as is forbidden');
  assert.equal(input.config['include-component-in-tag'], false);
  const bootstrap = !input.latestRelease;
  if (bootstrap) {
    assert.deepEqual(input.manifest, {}, 'Unreleased bootstrap manifest must be empty');
    assert.equal(input.requestedVersion, '0.1.0-alpha.1');
    assert.equal(input.config.packages['.']['initial-version'], '0.1.0-alpha.1');
  } else {
    assert.equal(input.manifest['.'], input.latestRelease.tagName.replace(/^v/, ''), 'Manifest/released-state mismatch');
    input = {...input, commits:input.commits.filter(productCommit)};
    assert(input.commits.length, 'No product changes: tooling/docs/deps do not release');
  }
  const candidate = await rawCandidate(input);
  assert(candidate?.version, 'No eligible release notes');
  const version = candidate.version.toString();
  assert.equal(version, input.requestedVersion, 'Requested version differs from verified candidate');
  const versionCode = code(version);
  if (input.latestRelease) assert(versionCode > code(input.latestRelease.tagName.replace(/^v/, '')), 'Version must increase');
  const files = {};
  for (const update of candidate.updates) {
    assert(['CHANGELOG.md','version.properties'].includes(update.path), 'Unexpected updater file');
    files[update.path] = update.updater.updateContent(input.files[update.path]);
  }
  assert.equal((files['version.properties'].match(/^VERSION_NAME=/gm)||[]).length, 1);
  assert(files['version.properties'].includes('VERSION_NAME='+version+'\n'));
  assert(files['version.properties'].includes('# x-release-please-start-version'));
  assert(files['version.properties'].includes('# x-release-please-end'));
  files['CHANGELOG.md'] = normalizedChangelog(input.files['CHANGELOG.md'], candidate.body.releaseData[0].notes, version, bootstrap, input.date || new Date().toISOString().slice(0,10));
  files['.release-please-manifest.json'] = JSON.stringify({'.':version},null,2)+'\n';
  return {runtime:VERSION, referenceActionSha:ACTION_SHA, version, versionCode, bootstrap, title:candidate.title.toString(), files, draft:true, labels:['autorelease: pending']};
}

module.exports = {plan, rawCandidate, code, productCommit, normalizedChangelog, entries, VERSION, ACTION_SHA};
if (require.main === module) {
  plan(JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))).then(result=>{
    fs.writeFileSync(process.argv[3], JSON.stringify(result,null,2)+'\n');
    console.log('PASS release-please '+VERSION+' plan '+result.version+' / '+result.versionCode+'; no remote writes');
  }).catch(error=>{console.error('BLOCKED: '+error.message); process.exitCode=1;});
}
