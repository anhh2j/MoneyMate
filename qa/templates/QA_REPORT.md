# Báo cáo QA – <Task> – <yyyy-mm-dd>

- **Gói/commit đã kiểm:** <tên gói, SHA-256 của gói, commit>
- **Căn cứ:** <brief, spec, DoD/AC áp dụng, phiên bản tài liệu>
- **Phán quyết:** QA-PASS | QA-PASS-WITH-NOTES | QA-FAIL | QA-BLOCKED
- **Môi trường chạy:** <OS, JDK, Gradle, công cụ; có hay không thiết bị/emulator>

## 1. Tóm tắt (≤ 5 dòng)

## 2. Kết quả kiểm tra tự động
<dán bảng từ verify_review_package.py>

## 3. Đối chiếu DoD/AC
| ID | Yêu cầu | Cách kiểm | Kết quả | Nhãn nguồn | Bằng chứng |
|---|---|---|---|---|---|
| | | | PASS / FAIL / DEFERRED / NOT-VERIFIED | VERIFIED / REPORTED | lệnh + trích log / file:dòng |

## 4. Lỗi
| ID | Mức | Tiêu đề | Trạng thái |
|---|---|---|---|

## 5. Rà soát phạm vi và bảo mật
- Phạm vi (diff so với file được phép):
- Quyền, dependency, secret, log:
- SEC-xx liên quan:

## 6. Test độc lập đã viết (qa/tests/)
<danh sách, cách chạy, kết quả>

## 7. Chưa kiểm được và lý do
<cần thiết bị, cần GitHub/CI, thiếu mẫu dữ liệu, ...>

## 8. Đề xuất cho Leader
<điểm cần phân xử, rủi ro, gợi ý chấm điểm các tiêu chí khách quan>
