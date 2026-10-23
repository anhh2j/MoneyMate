# B2-G2 — isolated x86 R8 experiment

Authority: Issue16 Leader6354170980 / PO6354549594, based on preflight6345775478.
Base main690a74af29897d43fcb9f4c58808ae6ea2e3365f. PR17 remains Draft and unchanged.
Only the eleven new paths approved by PO are used; the inspector enforces exact additions.

This separate Gradle application root is not included in MoneyMate settings/graph.
Argon2Kt1.6.0 is implementation only in this disposable test target. The production
MoneyMate app/security remain unchanged. No PIN/key lifecycle is implemented.
Catalog is an exact copy from accepted B2 HEAD
be26d275d621c4a0c64ed9dd5fb89cad42bf91b2. Verification metadata preserves all784
baseline artifact records/configuration and inserts only the ten G2-P01 records below.
The guard reconstructs baseline bytes plus precisely those insertions and rejects any
other delta, including a changed hash/configuration, deletion or unapproved addition.
The existing build-logic dependency policy is applied without modification.
No checksums beyond G2-P01, lenient mode, trust wildcard or task workaround.
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
Leader6354820006 clarified that test APK minification must be inspected independently;
in either case, target provider execution and provider absence from test APK are required.
No AGP/task/keep-rule change is authorized to force a PASS.

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

## G2-P02 option B — baseline compiler parity

Authority: PO approval recorded by Leader in Issue16 comment6356080091 (23/10/2026),
following assessment6355802110 and Leader6355871029. This supersedes the earlier
read-only pause only within the approved eleven paths. Option A's sixteen compiler2.2.10
checksums are not approved and must not be added. Metadata stays784+10, byte-exact.

Standalone buildscript explicitly requests KGP2.4.21, matching baseline main690a74af's
resolved buildscript and app/security compiler/BTA configurations. AGP stays9.4.1;
there is no Compose UI or legacy kotlin-android plugin, root inclusion or production edit.
The three256KiB literals in the target facade use one named constant with unchanged value.

Before compilation/R8, exportB2G2Toolchain records toolchain-graph.json for buildscript
classpath, kotlinCompilerClasspath and kotlinBuildToolsApiClasspath, with components,
requested/selected edges and selection reasons. toolchain-artifacts.json records each
resolved artifact's scope, component, filename and SHA256. The inspector requires KGP,
compiler/build-tools impl/API selected2.4.21, AGP9.4.1, and all artifact hashes admitted by
the unchanged strict metadata. It records toolchain-parity.json only after every check
passes; a catalog declaration alone cannot satisfy this gate. Graph evidence is saved
before artifact enumeration so a strict-verification failure can still be investigated.

Any differing selected toolchain version, new checksum or need for a path outside the
authorized scope is STOP/report. Subsequent build/security/license/runtime gates must
be reported separately; compiler parity is not G2 runtime or production acceptance.
The four-cell workflow,30-minute limits,three-day retention and all prior gates remain.

## G2-P01 exact checksum delta

Leader proposal: Issue16 comment6354820006, referring to Developer6354786767.
Official PO authorization: Issue16 comment6355498984 on23/10/2026.
Approval covers only this exact delta, corresponding guard/protocol and the canary fix.
This is not blanket authority for additional artifacts.
Independent read-only validation fetches upstream HTTPS bytes, checks SHA256 below
and published SHA1. Neither a hash match nor admission to metadata certifies CVE/license
status; strict inventories and security scans must run. A newly missing artifact is STOP.
The canary constant-returning function is changed to an immutable property under the
existing allowlist; the unreachable class must still disappear in target R8 output.

| Coordinate | Artifact / upstream bytes | Approved SHA256 |
|---|---|---|
| `androidx.annotation:annotation:1.3.0` | [annotation-1.3.0.module](https://dl.google.com/dl/android/maven2/androidx/annotation/annotation/1.3.0/annotation-1.3.0.module) | `9516c2ae44284ea0bd3d0eade0ee638879b708cbe31e3af92ba96c300604ebc3` |
| `androidx.annotation:annotation:1.6.0` | [annotation-1.6.0.module](https://dl.google.com/dl/android/maven2/androidx/annotation/annotation/1.6.0/annotation-1.6.0.module) | `6146b6138643b2ac0590df509dd51abaea769c79fd7602eb217168fe5af78cd2` |
| `androidx.annotation:annotation-jvm:1.6.0` | [annotation-jvm-1.6.0.jar](https://dl.google.com/dl/android/maven2/androidx/annotation/annotation-jvm/1.6.0/annotation-jvm-1.6.0.jar) | `60b10b5ef5769b79570172e015b8159405c92f034ba88b9391a977589c9deb4e` |
| `androidx.annotation:annotation-jvm:1.6.0` | [annotation-jvm-1.6.0.module](https://dl.google.com/dl/android/maven2/androidx/annotation/annotation-jvm/1.6.0/annotation-jvm-1.6.0.module) | `3f5a8faa19de667e63dca9730ff8ef0e478e4bafb5feeb8258e5c086246dc90c` |
| `org.jetbrains.kotlin:kotlin-stdlib-common:2.2.10` | [kotlin-stdlib-common-2.2.10.module](https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-stdlib-common/2.2.10/kotlin-stdlib-common-2.2.10.module) | `336afb512852028b1da5d5d07a6fb833cf9a797ee4b33519694d312f683227c9` |
| `org.jetbrains.kotlinx:kotlinx-coroutines-android:1.6.4` | [kotlinx-coroutines-android-1.6.4.jar](https://repo.maven.apache.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-android/1.6.4/kotlinx-coroutines-android-1.6.4.jar) | `3fdc0eed5bc4b83ee9622774520a2db25470370eacd1581cac1e37704f095b00` |
| `org.jetbrains.kotlinx:kotlinx-coroutines-core:1.6.4` | [kotlinx-coroutines-core-1.6.4.module](https://repo.maven.apache.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-core/1.6.4/kotlinx-coroutines-core-1.6.4.module) | `a6eed4a1835588e7c84fcd7b0475fce9a7b3444c870ebc797b88ba64ccf4576b` |
| `org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.6.4` | [kotlinx-coroutines-core-jvm-1.6.4.jar](https://repo.maven.apache.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-core-jvm/1.6.4/kotlinx-coroutines-core-jvm-1.6.4.jar) | `c24c8bb27bb320c4a93871501a7e5e0c61607638907b197aef675513d4c820be` |
| `org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.6.4` | [kotlinx-coroutines-core-jvm-1.6.4.module](https://repo.maven.apache.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-core-jvm/1.6.4/kotlinx-coroutines-core-jvm-1.6.4.module) | `0d94c8a41483e7c2707ebd693e1b1357a84152998ce85550ebbc54ca4321a3a7` |
| `androidx.tracing:tracing:1.0.0` | [tracing-1.0.0.aar](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing/1.0.0/tracing-1.0.0.aar) | `07b8b6139665b884a162eccf97891ca50f7f56831233bf25168ae04f7b568612` |
