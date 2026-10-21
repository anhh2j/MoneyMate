# ADR-0002 — Version một nguồn và công cụ phát hành T00b

- Ngày: 2026-10-19
- Trạng thái: Đề xuất để Leader review; phát hành thật DEFERRED cho PO/Leader.
- Căn cứ: DOC-BRIEF-M0 v1.5.0, DOC-VER v1.4.0, giao việc T00b ngày 19/10/2026 (PO duyệt).

## Quyết định

`version.properties` là nguồn version của APK. Convention plugin trong included build `build-logic` đọc một khóa VERSION_NAME, kiểm định SemVer và tính versionCode theo DOC-VER 3.5. Build fail khi sai định dạng, vượt MINOR/PATCH 99, pre-release 29 hoặc tràn số nguyên Android. Build metadata không vào versionName/code. Không thêm logic vào build.gradle.kts gốc; đồ thị module giữ nguyên.

T00b không thêm UI: BuildConfig.VERSION_NAME / GIT_SHA và VersionInfo chỉ cung cấp dữ liệu cho T13/T19, theo quyết định mục 3 của giao việc. GIT_SHA lấy 7 ký tự từ Git local; không đọc được Git trả unknown. Màn hình MoneyMate hiện hành không hiển thị version.

Đề xuất dùng release-please manifest, theo hướng Leader đã chọn. Backend `go` được tài liệu mô tả là repository có CHANGELOG; khi không khai báo version-file, source Go strategy chỉ cập nhật changelog. Dùng Generic extra-file updater để cập nhật block annotation trong version.properties. Không thêm file version.txt, không dùng simple updater vốn ghi đè cả file bằng chuỗi version. Tên strategy là cơ chế cập nhật file của công cụ; không thêm module/source Go vào MoneyMate.

Đã kiểm bằng release-please **17.11.2** thực tế, không gọi GitHub: alpha.1/beta.1/rc.1 lên .2; breaking từ 0.1.0 lên MINOR; Generic updater giữ đúng cú pháp VERSION_NAME và đúng một assignment. Log nộp kèm gói review. Workflow dùng release-please-action v5 ghim SHA, Node 24; kiểm chứng API/PR/tag/release thật còn DEFERRED.

Config `versioning: prerelease`, `prerelease: true`, `prerelease-type: alpha.1`, `bump-minor-pre-major: true`. Leader quản lý chuyển alpha → beta → rc → stable qua release PR và `release-as`/cấu hình prerelease; không giả định đổi prerelease-type sẽ tự chuyển stage của version đang prerelease. Giới hạn .29 được build-logic chặn, cần Leader quyết định mốc tiếp theo. `release-as: 0.1.0-alpha.1` chỉ bootstrap bản đầu; Leader phải gỡ sau bản đầu để chiến lược tự tăng có hiệu lực. Manifest JSON là trạng thái của công cụ release, không được Gradle dùng làm nguồn version APK.

Release-please soạn release PR; chỉ Leader/PO duyệt/merge mới kích hoạt phát hành trên GitHub. Tất cả action được soạn trong cùng workflow với build/verify/upload; không trông chờ tag của GITHUB_TOKEN kích hoạt workflow khác. Quyền ghi chỉ nằm ở job release-please và publish-apk. Bước publish yêu cầu đủ bốn secrets trước khi build; verify_release.py phải xanh trước khi đính kèm APK/checksum. PO/Leader quản lý secret/keystore thật và branch protection; dev không chạy workflow phát hành, tag hay release trong T00b.

## So sánh

| Phương án | Đánh giá |
| --- | --- |
| release-please + Generic updater | Có parser Conventional Commits, manifest/release PR/changelog; hỗ trợ các điều kiện đã kiểm local. Cần xác nhận tích hợp trên PR T00b. |
| Script tự viết toàn bộ phát hành | Phải tự duy trì bump/changelog/PR/idempotency/quyền GitHub; chưa có lý do thay đề xuất của Leader. Không triển khai phương án thay thế. |

verify_release.py chỉ là cổng xác minh độc lập, không phải công cụ tạo release. Script kiểm canonical version/tag/APK/code, chữ ký bằng apksigner, changelog và file signing tracked. Dry-run dùng keystore tạm ngoài repo; plugin giải mã vào thư mục tạm riêng và BuildService xóa khi build kết thúc. Thiếu biến môi trường: release build không ký. Dry-run xóa cả keystore gốc trong finally/context manager. Không dùng keystore thử để phát hành thật.

## Nguồn đã đọc ngày 19/10/2026

- https://github.com/googleapis/release-please/blob/main/docs/customizing.md — strategy và Generic updater annotations.
- https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md — manifest, prerelease và pre-major flags.
- https://github.com/googleapis/release-please/blob/main/src/strategies/go.ts — không tạo version file khi không cấu hình.
- https://github.com/googleapis/release-please/blob/main/src/strategies/simple.ts và src/updaters/default.ts — lý do không dùng simple cho properties.
- https://github.com/googleapis/release-please/blob/main/src/versioning-strategies/prerelease.ts — stage suffix và bump-minor-pre-major.
- https://github.com/googleapis/release-please-action — output/action, workflow và quyền.
- https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow — sự kiện từ GITHUB_TOKEN.

Dependency verification và persist-credentials được triển khai theo DOC-BRIEF-M0 v1.5.0 Approved; tài liệu hiện hành giữ nguyên từ main 30056b7.

## Kiểm candidate Release PR

Go strategy thực của release-please17.11.2 đã được thử trong bộ nhớ, không gọi GitHub: tên mặc định chore(main) bị commitlint chặn; pattern chore(release): release ${version} được chấp nhận. Manifest dùng cùng title làm commit message. CI kiểm pattern đã cấu hình qua chính commitlint. Candidate có các updater CHANGELOG.md và version.properties, giữ một assignment version, không tạo version file Go.

Config release-as không tự làm lịch sử ci-only trở thành releaseable. Khi PO/Leader muốn bootstrap từ squash merge T00b, họ thêm footer Release-As: 0.1.0-alpha.1 vào commit squash merge. Candidate khi đó có release note; nếu chưa sẵn sàng thì chờ feat/fix. Changelog updater prepend mục mới nên Leader bỏ mục Pending release cũ trong release PR đầu tiên. Verifier phải nhận cả heading thường ở bản đầu và heading có link ở các bản sau; dry-run kiểm hai dạng và từ chối version khác. Thực thi release PR/tag/phát hành thật vẫn thuộc Leader/PO.

Bằng chứng review được CI đóng gói với source, checksum, bundle, báo cáo và emulator. Baseline graph được tái hiện trong bản sao ngoài repo, chỉ tắt rule/constraints B; không thay metadata hoặc dependency source thật. QA auto result được ghi nguyên trạng trong gói, không đồng nghĩa QA acceptance.
