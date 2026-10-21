# P-01 Implementation Evidence

Task T01, baseline `4570e4e3cece382e5a69fa277046628c05f0aa07`. Implementation theo authorization ngày 21/10/2026, P01-D4 phương án A: chỉ Copy metadata trên mọi API; raw reveal cần xác nhận, không copy/export/share/persist. Không có sensitive clipboard flag hoặc raw clipboard timer.

## Phạm vi

Đúng 23 đường dẫn allowlist P-01. Không thêm module/dependency, không sửa Approved DOCX, qa/, version, workflow release/publication hoặc CI baseline. Thay đổi duy nhất checker baseline `.github/check_skeleton.py`: đối chiếu test theo variant/source-set, vẫn chặn tests thiếu/thừa/skipped/failure/error và giữ các assertion security khác. MainActivity launcher giữ nguyên; icon Spike riêng chỉ debug.

## Bằng chứng trước CI

- Local: 8 Python negative/control tests PASS (`python3 -m unittest discover -s scripts/tests -p 'test_t01_spike_checks.py' -v`).
- Local Gradle: BLOCKED khi tải distribution, Network is unreachable; không có SDK/emulator local. Không ghi build/runtime PASS từ kết quả Python.
- CI baseline và T01: chờ run tại HEAD PR; báo cáo bàn giao sẽ dẫn link run/job/artifact cùng SHA/digest, không đóng gói lại thứ đã có GitHub.

| Matrix | Evidence kỳ vọng | Trạng thái ban đầu |
| --- | --- | --- |
| ING-01 | Lazy extras gate/unit và snapshot instrumented + system callback | PENDING CI |
| ING-02 | Epoch, bytes/count/TTL/clear/background + process restart | PENDING CI |
| ING-03 | System binding exported=false + probe UID khác, bind/start denied | PENDING CI |
| ING-04 | Package opt-in UI và access fail-closed; user Settings/OEM riêng | PENDING CI / manual NOT VERIFIED |
| ING-05 | Synthetic canary log/disk/clipboard/evidence scan, no raw copy | PENDING CI |
| ING-06 | Manifest/Dex/resources và unshrunk release inventory | PENDING CI |
| API37 target runtime | Job API37 thực chạy; thiếu image/runtime là BLOCKED | NOT VERIFIED |
| Máy thật | ≥2 bank và đủ 6 tình huống theo findings | NOT VERIFIED |

Không tự tuyên bố T01 CLOSED. Không tạo tag/release, bump version hoặc signing secrets. R8 dry-run baseline sử dụng khóa dùng một lần theo workflow hiện hữu, không phát hành thật.

## Blocker ngoài allowlist phát hiện trong CI

CI 39588177473 tại HEAD4d51d67: build/lint/test/security/negative controls/R8 và smoke emulator debug/release đạt, nhưng `scripts/t00b_review_evidence.py:198–200` đòi tổng JUnit đúng20. P-01 thêm6 tests nên tổng26 và packager trả `Unexpected JUnit outcome`. File packager không thuộc23 file được phép; không sửa, không bỏ/giấu test, không thay kết quả để pass. CI tổng thể vẫn FAIL tại bước đóng gói; review package/C07 hậu đóng gói chưa có kết quả. Cần Leader duyệt mở allowlist hoặc giao task riêng cập nhật packager kiểm số test có căn cứ, vẫn fail với thiếu/thừa/skipped/errors/failures.

API37 lần đầu fail trước boot vì action dựng tên platform android-37 trong khi SDK đang dùng android-37.0; đang sửa đúng input và kiểm SDK thực tế, không hạ API. API26 cần shell Settings trên emulator sạch do cmd notification chưa có; đây không phải bằng chứng user-grant qua Settings.

## Runtime đã xác minh trước lượt chốt

Tại HEAD `24354085394c034abd4378248005ff0c28e211c5`, workflow T01 run `39593979913` đạt đầy đủ các job API26/29/33/35: callback thật, consent/reveal UI, metadata-only clipboard, revoke/regrant, external UID deny, canary log/disk/evidence và cold process. Grant được thực hiện sau khi instrumentation khởi động, qua mở Settings/quay về app; shell grant không thay xác nhận thao tác cấp quyền bằng người dùng trên máy thật.

API37 boot đúng `android-37.0;google_apis;x86_64`, đủ dung lượng data, nhưng cài test APK gặp `Broken pipe (32)`; log có crash launcher hệ thống trước khi test app chạy. Chưa có runtime PASS API37. Lượt chốt thử renderer `software` và cài APK không streaming; không hạ SDK, không đổi exported/binding permission, không bỏ assertions. Căn cứ cấu hình renderer: https://developer.android.com/studio/run/emulator-acceleration (software mode; swiftshader_indirect đã deprecated). Nếu không có bằng chứng runtime an toàn thì giữ NOT VERIFIED/BLOCKED.
