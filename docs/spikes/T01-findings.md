# T01 — Findings (PO điền, không chứa nội dung notification)

Baseline `4570e4e3cece382e5a69fa277046628c05f0aa07`. P-01 chỉ debug, RAM; chỉ Copy metadata. Raw chỉ xem sau xác nhận, không xuất/chia sẻ/lưu. Không dùng metadata từ emulator làm xác minh package ngân hàng thật.

## Máy thật — NOT VERIFIED / chờ PO

- Model/OEM/API/build: chưa cung cấp.
- Ngày/giờ và người chạy: chưa cung cấp.
- App ngân hàng thật và package PO xác minh: chưa có.
- Layout: ghi field nào có/không và quan hệ title/text/bigText/subText, không dán nội dung thật.

| Tình huống | Bank/package | Quyền/connected/session trước-sau | Callback metadata | Layout field | Kết quả | PO xác nhận |
| --- | --- | --- | --- | --- | --- | --- |
| App đang mở | Pending | Pending | Pending | Pending | NOT VERIFIED | Pending |
| Vuốt recent | Pending | Pending | Pending | Không giữ raw nền | NOT VERIFIED | Pending |
| Khóa máy 1 giờ | Pending | Pending | Pending | Không giữ raw nền | NOT VERIFIED | Pending |
| Tiết kiệm pin | Pending | Pending | Pending | Không giữ raw nền | NOT VERIFIED | Pending |
| Khởi động lại | Pending | Pending | Pending | RAM mất, IDLE | NOT VERIFIED | Pending |
| Tắt/bật quyền | Pending | Pending | Pending | Consent phải cấp lại | NOT VERIFIED | Pending |

Force-stop kiểm riêng, không đánh đồng với vuốt recent. Discovery tối đa 2 giờ; payload chỉ foreground 5 phút. Phiên mất sau reboot/process death là hành vi dự kiến, không tự import active notifications/replay.

## Emulator — chưa có kết quả khi tạo template

Synthetic publisher `com.app.moneymate.test` là test APK riêng, không phải ngân hàng và không được cài trên máy có ngân hàng thật. API26/29/33/35/37 có báo cáo riêng ở artifact workflow T01. Shell-grant phục vụ system callback không chứng minh user Settings grant hoặc OEM behavior.

T01 chỉ đóng khi PO xác nhận ≥2 ngân hàng thật và đủ sáu tình huống, cùng QA/Leader review. Emulator PASS không thay thế điều kiện này.
