# B2-G2 — isolated x86 R8 experiment

Authority: Issue16 Leader6354170980 / PO6354549594, based on preflight6345775478.
Base main690a74af29897d43fcb9f4c58808ae6ea2e3365f. PR17 remains Draft and unchanged.
Only the eleven new paths approved by PO are used; the inspector enforces exact additions.

This separate Gradle application root is not included in MoneyMate settings/graph.
Argon2Kt1.6.0 is implementation only in this disposable test target. The production
MoneyMate app/security remain unchanged. No PIN/key lifecycle is implemented.
Catalog and verification metadata are exact copies from accepted B2 HEAD
be26d275d621c4a0c64ed9dd5fb89cad42bf91b2. This provenance is checked before build.
The existing build-logic dependency policy is applied without modification.
No new checksums, lenient mode, trust wildcard, plugin upgrade or task workaround.
Stop and report a blocker if the proposed tasks/checksum policy do not work.

Reproduction uses the repository wrapper with `-p security/b2-g2`, strict verification,
`-Pandroid.useAndroidX=true` and Java17/SDK37/build-tools37. Run inspector modes:
`preflight`, `build`, then `instrument` on the requested emulator, then `inspect`.
The workflow supplies G2_CELL/API/TARGET/RAM/HEAP/TOOLS. Build mode records tasks,
minifyReleaseWithR8, assembleRelease/AndroidTest, lintRelease, dependency inventories,
the unchanged pinned scanner installer and HIGH/CRITICAL scans. Missing tasks or
unverified artifacts are blockers. CI original runs separately with its gates unchanged.

Four jobs only: API26 R8 / API35 R8 / API35 google_apis_ps16k / API35 bounded memory.
All x86_64; each max30 minutes, artifacts retained3 days, public standard runners.
Emulator37.2.12 build16428233 is pinned. Requested RAM2048MiB/heap256MiB controls;
memory cell RAM1536MiB/heap128MiB. Record effective total RAM/Java heap; the memory
inspector fails if the requested envelope is not effective. lowRamDevice is measured,
not assumed true. PAGE_SIZE is measured in-process with Os.sysconf (also getconf;
the latter may be unavailable on API26). ps16k requires both report16384.
x86 16KiB userspace is simulated; real ARM64 kernel16KiB remains ENV-BLOCKED.

Release target uses only the generated disposable Android debug signing material
to install matching target/test APKs, as PO allowed. No signing secret or keystore
is committed/uploaded; no release publication, tag, merge or version modification.

R8 proof: mapping/configuration/usage, mapped provider definitions in target DEX,
provider absent from test DEX and test native payload, unreachable canary removed,
non-debuggable target manifest, matching signer and executed native/KAT/negative calls.
Only the public target facade is kept; no provider blanket keep or global R8 disable.
All API calls use Argon2id V13. Two public upstream KATs from Argon2Kt commit
226d943ad1c6344a049c08a437e09688ceb07929, officialTestSuite_v13_argon2id_case3/case1,
m256/65536KiB t2/p1/output32. The test source labels its public input explicitly;
no credential, real PIN, bank notification or production data is used.
Any QA scanner finding must remain recorded for independent classification.

Five instrumented tests produce20 numeric/status metrics: two KAT, verifier/salt/m/t
sensitivity, exact malformed exception checks inside target, 15 benchmark rows,
bounded16MiB Java pressure. KDF profiles1/8/64MiB t2/p1 are TEST-ONLY: warm-up1,
measured5/profile, concurrency1. No production threshold/parameters selected.
PSS/native/Java readings are before/after snapshots, not per-call peak allocation.
Bounded memory success does not prove native allocation failure or exhausted-memory
behavior. ARM64 runtime, real ARM64 16KiB and native OOM remain OPEN/ENV-BLOCKED.

Capture source/head/tree, eleven-path SHA manifest, commands/exit codes, SDK catalogue,
actual API/ABI/kernel/page-size/memory, JUnit5/0/0/0, metrics20, target/test APK hashes,
signatures, mapping/DEX/ELF/ZIP evidence, inventory/security reports and failure logs.
Actual results are submitted in Vietnamese on Issue16; no fabricated or pending PASS.
Independent QA reviews the evidence before Leader decision; keep the new PR Draft.
