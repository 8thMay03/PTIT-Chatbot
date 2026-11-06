# Báo cáo: ngữ cảnh hàng bảng cho tìm kiếm (task `2026-11-05-table-search-context`)

Nhánh `feat/table-search-context` (tách từ `feat/table-chunking-coverage` tại `eeaf045`;
task trước chưa merge vào `dev`).

Index local: 2 tài liệu / 2.020 chunk (`e0997dd2…` = `data/Sổ tay sinh viên D26 _1_.pdf`,
dataset `default`; `7b99bad5…` = `Sổ tay sinh viên D26 _1_ _1_.md`, dataset `0ae10990…`).
Hai tài liệu là **cùng một sổ tay**, nên mỗi kết quả thường xuất hiện hai lần và top-4
thực chất chỉ chứa khoảng 2 parent khác nhau. Corpus fingerprint `d9bf102c…` giống nhau
trước và sau, vì fingerprint không tính `search_text`.

Cấu hình giữ nguyên: `parent 2048/256`, `child 1024/128`, `min_child_chars=120`,
`hybrid_vector_weight=0.8`, `rrf_k=60`, embedding `openai text-embedding-3-small` trên
trường `text` (`EMBEDDING_INPUT_FIELD` không đặt nên dùng mặc định `text`). Embedding câu hỏi
lấy từ cache `storage/eval/embedding_cache.json` (0 cache miss), nên eval không gọi OpenAI.

## Thay đổi

- `search_text` của chunk có bảng Markdown: mỗi bảng được thay bằng các dòng
  `Cột A: giá trị; Cột B: giá trị; …` (mỗi hàng một dòng), không còn header/phân cách/hàng thô
  `|…|`. Văn xuôi và bảng HTML giữ nguyên. `text`, `parent_text`, metadata, id chunk, vector
  và schema DB **không đổi**.
- Ô trống **đầu hàng** (gộp ô dọc, vd. `||||ULO1.3: …`) lấy giá trị cùng cột của hàng ngay
  trên trong cùng bảng logic của cả tài liệu (sau khi ghép bảng ngắt trang), kể cả khi hàng
  trên nằm ở child trước. Ô trống nằm sau ô có giá trị đầu tiên thì giữ trống.
- Bảng chỉ có header (LlamaParse hay coi hàng dữ liệu duy nhất là header, vd. một dòng liên
  hệ) vẫn giữ nội dung header trong `search_text`.
- Cập nhật index **không embed lại**: `python -m scripts.refresh_search_text --apply` chia lại
  `parsed_text` bằng `_chunk_records`. Script chỉ ghi `search_text` khi tập id và `text`
  của từng chunk khớp DB. Mọi luồng chunk có sẵn (`/documents/{id}/chunk`,
  `/datasets/{id}/chunk`, `/ingest/chunk`) đều gọi `_embed`. BM25 không cache trên đĩa, chỉ
  dựng trong bộ nhớ mỗi tiến trình, nên backend đang chạy phải khởi động lại.

Kết quả chạy trên DB local: 720/2.020 chunk đổi `search_text` (360 mỗi tài liệu, tức toàn bộ
chunk có bảng), 0 tài liệu bị bỏ qua. Độ dài `search_text` trung bình **826,7 → 942,6** ký
tự (tài liệu `.md`) và 822,7 → 938,6 (`.pdf`); dài nhất 2.874 ký tự.
`check_chunks --db --strict`: 0 vi phạm `table_*`, 0 `search_text_missing_context`; còn 2
`chunk_starts_mid_word` (`logo: PTIT`) có từ trước, nên exit 1 là đúng hành vi `--strict`.

## Kết quả (cùng index, trước → sau)

Lệnh: `python -m scripts.eval_retrieval --mode {bm25,hybrid} --dataset tests/fixtures/{ptit_ragas_100,table_questions}.json --output documents/rag-eval/table-search-context/{before,after}_*.json`.

| Bộ câu hỏi | Chế độ | hit@4 trước → sau | MRR trước → sau |
|---|---|---|---|
| Golden `ptit_ragas_100` (100) | bm25 | 0.78 → **0.79** | 0.743302 → **0.745746** |
| Golden `ptit_ragas_100` (100) | hybrid | 0.74 → 0.73 (*) | 0.708619 → **0.713952** |
| Bảng `table_questions` (14) | bm25 | 0.857 → **0.929** | 0.857143 → **0.928571** |
| Bảng `table_questions` (14) | hybrid | 0.786 → 0.786 | 0.738095 → 0.738095 |

Các câu đổi hạng:

- Bảng bm25: `q_table_contact_truongkhoa` từ ngoài top-10 lên **hạng 1** (child #14 → #1).
  Hàng `ĐƠN VỊ: Lãnh đạo Khoa; HỌ VÀ TÊN: GS.TS. Phạm Ngọc Anh; CHỨC VỤ: Trưởng khoa; …`
  không còn bị 8 bảng liên hệ khoa khác lấn át.
- Golden bm25: chỉ có câu lên hạng (`student_card_return` 5 → 3, `late_tuition_60_days`
  ngoài top-10 → 9); không câu nào xuống.
- Golden hybrid (*): `summer_credit_limit` 4 → 3, `diploma_original` 2 → 1,
  `process_grade_complaint` 4 → 5 (rơi khỏi top-4, nên hit@4 giảm 1 câu).

### (*) Vì sao golden hybrid mất 1 câu: nhiễu HNSW, không phải do `search_text`

- Hạng BM25 cấp child của mọi chunk liên quan tới `process_grade_complaint` giống hệt trước
  và sau (#1–#6). Điểm BM25 chỉ đổi rất nhỏ do IDF/avgdl toàn kho.
- Vector dùng chỉ mục **HNSW** (xấp xỉ). `UPDATE` cột `search_text` của 720 dòng tạo tuple
  mới, nên các dòng được chèn lại vào đồ thị HNSW dù embedding không đổi. Hiện tại thứ tự ANN
  khác thứ tự chính xác (top-40 cùng tập, khác thứ tự). Riêng hai bản sao gần như trùng nhau
  của `Điều 30. Khiếu nại điểm và sửa điểm` bị đảo: exact #5/#6, ANN #6/#5. Bản có BM25 #1
  mất vector #5, nên điểm RRF giảm từ 0.01559 xuống 0.01540. Trước đó câu này giữ hạng 4 chỉ
  hơn hạng 5 khoảng 0.00001 (bản sao `Điều 18` ở tài liệu kia).
- **Đối chứng tách hiệu ứng**: chạy hybrid với vector chính xác (brute-force numpy trên cùng
  embedding), lần lượt dùng `search_text` cũ (bản sao lưu trước khi ghi) và mới:

  | Bộ câu hỏi | hit@4 cũ → mới | MRR cũ → mới | Câu đổi hạng |
  |---|---|---|---|
  | Golden | 0.74 → 0.74 | 0.709452 → 0.711119 | `english_four_skills` 3 → 2 |
  | Bảng | 0.786 → 0.786 | 0.738095 → 0.738095 | không có |

  `process_grade_complaint` giữ hạng 4 ở cả hai lần, tức thay đổi `search_text` không làm
  golden hybrid thụt lùi. Script đối chứng nằm ở scratchpad phiên, không thuộc repo.

## Vì sao thay hàng thô thay vì nối thêm khối (đo trên cùng index, mô phỏng trong bộ nhớ)

Plan ban đầu là nối khối `Cột: giá trị` vào sau `text` trong `search_text`. Mô phỏng
(vá `search_text` khi BM25 nạp chunk, không ghi DB, HNSW không đổi) cho kết quả:

| Biến thể | Bảng bm25 hit@4 / MRR | Golden bm25 hit@4 / MRR | Golden hybrid hit@4 / MRR |
|---|---|---|---|
| Baseline | 0.857 / 0.857143 | 0.78 / 0.743302 | 0.74 / 0.708619 |
| Nối thêm, điền mọi ô trống | 0.857 / 0.871429 | 0.78 / 0.749317 | 0.74 / 0.712484 |
| Thay hàng thô, điền mọi ô trống | 0.929 / 0.880952 | 0.79 / 0.744913 | 0.74 / 0.707190 |
| Nối thêm, chỉ điền ô đầu hàng | 0.857 / 0.871429 | 0.78 / 0.746635 | 0.74 / 0.713357 |
| **Thay hàng thô, chỉ điền ô đầu hàng** | **0.929 / 0.928571** | **0.79 / 0.745746** | **0.74 / 0.708619** |

- **Nối thêm** nhân đôi nội dung bảng. `search_text` chunk bảng tăng trung bình 774 → 1.713
  ký tự, dài nhất 5.952; BM25 phạt độ dài nên `truongkhoa` chỉ lên hạng 5, chưa vào top-4.
- **Điền mọi ô trống** gán sai dữ liệu. Ở PHỤ LỤC 1 (khung xử lý kỷ luật), ô trống nghĩa là
  "không áp dụng", nhưng hàng `|6.|Tổ chức học, thi…||||Lần 1|…|` bị gán
  `Khiển trách: 3; Cảnh cáo: 4` của hàng trên. Chunk đáp án của `late_tuition_30_days` vì thế
  rơi khỏi top-10 hybrid.
- Biến thể được chọn là biến thể duy nhất đạt cả hai vế: bảng tăng, golden không giảm.

## Còn chưa đạt

- `q_table_ulo13` vẫn hụt ở cả bm25 và hybrid (child #47 → #47). Hàng `ULO1.3` nay đã mang
  `Phẩm chất người tốt nghiệp (Graduate Attributes): GA1; …`, nhưng tokenizer `\w+` tách
  `ULO1.3` thành `ulo1` + `3`, đều phổ biến trong bảng chuẩn đầu ra, và các từ khác trong
  câu hỏi (`chuẩn đầu ra`, `tiếng Anh`) khớp mạnh hơn với các Điều về chuẩn đầu ra tiếng Anh.
  Cần xử lý ở tokenizer hoặc truy vấn, ngoài phạm vi task này.
- Hybrid bảng không tăng: `q_table_drl_vanghop` và `q_table_drl_hienmau` đứng hạng 1 ở bm25
  nhưng vẫn ngoài top-10 hybrid (vector chiếm trọng số 0.8). `search_text` không đổi được
  phía vector, vì embedding dùng `text`.
- Bảng HTML không được tuần tự hóa. Ô gộp trong HTML là `rowspan`/`colspan` (ô vắng mặt,
  không phải ô trống), muốn đúng phải xử lý span. Index và `data/` hiện không có bảng HTML.
