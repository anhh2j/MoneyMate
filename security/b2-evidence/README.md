# B2 Argon2Kt 1.6.0 — isolated experiment, not production

Authorization: Issue #16 comments 6343828169, 6343963213 and PO 6344002046.
Baseline main: 690a74af29897d43fcb9f4c58808ae6ea2e3365f.
Only androidTest uses the candidate; production source and project edges are unchanged.

Reproduce with Java17, the existing SDK37/build-tools37 configuration and an Android
API26/29/33/35 x86_64 emulator: strict :security:assembleDebugAndroidTest, then
`bash security/b2-evidence/run-instrumented.sh`. The isolated workflow performs these
commands and uploads source identity, exact exit codes, JUnit XML, metrics and test APK.
The existing CI workflow is untouched and must still pass its original checks.

Known-answer reference: upstream Argon2Kt v1.6.0, commit
226d943ad1c6344a049c08a437e09688ceb07929,
lib/src/androidTest/java/com/lambdapioneer/argon2kt/Argon2KtTest.kt:
officialTestSuite_v13_argon2id_case3 (m=256 KiB) and case1 (m=65536 KiB),
t=2, p=1, output32, v=0x13, password/salt public synthetic upstream values.
No RFC9106 full secret/associated-data vector claim. No test password is a real PIN.

Benchmarks are TEST-ONLY: m=1024/8192/65536 KiB, t=2, p=1, five measured calls
per profile after warm-up. elapsedNs is measured. PSS/native/Java memory are
before/after snapshots, NOT peak per-call allocation. A bounded 16MiB Java pressure
probe is not exhausted-memory/OOM proof; exhausted-memory remains NOT-VERIFIED.
No production KDF parameters or performance acceptance threshold are selected.

R8 provider execution: NOT-VERIFIED. This debug instrumented APK is not minified.
ARM/x86 ABI runtime: NOT-VERIFIED unless actually run. AAR includes four ABIs;
packaging and ELF alignment do not prove native load on an unexecuted ABI or a
16KiB-page device. Record actual getconf PAGE_SIZE separately. API37 is optional
and not scheduled here. Missing image/runtime must be ENV-BLOCKED, never PASS.

Upstream licenses/provenance and resolved checksums will be recorded alongside
actual CI evidence. No CVE-free claim is made before scan and native-source triage.
Do not merge this evidence carrier as a production dependency. QA independently
verifies scope and reproduction; Leader decides ADR, PO retains merge authority.
