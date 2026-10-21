# ADR-0004 — T00c candidate planning and publication safety

- Date: 2026-10-21
- Status: Proposed for independent QA / Leader review (PR only).
- Scope: supersedes ADR-0002's push-to-main release activation and bootstrap release-as guidance; DOCX Approved documents remain unchanged.

## Decision
Use the exact release-please **17.6.0** core package. Its package integrity matches the lock at action SHA `45996ed1f6d02564a971a2fa1b5860e934307cf7` (see scripts/release-runtime.json). We call that package directly rather than the action's bundled entrypoint: this permits inspecting/normalizing all candidate files before any GitHub write. This is not a claim of executing the byte-identical ncc action bundle; transitive versions are pinned in this repository lock and remain inside the existing npm security scan.

Bootstrap released-state is an empty manifest, initial-version 0.1.0-alpha.1, with no persistent release-as. version.properties stays 0.1.0-alpha.1 / code 10001. An actual Manifest test and Go/Generic-updater tests run offline on 17.6.0. Tests reproduce the old release-as self-comparison and reject that state in the production planner.

A pure planner takes a GET-only snapshot and returns exactly CHANGELOG.md, version.properties and .release-please-manifest.json. The existing pending first entry is consumed once, Unreleased stays first, curated T00/T00b sections and Spec remain. Generated commit links are merged into Added/Changed/Fixed/Security/Breaking, not a duplicate version entry. Later releases require both product type/scope and a changed production-source path. Tooling/docs/deps/tests-only commits cannot trigger a bump. Unknown/new product paths fail conservatively and require an explicitly reviewed eligibility change.

## Candidate boundary
release.yml now has **workflow_dispatch only**, no push/tag/PR activation. PO `anhh2j` must specify the full current main SHA, expected version, and exact `CANDIDATE <version> @ <sha>` confirmation. Default mode is read-only plan with contents:read. An extra create-pr mode is disabled unless CANDIDATE_CREATION_ENABLED=true, protected moneymate-candidate environment requires PO review, branch policy restricts to protected branches, required pending label exists, and repository policy permits PR creation.

Writes only create a fresh release-candidates/<version>-<sha-prefix> branch and a Draft PR with pending label; there is no approve/merge/tag/release endpoint in this route. Any existing target branch causes a stop. The historical release-please--branches--main--components--MoneyMate branch is never touched. Contents write technically permits tags at platform level; the candidate transport also restricts endpoints and ref prefixes, rather than claiming GitHub offers a branch-only token scope.

The writer job alone has contents/PR/issues write (labeling) and actions read (environment policy check). The plan job gets no write permissions or signing secrets. No broad repository default-write setting is required.

## Publication boundary
publication.yml is a different manual workflow. No technical merge or main push invokes it. It is disabled unless PUBLICATION_ENABLED=true. An exact merged release-candidate PR/main SHA/version, expected signing-certificate fingerprint and `PUBLISH <version> @ <sha>` confirmation are mandatory. Only PO can dispatch; reruns are refused so partial publication is investigated instead of overwritten.

Read-only preflight requires protected main unchanged, protected moneymate-publication environment with PO reviewer, candidate PR merged at exactly that SHA and containing only allowed release files, pending label, and latest successful post-merge CI with build/emulator jobs. Existing tag/release, wrong signer, incomplete/duplicate/pending changelog or mismatched manifest/version block.

Signing occurs only after the environment approval, with a read-only repository token. Only that step receives the four signing secrets. APK verification and PO signer fingerprint are checked before artifact handoff. The publisher receives no signing secrets; it rechecks SHA/CI/PR/protection and APK metadata/signature/checksum/fingerprint. It creates an **annotated tag object** pointing to the approved commit, then a draft prerelease/release, attaches APK and checksum, checks the asset set, and makes the release public last. No tag is moved/deleted. Failed upload leaves a draft and an existing tag for PO/Leader investigation, never an automatic retry.

The same environment gates the signing and publication jobs. PO must configure the environment deliberately; the code does not create/change its protection. The human dispatch is release authorization, not implicit authorization from merging a technical or candidate PR. Annotated-tag/API/signing/upload order is tested only on fake transports; no real tag/release/keystore/signing secret is used in T00c testing.

## Operator setup — NOT performed by this PR
PO/Leader must separately approve and configure:
- moneymate-candidate and moneymate-publication environments, required reviewer containing PO, protected-branches-only deployment policy. If only PO can dispatch/approve, prevent-self-review=true would block the flow; do not silently bypass it. A two-person operator model requires a separately approved actor policy change.
- Required branch reviews/checks and no bot auto-approval/auto-merge. Keep repository default token restricted. Decide whether repository GITHUB_TOKEN PR creation is allowed; no checkbox is changed here.
- Required pending label. Post-publication label transition to autorelease: tagged is a manual PO action; the next plan uses verified GitHub releases/annotated tags, not mutable labels as version truth.
- Enablement variables remain unset/off until all checks are reviewed. Four signing secrets should be environment-scoped, with backup owned by PO. Do not place them in candidate/PR tests.
- GitHub's current token behavior can put opened/synchronize/reopened PR workflows in approval-required state. PO must approve workflow execution and then require success at the actual PR HEAD; approval to run CI is not PR approval. No pull_request_target workaround is introduced.
- Keep stale automatic release branch intact until Leader decides recovery; no force update/delete is part of this task.

## Limits
Existing GitHub permissions, live PR creation/labeling, protected-environment approvals, real signing, tag/release/upload and device installation are not exercised by this PR-only task. Missing configuration fails closed. Release side effects are not atomic: a failure after tag creation must be handled by PO without moving an issued tag. Environment policy and repository admin-bypass settings remain PO responsibilities. Real publication is not declared DONE.

## Verification
CI keeps all previous Gradle, lint, security, strict verification, negative-control and emulator gates. It adds offline Node/Python release regression logs under build/reports/t00c. npm lock covers release-please and YAML test parser in the existing full dependency scan; no ignore or severity reduction.

Sources: DOC-VER v1.4.0 Approved (3.2, 3.5–3.6, 5–6, 9); pinned action lock and release-please v17.6.0 source; GitHub environment REST API and workflow-trigger docs, checked 2026-10-21.
