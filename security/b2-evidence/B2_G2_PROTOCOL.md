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

## G2-P06 compile-only/reference input experiment and legacy backup

Authority: PO Issue16 comment6358851194 (23/10/2026), accepting Leader6358829389
and QA6358792966. Only build.gradle.kts, harness manifest, inspector and this protocol
change. Replace the P05 Error Prone declaration with androidTestCompileOnly for the
same alias2.36.0. Add fullBackupContent=false for API26-30; allowBackup=false,
dataExtractionRules exclusions/icon/permissions remain unchanged. Catalog P05 exact
insertion,795 checksum records,12-path allowlist/KAT/keep rules/workflow stay unchanged.

This section explicitly supersedes P05's test-runtime-presence oracle. Error Prone must
be selected2.36.0 in test compile classpath, absent from test/target runtime and both
program DEX, and present as an actual referenced/library input of test R8. The same
pinned JAR must provide the two annotation class files; no JDK enum/stub is packaged.
No classpath declaration or aggregate SBOM alone proves this role.

The inspector generates p06-observe-inputs.init.gradle inside build/reports/b2-g2 as
reproducible evidence, not a tracked source path. A beforeTask observer reads the actual
minifyReleaseAndroidTestWithR8 referencedClasses/programClasses/bootClasspath and
resolved compile/runtime graph, without changing inputs, R8 options, rules or task wiring.
It writes p06-classpaths.json and p06-r8-inputs.json BEFORE test R8 runs, retaining
requested/selected edges, selection reasons, file paths/SHA256 and annotation entries.
If no library input is observed, or the JAR leaks into program classes, it records failure
and stops. The Python validator checks exact scopes/versions, pinned library hash/classes
and program absence; p06-test-resolution.json PASS means input wiring only, not R8 success.
A build failure still leaves observer evidence; if the task was never reached the input
role stays NOT-VERIFIED, never guessed. The generated observer performs no file admission.

On completed runtime inspection, p06-apk-isolation.json additionally requires annotation
absence from both target/test DEX and mappings, test R8 execution, and unchanged provider
isolation/signature/KAT/JUnit/environment gates. No annotation runtime-presence expectation
from P05 is retained. Missing classes, missing library input, parity drift/new artifact or
out-of-scope need means STOP/report; no dontwarn, task disable or fallback is authorized.
All four cells must provide actual lint XML and runtime/security/license evidence, with
CI at the new HEAD. Infrastructure retry may be recorded by run/attempt; old CI PASS is
not substituted. PR17/18 remain Draft; ARM64/kernel16KiB/native OOM remain OPEN.

## G2-P07 — chỉ chẩn đoán zero-test / API26 logcat

Thẩm quyền: PO Issue16 comment6359471264, Leader6359453277, QA6359405275.
Delta chỉ trong inspector và protocol này. P06 được Leader ghi nhận QA-PASS;
G2 runtime vẫn BLOCKED. Không đổi source/test, build/manifest, workflow, keep rule,
task wiring, runner argument/filter/variant, dependency/catalog/795 checksum hay gate.

Tái lập: workflow G2 hiện có chạy `preflight`, `build`, `instrument`, `inspect` trên
cùng HEAD. Lệnh acceptance vẫn nguyên `:connectedReleaseAndroidTest` với strict
verification; clear-logcat vẫn bắt buộc và lỗi phải được raise. Chỉ tách stdout/stderr
ra file cho hai lệnh đó, đồng thời giữ combined log cũ. Chưa cấp phép sửa runtime.

Trong build, `p07-license-review.json` đối chiếu inventory/provenance gốc với graph
target/test compile/runtime và toolchain. Sao chép raw POM từ cache vào build reports,
ghi SHA256, root namespace và mọi khai báo license (cả POM không namespace). Không sửa
inventory/scanner, không admission/checksum mới. Khai báo nhiều license không tự chứng
minh điều kiện lựa chọn/distribution; UNKNOWN cũ và findings vẫn giữ để QA/PO đánh giá.

Trước instrumentation: đọc badging/manifest/chữ ký APK build, DEX class/method/annotation
metadata bằng dexdump; đọc pm list instrumentation, pm path/dumpsys package đúng hai
package harness, dumpsys activity instrumentation, getprop/process/log-buffer status,
logcat runner/classloader và crash buffer. Nếu pm path có bản cài trong /data/app,
chỉ adb pull APK đó về reports để ghi hash/chữ ký; không install/reinstall/uninstall.
Sau instrumentation: thu metrics/memory theo thứ tự acceptance cũ rồi lặp snapshot
chỉ đọc và index/hash XML/PROTO/Gradle output. Artifact workflow giữ XML/PROTO gốc.
Nếu clear-logcat fail: chụp snapshot lỗi rồi raise lỗi cũ, không chạy instrumentation.

Mỗi lệnh P07 được đánh dấu READ_ONLY_DIAGNOSTIC trong `p07/commands.json`, ghi argv,
timestamp, stdout/stderr file riêng + SHA256, exit/timeout/error. Timeout 12 giây/lệnh
(DEX metadata 30 giây). Lỗi diagnostic là NOT-VERIFIED và không thay kết quả acceptance.
Không gọi thêm `am instrument -w -r`, vì một lần chạy độc lập có thể thực thi test và
thay state; chỉ quan sát invocation/discovery/runner qua log acceptance, DEX và kết quả
UTP hiện có. Nếu invocation hay discovery list không xuất hiện trong bằng chứng,
ghi NOT-VERIFIED, không tạo danh sách test giả hoặc thêm `-e log`/class filter.

Snapshot trước/sau có thể không bắt được khoảng UTP install/uninstall ở giữa; thiếu
package tại snapshot không chứng minh APK chưa từng cài. Diagnostic có chi phí thời gian
trước clear-logcat; nếu lỗi API26 không tái hiện, không coi đó là root cause/fix hay dùng
lần trước làm PASS. Mọi dữ liệu chỉ từ emulator harness dùng synthetic test input.

Acceptance vẫn đòi JUnit5/0/0/0,20 metrics, JNI/KAT thật, R8/DEX isolation/signature/
page/ABI/bounded memory/lint/security gates. `OBSERVED` chỉ nghĩa thu được lệnh exit0,
không phải runtime/QA PASS. Zero tests là FAIL; gate chưa tới là NOT-VERIFIED.
Chẩn đoán/đối chiếu license không phải quyền sửa lỗi hay phê duyệt pháp lý.

Nếu nguyên nhân cần đổi source/test/wiring/keep/workflow/allowlist: DỪNG, giữ raw lỗi,
nộp phương án riêng cho PO. Chạy đủ4 cell, tối đa30 phút/cell, artifact3 ngày, CI nền
cùng HEAD nếu có commit. QA kiểm toán độc lập. PR17/18 giữ Draft; không merge/tag/release,
không T20 production; ARM64 thực/ARM64-16KiB thực/native OOM vẫn OPEN.

## G2-P08 — shared tracing runtime sau target R8

Thẩm quyền PO6359936855, Leader6359917934, QA6359881006 (23/10/2026).
P08 thay phạm vi diagnostic-only của P07 đúng cho tracing: chỉ catalog, build của
standalone harness, proguard-rules, inspector và protocol. Không đổi file khác trong
12-path allowlist; giữ metadata795 byte-exact, AGP9.4.1/KGP-compiler-BTA2.4.21,
Argon2Kt/KAT/test source, workflow, manifest/permission, production/root/QA/version.

P07 raw crash logs chứng minh AndroidJUnitRunner.onCreate thiếu androidx.tracing.Trace,
trước discovery. Test DEX còn đủ5 runtime Test annotations nhưng Trace definition vắng
cả2 DEX. Graph compile1.1.0/runtime1.0.0 là hazard riêng. DEX method_ids thực tế của
test APK P07 chỉ tham chiếu ba API Trace: beginSection(String), endSection(),
forceEnableAppTracing(). Đây là cơ sở keep chính xác ba public static void member đó
và class identity androidx.tracing.Trace, không keep cả package hay androidx.**.
Không allowshrinking/allowobfuscation cho entry points này; helper reachability do R8
xử lý, không blanket keep, dontwarn, tắt minify/resource shrinking hay đổi task wiring.

Catalog thêm đúng một dòng sau alias P05:
`b2-tracing = { module = "androidx.tracing:tracing", version = "1.1.0" }`.
Build chỉ thêm implementation(libs.b2.tracing) vào target harness. Catalog guard P08
thay exact-P05-only bằng baseline be26d275 + exact P05 + exact P08, không đổi baseline
alias/version. Giữ5 catalog controls cũ, thêm4 tracing controls; checksum/scope8 controls
vẫn giữ. Không thêm dependency tracing vào production hay ép constraint khác.

Observer chỉ đọc trước test R8 như P06, bổ sung releaseCompileClasspath và ghi
p08-classpaths.json đủ4 target/test compile/runtime graph; p06-classpaths.json vẫn đúng
3 scope cũ, oracle Error Prone không thay. p08-resolution.json đòi tracing1.1.0 ở đủ4
scope. Ba scope có baseline P07 được so hash canonical component set sau loại duy nhất
androidx.tracing:tracing, để chặn non-tracing version/component drift. Hash gốc lấy từ
P07 p06-classpaths.json (SHA256 4aae5c6f1d0d21deb956a2bd346b161af574fb7fbdf20e97f72881305b5983e5).
Target compile được quan sát mới; không bịa baseline hash, chỉ chấp nhận non-tracing
components thuộc union đã quan sát ở3 scope P07. Toolchain parity vẫn kiểm độc lập.
4 negative controls chặn downgrade runtime, mất tracing compile, thiếu target compile
graph và non-tracing drift. Tất cả graph evidence được ghi trước R8; validate trong
finally kể cả build fail nếu report có tồn tại. Chưa tới observer là NOT-VERIFIED.

Ngay sau build, p08-trace-apks.json ghi SHA APK, class definitions, public-static method
definitions và R8 task/canary facts trước assertion. DEX decoder đọc encoded class_data
để chứng minh member thật, không dùng method_ids reference làm definition. Bắt buộc
Trace identity ở target DEX, không duplicate ở test DEX, đủ ba API nói trên, cả2 R8
task thực thi và canary bị loại. 5 negative controls: thiếu target Trace, duplicate test,
thiếu force-enable API, canary còn và R8 không thực thi. Build proof không phải JNI PASS.

Lệnh acceptance không đổi; P07 snapshots/raw logs tiếp tục thu. Sau instrumentation,
p08-runtime-observation.json ghi JUnit/metrics và crash-log hash: chỉ PASS khi5/0/0/0,
20 metrics và có crash evidence không thấy lỗi Trace. Thiếu file/evidence không được
PASS. Inspector kiểm lại graph/DEX/P08 runtime rồi vẫn chạy nguyên các gate JNI/KAT,
metric content, page/ABI/heap/bounded-memory, R8/provider/test isolation, signature,
zipalign/ELF/lint/security cuối. Không thay bằng Gradle exit0, build report hay mock.

Tái lập dùng workflow G2 cũ với preflight/build/instrument/inspect, đủ4 cell,30 phút/cell,
retention3 ngày, CI nền cùng HEAD. Tracing1.1.0 AAR/module đã có pin trong metadata795
(AAR5b78e2c618fc10b3d14decc01df76158f15954ad746aacf0607766721da081f6;
module b1fed4309623b6f20bc817d8fbd70e4ea7085e40647694cd399ae58d2f0049e3).
Nếu artifact/checksum mới, non-tracing/toolchain drift hoặc cần sửa ngoài5 file: DỪNG,
giữ lỗi và xin quyết định riêng, không tự thêm pin/force/keep rộng hay fallback.

API26 clear-logcat vẫn required, lỗi thì dừng cell. Permission nội bộ, apksigner SDK37,
aapt badging và license collector vẫn ngoài P08, không sửa/nới gate, không tự đánh PASS.
License UNKNOWN/HIGH giữ nguyên. Nếu tracing qua nhưng gặp lỗi khác, ghi riêng phần
đã chứng minh và blocker còn lại; không nghiệm thu G2 khi chưa đủ gates. QA độc lập,
PR17/18 Draft, không Ready/merge/tag/release/T20 production; ARM64 thực/ARM64-16KiB thực/
native OOM vẫn OPEN.

## G2-P09 — ngoại lệ duy nhất annotation1.2.0 metadata

Thẩm quyền: PO6360301889, Leader6360285956, QA6360259200 (23/10/2026).
Chỉ verification-metadata.xml, inspector và protocol được sửa. P09 thay giới hạn795
trước đó bằng **796 =784 baseline +10 P01 +1 P03 +1 P09**; không mở ngoại lệ khác.
Mọi record/cấu hình strict trước đó giữ nguyên từng byte. Catalog P05/P08, dependency/
version/constraint, P08 keep rule/runner/task wiring, KAT/test, AGP9.4.1/Kotlin2.4.21,
manifest/permission/workflow/root/production/QA/release/version không đổi; vẫn12 path.

Record duy nhất được thêm: androidx.annotation:annotation:1.2.0 /
annotation-1.2.0.module, SHA256
2efcab81ef91b211bacd206eaacd995a51f633a2e96b57a8fc00144c5f9c56b3.
Nguồn Google Maven:
https://dl.google.com/dl/android/maven2/androidx/annotation/annotation/1.2.0/annotation-1.2.0.module
2709 byte; SHA1 26f06565ebe0e525e1a183b59a9ad2e2eb799b2a khớp cache path
trong P08 strict verification HTML. QA đã đối chiếu độc lập upstream. Tracing1.1.0.module
runtime variant yêu cầu annotation1.2.0; việc cần đọc metadata không tự chứng minh final
selected annotation version. Không thêm pin JAR/POM/variant hay chạy write-verification-metadata.

Guard dựng baseline và11 additions P01/P03 như cũ thành795 bytes, rồi chèn exact một
P09 block. Bỏ block mới phải phục hồi toàn bộ795 bytes trước, không reformat XML.
Positive control chấp nhận đúng796; giữ8 controls cũ và thêm6 controls chặn mất P09,
đổi hash/artifact/coordinate, duplicate block hoặc thêm hash. Báo cáo legacy
p04-negative-controls.json chứa14 controls và authority/positiveMetadata P09;
checksum-policy.json ghi796, p09Additions=1 và đủ12 additions. Catalog/R8/graph/JUnit/
metrics/security/license guard giữ nguyên; các negative controls khác không đổi.

Tái lập workflow G2 cũ: preflight/build/instrument/inspect trên đủ4 cell,30 phút/cell,
artifact3 ngày, CI nền cùng HEAD. Phải đọc actual final tracing/annotation graph, Trace
class và3 member trong target DEX, canary/R8,5 tests/20 metrics/JNI/KAT thật, lint XML,
page/ABI/heap/memory, APK isolation/signing và SBOM/vulnerability/license. Metadata
positive/negative PASS chỉ chứng minh admission scope; không thay bằng chứng build/runtime.

Nếu checksum mới, non-tracing graph/toolchain drift, blocker khác hay cần file ngoài3
path: DỪNG, giữ raw report và xin quyết định riêng. Không force/exclude/đổi dependency,
keep/runner/wiring hay hạ security/test gate để đi tiếp. API26 clear-logcat, permission
nội bộ, apksigner/aapt và license collector vẫn ngoài P09. Chưa tới gate là NOT-VERIFIED;
failure phải giữ FAIL, không suy từ P07/P08 hay CI nền. QA kiểm toán độc lập trước Leader
nghiệm thu. PR17/18 Draft, không Ready/merge/tag/release/T20 production; ARM64 thực,
ARM64-16KiB thực và native OOM OPEN.

## G2-P10 — diagnostic shared-runtime closure, không sửa runtime

Thẩm quyền PO6360661190, Leader6360644936, QA6360610821 (23/10/2026).
Delta chỉ inspector và protocol. Giữ đúng12 path, metadata796/cấu hình strict, catalog,
build/dependencies/constraints, P08 keep rules, AGP9.4.1/Kotlin2.4.21, source/test/KAT,
runner args/task wiring/workflow/manifest/permissions/root/production/QA/version.
Không tạo APK mới ngoài build acceptance cũ, không rewrite/sign/install thêm, không sửa
R8 input hay gọi instrumentation khác. Hai hook p07_safe chỉ thu diagnostic sau build/
scans và sau snapshot/runtime observation cũ; lỗi collector ghi NOT-VERIFIED, không
thay kết quả acceptance, không waive5 tests/20 metrics hoặc clear-logcat.

Collector tạo `build/reports/b2-g2/p10-build/` và `p10-runtime/` bằng dữ liệu thực tại
cùng HEAD. `closure.json` + `closure.md` có per-class/per-member sites, PC/dòng debug,
source APK/DEX/JAR hashes, graph/input manifest hashes, mapping/usage và taxonomy.
Các `target-classes*.dex.json`/`test-classes*.dex.json` ghi toàn bộ class definitions,
superclass/interfaces, declared field/method signatures/flags và references được giải
mã từ invoke, field access, new-instance/type instructions, catch types, annotation,
debug metadata/static encoded values. Không coi method_ids/type_ids là definitions.

DEX parser độc lập theo format AOSP, hỗ trợ header112/little-endian; instruction width
table đối chiếu dex_instruction_list.h của AOSP (decoded source SHA256
6dec605fb0d44317eb8534fe7c186d6d0fdeb651375f618de5a929f76d60ef45):
https://android.googlesource.com/platform/art/+/refs/heads/main/libdexfile/dex/dex_instruction_list.h
https://source.android.com/docs/core/runtime/dalvik-bytecode
https://source.android.com/docs/core/runtime/dex-format
Không fetch spec/table trong CI. Payloads, invoke-polymorphic/custom, method handles và
annotation encoded values được xử lý riêng. Opcode/container không hỗ trợ hoặc decode
lỗi ghi coverage PARTIAL/NOT-VERIFIED, không đoán reference. Descriptor strings trong
Kotlin Metadata không tự biến thành runtime type use. 9 classification controls chặn
nhầm static invoke/signature/annotation/type-pool/provider-unknown thành observed need;
thêm2 format controls từ chối non-DEX/non-classfile và4 descriptor controls, tổng15.
Parser tách tên member trước khi đọc descriptor; ký tự L trong getClassLoader/LEVEL/
nativeLoad không tạo type. Mọi reference phải nằm trong actual DEX type_ids (chuẩn hóa
array component), nếu không phải báo decode error, không đưa type giả vào closure.

Định nghĩa classification:
- REQUIRED: missing class trong crash của đúng PID harness, hoặc superclass/interface
  closure của class đó từ selected JAR có hierarchy không mâu thuẫn. Đây là class linkage
  requirement; member reference vẫn phải có site/declared ABI, không bịa đã được gọi.
- CONDITIONAL: có decoded runtime-capable site/signature và provider xác định, nhưng
  chưa có proof nhánh đó thực thi. Potential direct-invoke path không nâng thành REQUIRED.
- ANNOTATION-METADATA: chỉ typed annotation/debug sites; không đồng nghĩa tùy ý xóa mọi
  annotation hay khẳng định reflection không cần. VM annotation có semantics riêng.
- UNKNOWN: chỉ type pool, không provider/use-site xác định hoặc suy luận còn thiếu.

Chỉ raw harness PID exception làm seed; lỗi system process không được seed REQUIRED.
`build` chưa có runtime crash của run này nên không mượn seed từ P09. Sau runtime, giữ
raw log hash và stack frames. Chỉ khi dòng crash ánh xạ duy nhất tới allocation có failed
superclass mới dùng interface linkage bổ sung; không suy mọi new-instance trong stack
frame đã chạy. Supertype closure qua classfile CP/hierarchy khác CP member symbols:
CP symbols không phải per-method execution. Những thứ không xác định phải ghi rõ.

Program definitions lấy từ cả2 actual APK DEX. So actual R8 library/program/boot inputs
bằng SHA256 trước khi index selected JAR entries; classfile ABI lưu hash/fields/methods/
superclass/interfaces/CP symbols, per-member lookup có inherited declarations. Maven
cache path cho coordinate và graph membership; transformed JAR coordinate chưa xác định
thì ghi NOT-VERIFIED, không đoán group từ filename. Non-JAR input ghi unindexed; actual
program DEX vẫn được giải mã. Compile SDK boot JAR chỉ là static baseline, không chứng
minh class khả dụng trên thiết bị API26/35. Class definition/mapping presence không tự
chứng minh classloader visibility; collision giữa target/test được liệt kê riêng.

Đối chiếu R8 mapping/usage giúp tách removed/renamed và stable identity bị thiếu. Selected
JAR ABI không làm program definition xuất hiện. Với REQUIRED hoặc candidate có potential
runner path, `javap -p -s -c` đọc selected JAR và inherited declaring class, giữ stdout/
stderr/exit/hash trong P07 diagnostic manifest. javap không chạy class; lỗi/missing tool
là PARTIAL, không lấy output thiếu làm proof. Không cài thêm tool/dependency.

Call graph chỉ nối encoded invoke targets trùng program method definitions từ root
AndroidJUnitRunner.onCreate; không giải đầy đủ virtual dispatch, callbacks, reflection,
ServiceLoader, dynamic loading hay branch conditions. Path là STATIC, không phải trace.
JNI/native và test discovery vẫn phải xác nhận runtime sau khi được duyệt sửa. Không
mặc định35 Kotlin +4 concurrent candidates của P09 đều là runtime requirements.

Đầu ra dùng để trình thiết kế keep/dependency tối thiểu có source/member proof và giới
hạn: seed class linkage đã quan sát khác complete initialization/test closure. Không
áp dụng keep mới, không blanket Kotlin/AndroidX, dontwarn/stub/JDK hay hạ shrink/gate.
Nếu cần sửa ngoài2 file, dừng và xin PO duyệt phương án cụ thể. Rerun đủ4 cell để thu
report,30 phút/cell, retention3 ngày và CI nền cùng HEAD; G2 FAIL được giữ trung thực.
API26 logcat, permission, apksigner/aapt, license collector/legal vẫn ngoài P10. QA độc lập
trước Leader review; PR17/18 Draft, không Ready/merge/tag/release/T20 production;
ARM64 thực/ARM64-16KiB thực/native OOM OPEN.

### G2-P11 — bước đối chiếu program input trước keep

PO6361729695 phê duyệt thử nghiệm Phương án B theo Leader6361701203 trong3 path:
proguard-rules.pro, inspector và protocol; mọi bất biến P10/796 records/12 paths giữ nguyên.
Trước khi sửa keep, observer read-only thu `p11-target-r8-inputs.json` ngay trước
`:minifyReleaseWithR8`, gồm program/referenced/boot inputs và SHA256. Bước này chưa đổi
keep hoặc dependency: phải chứng minh selected stdlib2.4.21 là target PROGRAM input,
không dùng test R8 library input thay bằng chứng đó. Nếu không thể xác minh, STOP.
Sau khi đối chiếu classfile/member và program role mới được áp dụng exact ABI roots;
keep không thể chuyển library class thành program. Không tự chữa crash mới; mọi sửa
build/dependency hoặc mở rộng allowlist cần quyết định PO riêng. PR17/18 vẫn Draft.

### G2-P11 — thử nghiệm exact ABI roots (Phương án B)

Bước trước keep tại HEAD c61158b6e468d7f9dbd0b5262be1eea78769bcf3,
run39931996535, artifact API35 ID12492720897 (ZIP SHA256
b0440ec15948e75055d033eb355a53f838af596bdc0255824a7314fa50831455)
đã xác minh `BEFORE_TARGET_R8`, `mutatesTaskInputs=false`, selected stdlib2.4.21 thuộc
target **programClasses**, không thuộc referencedClasses. Input snapshot SHA256
a6a2e6823957324a62045acf573cf1b029e97eea540587e8f5dd708bfd366bb0.
JAR SHA256 bd8250210584cb659847dce9cda660f8e9906e5def7fbebcea93dc6dcb6a88a3
khớp P10 và QA6361646601. Trước khi sửa keep đã đọc classfile tất cả12 root classes
và exact signatures; không suy program role từ test library input.

P11 giữ nguyên từng byte keep cũ tại55f2da1 (B2KdfProbe và3 Trace API), chỉ append
exact rules từ `P11_ROOTS` trong inspector. Bảng này mô tả toàn bộ keep mới:

| Class identity | Exact members được giữ | Evidence |
|---|---|---|
| kotlin.jvm.internal.Lambda | public ctor(int), getArity():int | crash P10; TestDirCalculator inputDir$2/outputDir$2 ctor invoke PC3; classfile ctor/arity |
| kotlin.jvm.internal.FunctionBase | getArity():int | Lambda implements FunctionBase; classfile |
| kotlin.Function | không member | FunctionBase/Function0 extends Function |
| kotlin.jvm.functions.Function0 | invoke():Object | TestDirCalculator lazy argument/callback ABI; selected SynchronizedLazyImpl.getValue bytecode |
| kotlin.Lazy | getValue():Object | TestDirCalculator.getInputDir/getOutputDir actual invoke |
| kotlin.LazyKt | không member | actual invoke owner lazy(Function0):Lazy |
| kotlin.LazyKt__LazyKt | không member | classfile LazyKt superclass, bắc cầu tới declaring class |
| kotlin.LazyKt__LazyJVMKt | public static lazy(Function0):Lazy | inherited lookup và javap default overload |
| kotlin.SynchronizedLazyImpl | public ctor(Function0,Object), ctor(Function0,Object,int,DefaultConstructorMarker), getValue():Object | default lazy bytecode + constructor chain + Lazy.getValue dispatch |
| kotlin.UNINITIALIZED_VALUE | public static final INSTANCE:UNINITIALIZED_VALUE | constructor/getValue field access; initializer/ctor phụ thuộc do R8 giữ transitively |
| kotlin.jvm.internal.Intrinsics | public static checkNotNullParameter(Object,String):void | selected default lazy và SynchronizedLazyImpl constructor bytecode |
| kotlin.jvm.internal.DefaultConstructorMarker | không member | synthetic ctor descriptor; không giả định private ctor được gọi |

Class identity rules dùng `{}` explicit để không vô tình giữ default constructor.
Không wildcard member/namespace/overload; không keep isInitialized/toString/writeReplace,
overload lazy(mode,...)/lazy(lock,...), SafePublication/UnsafeLazyImpl hay coroutine roots.
Exact ABI roots giữ tên và chữ ký ở ranh giới hai APK; các member không liệt kê vẫn có
thể shrink/rename/optimize, implementation cần từ roots được R8 phân tích transitively.
Không tắt optimization/shrink toàn cục, không thêm dependency/program input.
Tham chiếu cách hiểu keep/member modifiers:
https://developer.android.com/topic/performance/app-optimization/add-keep-rules

Oracle fail-closed `p11-abi-oracle.json` là gate mới bổ sung sau build/scans/P10 diagnostics,
trước instrumentation. Nó không nằm trong safe diagnostic wrapper. Kiểm:
- Source keep đúng baseline+exact12 roots, chặn mọi thay đổi/wildcard/dontwarn ngoài hợp đồng.
- Snapshot target program role/hash; selected classfile declarations/kind/hierarchy và member
  visibility/static/abstract ABI. Thu `javap -p -s -c` cả12 classes trong CI P07 manifest,
  không còn chỉ dựa local supplement P10.
- Actual class_defs/class_data của mọi DEX target/test; decode errors là FAIL;12 original
  class identities/hierarchy và exact member owners/flags phải còn ở target. Mapping
  header nếu có phải giữ identity; thiếu header không thay actual original definition
  (R8 có thể không ghi header cho facade không còn member). Không chấp nhận chỉ có
  reference/type_id. LazyKt.lazy phải resolve qua hierarchy tới LazyKt__LazyJVMKt.
  Interface hierarchy so theo tập hợp: DEX có thể sắp xếp interface khác classfile;
  positive control đảo thứ tự phải vẫn qua, không nhầm encoding order với ABI.
- Actual test invoke/field sites trên ABI roots phải resolve đúng final target members;
  roots không có trong test program input/DEX; collision0; canary vẫn bị loại.
- Inspector cuối đối chiếu lại source/keep/APK hashes với oracle; không chấp nhận report
  cũ hoặc APK bị thay. Mọi5 tests/20 metrics/JNI/KAT/ABI/page/memory/signing/security gate
  cũ giữ nguyên, oracle PASS không thay runtime acceptance.

15 negative controls thuần dữ liệu: missing class, member bị đổi tên/mất, static drift,
broken hierarchy, duplicate test class, canary retained, decode error, blanket rule,
dontwarn, member rule removed, library-only provider, hash drift, mutating observer,
duplicate program provider, renamed mapping. Positive controls chấp nhận đảo thứ tự
interface và thiếu mapping header khi actual original class_def hiện diện. Không
mutate APK/build/source/input trong controls.

Giới hạn: oracle chỉ xác minh bounded ABI theo bảng, không complete shared-runtime
closure. Ví dụ Intrinsics.areEqual từ đường conditional khác không tự thành keep;
tham chiếu ngoài exact member contract được ghi `deferredConditionalReferences` với
vị trí thực và trạng thái resolve, không tuyên bố mọi reference đều đã đóng. Classloader,
virtual dispatch/reflection và tất cả paths chỉ được xác nhận bằng runtime thực.
Nếu có class/member crash mới, class không vào target DEX, cần đổi dependency/build,
checksum/toolchain hoặc ngoài3 path: giữ raw evidence và STOP, không nối keep theo crash.
Rerun4 cell30m/cell và CI nền cùng HEAD, artifact3 ngày; không bỏ gate API26 clear-logcat
hay biến G2 FAIL thành PASS. Permission/apksigner/aapt/license/legal vẫn OPEN ngoài P11.
QA độc lập trước Leader review; PR17/18 Draft, không Ready/merge/tag/release/production.

Lịch sử oracle P11: HEAD4185b47/run39932999378 bị gate từ chối vì bắt buộc mapping
header cho LazyKt, dù class_def gốc/hierarchy/member linkage đều có thật; API35-16KiB
artifact12491922815 ZIP SHA256346dc83d7cee1dd8e8ca036b8e299b9beca3dd227f949ba22ee019c645835aeb
giữ raw FAIL. Đây là lỗi oracle trước instrumentation, không phải crash runtime mới.
Đã sửa chỉ inspector/protocol: actual original class_def bắt buộc, header nếu có không
được rename; thêm renamed-mapping negative và2 positive boundary controls. Keep byte
không đổi. Lần chạy lại tại HEAD sửa oracle mới là bằng chứng để bàn giao P11.

### G2-P12 — chẩn đoán member ABI, không sửa runtime

Theo PO6368999821/Leader6368952905, delta chỉ inspector/protocol trên mốc P11
3dce1fdc415256d795574dde51ec66232e27fb7d. Không sửa keep/build/input/task wiring,
metadata796/catalog/dependencies/toolchain/test/KAT/runner/workflow/gate/production.

Collector `p12-build/` và `p12-runtime/` sinh `members.json` + `members.md`, source/hash
manifest và25 controls. Hai hook dùng safe diagnostic wrapper sau build/oracle và
sau instrumentation/P10; không thay exit/acceptance cũ. API26 lỗi clear-logcat vẫn
dừng trước instrumentation, chỉ có build report. CI nền phải cùng HEAD,4 cell tối đa
30 phút/cell, retention3 ngày; QA độc lập trước Leader review, PR17/18 giữ Draft.

Coverage: mọi field_id/method_id của actual test DEX được biểu diễn ít nhất một lần,
gồm các symbol có decoded instruction/annotation/static-encoded/handle sites, hoặc
MEMBER_ID_ONLY nếu không có decoded use. Decoder giữ nguyên P10 definitions/type refs,
chỉ thêm memberUses và table counts. Key là owner + name/descriptor + FIELD/METHOD +
STATIC/INSTANCE/UNKNOWN. ID pool/annotation/CP không tự thành executed code; method
handles giữ dispatch từ handle kind, invokes/field opcodes giữ static/instance.
Không coi method_ids/field_ids là definitions. DEX PCs/dòng là minified positions.

Final target/test class_defs/class_data quyết định sự hiện diện thật và declared ABI.
Field lookup: class, superinterfaces rồi superclass. Method lookup: class/superclass
rồi interfaces; constructor/clinit không inherited. Missing hierarchy, class collision,
ambiguous interface/default resolution, arrays và signature-polymorphic MethodHandle/
VarHandle giữ UNKNOWN. Lookup nhiều interface được xử lý bảo thủ, không mô phỏng đủ
VM maximally-specific/default selection. PRESENT xác nhận definition/kind tĩnh, chưa
chứng minh access check, classloader visibility, dispatch path hay nhánh thực thi.
Boot member lấy từ compileSDK37 classfile, luôn ghi COMPILE_BOOT; không thay device proof.

Đọc target/test mapping và usage bằng Java type→JVM descriptor (primitive/array/erased
signature); phân biệt overload và owner/name/descriptor. Mapping inline từ owner khác
không tự dùng làm renamed proof. Original↔obfuscated class aliases mâu thuẫn giữ rõ
ambiguous; không suy field rename chỉ từ class rename. Member rename cần exact member
mapping tới actual live definition. Usage CLASS removal khác block removed MEMBER.
Unknown format ghi parseErrors/PARTIAL_NOT_VERIFIED, không bỏ lặng lẽ. Varargs/enum
usage modifiers và JVM package-info class names được hỗ trợ.

Hai trục độc lập:
- status PRESENT: exact symbolic member/kind resolve tĩnh; memberNameState có thể
  RENAMED nếu chính reference đã dùng tên mới. ownerRenamed được ghi riêng.
- status MISSING: thiếu class trong captured program/boot có selected provider, thiếu
  member khi lookup đầy đủ, kind mismatch, hoặc typed VM error chứng minh gap.
- status RENAMED: symbolic reference cũ không resolve nhưng mapping có alternative
  member sống. Linkage vẫn UNRESOLVED, không báo PRESENT để che stale reference.
- status UNKNOWN: thiếu/ambiguous hierarchy/provider, dynamic semantics hoặc conflict.
- REQUIRED chỉ từ typed NoSuchField/MethodError của XML failure run hiện tại. Phân biệt
  identity bị lỗi với site nào trùng actual stack frame; không nói mọi site đã chạy.
  Field error không nêu dispatch chỉ gán khi actual instruction dispatch duy nhất.
- CONDITIONAL cho static site không có crash proof; ANNOTATION-METADATA cho typed
  annotation-only; UNKNOWN cho MEMBER_ID_ONLY hoặc resolution chưa đủ. Không coi toàn
  bộ static gaps là runtime-required. Build pha chưa có crash không mượn seed P11.

Nguồn ABI: JAR entries từ target/test observed program/referenced/boot inputs, hash
đối chiếu trước đọc; ưu tiên program input tương ứng owner APK. Lưu selected member
declaration/access/static flags, class hash/JAR hash/coordinate khi có; provider ABI
khác nhau ghi ambiguity. Non-JAR inputs ghi unindexed, actual final program DEX vẫn
decode đầy đủ. Classfile ABI/CP không phải per-method execution. Report có mapping/
usage/input/DEX/APK/XML hashes và table coverage để QA kiểm toán từng row.

25 controls kiểm class-only khác member proof, exact overload/descriptor, inheritance
field/method và interface precedence, constructor không inherited, incomplete owner/
parent, static-kind, member rename khác removal/class-map, array/obfuscated descriptor,
tên member chứa L, malformed mapping, stale/live renamed references, ambiguous interfaces,
clinit không inherited và taxonomy observed/static/annotation/ID-only.
Controls chỉ trên dữ liệu synthetic, không mutate APK/input/source hay gate.

P11 exemplar cần chứng minh lại: mapping kotlin.text.Charsets→q; actual Lq; có
US_ASCII→a, không UTF_8; usage removed field UTF_8; test sget-object q.UTF_8:Charset
trong constructor PC3/dòng4; XML NoSuchFieldError và frame tương ứng. Class có mặt
không đủ. Lỗi JUnit-caught có thể không ở crash buffer, dùng XML/TestRunner evidence.

Thiết kế tối thiểu CHƯA ÁP DỤNG cho member đã observed (nếu vẫn xác nhận đúng ở P12):
`-keepclassmembers class kotlin.text.Charsets { public static final java.nio.charset.Charset UTF_8; }`
chỉ giữ exact field ABI khi class còn sống; class owner có thể vẫn obfuscate nhưng phải
remap đồng nhất ở test. Không bảo đảm class survival bằng keepclassmembers; nếu cần
class identity root/allowoptimization riêng phải trình Leader/PO với evidence. Không
đề xuất giữ mọi Charsets member/namespace, không thêm dependency. Các conditional gaps
khác cần review actual call-path và source-to-final-DEX riêng, không tự nối keep theo
crash. Chưa chứng minh minimum toàn cục/đủ5 test bodies/JNI/KAT/20 metrics.

Nếu cần sửa keep/dependency/acceptance để chữa gap: STOP xin PO quyết định riêng.
API26 logcat, permission AndroidX, apksigner/aapt, license collector/legal và ARM64 thật/
ARM64-16KiB thật/native OOM vẫn OPEN ngoài P12. Không Ready/merge/tag/release/production.
