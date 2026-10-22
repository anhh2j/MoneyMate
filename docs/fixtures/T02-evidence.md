# T02-SYNTHETIC-PACK — Developer evidence

Authorized by Issue #14 comment 6333655803; controlling plan DESIGN-R1, QA design APPROVE. This is implementation evidence, not QA acceptance. Baseline main: `4570e4e3cece382e5a69fa277046628c05f0aa07`. Separate branch feature/T02-fixtures. PR #10 not modified or cherry-picked.

## Content and privacy status

15 pairs (5 BIDV, 5 MSB, 5 MB; 2 noise each), 72 declarative scenarios covering FX-01..24 per bank. `corpusClass=SYNTHETIC_CONTRACT`; no real-bank golden. Current status: all 15 seeds have PO and QA privacy APPROVED, recorded by REVIEW_PO_QA_T02_PRIVACY_SIGNOFF_A below; acceptedCorpus is computed by the unchanged validator for this synthetic contract only. This is not permission for PR Ready/merge or real-bank use. No numeric/time exceptions requested or approved. Three missing-amount oracles unresolved; numeric stress above seven digits remains BLOCKED pending exact value approval. Existing small numbers and fixed ISO times pass both scanners without exceptions. Body `.txt` never receives an exception. Hashes are colon-delimited SHA-256, still recomputable over original bytes.

## F1–F8 trace

| Finding | Implementation | Evidence |
| --- | --- | --- |
| F1 | README first warning + corpus flag, loader metadata | validator + NC-10 + FixtureLoaderTest |
| F2 | schema source scopes crosschecked against code, MSB IN/all MB synthetic_contract | NC-10 source-scope subcases |
| F3 | Descriptive filenames retain approved naming exception | 41-path diff |
| F4 | Original, decoded, Unicode/zero-width/separator normalized detection | NC-07/08 per-separator subcases |
| F5 | No text exceptions; safe grouped body amounts; QA C09 unchanged | baseline empty C09 NA, working corpus C09 PASS, QA tool blob |
| F6 | manifest order; double load bytes, LF/CRLF/NFC/NFD | JUnit FixtureLoaderTest, deterministic validator replay |
| F7 | header/package/title/observedPackage consistency and unresolved-golden rejection | NC-03/11 |
| F8 | namespace/SYNTHETIC_ content UTF-8/UTF-16 scans and ZIP entry checks | negative ZIP canaries; both real APK scans in CI |

FixtureLoader extracts only restricted safe manifest string fields after independent Python strict JSON/schema validation. It does not decode expected JSON into a transaction, execute scenarios, parse bank notifications, or add a production dependency. Sharing the loader with dedup/Simulator is outside this task.

## Commands and artifacts

Local: `python3 scripts/t02_fixture_checks.py --report build/reports/t02/fixture-validation.json`; `python3 -m unittest discover -s scripts/tests -p 'test_t02_fixture_checks.py' -v`; ktlint formatter/checker on the two new Kotlin files and parser Gradle resource mapping; `git diff --check`. CI runs the full baseline gates unchanged plus these commands and scans both generated debug/R8 APKs. Reports: `build/reports/t02/fixture-validation.json`, `negative-controls.json`, `apk-isolation.json` and logs in test-lint-dod-reports. JUnit XML is in parser build/test-results/test. Original hashes compared after every negative mutation; no invalid fixture is uploaded. Canary negative controls are temporary synthetic data only. Legacy QA tool emits ResourceWarning for its existing unclosed file reads when Python warnings are enabled; qa/ is unchanged.

## T02-P01 — sửa accounting packager theo ngoại lệ file thứ42

Leader đã duyệt tại Issue #14, comment 6334175682: tổng allowlist 42 file; đường dẫn bổ sung duy nhất là `scripts/t00b_review_evidence.py`. Bản gốc ở main ghim 20 tests; CI 39731261384 đã có 22 tests sạch nhưng dừng trước source-review-package/C07. Đây là lỗi lịch sử được giữ nguyên trong evidence, không chuyển thành PASS.

Packager hiện trích chính xác identity từ source snapshot đã lấy bằng Git HEAD: module + Gradle task + variant + class + method, kèm sourceSet/path/SHA-256. JUnit XML được đối chiếu toàn bộ theo vị trí module/build/test-results/task, tên suite/file/class/method, summary và outcome; không ghim 22, không dùng ngưỡng >=20. Source set/annotation không hỗ trợ, source hoặc XML trùng/thiếu/thừa, sai module/task/variant/class/method, XML hỏng, failure/error/skip đều bị từ chối. Chỉ hỗ trợ JUnit4 Kotlin thường đang được pipeline thực chạy; dạng mới không suy diễn mà fail closed.

`review/junit-inventory.json` ghi HEAD/tree, inventory source/variant, từng XML path/hash và kết quả khớp. Kiểm source tree, checksum, APK/emulator và các cổng security/C07/C09 giữ nguyên. Không cherry-pick hoặc sửa PR #10, không sửa qa/.

Test bổ sung nằm trong file selftest Dev đã được phép: hồi quy 20 tests tại baseline và 22 tests T02, 13 mutation âm tính, cùng probe tạm cho Android testDebug hợp nhất với test base; không sửa source/test thật để làm probe. Các ca kiểm này xuất `build/reports/t02/packager-negative-controls.json`. Local đã đối chiếu thêm 13 XML thật của CI trước: 22/22 identity khớp, không failure/error/skip. CI mới phải chạy đầy đủ để xác nhận đóng gói/C07; trước khi có kết quả thì vẫn NOT VERIFIED. Nguồn synthetic và 15 signoff vẫn PENDING, T02-REAL-CORPUS vẫn BLOCKED. Tất cả bình luận bàn giao mới trên GitHub dùng tiếng Việt theo yêu cầu PO.

## CONTENT PLAN — lượt chỉnh nội dung hợp nhất ngày 22/10/2026

Theo quyết định Leader tại Issue #14, bình luận 6335484558; tham chiếu các bổ sung UX PO trước đó. Đây là **PO_UX_REFERENCE_UNVERIFIED**: lời mô tả UX do PO cung cấp, không phải metadata/notification thu trực tiếp trên Android, không nâng provenance hay layout verification.

| Nhóm | Xử lý trong lượt này |
| --- | --- |
| BIDV IN/OUT | Đã khớp bốn nhãn; giữ nguyên byte cả input và expected |
| BIDV marketing | Title chương trình giả lập có emoji; body ưu đãi QR Pay/BIDV SmartBanking giả lập, parse=false |
| BIDV missing/notice | Giữ nguyên synthetic contract, byte không đổi |
| MSB IN | Chuyển sang bốn dòng: số tiền có dấu, tài khoản XXX, So du, Noi dung; giá trị synthetic cũ vẫn khớp expected |
| MSB OUT | Đã khớp bốn dòng; giữ nguyên byte, không đổi tiền/số dư/memo để tạo diff không cần thiết |
| MSB missing/notice/promotion | Giữ nguyên byte, synthetic contract |
| MB IN/OUT | Title biến động số dư; body TK XXX, dấu ±, VND, giờ/ngày giả lập, GD, SD; expected khớp amount/direction/balance/description |
| MB missing amount | Cùng UX MB nhưng phần số tiền rỗng, parse=null và T04_MISSING_AMOUNT giữ nguyên |
| MB Digital OTP push | Title xác thực giao dịch; body chỉ có SYNTHETIC_REQUEST_A, không mã OTP hay mã giao dịch thật; parse=false |
| MB marketing | Title emoji/program giả lập; body ưu đãi điện/nước giả lập, parse=false |

Delta dữ liệu thực tế: **7 input .txt thay đổi** (5 MB, BIDV marketing, MSB IN); 8 input .txt còn lại và **toàn bộ 15 expected JSON giữ nguyên byte** — 23/30 file dữ liệu không đổi so với HEAD c5a67c2. Mẫu MSB OUT nằm trong phạm vi rà soát nhưng đã khớp nên giữ byte theo yêu cầu tránh sửa không cần thiết. Đồng bộ đúng 7 inputSha256; provenance/approval/envelope/extras pointers trong manifest giữ nguyên. Không sửa schema, không thêm field contract, không sửa packager/JVM loader/CI hoặc file ngoài allowlist 42.

Validator chỉ thêm kiểm nội dung corpus test: 6 giao dịch parse=true với sign/amount/balance/memo khớp layout đã duyệt; 6 noise parse=false; 3 missing parse=null/T04_MISSING_AMOUNT; title/body qua txtTitle/txtBody phải đúng ngữ cảnh MB/marketing. Đây không phải engine/parser production hoặc xác minh format bank thật. Kiểm privacy trước content invariants để sentinel vẫn bị từ chối bởi đúng rule privacy. Negative controls bổ sung cho sai amount/balance/memo/sign/title, missing bị điền lại tiền, marketing bị gán transaction và OTP push chứa sentinel số; tất cả mutation chỉ trên bản sao tạm, manifest hash được cập nhật để không thể chỉ dựa vào hash stale.

Local sau lượt content: validator/C09 PASS; **22 Python selftests PASS**, 60 subcase NC fixture; 16 ca packager regression giữ nguyên. Report fixture-validation.json bổ sung contentCounts và contentInventory cho 15 mẫu. Các số CI/JUnit/C07/C09/APK và artifact digests tại HEAD mới được bàn giao trên Issue #14 sau khi chạy thật, không lấy kết quả HEAD c5a67c2 thay thế.

Tại HEAD content 547bc6c trước quyết định PO bên dưới: 15/15 PO/QA privacy signoff còn PENDING, acceptedCorpus=false. Ba seed null, 18 scenario UNRESOLVED, large numeric stress và T02-REAL-CORPUS giữ BLOCKED theo quyết định cũ. PR #15 Draft; Developer → QA độc lập (không sửa code) → Leader → PO; không Ready/merge/tag/release.

## REVIEW_PO_T02_PRIVACY_SIGNOFF_A

Lịch sử tại HEAD `78a61bfd88c7ffbf96b5f5cffbbc10db52c9afd5`: mã `REVIEW_PO_T02_PRIVACY_SIGNOFF_A` trong `approval.evidenceRef` của manifest ánh xạ duy nhất tới [Quyết định PO — T02 PRIVACY SIGNOFF 15/15 và Leader Assignment](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6336501800), ngày 22/10/2026. Phạm vi chỉ **SYNTHETIC TEST-ONLY**.

HEAD nguồn được PO ký: `547bc6c05d3655fd8d02635e038d9f0292b75118`; tree nguồn: `9cd53637e7767ffca7d662582abb125c7d1498e7`. Mã tham chiếu quyết định đã tồn tại và HEAD nguồn bất biến, không tham chiếu hash commit đang ghi nhận nên không tạo vòng phụ thuộc. Đã báo phương án trước sửa tại [Issue #14](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6336543800) và [bổ sung selftest](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6336550183).

Developer ghi đúng `poPrivacy=APPROVED` cho 15 seed bên dưới; `qaPrivacy=PENDING` giữ nguyên. Evidence này **chỉ là PO privacy signoff**, không bao gồm QA privacy signoff, không xác minh Android package/layout, real-bank golden hay oracle. `acceptedCorpus=false` theo validator hiện hữu; không thay gate, không thêm privacy exception. `corpusClass=SYNTHETIC_CONTRACT`, `eligibleForRealBankGolden=false`, provenance/formatVerification/envelope và cả 30 file dữ liệu giữ nguyên so với HEAD nguồn. Ba null-oracle, 18 scenario UNRESOLVED, FX-07 numeric stress và real-corpus tiếp tục BLOCKED theo phạm vi đã ghi nhận; PR #15 OPEN/Draft, chưa Ready/merge/tag/release.

Bảng dưới gắn từng seed được PO liệt kê với SHA-256 byte gốc tại HEAD nguồn. Hash trong manifest giữ nguyên định dạng nhóm có dấu hai chấm; bảng thể hiện SHA-256 chuẩn để đối chiếu Git blob.

| Seed | Input SHA-256 tại HEAD nguồn | Expected SHA-256 tại HEAD nguồn |
| --- | --- | --- |
| `bidv_txn_in_01` | `d7d2e1dbbd07c6a6e0248561f4368c8ad572683e3da99165899eff4c8773da46` | `7721ffd274931e6d83deedf1105eef7f276cf11ca8f8317052c977132bab9cdf` |
| `bidv_txn_out_01` | `451c2200385a7541fff0a0dfc59e1176b5fc1d0a6f8cb23d5dd91cedec84380d` | `a7be11dc61708f9308a58596c67841196f55e3614900b5053cc3f13eb5a370bc` |
| `bidv_invalid_missing_amount_01` | `40033a52ce1b8094c8a949e73e573888b114fdce15399ca3df558ca7c9727d24` | `07a2187e8b8c00f799fb27c838cd63beb1eab25b1778027795bb337d1895fb9f` |
| `bidv_noise_notice_01` | `a2a2abbd4e6f22dd705741b7d96872030a67698851a0e8274d12fe30381513c4` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `bidv_noise_promotion_01` | `7b9f0a588af3842c32f4966de82cd30accc5013f68d2ea761e11a088a560f9c9` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `msb_txn_in_01` | `f62da300b938992245a299cac5f2df999a283c6153d63b7d63ffb432a7a14c38` | `7721ffd274931e6d83deedf1105eef7f276cf11ca8f8317052c977132bab9cdf` |
| `msb_txn_out_01` | `d1be2005d305a529d8255846756b572f88e06f6e4fef8951c2dd8c6689ac99ee` | `a7be11dc61708f9308a58596c67841196f55e3614900b5053cc3f13eb5a370bc` |
| `msb_invalid_missing_amount_01` | `e97d645653af117239dac5f16f2a00e2498efc15a5a8dfe9c4d9559708bbd1fe` | `07a2187e8b8c00f799fb27c838cd63beb1eab25b1778027795bb337d1895fb9f` |
| `msb_noise_notice_01` | `7390a0f088e508b565ce2a38ec4ea84cd8f2dc7d635e1613e2e4c6cb1b8b0d2a` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `msb_noise_promotion_01` | `e34c9d4910b6a6c3f0f164fbfc320c049e98605f5c7a7b97c180d0ce3506534a` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `mb_txn_in_01` | `0cac6f130deb402bd5604a7ae976ff61a06f0dfaaa1c649c34619afbda087b95` | `7721ffd274931e6d83deedf1105eef7f276cf11ca8f8317052c977132bab9cdf` |
| `mb_txn_out_01` | `3cfac7ccbf084200b939ed18bcab6ad3a014bc661a0436a1a167fe3dfff84b9c` | `a7be11dc61708f9308a58596c67841196f55e3614900b5053cc3f13eb5a370bc` |
| `mb_invalid_missing_amount_01` | `ff2fbe7eb288c46cbd5cdff7b1ed0d69a8576f2ddcc47e0a97fbdf0cdccce422` | `07a2187e8b8c00f799fb27c838cd63beb1eab25b1778027795bb337d1895fb9f` |
| `mb_noise_notice_01` | `27f2906b0939ceac7c78232a24b69f07909a0a178c6b8f1c8da4d90e55453475` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `mb_noise_promotion_01` | `174fce691eeb4e16be886b68f4fb246bedc742cf3550d88b2efa4def864ce988` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |

Chuyển QA độc lập kiểm từng approval/evidence/hash và regression tại HEAD ghi nhận mới; QA tự quyết qaPrivacy, không sửa code, không ký thay PO. Sau đó Leader review và trình PO quyết định Ready/merge riêng. Kết quả CI, C07/C09, APK isolation và artifact của HEAD mới sẽ nộp trên Issue #14/PR #15, không kế thừa kết quả HEAD nguồn.

## REVIEW_PO_QA_T02_PRIVACY_SIGNOFF_A

Mã hợp nhất `REVIEW_PO_QA_T02_PRIVACY_SIGNOFF_A` hiện dùng trong `approval.evidenceRef` của đúng 15 seed ánh xạ tới **cả hai** quyết định độc lập dưới đây. Mã PO-only trong mục trước được giữ làm lịch sử, không bị thay bằng bằng chứng chỉ của QA.

| Vai trò | Quyết định privacy | HEAD nguồn được duyệt/kiểm chứng | Tree nguồn |
| --- | --- | --- | --- |
| PO | [PO Privacy Signoff 15/15](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6336501800) | `547bc6c05d3655fd8d02635e038d9f0292b75118` | `9cd53637e7767ffca7d662582abb125c7d1498e7` |
| QA độc lập | [QA Privacy APPROVED 15/15, mục 5](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6337179703) | `78a61bfd88c7ffbf96b5f5cffbbc10db52c9afd5` | `43c00089012b144ebf67a4a36f3ffd3a15558f5e` |

Leader giao ghi nhận tại [6337259482](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6337259482); Developer đã [báo phương án trước sửa](https://github.com/anhh2j/MoneyMate/issues/14#issuecomment-6337314630). Các tham chiếu trỏ quyết định/HEAD đã tồn tại, không trỏ hash commit đang tạo.

Cả hai quyết định chỉ cho privacy của nội dung **SYNTHETIC TEST-ONLY**, cùng 15 seed và cặp hash sau. Tất cả 30 input/expected giữ nguyên byte giữa HEAD PO, HEAD QA và bản ghi hiện tại; bảng này đồng thời ràng buộc cả hai nguồn. `poPrivacy=APPROVED` được giữ, `qaPrivacy=APPROVED` ghi từ quyết định QA đã có; Developer không tự cấp approval.

| Seed | Input SHA-256 tại cả hai HEAD nguồn | Expected SHA-256 tại cả hai HEAD nguồn |
| --- | --- | --- |
| `bidv_txn_in_01` | `d7d2e1dbbd07c6a6e0248561f4368c8ad572683e3da99165899eff4c8773da46` | `7721ffd274931e6d83deedf1105eef7f276cf11ca8f8317052c977132bab9cdf` |
| `bidv_txn_out_01` | `451c2200385a7541fff0a0dfc59e1176b5fc1d0a6f8cb23d5dd91cedec84380d` | `a7be11dc61708f9308a58596c67841196f55e3614900b5053cc3f13eb5a370bc` |
| `bidv_invalid_missing_amount_01` | `40033a52ce1b8094c8a949e73e573888b114fdce15399ca3df558ca7c9727d24` | `07a2187e8b8c00f799fb27c838cd63beb1eab25b1778027795bb337d1895fb9f` |
| `bidv_noise_notice_01` | `a2a2abbd4e6f22dd705741b7d96872030a67698851a0e8274d12fe30381513c4` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `bidv_noise_promotion_01` | `7b9f0a588af3842c32f4966de82cd30accc5013f68d2ea761e11a088a560f9c9` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `msb_txn_in_01` | `f62da300b938992245a299cac5f2df999a283c6153d63b7d63ffb432a7a14c38` | `7721ffd274931e6d83deedf1105eef7f276cf11ca8f8317052c977132bab9cdf` |
| `msb_txn_out_01` | `d1be2005d305a529d8255846756b572f88e06f6e4fef8951c2dd8c6689ac99ee` | `a7be11dc61708f9308a58596c67841196f55e3614900b5053cc3f13eb5a370bc` |
| `msb_invalid_missing_amount_01` | `e97d645653af117239dac5f16f2a00e2498efc15a5a8dfe9c4d9559708bbd1fe` | `07a2187e8b8c00f799fb27c838cd63beb1eab25b1778027795bb337d1895fb9f` |
| `msb_noise_notice_01` | `7390a0f088e508b565ce2a38ec4ea84cd8f2dc7d635e1613e2e4c6cb1b8b0d2a` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `msb_noise_promotion_01` | `e34c9d4910b6a6c3f0f164fbfc320c049e98605f5c7a7b97c180d0ce3506534a` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `mb_txn_in_01` | `0cac6f130deb402bd5604a7ae976ff61a06f0dfaaa1c649c34619afbda087b95` | `7721ffd274931e6d83deedf1105eef7f276cf11ca8f8317052c977132bab9cdf` |
| `mb_txn_out_01` | `3cfac7ccbf084200b939ed18bcab6ad3a014bc661a0436a1a167fe3dfff84b9c` | `a7be11dc61708f9308a58596c67841196f55e3614900b5053cc3f13eb5a370bc` |
| `mb_invalid_missing_amount_01` | `ff2fbe7eb288c46cbd5cdff7b1ed0d69a8576f2ddcc47e0a97fbdf0cdccce422` | `07a2187e8b8c00f799fb27c838cd63beb1eab25b1778027795bb337d1895fb9f` |
| `mb_noise_notice_01` | `27f2906b0939ceac7c78232a24b69f07909a0a178c6b8f1c8da4d90e55453475` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |
| `mb_noise_promotion_01` | `174fce691eeb4e16be886b68f4fb246bedc742cf3550d88b2efa4def864ce988` | `3f30c2abac24eb9779eebe3b1476e830f8f2eec69672fda9344ba9e42ff626be` |

`acceptedCorpus` do validator gốc tính từ đủ hai approval cho mọi seed; không thêm field/hardcode trạng thái trong manifest. `--require-approved` được chạy để kiểm chứng gate hiện hữu. Giá trị true chỉ phản ánh acceptance privacy của synthetic contract, **không** đóng 3 null-oracle, 18 scenario UNRESOLVED, FX-07 numeric stress BLOCKED hay T02-REAL-CORPUS BLOCKED. Không xác minh Android package/layout/real-bank golden, không cho PR Ready/merge/tag/release. Provenance/formatVerification/envelope/oracle/flags, `corpusClass=SYNTHETIC_CONTRACT`, `eligibleForRealBankGolden=false` giữ nguyên.

Validator hiện hữu chỉ kiểm định dạng REVIEW_ của evidenceRef; nó không xác thực nội dung quyết định GitHub hay mọi mã giả. Regression đối chiếu manifest chính xác với hai quyết định và source hash; QA hậu kiểm độc lập xác minh tính trung thực. Các ca thiếu evidence/URL thô/thiếu PO hoặc QA approval tiếp tục bị kiểm, không nới gate hay thêm exception. Sau CI mới, chuyển QA hậu kiểm bản ghi tại HEAD mới (không sửa code) → Leader review → trình PO quyết định Ready/merge riêng. Kết quả và artifact được nộp tại Issue #14/PR #15, không kế thừa CI HEAD trước.

## Governance and handover

Full HEAD, PR/run links, job/artifact IDs/digests and final outcomes will be recorded on Issue #14 and the Draft PR at the exact built SHA after CI. Developer records the explicit PO and independent QA decisions referenced above, without granting approvals or writing a new QA verdict. Both privacy approvals are recorded for the synthetic contract; the unchanged validator computes acceptance. QA must independently verify this recording at its new HEAD before Leader review and a separate PO Ready/merge decision. T02-REAL-CORPUS BLOCKED, T01 OPEN, B2 API37 ENV-FAIL and B3 PENDING PO DEVICE unchanged. No production parser/dedup/DB/capture, qa/, Approved DOCX, version, dependencies, permissions or release settings changed.
