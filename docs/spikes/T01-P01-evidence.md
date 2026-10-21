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
