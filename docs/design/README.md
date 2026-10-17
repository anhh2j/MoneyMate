# Gói bàn giao thiết kế MoneyMate (G4)

Phiên bản: 1.0.0 · Căn cứ: DOC-UX v1.2.0 · PO đã duyệt G1 (luồng), G2 (wireframe), G3 (prototype) và xác nhận G4 (bàn giao) ngày 16/10/2026.

## Cấu trúc
- `design-tokens.json` – màu (sáng/tối), chữ, khoảng cách, bo góc, kích thước. **Nguồn duy nhất.**
- `flows/` – 8 user flow (F1-F5 thuộc MVP; F6-F8 thuộc Giai đoạn 2).
- `wireframes/` – 14 wireframe (W01-W09, W13 thuộc MVP; W10-W12, W14 thuộc Giai đoạn 2).
- `prototype/moneymate-prototype.html` – prototype click được (F1, F2, F5). Mở bằng trình duyệt.

## Quy tắc cho dev
1. UI phải khớp wireframe và prototype đã duyệt: bố cục, nội dung, cảnh báo, trạng thái. Muốn khác thì ghi đề xuất trong PR, **không tự đổi**.
2. Không hardcode màu, cỡ chữ, khoảng cách. Đọc từ tokens, dựng `ColorScheme`/`Typography`/`Shapes` của Material 3 một lần trong Theme, hỗ trợ sáng/tối theo hệ thống.
3. Bản đồ màu → vai trò Material 3: background, surface, surfaceVariant (thẻ), onSurface, onSurfaceVariant (chữ phụ), primary, onPrimary, outline, error. `success` (thu) và `warningContainer` là vai trò mở rộng, đặt trong CompositionLocal riêng.
4. Số tiền: định dạng vi-VN `25.000 đ`; chi có dấu trừ, thu có dấu cộng và màu `success`; căn phải; chữ số độ rộng đều.
5. Vùng chạm tối thiểu 48dp (nút trong prototype cao khoảng 47px, **bản thật phải đủ 48dp**). Mọi điều khiển có nhãn cho TalkBack. Không dùng màu làm cách duy nhất truyền đạt ý nghĩa. Lề ngang màn hình 16dp (prototype dùng 18px, bản thật theo token).
6. Luôn cài đủ các trạng thái: trống, đang tải, lỗi, ngoại tuyến (Giai đoạn 2), bị khóa.
7. Màn hình có dữ liệu tài chính bật FLAG_SECURE theo mặc định (DOC-SEC mục 4.2).

## Nội dung bắt buộc giữ nguyên (microcopy)
| Chỗ | Nội dung |
|---|---|
| W01 | Không cần nhập tay · Không liên kết tài khoản ngân hàng · Dữ liệu nằm trên điện thoại của bạn |
| W03 | MoneyMate chỉ đọc thông báo của app ngân hàng được hỗ trợ để tự ghi giao dịch. |
| W03 (lưu ý) | Android 13+ cài từ APK? Cần bật “Cho phép cài đặt bị hạn chế” trước. |
| W05 trống | Không có gì cần xác nhận |
| W13 sai PIN | Sai PIN (n/5) · sau 5 lần: khóa tạm thời, thời gian chờ tăng dần |
| Quên PIN | Xác thực bằng khóa màn hình của thiết bị để đặt PIN mới. Nếu không xác thực được, dữ liệu cục bộ sẽ bị xóa. |

## Truy vết
| Màn hình | Task | AC |
|---|---|---|
| W01-W03, W13 | T13, T19 | AC-1, AC-10 |
| W04-W06 | T14 | AC-1..AC-5 |
| W07-W08 | T15 | AC-4 |
| W09 | T13, T19 | AC-9, AC-10 |
