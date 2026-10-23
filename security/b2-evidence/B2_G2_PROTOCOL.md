# B2-G2 — isolated x86 R8 experiment

Authority: Issue16 Leader6354170980 / PO6354549594, based on preflight6345775478.
Base main690a74af29897d43fcb9f4c58808ae6ea2e3365f. PR17 remains Draft and unchanged.
Only the twelve paths approved through PO G2-P04 are used; the inspector enforces exact additions.

This separate Gradle application root is not included in MoneyMate settings/graph.
Argon2Kt1.6.0 is implementation only in this disposable test target. The production
MoneyMate app/security remain unchanged. No PIN/key lifecycle is implemented.
Catalog preserves every baseline byte from accepted B2 HEAD
be26d275d621c4a0c64ed9dd5fb89cad42bf91b2 plus the one exact P05 test-only alias below. Verification metadata preserves all784
baseline artifact records/configuration and inserts only ten G2-P01 records and one
G2-P03 record below, for795 total. Prior ten approved records remain unchanged.
The guard reconstructs baseline bytes plus precisely those insertions and rejects any
other delta, including a changed hash/configuration, deletion or unapproved addition.
The existing build-logic dependency policy is applied without modification.
No checksums beyond G2-P01/P03, lenient mode, trust wildcard or task workaround.
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

Capture source/head/tree, twelve-path SHA manifest, commands/exit codes, SDK catalogue,
actual API/ABI/kernel/page-size/memory, JUnit5/0/0/0, metrics20, target/test APK hashes,
signatures, mapping/DEX/ELF/ZIP evidence, inventory/security reports and failure logs.
Actual results are submitted in Vietnamese on Issue16; no fabricated or pending PASS.
Independent QA reviews the evidence before Leader decision; keep the new PR Draft.

## G2-P02 option B — baseline compiler parity

Authority: PO approval recorded by Leader in Issue16 comment6356080091 (23/10/2026),
following assessment6355802110 and Leader6355871029. This supersedes the earlier
read-only pause only within the approved eleven paths. Option A's sixteen compiler2.2.10
checksums are not approved and must not be added. G2-P03 below authorizes precisely
one later metadata insertion; all784+10 previous records/configuration stay byte-exact.

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

## G2-P03 exact checksum delta

Authority: official PO authorization Issue16 comment6356299057 (23/10/2026), accepting
Leader6356290692 and the blocker evidenced in Developer6356251256. Only standalone
metadata, this protocol and the inspector checksum guard change; no twelfth path.

Coordinate `org.jetbrains.kotlin:kotlin-stdlib-common:2.4.21`, artifact
`kotlin-stdlib-common-2.4.21.module`, SHA256
`aeae4f24688e1dd7ebee648ab2b12be685cbe33e9c72bc1439730a794d6e2d5b`.
Upstream bytes: https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-stdlib-common/2.4.21/kotlin-stdlib-common-2.4.21.module
Read626 bytes independently over HTTPS and verify SHA256 against the exact PO value;
also compare SHA1 with the upstream `.sha1` response:
`e874d771dc445b01a30fb832f22f4f6666aa5dfa`. Matching hashes do not replace security/license review.

The guard reconstructs accepted baseline bytes plus precisely ten unchanged P01 insertions
and this one P03 insertion. Negative controls must reject changed baseline/P01/P03 hashes,
deleted records, unapproved additions and changed verification configuration. Metadata
contains795 artifact records; strict verification, catalog and2.4.21 parity gate are unchanged.
Reproduce the four workflow cells using the existing preflight/build/instrument/inspect
modes above, retaining graph, manifest, source, exit codes and all runtime/security evidence.
Any other missing artifact or blocker is STOP/report, not authority for another insertion.

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

## G2-P04 Android Lint remediation and twelfth path

Authority: PO Issue16 comment6356956055 (23/10/2026), accepting Leader6356470178
and QA6356875416. KGP is requested through the existing pinned kotlin-jvm alias with
apply false; the JVM plugin is not applied. AGP9.4.1/compiler/KGP/BTA2.4.21 parity
must still be observed, not inferred. Release resource shrinking is enabled alongside
R8. No keep rule, KAT, task, catalog, checksum, production or original CI change.

The manifest references framework drawable ic_menu_info_details and the only new path:
security/b2-g2/src/main/res/xml/data_extraction_rules.xml. Cloud backup and device
transfer exclude root/file/database/sharedpref/external and all four device-protected
domains at path dot. allowBackup=false is preserved, with no permission added.
Android Lint and actual merged/packaged resources must validate this test-only config.
The source guard accepts exactly twelve added paths and rejects missing/modified or
thirteenth paths. The existing upload globs already capture generated evidence, so
no workflow edit is needed. Metadata stays byte-exact795=784+10+1.

License evidence is collected for every component of both resolved inventories from
cached or upstream Maven/Google POM declarations, including bounded parent traversal.
Each read records coordinate/source/SHA256. These are read-only license declarations,
not new Gradle dependency admissions or verification checksum additions. An enriched
SBOM copy preserves every component, marks unresolved declarations UNKNOWN, and is
scanned with the already pinned Trivy license scanner. The original inventory and
HIGH/CRITICAL vulnerability gates are unchanged. License provenance/classification
is evidence for independent QA, not a legal PASS; missing declarations remain explicitly
NOT-VERIFIED, never silently omitted. Scanner execution errors still fail the command.
No ignored-license list or policy exemption is introduced.

## G2-P05 test-only Error Prone annotation dependency

Authority: official PO approval Issue16 comment6357366408 (23/10/2026), following
Leader6357294759, QA6357275532 and Developer6357124891. Only standalone catalog,
build.gradle.kts, inspector and this protocol change; twelve paths total, no thirteenth.

Exact insertion immediately after [libraries]:
`b2-errorprone-annotations = { module = "com.google.errorprone:error_prone_annotations", version = "2.36.0" }`
Only androidTestImplementation(libs.b2.errorprone.annotations) is added. It is not a
target implementation/production dependency. AGP9.4.1/KGP-compiler-BTA2.4.21,
R8 tasks/keep rules/KAT and all other dependencies/versions remain unchanged.

Upstream Maven Central coordinate com.google.errorprone:error_prone_annotations:2.36.0:
https://repo.maven.apache.org/maven2/com/google/errorprone/error_prone_annotations/2.36.0/
JAR SHA256 77440e270b0bc9a249903c5a076c36a722c4886ca4f42675f2903a1c53ed61a5
POM SHA256 d79cfd37c85f76d6b754c7501ee1dc8447b7b2642c2382d778252166bd331e9c
Both were independently fetched and matched existing baseline metadata. The JAR
contains CanIgnoreReturnValue and MustBeClosed; no checksum is added to the795 records.
The catalog guard reconstructs accepted B2 bytes plus exactly the approved insertion,
rejecting omissions/version changes/renames/extra aliases or other baseline edits.
Catalog policy and five negative controls are uploaded per cell, with existing P04 controls.

After strict build, actual test compile dependencyInsight and target/test runtime
resolution reports must show2.36.0 in test and its absence from target runtime. The
cached resolved JAR must match its existing pin and contain both annotation class files.
The APK inspector checks target mapping/DEX for absence of this test-only dependency,
records actual annotation definitions/removal in test DEX/mapping/usage, and requires
the test APK R8 task to have executed. Optimizer retention/removal is reported separately;
classpath evidence is not used to invent post-R8 class presence or runtime JNI PASS.
Existing provider-in-target/provider-absent-from-test, matching signatures, KAT/JUnit,
page-size/memory, strict lint/security/license gates remain mandatory. No dontwarn,
blanket keep, task bypass, new checksum or production dependency is authorized.
