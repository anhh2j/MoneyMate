# Quy tắc chung cho AI dev

Nguồn: DOC-BRIEF-M0 v1.2.1, mục 2.

Chỉ làm đúng phạm vi trong brief. Thấy việc cần làm thêm thì ghi vào mục “Đề xuất” trong PR, không tự làm.

Chỉ sửa các file được liệt kê. Cần sửa file ngoài danh sách thì dừng và hỏi.

Không bịa dữ liệu hay format ngân hàng. Thiếu thông tin thì báo BLOCKER và dừng phần đó.

Không xóa, skip, hoặc làm yếu test để pass. Không hạ ngưỡng lint/coverage.

Không ghi PII vào log, code, test, fixture. Không hardcode secret hoặc keystore.

Không dùng phiên bản thư viện động (dấu +, latest). Dùng bản ổn định mới nhất tại thời điểm làm và ghi cụ thể vào version catalog.

Không đổi version, không tạo tag, không ký/phát hành release. Chỉ đề xuất mức version trong PR.

Commit theo Conventional Commits; tiêu đề PR cũng theo định dạng đó. PR mô tả: Task ID, AC liên quan, đã làm gì, cách kiểm tra, điều chưa làm, BLOCKER nếu có.

Trước khi báo xong: tự chạy toàn bộ lệnh kiểm tra trong DoD và dán kết quả vào PR. Không tự tuyên bố “xong” khi CI chưa xanh.
