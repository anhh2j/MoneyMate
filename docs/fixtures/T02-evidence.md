# T02-SYNTHETIC-PACK — Developer evidence

Authorized by Issue #14 comment 6333655803; controlling plan DESIGN-R1, QA design APPROVE. This is implementation evidence, not QA acceptance. Baseline main: `4570e4e3cece382e5a69fa277046628c05f0aa07`. Separate branch feature/T02-fixtures. PR #10 not modified or cherry-picked.

## Content and privacy status

15 pairs (5 BIDV, 5 MSB, 5 MB; 2 noise each), 72 declarative scenarios covering FX-01..24 per bank. `corpusClass=SYNTHETIC_CONTRACT`; no real-bank golden. Every seed PO/QA privacy approval PENDING; acceptedCorpus=false. No numeric/time exceptions requested or approved. Three missing-amount oracles unresolved; numeric stress above seven digits remains BLOCKED pending exact value approval. Existing small numbers and fixed ISO times pass both scanners without exceptions. Body `.txt` never receives an exception. Hashes are colon-delimited SHA-256, still recomputable over original bytes.

## F1–F8 trace

| Finding | Implementation | Evidence |
| --- | --- | --- |
| F1 | README first warning + corpus flag, loader metadata | validator + NC-10 + FixtureLoaderTest |
| F2 | schema source scopes crosschecked against code, MSB IN/all MB synthetic_contract | NC-10 source-scope subcases |
| F3 | Descriptive filenames retain approved naming exception | 41-path diff |
| F4 | Original, decoded, Unicode/zero-width/separator normalized detection | NC-07/08 per-separator subcases |
| F5 | No text exceptions; safe grouped body amounts; QA C09 unchanged | baseline empty C09 NA, working corpus C09 PASS, QA tool blob |
| F6 | manifest order; double load bytes, LF/CRLF/NFC/NFD | JUnit FixtureLoaderTest, deterministic validator replay |
| F7 | header/package/title/observedPackage consistency and unresolved-golden rejection | NC-03/11 |
| F8 | namespace/SYNTHETIC_ content UTF-8/UTF-16 scans and ZIP entry checks | negative ZIP canaries; both real APK scans in CI |

FixtureLoader extracts only restricted safe manifest string fields after independent Python strict JSON/schema validation. It does not decode expected JSON into a transaction, execute scenarios, parse bank notifications, or add a production dependency. Sharing the loader with dedup/Simulator is outside this task.

## Commands and artifacts

Local: `python3 scripts/t02_fixture_checks.py --report build/reports/t02/fixture-validation.json`; `python3 -m unittest discover -s scripts/tests -p 'test_t02_fixture_checks.py' -v`; ktlint formatter/checker on the two new Kotlin files and parser Gradle resource mapping; `git diff --check`. CI runs the full baseline gates unchanged plus these commands and scans both generated debug/R8 APKs. Reports: `build/reports/t02/fixture-validation.json`, `negative-controls.json`, `apk-isolation.json` and logs in test-lint-dod-reports. JUnit XML is in parser build/test-results/test. Original hashes compared after every negative mutation; no invalid fixture is uploaded. Canary negative controls are temporary synthetic data only. Legacy QA tool emits ResourceWarning for its existing unclosed file reads when Python warnings are enabled; qa/ is unchanged.

## Known blocker — unchanged baseline review packager

At main, `scripts/t00b_review_evidence.py` lines around verify_junit require exactly 20 JUnit tests. T02 adds two real loader tests, so expected total is 22; `.github/check_skeleton.py` derives the count from source and supports these tests, but the unchanged packager will reject 22. Packager is outside this 41-file allowlist: not modified and not cherry-picked from PR #10. No test is removed/skipped, no result rewritten, and no alternate package is used to impersonate a passing baseline gate. CI/runtime evidence will be handed off with this blocker if reproduced. Root CI and source-review-package/C07 remain NOT VERIFIED until the actual run result; no synthetic pack acceptance is claimed.

## Governance and handover

Full HEAD, PR/run links, job/artifact IDs/digests and final outcomes will be recorded on Issue #14 and the Draft PR at the exact built SHA after CI. Developer does not write QA verdict or PO signoff. PO should review all 15 safe seeds and the per-case provenance/expected matrix before authorizing accepted status; statuses stay PENDING until evidence exists. T02-REAL-CORPUS BLOCKED, T01 OPEN, B2 API37 ENV-FAIL and B3 PENDING PO DEVICE unchanged. No production parser/dedup/DB/capture, qa/, Approved DOCX, version, dependencies, permissions or release settings changed.
