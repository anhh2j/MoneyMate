# ADR-0001 — Cấu trúc module và nền build T00

- Ngày: 2026-10-17
- Trạng thái: Đề xuất để Leader review trong PR T00
- Căn cứ: DOC-SPEC v2.1.0 mục 3/8, DOC-BRIEF-M0 v1.2.1 mục 2/3, DOC-VER v1.2.5.

## Bối cảnh

Cần khung đa module build được, test JVM nhanh và không kéo Android vào parser/dedup/categorizer. MVP hoàn toàn local; chưa tạo auth/sync, Firebase hay thư viện mạng. Không có nghiệp vụ ở T00.

## Quyết định

app là Android application (cần tạo APK theo DoD); capture/data/privacy/security là Android library. core-model/parser/dedup/categorizer là Kotlin/JVM. Cụm “app ... (Android library)” trong bảng phạm vi được hiểu theo mục tiêu APK và Spec: app là application, bốn module kia là library.

Quy tắc cạnh trực tiếp:

- app → core-model, capture, data, parser, dedup, categorizer, privacy, security.
- parser/dedup/categorizer/capture/data → core-model.
- core-model/privacy/security chưa phụ thuộc module nào.

`verifyModuleGraph` so sánh chính xác tập module và cạnh ProjectDependency với bảng trên. Đồ thị này không có chu trình. Ba module thuật toán chỉ thêm test dependency JUnit; không có plugin hoặc dependency Android. Đổi cạnh sau T00 cần ADR/brief tương ứng.

JDK 17, Gradle wrapper 9.8.1, AGP 9.4.0 và Kotlin 2.4.21; Android dùng built-in Kotlin của AGP (KGP phiên bản cao hơn được khai báo qua plugin JVM/Compose). SDK 37, Build Tools theo AGP, minSdk 26. Không dùng QPR beta. Phiên bản được pin trong version catalog; Gradle distribution và checksum pin trong wrapper.

ktlint CLI và detekt CLI chạy trong JavaExec riêng, tránh phụ thuộc Gradle plugin của chúng vào API AGP/Gradle. Không trộn runtime Kotlin của detekt với runtime compiler của ứng dụng. ktlint quét toàn bộ Kotlin/build scripts; detekt quét source/test .kt (build scripts được ktlint kiểm), dùng default config cộng maxIssues=0, validate config và baseline rỗng. Android lint coi warning là lỗi.

Dùng JaCoCo tích hợp Gradle cho JVM; gate LINE coverage 85% ở parser/dedup/categorizer chỉ bật khi có production code. T00 không có production class ở ba module này, chỉ có resource định danh; không viết class/test giả để nâng coverage. T04 phải bật gate mặc định, nối check vào CI và chứng minh fail khi <85%; thuộc phạm vi T04, không tuyên bố coverage đạt ở T00. Báo cáo vẫn được cấu hình và CI thu thập.

Mỗi module đúng một smoke test. Resource định danh JVM là dữ liệu đóng gói của module; smoke test kiểm classpath/runtime resource và core-model dependency. Android library kiểm BuildConfig namespace; app kiểm launcher class nạp được. Emulator CI kiểm APK cài/mở và text “MoneyMate”, không thêm test nghiệp vụ.

Version tạm nằm một chỗ ở app/build.gradle.kts, có chú thích theo Brief. T00b phải gỡ các giá trị viết cứng, dùng version.properties. Không thêm release workflow, signingConfig, secret hay tag.

## Phương án đã cân nhắc

- Monolith: không đáp ứng Spec và khó giữ thuật toán độc lập Android.
- Convention plugin/buildSrc: chưa cần cho chín module trống; tránh thêm cấu trúc build không cần thiết ở T00.
- Kover: Brief cho phép JaCoCo; chọn plugin JaCoCo có sẵn trong Gradle để giảm plugin ngoài.

## Kiểm chứng và hệ quả

CI chạy `ktlintCheck detekt test assembleDebug`, Android lint, kiểm graph, dependency reports, merged manifests debug/release và hygiene file tracked. Báo cáo được upload kể cả khi build thất bại. Emulator job kiểm launcher và text, lưu UI hierarchy/screenshot. Không build/phát hành APK release.

Nguồn kiểm tra phiên bản tại ngày thực hiện:

- https://developer.android.com/build/releases/agp-9-4-0-release-notes
- https://developer.android.com/about/versions/17/setup-sdk
- https://github.com/gradle/gradle/releases/tag/v9.8.1
- https://github.com/JetBrains/kotlin/releases/tag/v2.4.21
- https://developer.android.com/jetpack/androidx/releases/compose
- https://developer.android.com/jetpack/androidx/releases/activity
- https://github.com/ktlint/ktlint/releases/tag/1.8.0
- https://github.com/detekt/detekt/releases/tag/v1.23.8
- https://www.jacoco.org/jacoco/trunk/doc/changes.html
