# ADR-0003 — Cổng quét dependency và secret

- Ngày: 2026-10-19
- Trạng thái: Đề xuất để Leader review; bằng chứng local, CI và QA nộp tại HEAD PR.
- Căn cứ: DOC-SEC v1.1.0 SEC-14/SEC-19, DOC-BRIEF-M0 v1.5.0 và DOC-VER v1.4.0 Approved trên main 30056b7.

## Tiêu chí và lựa chọn

Cần quét được lịch sử Git local đầy đủ, che secret trong báo cáo, quét dependency Java/Kotlin và npm, chặn HIGH/CRITICAL, có log âm tính/dương tính và không cần GitHub account hay API key trả phí.

Chọn **Gitleaks v8.30.1** cho secret; **Trivy v0.76.0** cho dependency. Binary công khai và SHA-256 ghim tại scripts/security-tools.json; đối chiếu digest từ metadata release chính thức trước khi chạy. Installer chỉ giải nén executable xác định, không chạy installer từ mạng, cài ngoài repo. Không tải tool theo latest trong CI.

Gitleaks chạy `git --log-opts=--all` để quét cả các file đã xóa trong lịch sử, và `dir` trên bản sao toàn bộ file Git đang tracked để bao gồm thay đổi được stage. Không quét node_modules/cache/build outputs làm đại diện source; không thay check_skeleton.py. Mọi báo cáo Gitleaks dùng redact=100. Không dùng allowlist rộng hay bỏ qua finding để pass.

Gradle task exportDependencyInventory giải quyết mọi cấu hình canBeResolved đã đăng ký của root/module và buildscript; included build cũng xuất cả cấu hình project lẫn buildscript. Phạm vi gồm app debug/release, test, lint và tooling. Chỉ external ModuleComponentIdentifier có Maven coordinates được xuất, bao gồm dependency bắc cầu; gặp unresolved dependency thì fail. Hai CycloneDX JSON là dữ liệu build sinh ra, không phải danh sách dependency viết tay. Trivy quét hai SBOM này và package-lock.json trong cây tracked (bật `--include-dev-deps` vì commitlint nằm trong devDependencies); `--severity HIGH,CRITICAL --exit-code 1`. Không dùng ignore-unfixed hoặc ignorefile để làm xanh. Trivy cảnh báo SBOM ngoài có thể thiếu thuộc tính riêng: purl Maven/version được giữ; việc mapping vulnerability vẫn phụ thuộc dữ liệu scanner, không tuyên bố phát hiện toàn bộ lỗ hổng.

DB Trivy tải từ nguồn công khai; mạng/DB không truy cập được là BLOCKED, không phải pass. Finding HIGH/CRITICAL ở dependency đang pin phải báo Leader, không tự đổi catalog T00 hoặc hạ ngưỡng/allowlist. Bản ghi ngày/phiên bản công cụ và log finding đi cùng gói review.

## Phương án khác

| Phương án | Lý do không chọn |
| --- | --- |
| OSV-Scanner | Hỗ trợ Gradle lockfile và dữ liệu custom; cần thêm xử lý severity/gate và inventory trong cấu hình hiện tại. Trivy đã có cổng severity trực tiếp và CycloneDX input. |
| OWASP Dependency-Check | Cần quản lý NVD/API/rate limit và DB lớn; chi phí bootstrap cao cho khung nhỏ. |
| GitHub secret/dependency services | Cần account/GitHub; không kiểm được ngay local. Có thể bổ sung sau, không thay cổng local. |
| Trivy secret scan đơn lẻ | Không thay thế quét toàn lịch sử Git; giữ Gitleaks cho yêu cầu này. |

## Kiểm chứng bắt buộc

Fixture nằm trong thư mục tạm ngoài repo, không chứa dữ liệu ngân hàng/PII hoặc secret thật. Một repo Git tạm có token giả rồi xóa ở commit sau, Gitleaks vẫn phải fail và report redacted. Một SBOM tạm chứa log4j-core 2.14.1 phải tạo finding HIGH/CRITICAL và exit 1; lỗi tải DB không được coi là negative test pass. Sau đó quét repo/inventory thật, giữ nguyên finding; chỉ ghi PASS nếu cổng thật exit 0.

## Dependency verification — cập nhật 20/10/2026

DOC-BRIEF-M0 v1.5.0 giữ yêu cầu dependency verification của bản v1.4.0, nên thực hiện: tạo `gradle/verification-metadata.xml` bằng `--write-verification-metadata sha256` với toàn bộ build/test/lint/dependency và task T00b. Một file root áp dụng cho subprojects và included build theo tài liệu Gradle; giữ `verify-metadata=true`, không có trusted-artifacts rộng. Tác vụ xác minh chạy chế độ strict. Checksum artifact và metadata không đánh giá CVE; phương án B đã được phép thử nghiệm; chỉ kết quả scan mới trên nhánh đã rebase mới được dùng cho review T00b.

Quy trình thêm dependency: chỉ sau khi được duyệt, resolve qua repository chính thức với TLS, tái tạo metadata bằng tập tác vụ trong README, review diff từng GAV/artifact/POM/module và nguồn checksum, commit cùng thay đổi dependency rồi chạy lại strict build và CI. Không thêm also-trust hoặc tạo lại checksum khi gặp mismatch chưa giải thích được. Bootstrap là thiết lập tập checksum tin cậy ban đầu, không chứng minh artifact không có lỗ hổng.

Probe trên bản sao local: lưu nguyên bytes XML, sửa một checksum của artifact được resolve, chạy strict build phải fail vì dependency verification (không nhận lỗi mạng/configuration làm bằng chứng), hoàn nguyên trong finally và chạy lại pass. Không sửa cache, không commit bản lỗi. Log/mã thoát được nộp cùng review; không ghi PASS trước khi có log.

Phương án sửa dependency AGP/constraint phải trình Leader duyệt riêng theo review 20/10/2026; không chuyển runtime dependency sang compileOnly hay bỏ khỏi inventory để làm xanh scanner.

## Nguồn đã đọc ngày 19/10/2026

- https://github.com/gitleaks/gitleaks — CLI git/dir, log-opts, redact.
- https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1 — binary/digest.
- https://trivy.dev/docs/latest/target/sbom/ — CycloneDX input và giới hạn mapping SBOM.
- https://trivy.dev/docs/latest/configuration/filtering/ — severity và exit-code.
- https://trivy.dev/docs/latest/coverage/language/java/ — Java dependencies.
- https://github.com/aquasecurity/trivy/releases/tag/v0.76.0 — binary/digest.
- https://github.com/google/osv-scanner/blob/main/docs/supported_languages_and_lockfiles.md — đối chiếu lựa chọn OSV.

- https://docs.gradle.org/current/userguide/dependency_verification.html — kiểm SHA-256, phạm vi root/included build và bootstrap metadata.

## Thử nghiệm B được ủy quyền ngày 20/10/2026

PO đã yêu cầu triển khai thử B theo proposal, chưa cho phép tự merge/phát hành. Chọn exact GAV jose4j0.9.7, bcprov/bcutil/bcpkix-jdk18on1.86, jdom2.0.6.1 từ catalog; giữ AGP/Kotlin và version app. Included build có strict constraints, settings policy sửa resolution buildscript và androidLintTool cho đúng 5 GAV. Không thay runtime dependency của app bằng rule tổng quát.

Hai phép thử đầu phơi bày vấn đề classloader, được giữ log: đặt AGP trên settings classpath gây unknown plugin version; chỉ loại AGP khỏi settings còn khiến AppBuildPlugin có type signature trỏ tới AGP không nhìn thấy. Cách xử lý trong phạm vi: settings classpath Gradle-only và convention plugin dùng public Groovy DSL bridge trên extension thực của project. Root AGP vẫn được resolve bằng version catalog và SHA-256; AGP vẫn là implementation dependency trong build-logic. Đây là rủi ro thiết kế cần Leader đánh giá, không phải chứng nhận hỗ trợ của Google.

Bổ sung graph/scan mọi cấu hình canBeResolved trong container root/module/included build và buildscript, giữ edges và selection reason. Audit fail nếu unresolved hoặc GAV được pin còn sai version. Audit JAR thực nạp của 5 thư viện ở root/từng module Android qua cả AGP và project-script classloader; source JAR phải khớp phiên bản catalog. Settings exclusion không được dùng làm bằng chứng sửa CVE: root/classloader và build-logic inventory đều phải giữ AGP cùng tập dependency đã sửa.

Mở rộng scan có thể phát hiện thêm finding ngoài bốn CVE ban đầu; nếu có phải báo BLOCKED, không tự mở scope/allowlist. Trivy chỉ mapping Maven purl, không chứng minh mọi thư viện shaded hoặc SDK/JDK binary an toàn. Dependency verification là kiểm toàn vẹn, không thay scan CVE.

TestKit dùng Maven fixture và Gradle home riêng ở thư mục tạm; root/child phải cùng được pin, unrelated GAV và project runtime không bị rule đổi, secure artifact thiếu phải fail. Phải kiểm thực tế quality, R8, signing thử, verifier và các negative controls trên HEAD cuối. Báo cáo/log mới quyết định kết quả; không tự coi việc pin version là PASS.

Bổ sung từ full graph: policy exact-GAV cũng áp dụng cho cấu hình tooling `androidLintTool`, vì lint có classpath BC riêng. Không áp dụng rule này lên compile/runtime dependency của app. TestKit kiểm cả buildscript lẫn lint ở root/child; audit toàn bộ cấu hình phải chặn nếu còn bản cũ.

Lượt thử B local 20/10/2026 đã chạy quality/build/lint/R8, 20 test JUnit và smoke API trên classloader AGP thực: BC RSA/X509, JWE nén với kiểm ciphertext sai, JDOM XML lành tính. Scan HIGH/CRITICAL và secret của inventory mở rộng đã pass ở lượt bootstrap. Metadata SHA-256 được tái tạo từ rỗng; chỉ có bộ 5 GAV mới. Gói review phải kèm lượt strict, negative controls, APK ký tạm và kết quả HEAD cuối. Đây chưa phải nghiệm thu: CI GitHub, emulator và tương thích vendor vẫn cần kiểm/duyệt.

Sau rebase lên main30056b7: kế thừa Gradle9.8.2. Lượt refresh toàn project bị dừng (exit130, không tính PASS) khi tiếp tục resolve metadata sau help. Để ghi đủ descriptor parent đã quan sát ở resolve lạnh, dùng fixture Gradle ngoài repo, mỗi POM/module một cấu hình riêng không transitive, sinh SHA-256 bằng --write-verification-metadata rồi hợp nhất artifact còn thiếu. Không thay checksum có sẵn, không thêm dependency runtime hoặc trust exception. Đối chiếu bytes mới với Maven Central qua TLS, giữ fixture/log để tái hiện, rồi chạy đầy đủ strict và negative controls. CI T00b tại HEAD PR là bằng chứng riêng; CI sau merge T00 không thay thế.
