# Plan: 2026-11-18-guardrail-unaccented-scope

## Phân công

### S-01 — Thu gọn `check_scope` thành danh sách chặn, so khớp hai lượt có dấu/không dấu

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-01`, `AC-02`, `AC-03`, `AC-04`.
- Việc cần làm:
  1. `scope.py`: bỏ bước so khớp `DOMAIN_TERMS` và nhánh câu nối tiếp; câu không khớp mẫu chặn trả `ScopeDecision(True, "passed")`. Bỏ tham số `history` (chỉ dùng cho câu nối tiếp) và sửa chỗ gọi `rag_chain.py:158`.
  2. `patterns.py`: xóa `DOMAIN_TERMS`, `FOLLOW_UP_PATTERNS`.
  3. `normalization.py` + `patterns.py`: so khớp hai lượt (review R-01).
     - Thêm hàm bỏ dấu: NFD → bỏ ký tự loại `Mn` → `đ/Đ → d` → NFC.
     - Lượt 1: mẫu gốc trên văn bản đã chuẩn hóa như hiện tại (`normalize_text` cho `BLOCKED_PATTERNS`, `security_normalize` cho `PROMPT_INJECTION_PATTERNS`), luôn chạy.
     - Lượt 2: bộ mẫu không dấu trên văn bản đã bỏ dấu, chỉ chạy khi văn bản không có dấu (bỏ dấu không làm văn bản thay đổi).
     - Bộ mẫu không dấu sinh từ mẫu gốc lúc nạp module (bỏ dấu + biên dịch một lần). Loại các nhánh mà dạng không dấu trùng từ thông dụng. Danh sách ban đầu:
       - `hãy là` → `hay la` (= "hoặc là"): bỏ khỏi nhóm động từ của mẫu giả vai trò.
       - `quên đi` → `quen di` (= "quen làm gì"): bỏ khỏi nhóm động từ của mẫu `bỏ qua … hướng dẫn`. Vẫn còn `bo qua`, `phot lo`, `ghi de`, `vo hieu hoa`, `khong tuan theo`.
       - `làm` + `mã` → `lam ma` (= "làm mà"): bỏ `làm` khỏi nhóm động từ của mẫu `code_generation` thứ nhất.
       - `\bdan\b` → khớp `dân`, `hướng dẫn`: chỉ giữ `dan mode` ở nhóm thứ hai của mẫu giả vai trò.
     - Được bổ sung nhánh vào danh sách loại nếu phát hiện va chạm mới. Mỗi nhánh bị loại ghi lý do trong `implementation.md`. Thứ tự bỏ dấu và đổi leetspeak trong `security_normalize` không được phá mẫu hiện có.
  4. `security.py` / `history.py`: `contains_prompt_injection` (dùng cho lịch sử và chunk tài liệu) dùng cùng cơ chế hai lượt.
  5. `patterns.py`: thắt chặt mẫu `code_generation` thứ nhất để `tuyển sinh chương trình` không khớp, ví dụ bỏ `sinh` khỏi nhóm động từ hoặc thêm `(?<!tuyển )`/`(?<!tuyen )` (R-02). Câu tấn công trong test hiện có vẫn bị chặn với cùng `reason`.
  6. Rà va chạm (AC-03):
     - Chạy toàn bộ câu trong 3 fixture (có dấu và bỏ dấu) qua danh sách chặn; không câu nào được bị bắt.
     - Chạy bộ câu đối chứng trong AC-03 ở cả hai dạng; tất cả phải `passed`.
     - Đếm số chunk bị `contains_prompt_injection` loại trước/sau khi sửa (bảng `chunks` nếu DB chạy; nếu không, các đoạn trong `backend/storage/converted/*.md`); số này phải không đổi.

     Script đo đặt ở scratchpad; kết quả ghi vào V-03.
  7. (Không bắt buộc, R-03) Thắt chặt nhóm thứ hai của mẫu `bỏ qua … hướng dẫn|…|yêu cầu|quy tắc`: ví dụ `yêu cầu`/`quy tắc` phải đi kèm `trước`/`trên`/`hệ thống`. Mục tiêu là `Nếu bỏ qua kỳ thi thì có được thi lại theo yêu cầu không?` (hiện bị chặn `prompt_injection`) được `passed`. Nếu không làm, ghi `deferred` trong `review.md` kèm lý do.
  8. (Không bắt buộc, R-08) Sửa nhánh `(?:\]|>|\s*:)` của mẫu giả vai trò: hiện không bao giờ khớp vì `security_normalize` thay `:` bằng khoảng trắng. Có thể giữ `:` trong `security_normalize` hoặc đổi nhánh; thêm test `### system: …`. Nếu không làm, ghi `deferred`.
  9. Test:
     - `test_guardrails.py`: bỏ/sửa test dựa trên lọc từ khóa (`test_guardrail_blocks_unrelated_general_question` → kỳ vọng `passed`; bỏ `test_guardrail_allows_domain_follow_up_from_history`), ghi lý do trong `implementation.md`.
     - `test_guardrails.py`: `test_guardrail_does_not_allow_code_request_inside_domain_conversation` (dòng 35-38) chỉ bỏ đối số `history`, giữ kỳ vọng.
     - Thêm test biến thể không dấu (AC-02), bộ câu đối chứng (AC-03), câu `tuyển sinh chương trình` (R-02) và test chạy fixture.
     - Sửa `test_no_answer_set.py::test_most_cases_pass_the_scope_guardrail` và `test_rag_chain.py:197` (`ptit_domain` → `passed`).
- Phạm vi file được sửa: `backend/app/guardrails/*.py`, `backend/app/generation/rag_chain.py` (chỉ chỗ gọi `check_scope`), `backend/tests/test_guardrails.py`, `backend/tests/test_no_answer_set.py`, `backend/tests/test_rag_chain.py`, test mới trong `backend/tests/`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: code + test; `pytest backend/tests` đạt; danh sách nhánh bị loại khỏi bộ mẫu không dấu và số chunk trước/sau trong `implementation.md`.
- Người nhận: `agent-backend` (S-02, S-03).

### S-02 — Cập nhật nhãn giao diện

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-06`.
- Việc cần làm:
  - `ReasoningPanel.jsx:9`: đổi nhãn bước `guardrail` ("Kiểm tra phạm vi câu hỏi" → ví dụ "Kiểm tra an toàn câu hỏi").
  - `ReasoningPanel.jsx:21`: đổi dòng tóm tắt `Ngoài phạm vi`/`Trong phạm vi` (ví dụ "Bị chặn"/"Hợp lệ").
  - `ChatView.jsx:68`: kiểm tra; "Đang kiểm tra câu hỏi..." có thể giữ.
  - Nhãn công tắc `scopeEnabled` trong `configDraft.js:99` và `ConfigView.jsx:750` ("Kiểm soát phạm vi PTIT" → ví dụ "Chặn yêu cầu không an toàn"), kèm mô tả ngắn nếu có.
  - Nếu UI hiển thị `reason`, thêm/sửa nhãn cho `passed` và bỏ nhãn cho reason đã xóa.
  - Cập nhật test frontend có chuỗi nhãn, ít nhất `ConfigView.gate.test.jsx:327` (`Kiểm soát phạm vi PTIT Bật→Tắt`).
- Phạm vi file được sửa: `frontend/src/components/ReasoningPanel.jsx`, `frontend/src/ChatView.jsx`, `frontend/src/lib/configDraft.js`, `frontend/src/ConfigView.jsx`, `frontend/src/ConfigView.gate.test.jsx`, các file `*.test.jsx`/`*.test.js` liên quan khác.
- Phụ thuộc: S-01 (chốt tập `reason`).
- Đầu ra/bàn giao: `npm test` trong `frontend/` đạt; `grep "phạm vi" frontend/src` không còn chuỗi nào gắn với guardrail.
- Người nhận: `agent-backend` (verifier).

### S-03 — Đo retrieval/confidence gate với câu không dấu

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-05`.
- Việc cần làm:
  1. Sinh bản bỏ dấu của `ptit_rag_300.json` (giữ `id`, `expected_terms` nguyên bản có dấu vì dùng để so với chunk) vào thư mục scratchpad, không thêm vào `backend/tests/fixtures/`.
  2. Chạy `python -m scripts.eval_confidence --dataset <ptit_rag_300 có dấu> --dataset <bản bỏ dấu> --dataset tests/fixtures/ptit_no_answer_56.json --output <file>` trên cùng corpus, cùng cấu hình, bằng `backend/.venv/Scripts/python.exe` (Python có `pgvector`). Cần Postgres đang chạy.
  3. Ghi tỷ lệ qua gate, hit@4 cho hai bản và tỷ lệ từ chối đúng `out_of_domain` vào `verification.md` (V-05). Lưu báo cáo vào `documents/rag-eval/guardrail-unaccented/` nếu muốn giữ lại.
  4. Lưu ý (R-06): chế độ `full` (`scripts/eval_retrieval.py:485-535`) dùng `VietnameseQueryRewriter`/`VietnameseMultiQueryGenerator` theo cấu hình `QUERY_REWRITE_USE_LLM`/`MULTI_QUERY_USE_LLM`. Mặc định `false`; nếu bật thì in cảnh báo và kết quả không lặp lại được. Đo với cả hai cờ `false` và ghi giá trị cờ trong V-05. Nếu cấu hình chạy thật bật LLM viết lại câu hỏi, ghi rõ số liệu chưa phản ánh bước đó.
  5. Nếu chênh lệch tỷ lệ qua gate > 10 điểm phần trăm: viết đề xuất task "chuẩn hóa câu không dấu trước truy xuất" vào `implementation.md` cho coordinator. Đề xuất này khớp mục 🆕 "chuẩn hóa không dấu" trong thiết kế Chương 2 và ĐA dòng 127 (Recall@k trên cặp câu có dấu/không dấu).
- Phạm vi file được sửa: không sửa mã ứng dụng; có thể thêm `documents/rag-eval/guardrail-unaccented/`.
- Phụ thuộc: S-01 (để cột `scope_allowed` trong báo cáo phản ánh guardrail mới); cần DB đã index và khóa API embedding trong `.env`.
- Đầu ra/bàn giao: số liệu V-05, đề xuất task nếu cần.
- Người nhận: coordinator.

### S-04 — Cập nhật README

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-07` (phần README).
- Việc cần làm: sửa `README.md` dòng 14, 63–65 (sơ đồ: nhánh "Ngoài phạm vi" → "Yêu cầu bị chặn"/"Chèn lệnh"), 87, 110 để mô tả guardrail là danh sách chặn injection/tác vụ cấm; câu ngoài phạm vi do confidence gate và LLM từ chối.
- Phạm vi file được sửa: `README.md`.
- Phụ thuộc: S-01.
- Người nhận: `agent-backend` (verifier).

### S-05 — Cập nhật tài liệu thiết kế Chương 2 (cần người dùng xác nhận)

- Agent: `agent-backend`
- Trạng thái: `done` (người dùng quyết định không sửa tài liệu, MSG-user-001)
- Mục tiêu: phục vụ `AC-07` (phần Chương 2).
- Việc cần làm:
  1. Soạn đề xuất sửa (chưa ghi vào file) cho:
     - `specs/2.1-tac-nhan-thuat-ngu.md:30` (định nghĩa "Kiểm soát phạm vi")
     - `specs/2.5-tuan-tu.md` (mục 22, 25, 64, 101)
     - `import/2.5.1-tuan-tu-tra-loi-tu-bo-nho-dem.txt:22` và `import/2.5.2-tuan-tu-truy-xuat-va-sinh-cau-tra-loi.txt:26` (`API->GUARD: Kiểm tra phạm vi, …`)
     - `import/2.5.3-tuan-tu-tu-choi-cau-hoi.txt` (nhánh `alt` "Ngoài phạm vi")
     - `specs/2.7-kien-truc.md:36`
     - `import/2.7.2a-hoat-dong-luong-truy-van.xml` (nút quyết định kiểm tra phạm vi)
     - `specs/truy-vet.md:19,32` (dòng CN14, QT7 → 2.5.3 nhánh 1, 2.7.2a (3))
     - `chuan-bi-bao-ve.md:48` (lập luận "chuẩn hóa trước thì kiểm tra phạm vi mới đúng")

     Thiết kế còn yêu cầu từ chối câu hỏi dữ liệu cá nhân/giao dịch (QT7) ở Bộ kiểm soát: giữ nguyên yêu cầu đó, chỉ đổi cách xử lý câu ngoài miền tri thức.
  2. Đối chiếu ĐA (R-04; chỉ đọc, không sửa):
     - Chỉ ra QT7 (dòng 86) và CN14 (dòng 111) vẫn đạt: câu chèn lệnh/tác vụ cấm bị Bộ kiểm soát đầu vào chặn; câu ngoài miền bị kiểm tra đủ căn cứ từ chối, dẫn tỷ lệ từ chối đúng `out_of_domain` từ V-05.
     - Đề xuất cách diễn đạt khớp dòng 117 ("chuẩn hóa trước khi kiểm tra phạm vi") và Hình 1.
  3. Gửi đề xuất cho người dùng (MSG trong `implementation.md` + nhắn trong phiên). Chỉ sửa file sau khi người dùng xác nhận. Nếu sửa sơ đồ `.txt`/`.xml` trong `import/`, ghi chú cần import lại vào Visual Paradigm.
- Phạm vi file được sửa: các file `documents/chuong-2/` nêu trên, chỉ sau khi được xác nhận. Không sửa ĐA.
- Phụ thuộc: S-01, S-03 (số liệu dùng làm căn cứ trong `chuan-bi-bao-ve.md` và đối chiếu QT7).
- Đầu ra/bàn giao: tài liệu đã sửa, hoặc ghi quyết định giữ nguyên/hoãn của người dùng.
- Người nhận: user (xác nhận), coordinator.

## Hợp đồng dùng chung

- `check_scope(question: str) -> ScopeDecision(allowed: bool, reason: str)` — bỏ tham số `history`. Tập `reason`: `empty`, `prompt_injection`, `code_generation`, `creative_request`, `general_task`, `passed`. Bên dùng: `backend/app/generation/rag_chain.py`, `backend/scripts/eval_confidence.py`, `backend/app/generation/guardrails.py` (re-export).
- `reason` khi tắt guardrail giữ `disabled` (do `rag_chain.py` gán).
- `contains_prompt_injection(value, *, normalized=False)` và `filter_safe_history(history)` — giữ chữ ký. Cơ chế hai lượt cần cả văn bản gốc để biết có dấu hay không. Nếu `normalized=True` (chỉ `scope.py` dùng) không còn đủ thông tin thì đổi cách gọi trong `scope.py`, sửa mọi chỗ gọi và ghi lại trong `implementation.md`.
- Hành vi với văn bản có dấu không đổi so với hiện tại, trừ các mẫu được thắt chặt có chủ đích (S-01.5, S-01.7, S-01.8).
- Khóa cấu hình `guardrails.scope_enabled` / `GUARDRAIL_SCOPE_ENABLED` giữ nguyên tên.
- File mã nguồn dùng chung và người sửa: tất cả — `agent-backend`.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `agent-backend`; phạm vi kiểm chứng: AC-01 … AC-08.
- Reviewer: `agent-backend`; phạm vi review: diff backend, frontend, README, tài liệu Chương 2.
- Hình thức review: `self_review` (đổi thành `independent` nếu có agent/người khác review). Kế hoạch đã có review vòng 0 của `agent-reviewer` (`review.md`).
- Người xử lý nhận xét: `agent-backend`.

## Thứ tự tích hợp và kiểm chứng

0. Reviewer xác nhận kế hoạch đã phản ánh R-01, R-02, R-04, R-05 (vòng 0). Verifier sửa V-00 trong `verification.md`: 44 câu có dấu bị chặn = 43 thiếu từ khóa + 1 `code_generation`.
1. Working tree `dev` (lúc `2026-11-18T22:39:40+07:00`) chỉ còn thư mục task này chưa track. Thư mục chưa track đi theo khi đổi nhánh. Cập nhật `dev` (`git pull origin dev`), tạo nhánh `feat/guardrail-unaccented-scope`. Nếu lúc đó có thay đổi khác chưa commit, hỏi người dùng trước, không tự stash.
2. S-01 → `pytest backend/tests`.
3. S-02 và S-04 (độc lập với nhau, đều sau S-01) → `npm test` trong `frontend/`.
4. S-03 (cần DB/API key) → ghi V-05.
5. S-05: gửi đề xuất, chờ người dùng xác nhận, rồi sửa.
6. Verifier chạy lại toàn bộ test (AC-08), ghi V-01 … V-08.
7. Review trong `review.md`; sửa nhận xét bắt buộc; kiểm tra lại.
8. Coordinator đóng task khi đủ điều kiện; mở PR vào `dev`.

## Rủi ro và điều chỉnh kế hoạch

- **Câu không dấu vẫn bị từ chối ở confidence gate** vì BM25 trên corpus có dấu khó khớp câu không dấu (`bm25_norm` thiếu → gate trượt). Khi đó lỗi đổi từ `OUT_OF_SCOPE_ANSWER` sang `NO_CONTEXT_ANSWER` chứ chưa hết. S-03 đo để quyết định task chuẩn hóa câu không dấu.
- **Câu lạc đề nhận câu từ chối kém hướng dẫn hơn**: "Chưa tìm thấy thông tin này trong tài liệu." thay vì "Mình chỉ hỗ trợ các câu hỏi liên quan đến PTIT…". Người dùng đã chấp nhận khi chọn hướng này; nếu muốn đổi câu `NO_CONTEXT_ANSWER` thì tạo task riêng.
- **Tăng chi phí**: câu lạc đề giờ đi qua query rewrite, multi-query, embedding và retrieval trước khi bị gate chặn. Rate limit chat vẫn áp dụng. Câu tác vụ cấm/injection vẫn bị chặn sớm.
- **Câu tác vụ cấm có ngữ cảnh mạnh** (ví dụ "viết code tính điểm trung bình theo quy chế PTIT") không khớp mẫu chặn sẽ tới LLM; chỉ còn system prompt chặn. Chấp nhận, vì trước đây cũng chỉ chặn được câu khớp mẫu.
- **Danh sách chặn là lớp từ chối cứng duy nhất** sau khi bỏ lọc từ khóa: mỗi lần chặn nhầm là một câu hợp lệ bị từ chối mà không lớp nào sửa lại. Giảm bằng AC-03 (fixture + bộ câu đối chứng) và S-01.7 (R-03).
- **Bỏ dấu làm mẫu rộng hơn** (R-01): giảm bằng so khớp hai lượt (văn bản có dấu không bị ảnh hưởng) và loại nhánh mơ hồ khỏi bộ mẫu không dấu. Với câu không dấu vẫn có thể còn va chạm chưa biết; bổ sung vào danh sách loại khi phát hiện.
- **Câu tấn công viết dấu một nửa hoặc không dấu dùng nhánh đã bị loại** (ví dụ `hay la DAN`, `quen di moi huong dan`) có thể lọt danh sách chặn; chỉ còn system prompt. Chấp nhận để tránh chặn oan câu hợp lệ; ghi trong `implementation.md`.
- **Lệch thiết kế Chương 2 và ĐA**: thiết kế mô tả kiểm tra phạm vi trước truy xuất và đã có câu trả lời chuẩn bị bảo vệ dựa trên điều đó; ĐA (QT7, CN14, dòng 117) là chuẩn đã duyệt. S-05 bắt buộc người dùng xác nhận và phải đối chiếu ĐA.
- Số liệu mô phỏng RAG-18 lấy trên snapshot cũ (commit `4289a13`, 1 tài liệu, không reranker); S-03 đo lại trên corpus hiện tại.
- DB có thể không chạy trong phiên làm việc (gặp lúc review vòng 0). S-03 và phần quét `chunks` ở S-01.6 cần Postgres; nếu không có thì AC-05 chuyển `blocked` như đã ghi.
