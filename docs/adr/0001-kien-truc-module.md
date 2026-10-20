# ADR-0001 — Cấu trúc module và nền build T00

- Ngày: 2026-10-17
- Trạng thái: Đề xuất để Leader review trong PR T00
- Căn cứ: DOC-SPEC v2.1.0 mục 3/8, DOC-BRIEF-M0 v1.5.0 mục 2/3, DOC-VER v1.4.0.

## Bối cảnh

Cần khung đa module build được, test JVM nhanh và không kéo Android vào parser/dedup/categorizer. MVP hoàn toàn local; chưa tạo auth/sync, Firebase hay thư viện mạng. Không có nghiệp vụ ở T00.

## Quyết định

app là Android application (cần tạo APK theo DoD); capture/data/privacy/security là Android library. core-model/parser/dedup/categorizer là Kotlin/JVM. Cụm “app ... (Android library)” trong bảng phạm vi được hiểu theo mục tiêu APK và Spec: app là application, bốn module kia là library.

Quy tắc cạnh trực tiếp:

- app → core-model, capture, data, parser, dedup, categorizer, privacy, security.
- parser/dedup/categorizer/capture/data → core-model.
- core-model/privacy/security chưa phụ thuộc module nào.

`verifyModuleGraph` so sánh chính xác tập module và cạnh ProjectDependency với bảng trên. Đồ thị này không có chu trình. Các cạnh self-reference do AGP tự sinh trong UnitTest/AndroidTest CompileClasspath/RuntimeClasspath được loại khỏi tập cạnh kiến trúc; self-dependency trong cấu hình khai báo vẫn bị chặn. Ba module thuật toán chỉ thêm test dependency JUnit; không có plugin hoặc dependency Android. Đổi cạnh sau T00 cần ADR/brief tương ứng.

JDK 17, Gradle wrapper 9.8.1, AGP 9.4.1 và Kotlin 2.4.21; Android dùng built-in Kotlin của AGP (KGP phiên bản cao hơn được khai báo qua plugin JVM/Compose). SDK 37, Build Tools theo AGP, minSdk 26. Không dùng QPR beta. AndroidX core thêm permission signature nội bộ `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` vào manifest qua dependency. T00 chưa có dynamic receiver nên manifest app gỡ đúng hai node khai báo/sử dụng permission này bằng manifest-merger, giữ APK khung không có uses-permission. Không dùng removeAll để che quyền không mong muốn từ dependency khác; CI kiểm merged manifests cả debug/release. Khi task sau cần dynamic receiver qua ContextCompat, phải review lại cơ chế receiver isolation và quyền nội bộ trong phạm vi task đó. Phiên bản được pin trong version catalog; Gradle distribution và checksum pin trong wrapper.

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

- https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml (artifact 9.4.1 đã được đăng; xem BLOCKER bên dưới)
- https://developer.android.com/build/releases/agp-9-4-0-release-notes
- https://developer.android.com/about/versions/17/setup-sdk
- https://github.com/gradle/gradle/releases/tag/v9.8.1
- https://github.com/JetBrains/kotlin/releases/tag/v2.4.21
- https://developer.android.com/jetpack/androidx/releases/compose
- https://developer.android.com/jetpack/androidx/releases/activity
- https://github.com/ktlint/ktlint/releases/tag/1.8.0
- https://github.com/detekt/detekt/releases/tag/v1.23.8
- https://www.jacoco.org/jacoco/trunk/doc/changes.html

## Bổ sung sau Leader review tại commit 68f3b6b

### Khôi phục permission helper của AndroidX

Việc gỡ `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` chỉ áp dụng cho khung T00 chưa có dynamic receiver. T08 (SMS receiver), hoặc bất kỳ task nào khác, phải kiểm tra lại trước khi dùng `ContextCompat.registerReceiver(..., RECEIVER_NOT_EXPORTED)` hay cơ chế đăng ký receiver không export có đường fallback dùng permission signature trên Android 26–32. Không suy ra rằng mọi SMS receiver đều cần helper này: phải đối chiếu cách đăng ký và code AndroidX thực tế.

Nếu đường code được thêm cần helper, trong cùng task phải gỡ hai marker `tools:node="remove"` tương ứng trong manifest app để AndroidX đóng góp lại cả khai báo `<permission>` signature và `<uses-permission>`. Đồng thời cập nhật có chủ đích kiểm tra manifest đang yêu cầu zero uses-permission, chỉ cho phép permission nội bộ đã duyệt, vẫn chặn INTERNET/quyền ngoài brief; bổ sung test trên phiên bản Android chịu ảnh hưởng. Không tự khôi phục quyền ở T00 khi chưa có consumer.

### AGP 9.4.1 — bằng chứng và BLOCKER R3.3-2

Ngày kiểm tra: 2026-10-17. [Trang phát hành chính thức AGP 9.4](https://developer.android.com/build/releases/agp-9-4-0-release-notes?hl=en) hiện có tiêu đề 9.4.0; xác nhận dòng 9.4 hỗ trợ tối đa API 37, Gradle tối thiểu 9.6.0 và JDK 17. Trang này không có mục 9.4.1 trong nội dung đã truy xuất. URL riêng `https://developer.android.com/build/releases/agp-9-4-1-release-notes?hl=en` trả HTTP 404 khi kiểm tra.

[Metadata Google Maven chính thức](https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml) liệt kê artifact 9.4.1. Đây là bằng chứng artifact đã được đăng, không được ghi thành bằng chứng độc lập rằng có trang phát hành xác nhận stable. Lượt CI trước cũng phát hiện 9.4.1 là bản mới hơn qua Android lint, nhưng chưa thay thế được loại nguồn Leader yêu cầu.

**BLOCKER R3.3-2:** chưa tìm được trang phát hành chính thức ghi rõ patch 9.4.1 stable. Giữ nguyên catalog 9.4.1 đã được dùng trong commit được review; không đổi phiên bản công cụ hay tuyên bố mục này đã đóng. Cần Leader cung cấp nguồn đáp ứng yêu cầu, hoặc xác nhận loại bằng chứng bổ sung được chấp nhận. Các phần sửa khác có thể được kiểm chứng độc lập; PR chưa đủ điều kiện merge khi BLOCKER còn mở.

### Phạm vi kiểm chứng targetSdk

Ứng dụng compileSdk/targetSdk 37 nhưng bằng chứng chạy thực tế hiện chỉ trên emulator API 35. Build với SDK 37 không chứng minh hành vi runtime trên API 36/37. Đây là rủi ro tương thích đã biết, để kiểm trên máy thật phù hợp hoặc trong T17; T00 không tự mở rộng ma trận emulator hay tuyên bố đã kiểm các API đó.

### Duy trì đồ thị chính xác tại T03 và T20

`verifyModuleGraph` so sánh tập cạnh chính xác, không chỉ phát hiện chu trình. Khi T03 hoặc T20 thêm dependency hợp lệ theo brief, chính task đó phải cập nhật bảng cạnh `moduleEdges` và ADR tương ứng, chạy lại kiểm graph và kiểm độc lập Android cho các module thuật toán. Không tắt task, bỏ cạnh khỏi việc kiểm hoặc đổi sang kiểm lỏng để làm CI xanh. T00 giữ nguyên đồ thị hiện tại.

### Tính tạm thời của resource smoke test

Các file `src/main/resources/moneymate/*.properties` chỉ là tài nguyên tạm để smoke test kiểm được đóng gói module và liên kết classpath khi chưa có production class. Chúng không phải dữ liệu nghiệp vụ. Khi module có code thật, trong cùng thay đổi phải xóa resource tạm và thay assertion smoke test bằng việc nạp/kiểm entry point hay kiểu dữ liệu thật; cập nhật các smoke test module khác còn tham chiếu resource đó, giữ kiểm chứng dependency thật. Không giữ chúng để tăng coverage hoặc thay thế test nghiệp vụ. T00 chưa xóa vì chưa có code thật để thay.

### Vị trí script CI và xác thực wrapper

`.github/check_skeleton.py` và `.github/emulator_smoke.sh` là công cụ nghiệm thu khung project chỉ được workflow gọi: script đầu kiểm generated artifacts/tracked files; script sau điều khiển adb và lưu bằng chứng emulator. Đặt chúng cạnh workflow trong `.github/` để thể hiện quyền sở hữu CI, không đưa vào module Android, APK hay build-logic nghiệp vụ. Workflow gọi đường dẫn tường minh; script Python chỉ dùng thư viện chuẩn, shell dùng công cụ runner có sẵn. Nếu sau này được dùng như công cụ phát triển chung, task được giao sẽ đánh giá chuyển vị trí; T00 không tạo thêm lớp công cụ.

[Input chính thức của setup-gradle tại commit đã ghim](https://github.com/gradle/actions/blob/0723195856401067f7a2779048b490ace7a47d7c/setup-gradle/action.yml) khai báo `validate-wrappers` mặc định `true`, kiểm tất cả wrapper JAR trong repo và làm action fail nếu checksum không hợp lệ. Workflow T00 đã được hưởng mặc định này; sau review khai báo rõ `validate-wrappers: true` tại cùng bước setup-gradle. Không cần thêm action wrapper-validation trùng chức năng. `distributionSha256Sum` trong wrapper properties kiểm distribution ZIP, là kiểm tra khác với xác thực wrapper JAR.

Ba action bên thứ ba được ghim commit SHA đầy đủ, kèm comment tag đã đối chiếu:

| Action | Tag | Commit SHA |
| --- | --- | --- |
| android-actions/setup-android | v3 | 9fc6c4e9069bf8d3d10b2204b1fb8f6ef7065407 |
| gradle/actions/setup-gradle | v5 | 0723195856401067f7a2779048b490ace7a47d7c |
| reactivecircus/android-emulator-runner | v2 | a421e43855164a8197daf9d8d40fe71c6996bb0d |

`actions/*` giữ tag theo quyết định Leader. Không thêm secret, Dependabot, quét dependency/secret, pipeline version hay release trong lần sửa T00 này; các việc đó vẫn thuộc task sau.

### Cập nhật bằng chứng AGP ngày 2026-10-19 (làm việc local)

[Android Gradle plugin API reference chính thức](https://developer.android.com/reference/tools/gradle-api) ghi bảng `Current Release` là `9.4.1`, còn `Preview Releases` là `9.5.0-alpha10`. Liên kết 9.4.1 dẫn tới [API của dòng 9.4](https://developer.android.com/reference/tools/gradle-api/9.4/classes). Đây là nguồn chính thức bổ sung mạnh hơn việc chỉ thấy artifact trong Maven; việc phân loại Current Release riêng với Preview hỗ trợ nhận định 9.4.1 thuộc dòng phát hành hiện tại, không phải preview.

[Liên kết stable release notes từ cùng trang](https://developer.android.com/studio/releases/gradle-plugin) vẫn dẫn tới trang AGP 9.4.0; nội dung được truy xuất ngày 2026-10-19 chưa có mục patch 9.4.1. Vì yêu cầu R3.3-2 của Leader chỉ định trang phát hành chứng minh patch stable, giữ trạng thái **chờ Leader chấp nhận bằng chứng API reference**, không tự đóng BLOCKER. Không thay đổi catalog, version ứng dụng hoặc cấu hình build. Bản cập nhật này chưa commit/push theo quyết định tạm ngừng Git/GitHub của PO.

### Quyết định Leader review R2 ngày 2026-10-19

Leader đã **đóng R3.3-2**, chấp nhận tổng hợp bằng chứng Google Maven, API reference chính thức ghi Current Release 9.4.1, và đối chiếu release notes AGP 9.5.0 ở review R2. Các đoạn BLOCKER phía trên ghi lại diễn biến trước quyết định này; trạng thái hiện hành là **đã đóng theo Leader**, không còn chờ chấp nhận nguồn API reference. Khi release notes chính thức có mục patch 9.4.1, bổ sung link ở lần sửa ADR kế tiếp; đây không phải điều kiện chặn.

Theo ngoại lệ R2 đã được PO cho phép, tiếp tục dùng Git local, tải công cụ công khai không đăng nhập và chạy kiểm tra trên clone local sạch; không dùng tài khoản GitHub, push, PR, tag, release hoặc merge. Chỉ xem xét Local-accepted sau khi có đầy đủ log Gradle và check_skeleton chạy thật; CI PR và emulator có thể DEFERRED, không ghi pass. Leader là người chốt nghiệm thu.

Ghi nhận cảnh báo deprecation Configuration.setVisible() có thể xuất hiện khi AGP 9.4.1 chạy cùng Gradle mới. Không bật warnings-as-errors cho cảnh báo Gradle; giữ nguyên Android lint warningsAsErrors và mọi ngưỡng kiểm tra. Báo cáo lần chạy phải lưu đầy đủ nội dung và số cảnh báo thực tế.

### Khôi phục CI GitHub ngày 2026-10-20

CI thật tại commit46531c5 qua build/test nhưng lintDebug chặn vì Gradle9.8.2 đã được phát hành, trong khi wrapper ghim9.8.1. Cập nhật công cụ Gradle lên patch9.8.2 theo [trang phát hành](https://gradle.org/releases/) và [checksum chính thức](https://gradle.org/release-checksums/): distribution ZIP SHA256 `21bd5da2de49b642904077f38c0efdc7778e92b3ed0889392dca61b97e389607`. Wrapper JAR hiện có khớp SHA256 công bố cho cả9.8.1/9.8.2 nên không thay JAR. Giữ URL distribution chính thức và checksum bắt buộc.

Đây là cập nhật công cụ build trong phạm vi Gradle wrapper của T00 để đáp ứng kiểm stable hiện tại, không đổi version ứng dụng0.0.0-dev/code1, AGP, Kotlin hoặc dependency catalog. Giữ nguyên lint warningsAsErrors/abortOnError, test và ngưỡng coverage; không ignore/baseline lỗi để làm xanh. Các lệnh DoD và emulator phải chạy lại trên HEAD mới. Lượt lỗi cũ được giữ tại https://github.com/anhh2j/MoneyMate/actions/runs/39415129557; kết quả mới sẽ ghi vào PR.

### Đồng bộ tài liệu Approved theo Leader R3.1 ngày 2026-10-20

Đồng bộ main tại `c11a50f477b12a57498f7f8c99a5ab797491d4d8` vào nhánh T00. Chín DOCX hiện hành giữ nguyên blob/bytes của main: Spec2.1.0, Plan2.3.0, Test2.3.0, Ver1.4.0, Brief-M0 1.5.0, Sec1.1.0, UX/UI1.2.0, QA1.1.0 và Test Cases1.0.0. AGENTS, README và danh mục tài liệu tham chiếu bản Approved này; các đoạn R1/R2 phía trên giữ ý nghĩa lịch sử theo ngày review.

Có hai xung đột rename/delete do T00 đã đưa Ver1.2.5 và Brief1.2.1 vào archive, còn main xóa đường dẫn cũ. Giữ hai bản archive đã có; chuyển Ver1.2.6 và Brief1.3.0 khỏi danh mục hiện hành vào archive bằng rename, không nhân bản. Không khôi phục Plan2.1.3/Test2.1.0 đã được main xóa. Bộ qa/ được lấy từ main; chỉ sửa tham chiếu DOC-QA ở header AGENT.md thành1.1.0, không đổi tool, checklist hay test QA. Không đổi code/build/workflow, version app hoặc đưa T00b vào T00.
