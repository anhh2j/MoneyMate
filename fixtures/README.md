# SYNTHETIC_CONTRACT

**Không case nào trong pack này là format ngân hàng đã xác minh; không dùng để tuyên bố hỗ trợ ngân hàng thật hoặc đạt DoD real-corpus.**

15 synthetic pairs, five per bank, including two noise cases. All source values have been replaced. Namespace `com.example.moneymate.fixture` and token prefix `SYNTHETIC_` are test markers only. MSB IN and every MB case are synthetic_contract. MSB OUT / BIDV IN and OUT preserve only source-scoped labels, never observed extras layout or bank identity.

PO privacy and independent QA signoffs are PENDING per seed. Validation success does not imply accepted content. Run `python3 scripts/t02_fixture_checks.py`; `--require-approved` blocks until individual safe evidence-backed approvals and exact exceptions are reviewed. No numeric/time exceptions are requested in this pack. FX-07 large/overflow stress literal is BLOCKED pending separately reviewed exact values; no raw bank content is needed.

Files are paired text/expected JSON. Text has package/title headers, delimiter, and unmodified body bytes. SHA-256 values use colon-separated hex groups to avoid false digit runs without exempting text. Manifest determines order. Null parse oracle requires decisionId and is never golden. Scenarios are declarative, not executed or counted as independent bank samples. No JSON decoder or production bank parser is provided.

Every input and literal must pass original and decoded/Unicode/zero-width/separator-normalized privacy checks. Text has no exceptions; amounts are grouped and at most seven digits after normalization. Exceptions require exact JSON pointer/value/reviewer approval; none are currently present. C09 remains unchanged. Only approved synthetic content belongs in this directory; never import raw notifications, real suffixes, names, memos, OTPs, credentials, mappings, or raw hashes. Do not copy raw from T01. Negative controls run only on temporary copies. Real-corpus DoD remains BLOCKED.
