# Checklist QA theo loại task

Mọi mục: ghi PASS / FAIL / NOT-VERIFIED kèm bằng chứng. Áp dụng thêm các điểm riêng của brief.

## A. Build và hạ tầng (T00, T00b)
- [ ] Bản clone sạch build được: `ktlintCheck detekt test assembleDebug` (mã thoát 0, log đầy đủ).
- [ ] Không có test bị xóa/`@Ignore`/skip; số test không giảm so với trước.
- [ ] Không hạ ngưỡng lint/detekt/coverage; baseline detekt vẫn rỗng.
- [ ] Phiên bản thư viện ghim cụ thể (không `+`, `latest`); wrapper có checksum.
- [ ] Merged manifest: không `uses-permission`; `allowBackup=false`; rules loại trừ đủ domain.
- [ ] Dependency report: không Firebase/mạng; module thuần không phụ thuộc Android.
- [ ] Workflow: action bên thứ ba ghim SHA; `permissions` tối thiểu; không secret; `persist-credentials: false` khi không push.
- [ ] Version: một nguồn duy nhất; không `versionName/versionCode` viết cứng; công thức versionCode đúng bảng DOC-VER 3.5; version sai làm build fail.
- [ ] Release: R8 bật; `apksigner verify`; versionName/Code trong APK khớp tag; không keystore/secret trong repo.
- [ ] Diff đúng phạm vi brief; file ngoài danh sách có giải thích trong ADR.

## B. Parser (T04, T05)
- [ ] Mỗi rule có fixture thật; golden test 100% pass; **không có mẫu bịa** (so với danh sách do PO cung cấp).
- [ ] Ca âm tính: OTP, quảng cáo, thông báo không phải giao dịch trả `null`, không tạo giao dịch.
- [ ] Ca biên: số tiền lớn, có phần thập phân, dấu phân cách, nội dung rỗng/dài, Unicode, có dấu/không dấu, nhiều dòng, khoảng trắng thừa.
- [ ] Chiều thu/chi từ dấu `+/-` đúng; không suy diễn khi thiếu dấu.
- [ ] Thời gian: dùng thời điểm nhận khi thiếu trong nội dung; không bị lệch múi giờ.
- [ ] Hiệu năng < 50 ms/notification (đo, ghi số).
- [ ] Rule không bị ReDoS (thử chuỗi dài lặp).

## C. Dedup (T06)
- [ ] Cùng giao dịch từ notif và SMS → 1 bản ghi (AC-2).
- [ ] Khác refCode/accountMask/số tiền → không gộp nhầm.
- [ ] Biên bucket ±2 phút; property test với dữ liệu ngẫu nhiên, thứ tự đảo.

## D. Phân loại (T09–T12)
- [ ] Ưu tiên đúng: user rule → từ điển → classifier; `categorySource` đúng (AC-4).
- [ ] Ngưỡng 0.7: dưới ngưỡng vào NEEDS_REVIEW; sửa danh mục chỉ tạo rule khi người dùng đồng ý (AC-5).
- [ ] Báo cáo accuracy trên tập có nhãn ≥ 300; không rò rỉ tập đánh giá vào huấn luyện.
- [ ] Không gửi dữ liệu ra ngoài (AC-6).

## E. Dữ liệu, mật mã, khóa app (T03, T16, T19, T20)
- [ ] DB mã hóa: không mở được bằng sqlite thường; không plaintext trong file (SEC-01).
- [ ] Khóa bọc Keystore; không khóa/PIN trong log, prefs thô, crash report (SEC-02).
- [ ] Chỉ dùng thư viện mật mã đã duyệt; có test vector; nonce không lặp (SEC-05..07).
- [ ] Khóa app: PIN 6 số; sai 5 lần → khóa tạm tăng dần, bộ đếm bền vững; tự khóa; FLAG_SECURE; quên PIN qua khóa màn hình (AC-10).
- [ ] Xóa dữ liệu xóa sạch DB, RawEvent, khóa, cấu hình (AC-7).
- [ ] Export CSV đúng số bản ghi và định dạng (AC-8).

## F. UI (T13–T15, T19)
- [ ] Khớp wireframe W-xx, tokens, microcopy bắt buộc (DOC-UX, `docs/design`).
- [ ] Đủ trạng thái: trống, tải, lỗi, bị khóa.
- [ ] Vùng chạm ≥ 48 dp; nhãn TalkBack; tương phản ≥ 4.5:1; cỡ chữ lớn; sáng/tối.
- [ ] Xác nhận giao dịch ≤ 2 chạm.
- [ ] **NOT-VERIFIED (cần thiết bị/PO)** cho hiển thị thực tế nếu không có thiết bị.

## G. Giai đoạn 2 – tài khoản và đồng bộ (khi kích hoạt)
- [ ] Firebase khởi tạo lười; không request khi chưa opt-in (AC-11).
- [ ] Cloud chỉ ciphertext; quét emulator (AC-13); Security Rules chặn chéo user (AC-17).
- [ ] Sai passphrase không crash/hỏng dữ liệu (AC-15); xóa tài khoản xóa sạch (AC-16).
- [ ] Hợp nhất HLC, tombstone, đa thiết bị (AC-14).

## H. Thiết bị thật (PO, QA agent chỉ lập kịch bản)
- Checklist DOC-TEST A4: miss rate 7 ngày, kill service theo hãng máy, khóa màn hình, khởi động lại, tiết kiệm pin.
