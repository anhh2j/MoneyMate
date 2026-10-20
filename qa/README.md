# Thư mục `qa/` – AI QA Engineer Agent

| Tệp | Mục đích |
|---|---|
| `AGENT.md` | Chỉ dẫn hệ thống cho phiên AI QA (dán làm system prompt / hướng dẫn dự án) |
| `tools/verify_review_package.py` | Kiểm tra tự động gói review (10 kiểm tra khách quan); `--selftest` để tự kiểm công cụ |
| `templates/` | Mẫu báo cáo QA, mẫu lỗi, mẫu kế hoạch kiểm thử |
| `checklists/CHECKLISTS.md` | Checklist theo loại task |
| `calibration/README.md` | Quy trình hiệu chuẩn QA agent bằng lỗi cài sẵn |
| `tests/` | (tạo khi cần) test độc lập do QA agent viết; dev không được sửa |

## Cách vận hành (PO)
1. Mở **một phiên AI mới** (độc lập với phiên dev và Leader), nạp `AGENT.md` làm chỉ dẫn, đính kèm brief, spec, DOC-SEC, DOC-TEST liên quan.
2. Khi dev nộp gói review, đưa gói cho phiên QA. QA trả `QA_REPORT`.
3. Đưa `QA_REPORT` cho Leader. Leader chấm điểm dựa trên báo cáo và kiểm tra chéo ngẫu nhiên.
4. Dev sửa lỗi QA nêu; QA kiểm thử lại.

## Chạy công cụ
```
python3 qa/tools/verify_review_package.py --selftest
python3 qa/tools/verify_review_package.py <thư-mục-gói> --md reports/auto-checks.md
```
Mã thoát: 0 qua, 1 có FAIL, 2 có BLOCKED. `AUTO-CHECKS-PASS` **không** đồng nghĩa `QA-PASS`.
