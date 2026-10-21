# MoneyMate

Trợ lý tài chính cá nhân Android local-first. T00 chỉ tạo khung build; ứng dụng mở một màn hình “MoneyMate”. Không có parser, DB, capture service, khóa ứng dụng hay chức năng mạng ở task này.

## Yêu cầu và build từ clone sạch

- JDK 17 (`java -version`).
- Android Studio có SDK Manager, hoặc Android command-line tools.
- Cài Android SDK Platform 37.0, Build Tools 37.0.0, Platform Tools; chấp nhận SDK licenses.
- Đặt `ANDROID_HOME` trỏ tới SDK (hoặc cấu hình `sdk.dir` trong `local.properties`, không commit).
- Lần build đầu cần Internet để tải công cụ/dependency; APK không có quyền INTERNET.

```sh
git clone https://github.com/anhh2j/MoneyMate.git
cd MoneyMate
# Khi review T00b: git switch feature/T00b-version-release
sdkmanager "platforms;android-37.0" "build-tools;37.0.0" "platform-tools"
sdkmanager --licenses
./gradlew ktlintCheck detekt test assembleDebug
./gradlew lintDebug verifyModuleGraph
```

Windows PowerShell: dùng `gradlew.bat` thay cho `./gradlew`; đặt `$env:ANDROID_HOME` tới thư mục SDK. Không cần cài Gradle toàn cục; wrapper pin Gradle và SHA-256.

APK: `app/build/outputs/apk/debug/app-debug.apk`. Khởi động một AVD Android API 26 trở lên từ Android Studio Device Manager, sau đó:

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -W -n com.app.moneymate/.MainActivity
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml
```

Màn hình phải hiển thị “MoneyMate”. CI tự kiểm text trong UI hierarchy và lưu ảnh chụp.

## Kiểm tra

```sh
./gradlew :parser:dependencies :dedup:dependencies :categorizer:dependencies
./gradlew :app:dependencies
./gradlew :app:processDebugMainManifest :app:processReleaseMainManifest
./gradlew verifyModuleGraph
```

CI ghi dependency report từng module và kiểm merged manifests debug/release. Báo cáo nằm ở `build/reports/`, `<module>/build/reports/`, `<module>/build/test-results/`. Mỗi module có đúng một smoke test: JVM kiểm resource thật đã đóng gói và liên kết core-model; Android library kiểm BuildConfig được sinh; app kiểm nạp launcher Activity. Không dùng smoke test để tạo tỷ lệ coverage giả.

JaCoCo đo coverage cho các module Kotlin/JVM. Ngưỡng 85% ở parser/dedup/categorizer được cấu hình nhưng chưa bật vì chưa có production class; T04 phải bật gate mặc định khi thêm code thật. Có thể chạy thử cấu hình bằng `./gradlew :parser:check :dedup:check :categorizer:check -PenableProductionCoverage=true`; khi chưa có class, không coi kết quả bỏ qua của JaCoCo là đạt coverage. Xem ADR-0001.

## Cấu trúc module

| Module | Loại / trách nhiệm về sau | Phụ thuộc module trực tiếp |
| --- | --- | --- |
| app | Android application, Compose / navigation / DI | tất cả tám module còn lại |
| core-model | Kotlin/JVM, model / interface | không |
| parser | Kotlin/JVM, template engine | core-model |
| dedup | Kotlin/JVM, khử trùng lặp | core-model |
| categorizer | Kotlin/JVM, phân loại | core-model |
| capture | Android library, thu thập | core-model |
| data | Android library, persistence | core-model |
| privacy | Android library, quyền riêng tư | không ở T00 |
| security | Android library, khóa cục bộ | không ở T00 |

Không tạo auth/sync ở MVP. `applicationId`: `com.app.moneymate`; minSdk 26, compileSdk/targetSdk 37 (Android 17 ổn định; không dùng QPR beta).

## Version và phạm vi

Version APK đọc duy nhất từ `version.properties` qua `build-logic`, giá trị khởi đầu `0.1.0-alpha.1` → versionCode `10001`. BuildConfig và VersionInfo cung cấp version/Git SHA cho T13/T19; T00b không thêm UI. Giá trị không hợp lệ làm build fail. Không sửa versionName/versionCode bằng tay trong Gradle scripts. T00 đã merge tại `30056b7`; T00b dùng nhánh `feature/T00b-version-release` và cần CI riêng tại HEAD của PR.

Quy tắc làm việc: [AGENTS.md](AGENTS.md). Tài liệu: [docs/README.md](docs/README.md). Quyết định: [ADR-0001](docs/adr/0001-kien-truc-module.md).


## T00b — kiểm tra local và phát hành

Căn cứ: [ADR-0002](docs/adr/0002-cong-cu-phat-hanh.md), [ADR-0003](docs/adr/0003-quet-bao-mat.md), DOC-BRIEF-M0 v1.5.0 và DOC-VER v1.4.0 Approved trên main; danh mục đủ 9 tài liệu nằm ở docs/README.md.

Dùng JDK 17 đầy đủ (có javac/keytool), Node 24.19.0 và Android SDK nêu ở trên. T00b được rebase lên main `30056b7`; chỉ push nhánh và mở PR khi có bằng chứng kiểm tra. Không tự merge/tag/release. Lịch sử cần được giữ cho GIT_SHA, commitlint và quét secret.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npx --no-install commitlint --from 30056b7 --to HEAD --verbose
python3 scripts/check_docs.py
./gradlew ktlintCheck detekt test assembleDebug :build-logic:test --console=plain
./gradlew lintDebug verifyModuleGraph :app:processReleaseMainManifest --console=plain
./gradlew exportDependencyInventory --console=plain
```

Lưu bốn dependency report theo workflow trước khi chạy `python3 .github/check_skeleton.py`. Script giữ kiểm permission/Android isolation/hygiene, chuyển kiểm version tạm sang kiểm canonical source; app có thêm test metadata, mọi test phải thực sự chạy, không skip.

`python3 scripts/install_security_tools.py /tmp/moneymate-tools` tải binary Linux x64 ghim checksum; có thể chọn thư mục tạm tương đương ngoài repo. `python3 scripts/security_scan.py --tools /tmp/moneymate-tools` quét lịch sử/cây tracked, SBOM Gradle và npm lock, chặn HIGH/CRITICAL hoặc secret. `python3 scripts/check_negative_controls.py --tools /tmp/moneymate-tools` kiểm gate với fixture tạm: secret lịch sử, CVE, commit sai, checksum sai và version sai. Lưu exit code và hoàn nguyên nguyên bytes file nguồn; CI chạy trước dry-run. Cần Internet tải DB. Finding/lỗi mạng phải giữ log và báo BLOCKER. Không dùng ignorefile để pass.

### Dry-run R8 và xác minh

```sh
python3 scripts/dry_run.py
python3 scripts/verify_release.py v0.1.0-alpha.1 app/build/outputs/apk/release/app-release.apk --checksum app/build/outputs/apk/release/app-release.apk.sha256
```

Dry-run sinh keystore/mật khẩu ngẫu nhiên ngoài repo, build signed R8, kiểm aapt/apksigner/changelog/tag/code, thử tag lệch phải fail, chạy lại pass và xóa keystore tạm. Log ở build/reports/release; APK release chỉ phục vụ test, không dùng phát hành thật. Kích thước APK debug/release được ghi cùng log. CI cài và mở cả debug lẫn APK release R8 ký thử trên emulator, lưu log và ảnh theo từng variant. Kiểm thiết bị thật và bản ký phát hành do PO thực hiện.

Build release bình thường thiếu bất kỳ biến signing nào sẽ không ký. Bốn biến: KEYSTORE_BASE64, KEYSTORE_PASSWORD, KEY_ALIAS, KEY_PASSWORD. Keystore thật/mật khẩu do PO quản lý và sao lưu; thêm dưới GitHub secrets khi nghiệm thu, không đưa vào Git. Quy trình decode chỉ tạo file tạm ngoài repo và xóa lúc build kết thúc. Không in secrets ra log.

### GitHub và thẩm quyền

PO/Leader quản lý branch protection, review và quyết định phát hành. Quy trình T00c ở cuối trang và ADR-0004 thay hướng dẫn auto-release cũ; không bật quyền repository hoặc phát hành trong task PR-only.

### Khóa toàn vẹn dependency — Brief v1.5.0

`gradle/verification-metadata.xml` kiểm SHA-256 cả artifact và metadata (POM/module), áp dụng từ root cho các module và included build. Giữ `verify-metadata=true`, không thêm `trusted-artifacts` rộng hoặc chạy ở chế độ lenient/off. Kiểm toàn vẹn không thay thế scanner lỗ hổng: checksum đúng vẫn có thể thuộc một dependency có CVE.

Khi thêm hoặc đổi dependency đã được duyệt, chạy tác vụ thực tế để Gradle cập nhật metadata. Khi thay wrapper hoặc đã có cache, dùng thêm `--refresh-dependencies` lúc cập nhật để ghi cả parent POM/BOM được resolve; đối chiếu nguồn chính thức rồi chạy lại strict:

```sh
./gradlew --write-verification-metadata sha256 ktlintCheck detekt test :build-logic:test assembleDebug lintDebug verifyModuleGraph :app:processReleaseMainManifest :app:assembleRelease :parser:dependencies :dedup:dependencies :categorizer:dependencies :app:dependencies exportDependencyInventory --console=plain
# Review diff XML: tọa độ, artifact/POM/module, SHA-256 và nguồn tải chính thức.
git diff -- gradle/verification-metadata.xml
./gradlew --dependency-verification strict ktlintCheck detekt test :build-logic:test assembleDebug lintDebug verifyModuleGraph :app:assembleRelease exportDependencyInventory --console=plain
python3 scripts/dry_run.py
```

Lần đầu bootstrap cần đối chiếu artifact từ repository chính thức qua TLS và review các checksum sinh ra; không coi việc tự tạo checksum là bằng chứng dependency an toàn. Nếu build báo checksum lệch, dừng để kiểm nguồn/cache và báo Leader; không tái tạo XML chỉ để bỏ lỗi. Sau thay đổi đã duyệt, commit metadata cùng thay đổi dependency, chạy lại các task dependency/CI và các ca âm tính. Khi graph sửa CVE được Leader duyệt, phải tái tạo/review metadata theo graph mới; file khóa hiện tại không đóng BLOCKER CVE.

Probe bắt buộc chạy trên bản sao local: lưu nguyên bytes XML, đổi đúng một SHA-256 của artifact thực sự được resolve, chạy build với `--dependency-verification strict` và xác nhận fail do checksum; hoàn nguyên XML trong `finally`, chạy lại pass. Không đổi file cache dependency, không commit checksum sai, không làm probe trên nhánh dùng chung đang có build chạy.

Đợt kiểm chứng metadata này dùng Linux. Windows/macOS chưa được kiểm chứng; artifact khác classifier phải được bổ sung và review checksum theo cùng quy trình, không tắt xác minh để chạy qua.

### Thử nghiệm policy B — chờ Leader review

Theo ủy quyền thử nghiệm ngày 20/10/2026, giữ AGP 9.4.1 và chỉ ghim 5 GAV tooling: jose4j 0.9.7, bcprov/bcutil/bcpkix-jdk18on 1.86, jdom2 2.0.6.1. Giá trị ở version catalog. Constraint strict áp dụng cho included build; settings policy đặt rule exact GAV sớm cho buildscript của root/subproject. Không force cả group hoặc thay version ứng dụng. Đây là override chưa được Google chứng nhận tương thích AGP; không tự merge hoặc đóng CVE trước review.

Settings policy chỉ dùng Gradle API nên settings classpath loại AGP để không làm plugin version trở thành unknown. AGP vẫn là implementation dependency của build-logic và vẫn hiện diện ở root/project classpath, không chuyển sang compileOnly và không bỏ khỏi scan. App convention dùng public Groovy DSL trên Android extension của project để không đưa AGP type signature vào classloader settings. Hành vi version/R8/signing phải được kiểm bằng build APK và dry-run thật.

`exportDependencyInventory` xuất tất cả cấu hình có thể resolve trong container và buildscript classpath của root/subprojects; included build cũng quét mọi cấu hình project và buildscript resolve được. JSON graph giữ edges/selection reasons, SBOM giữ Maven purl; unresolved dependency hoặc một trong 5 GAV resolve sai version đều fail. Audit thêm JAR thực nạp qua AGP/project script classloader của root và từng module Android; không chấp nhận graph mới nhưng classloader còn bản cũ. Gradle/SDK binaries và dependency đã shaded không được coi là được phân tích đầy đủ chỉ từ purl.

TestKit có fixture Maven local, Gradle home riêng trong thư mục tạm, kiểm root/subproject cùng được pin, GAV ngoài danh sách và runtime của app không bị rule thay đổi, missing secure artifact phải fail. Fixture không dùng repo production, mật khẩu, keystore hoặc PII.

Khi có vendor AGP stable phù hợp: Leader review graph mới và cân nhắc gỡ override theo cùng quy trình checksum/quality/security/R8/negative tests. Không gỡ gate để qua build. Bằng chứng thử nghiệm nằm trong gói review mới; các bước GitHub/emulator phải có run thật ở HEAD PR mới.

Bổ sung từ full graph: policy exact-GAV cũng áp dụng cho cấu hình tooling `androidLintTool`, vì lint có classpath BC riêng. Không áp dụng rule này lên compile/runtime dependency của app. TestKit kiểm cả buildscript lẫn lint ở root/child; audit toàn bộ cấu hình phải chặn nếu còn bản cũ.

Lượt thử B local 20/10/2026 đã chạy quality/build/lint/R8, 20 test JUnit và smoke API trên classloader AGP thực: BC RSA/X509, JWE nén với kiểm ciphertext sai, JDOM XML lành tính. Scan HIGH/CRITICAL và secret của inventory mở rộng đã pass ở lượt bootstrap. Metadata SHA-256 được tái tạo từ rỗng; chỉ có bộ 5 GAV mới. Gói review phải kèm lượt strict, negative controls, APK ký tạm và kết quả HEAD cuối. Đây chưa phải nghiệm thu: CI GitHub, emulator và tương thích vendor vẫn cần kiểm/duyệt.

### T00c — bootstrap, candidate và publication

T00c thay hướng dẫn bootstrap/push-to-main cũ của ADR-0002 bằng [ADR-0004](docs/adr/0004-release-bootstrap-publication-safety.md). Merge PR kỹ thuật hoặc push main không tạo candidate/tag/release. Nhánh release cũ giữ nguyên làm bằng chứng.

`version.properties` vẫn là nguồn APK duy nhất: 0.1.0-alpha.1 / 10001. Manifest bootstrap rỗng mô tả chưa có release; initial-version chỉ áp dụng bản đầu. Không còn release-as ghim version. Candidate chuẩn hóa một mục release, giữ Unreleased và toàn bộ nội dung M0.

Kiểm offline, không dùng signing secrets hay API ghi:
```sh
npm ci --ignore-scripts --no-audit --no-fund
node --test scripts/tests/release_plan.test.cjs
python3 -m unittest discover -s scripts/tests -p 'test_release_*.py' -v
```

Release candidate workflow chỉ workflow_dispatch: PO nhập full main SHA, version dự kiến và xác nhận `CANDIDATE <version> @ <sha>`. Plan mặc định chỉ đọc. create-pr cần biến CANDIDATE_CREATION_ENABLED=true, môi trường moneymate-candidate có PO reviewer, protected-branches-only và label autorelease: pending đã tồn tại. Nó tạo một nhánh mới release-candidates/... và PR Draft; không chạm nhánh release-please cũ, không approve/merge/tag/release. Quyền tạo PR bằng GITHUB_TOKEN do PO quyết định ở task cấu hình riêng, không tự bật.

Release publication là workflow_dispatch riêng. PUBLICATION_ENABLED mặc định chưa bật. PO phải nhập SHA main của PR release đã merge, version, số PR, fingerprint SHA-256 chứng thư ký đã kiểm độc lập và `PUBLISH <version> @ <sha>`. Preflight chỉ đọc kiểm environment moneymate-publication có PO reviewer/protected branches, main SHA không đổi, CI hậu merge mới nhất đạt và PR chỉ đổi ba file release được phép. Signing job qua environment approval mới nhận bốn signing secrets; publisher không nhận signing secrets. Nó kiểm lại APK/version/signature/checksum/signer rồi tạo annotated tag, draft release, tải APK/checksum, kiểm assets trước khi công bố. Thất bại sau tạo tag phải báo PO/Leader điều tra, không rerun/ghi đè tag.

Không chạy các workflow này trong task PR-only. Thiết lập environment/reviewer, biến enablement, label, repository PR permission và secrets thuộc PO sau khi Leader duyệt; thiếu điều kiện thì BLOCKED. Nếu environment yêu cầu prevent-self-review trong mô hình chỉ một PO, phải giải quyết mô hình người vận hành bằng quyết định riêng; không bỏ approval để chạy qua.

CI của PR do GITHUB_TOKEN tạo có thể chờ người có quyền chọn Approve workflows to run theo tài liệu GitHub hiện hành. Sau đó vẫn cần QA/Leader review và required checks đúng HEAD; không dùng bot tự approve/merge hoặc pull_request_target để né cổng. Luồng publication thực, signing secrets thật và thiết bị thật chưa được nghiệm thu bởi regression offline.
