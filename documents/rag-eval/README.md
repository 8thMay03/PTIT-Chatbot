# Baseline đánh giá retrieval offline

Bộ đánh giá retrieval riêng (không sinh câu trả lời, không cần LLM judge) để đo
nhanh sau mỗi thay đổi về chunking, index hoặc cấu hình hybrid/rerank.

Script: [`backend/scripts/eval_retrieval.py`](../../backend/scripts/eval_retrieval.py) ·
Dataset: [`backend/tests/fixtures/ptit_ragas_100.json`](../../backend/tests/fixtures/ptit_ragas_100.json) (100 câu, sha256 `fa9d2d64f4045c0f…`)
Unit test: [`backend/tests/test_eval_retrieval.py`](../../backend/tests/test_eval_retrieval.py)

## Cách chạy

```powershell
cd backend
python -m scripts.eval_retrieval --mode bm25    # hoặc vector | hybrid | full
python -m scripts.eval_retrieval --compare ..\documents\rag-eval\baseline_bm25.json ..\documents\rag-eval\baseline_hybrid.json
```

- Chỉ số:
  - **hit@1 / hit@4 / hit@10 và MRR** — theo rank context đầu tiên chứa một `expected_terms`;
  - **coverage@1/4/10** — tỉ lệ `expected_terms` được phủ bởi top-k (recall theo term), đo việc truy xuất **đủ** thông tin cho câu trả lời thay vì chỉ trúng một.
  - **section_dominance** (từ schema v3) — tỉ lệ câu có mỗi section (`source_name` + `section_path`) trong top-4; `--compare` tự tính lại từ `heading` cho báo cáo cũ.
  - "Trúng" khi một `expected_terms` xuất hiện trong text context sau chuẩn hóa NFKC + bỏ thẻ HTML
  + casefold — nhãn không phụ thuộc chunk ID nên vẫn dùng được khi đổi chunking.
- Embedding câu hỏi được cache tại `backend/storage/eval/embedding_cache.json`
  (khóa = provider + model + text) nên chạy lại không tốn API.
- Mỗi báo cáo JSON tự ghi: snapshot cấu hình RAG, model embedding, fingerprint kho
  tài liệu, git commit, thời điểm chạy và chi tiết từng câu.

## Baseline 2026-10-25

Index hiện tại: 1 tài liệu "Sổ tay sinh viên D26" (1269 chunk, embed đủ), fingerprint `ccf48780bbcc813d…`.
Commit `2acff9660a83` (bản có coverage@k; hit/MRR không đổi so với bản đo tại `bdff20ba3148`), nhánh `dev`. Chạy trên `.env` local (khác `.env.example`).

| Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@1 | cov@4 | cov@10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | **0.690** | 0.830 | **0.900** | **0.755** | **0.637** | 0.797 | **0.866** |
| vector | 0.590 | 0.800 | 0.870 | 0.688 | 0.530 | 0.749 | 0.826 |
| hybrid | 0.650 | **0.840** | **0.900** | 0.739 | 0.593 | **0.799** | 0.858 |
| full | 0.620 | 0.830 | **0.900** | 0.722 | 0.568 | 0.793 | 0.858 |

Cấu hình đáng chú ý tại thời điểm đo (lấy từ `config` trong từng báo cáo):

- Chunking: parent 2048/overlap 256, parent-child bật, child 1024/overlap 128.
- Hybrid: `HYBRID_VECTOR_WEIGHT=0.80`, candidate multiplier 4, RRF k=60.
- Multi-query và reranker đang **tắt**; query rewrite theo luật (không LLM).
- Embedding: OpenAI `text-embedding-3-small` (1536 chiều).
- `full` = hybrid + query rewrite theo luật; vì multi-query/rerank tắt nên khác
  biệt chính so với `hybrid` là câu hỏi được chuẩn hóa (casefold, bỏ lời dẫn)
  trước khi embed.

Đọc số:

- BM25 đơn thuần đang dẫn đầu hit@1/MRR **và** coverage trên bộ câu này; vector là
  thành phần yếu nhất. Hybrid với trọng số vector 0.80 bị vector kéo xuống hit@1
  (0.650 < 0.690 của BM25) nhưng lại tốt nhất ở hit@4 — hạ `HYBRID_VECTOR_WEIGHT`
  là thí nghiệm đáng làm đầu tiên.
- Khoảng cách hit@4 (0.84) với coverage@4 (0.80) của hybrid cho thấy: câu trúng
  thường vẫn thiếu một phần thông tin trong top-4 — với câu hỏi cần nhiều dữ kiện,
  LLM có thể trả lời thiếu dù retrieval "đạt". Tăng top_k hoặc multi-query là hai
  hướng xử trực tiếp khoảng trống này.
- Hai lần chạy liên tiếp cùng cấu hình cho kết quả giống hệt nhau (kể cả thứ tự
  chunk, điểm số và coverage); hybrid chạy ~4.5–5.5s với cache embedding nóng.

## RAG-05 — chuẩn hóa phân cấp heading (2026-10-25)

Báo cáo: [`rag-05/`](rag-05/) (schema v3: thêm `retrieved[].section_path` và
`metrics.section_dominance`, tức tỉ lệ câu có mỗi section trong top-4). Cấu hình RAG giữ
nguyên như baseline; chỉ đổi Markdown đầu vào nhờ bước `normalize_markdown` chạy sau mọi
parser (PHẦN=1, tiêu đề văn bản=2, Chương=3, Mục=4, Điều=5).

| Bản D26 | Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@4 | cov@10 | section chiếm chỗ nhất (top-4) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| baseline (processed, chưa chuẩn hóa) | hybrid | 0.650 | 0.840 | 0.900 | 0.739 | 0.799 | 0.858 | 0.45 "2. Khóa học" |
| **processed + chuẩn hóa** (chọn) | hybrid | **0.720** | **0.850** | 0.900 | **0.780** | **0.807** | 0.853 | **0.15** "Điều 25. Thang điểm đánh giá" |
| Docling + chuẩn hóa | hybrid | 0.680 | 0.850 | 0.890 | 0.763 | 0.792 | 0.835 | 0.16 "Điều 25. Thang điểm đánh giá" |
| baseline (processed, chưa chuẩn hóa) | bm25 | 0.690 | 0.830 | 0.900 | 0.755 | 0.797 | 0.866 | 0.42 "2. Khóa học" |
| processed + chuẩn hóa | bm25 | 0.700 | 0.830 | 0.890 | 0.762 | 0.797 | 0.851 | 0.15 "Điều 12. Đăng ký học tập" |
| Docling + chuẩn hóa | bm25 | 0.730 | 0.840 | 0.890 | 0.786 | 0.803 | 0.846 | 0.15 "3. Khối lượng học tập" |

- Index: processed 1283 chunk (fingerprint `0a63b72686b2…`), Docling 1038 chunk
  (`86e726a7316d…`). Đo trên working tree chưa commit, nền commit `9d67b581ee6d`.
- **Bản chuẩn cho D26: `data/processed/Sổ tay sinh viên D26 _1_ _1_.md` (parser `text`).**
  Bản này tốt hơn Docling ở chế độ hybrid (chế độ app dùng) trên mọi chỉ số, đạt ngưỡng
  chiếm chỗ ≤ 15%. Văn bản Docling còn lỗi thứ tự đọc: tiêu đề Nghị định 238 dính đoạn
  "Lắng nghe giảng viên…", Điều 16 đứng trước Điều 12. Docling chỉ nhỉnh hơn ở BM25
  thuần (hit@1 0.730).
- So với baseline hybrid: 3 câu có thêm hit@4 (`intensive_course_limit`,
  `grade_improvement_rule`, `student_card_return`) và 2 câu mất
  (`student_card_initial_deadline` rank 1→7, `exam_review_form_destination` rank 3→ngoài
  top-10). Trường hợp thứ hai là do Điều 30 trước đây nằm chung section "Điều 26"; giờ
  nó là section riêng nên không còn được kéo theo. coverage@10 giảm nhẹ (0.858→0.853).
- Ingest lại làm chỉ mục vector xấp xỉ được dựng lại, nên các rank 5–10 có thể xê dịch
  giữa hai lần ingest cùng nội dung (lần đo này: coverage@10 0.850 so với 0.853; hit@1/4
  và MRR không đổi). Trên cùng một index, chạy lại vẫn cho kết quả giống hệt.
- Kiểm tra cấu trúc: `python -m scripts.check_structure <file> [--parser docling] --tree --strict`.

## RAG-06 — chunking Điều/Khoản, `search_text`, lọc nhiễu (2026-10-25)

Báo cáo: [`rag-06/`](rag-06/) (cùng schema v3; thí nghiệm A/B ở
[`rag-06/experiments/`](rag-06/experiments/)). Thay đổi đầu vào index so với RAG-05:

- **Chunking theo Điều/Khoản**: parent = một Điều/mục (Điều dài thì nhóm Khoản liên
  tiếp), child = Khoản/đoạn; cắt đoạn dài theo ranh giới câu, gộp chunk < 120 ký tự
  vào chunk liền kề cùng section (`MIN_CHILD_CHUNK_CHARS`). Vẫn dùng cấu hình local
  2048/1024 trong `.env`.
- **`search_text`** = `"{tên tài liệu} > {section_path}\n{text}"` (cột mới qua
  migration `0003`); **BM25 tokenize `search_text`**; embedding đọc trường theo
  `EMBEDDING_INPUT_FIELD` (mặc định `text` — xem ghi chú dưới).
- **Lọc nhiễu** trong cleaner: mục lục (cả section, kể cả bảng), quốc hiệu + tiêu ngữ,
  dòng ngày tháng, số trang, khối chữ ký + "Nơi nhận", watermark scan. Script kiểm tra
  mới: `python -m scripts.check_chunks --db | --data <dir> [--strict]`.

Index: 1203 chunk / 749 parent (fingerprint `620d26fd0e0c…`), chi phí re-embed ~$0.007.

| Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@4 | so với RAG-05 |
|---|---:|---:|---:|---:|---:|---|
| hybrid (RAG-06) | 0.720 | **0.850** | 0.890 | **0.778** | 0.804 | ngang (RAG-05: 0.850/0.780) |
| bm25 (RAG-06) | 0.710 | **0.850** | **0.910** | **0.770** | 0.798 | **+0.02 hit@4** (0.830/0.762) |
| vector (RAG-06) | 0.620 | 0.770 | 0.850 | 0.700 | 0.727 | hit@4 −0.03, MRR +0.01 (0.800/0.688) |

Đọc số và quyết định:

- **Header ngữ cảnh giúp BM25** (term như "BHYT" giờ nằm trong text được tokenize) nhưng
  **làm vector tụt** khi embed thẳng: thí nghiệm embed `search_text` cho hybrid
  0.820/0.738 (thấp hơn cả RAG-05) vì header tĩnh dài, nhiều chữ HOA làm vector
  `text-embedding-3-small` lệch. Vì vậy mặc định `EMBEDDING_INPUT_FIELD=text` — embedding
  dùng text hiển thị, BM25 dùng `search_text`; muốn bật lại cho model khác chỉ cần đổi env.
- **Chưa đạt tiêu chí "hybrid tăng"**: hybrid ngang bằng RAG-05 (chênh MRR −0.002, trong
  sai số hai lần ingest đã ghi nhận ở RAG-05), nhóm 18 câu thủ tục giảm hit@4
  0.667 → 0.611 — 3 câu thua đều nằm ở guide "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH" mà parent
  theo mục làm evidence phân mảnh. Hướng xử lý tiếp: parent lớn hơn cho tài liệu guide,
  tune `HYBRID_VECTOR_WEIGHT`, hoặc contextual embedding bằng LLM.
- Chất lượng ngữ liệu: 0 chunk mục lục/quốc hiệu/chữ ký (index RAG-05 còn 4 chunk "MỤC
  LỤC"), 0 chunk cắt giữa từ (trước: 143), 0 chunk < 120 ký tự ngoài section ngắn thật
  (trước: 59). `check_chunks --db --strict` sạch.

## RAG-18 — confidence gate hiệu chỉnh theo phân bố điểm (2026-11-08)

Báo cáo: [`rag-18/`](rag-18/) — mỗi cấu hình một JSON (từng câu: scope, tín hiệu top-1,
rank trúng, quyết định gate cũ/mới, top-3 context) và một `.txt` (percentile, histogram,
bảng quét ngưỡng). Script: [`backend/scripts/eval_confidence.py`](../../backend/scripts/eval_confidence.py);
bộ câu không có đáp án: [`backend/tests/fixtures/ptit_no_answer_56.json`](../../backend/tests/fixtures/ptit_no_answer_56.json)
(56 câu: 22 `in_domain_missing`, 20 `near_miss`, 14 `out_of_domain`; 51 câu lọt scope guardrail).

```powershell
cd backend
python -m scripts.eval_confidence --sweep --output ..\documents\rag-eval\rag-18\local_env.json
python -m scripts.eval_confidence --set multi_query_enabled=true --set reranker_enabled=true `
  --set reranker_provider=cross-encoder --set hybrid_vector_weight=0.65 --sweep `
  --output ..\documents\rag-eval\rag-18\example_cross_encoder.json
```

Điều kiện đo: index 1 tài liệu (Sổ tay D26, LlamaParse agentic, 1010 chunk, fingerprint
`d33ac7329944…`), embedding `text-embedding-3-small`, top_k 4, query rewrite/multi-query theo
luật (không LLM). Dataset sha256: `ptit_rag_300` `af2a7a06d823…`, `ptit_ragas_100`
`fa9d2d64f404…`, `ptit_no_answer_56` `2b49e309aa71…`. Commit `4289a134074d` (working tree
`dirty` chỉ do các file stat/CRLF có sẵn trên `dev`, không có thay đổi nội dung).

| Báo cáo | Cấu hình |
|---|---|
| `local_env` | `.env` local: multi-query tắt, reranker tắt, hybrid vector 0.80 |
| `example_heuristic` | núm retrieval của `.env.example`: multi-query bật, reranker `heuristic`, hybrid 0.65 |
| `example_cross_encoder` | như trên nhưng reranker `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |

**Cách đọc số.** *Gate-only*: gate áp lên mọi câu, bỏ qua scope guardrail; với câu không có
đáp án chỉ tính 51 câu lọt scope. *E2E*: câu bị scope chặn cũng tính là từ chối. Scope
guardrail hiện tại đã chặn **14.7% câu `ptit_rag_300`** trước khi tới gate (câu không chứa từ
khóa miền, ví dụ "Phó Bí thư Đoàn trường là ai?", "Số điện thoại liên hệ cơ sở TP. Hồ Chí Minh
là gì?") — đây là từ chối nhầm sẵn có của scope guardrail (RAG-19), không do gate.

### Phân bố tín hiệu top-1 (p5 / p50 / p95, `example_cross_encoder`)

| Nhóm | vector (cosine) | BM25 thô | `bm25_norm` | cross-encoder |
|---|---|---|---|---|
| `ptit_rag_300` (300) | 0.504 / 0.613 / 0.708 | 14.6 / 33.1 / 49.9 | 0.310 / 0.510 / 0.720 | −1.34 / 3.92 / 9.04 |
| `ptit_ragas_100` (100) | 0.501 / 0.620 / 0.713 | 18.0 / 30.2 / 49.1 | 0.301 / 0.477 / 0.716 | −1.41 / 3.66 / 9.17 |
| không có đáp án (56) | 0.358 / 0.507 / 0.600 | 9.4 / 19.8 / 37.0 | 0.114 / 0.271 / 0.462 | −4.54 / −2.23 / 1.39 |

- **Cosine gần như không phân tách**: p95 câu không có đáp án (0.60) cao hơn p5 câu có đáp án
  (0.50); ngưỡng cũ 0.30 thấp hơn mọi câu đã đo nên gate cũ **không từ chối câu nào**.
- **BM25 thô** chồng lấn lớn và phụ thuộc kích thước kho/độ dài query.
- **`bm25_norm`** (điểm thô / cận trên lý thuyết Σ idf·(k1+1) của chính query; term không có
  trong kho tính với idf của df = 1) tách tốt hơn rõ rệt; biến thể bỏ term ngoài kho khỏi mẫu
  số kém hơn (từ chối đúng 0.47 so với 0.59 ở cùng ngân sách) nên đã bị loại.
- **Cross-encoder** là tín hiệu tách tốt nhất; `rerank_score` của reranker `heuristic` là
  min-max trong danh sách ứng viên (top-1 luôn ≈ 1) nên không dùng làm ngưỡng.

### Quét ngưỡng (từ chối nhầm `ptit_rag_300` gate-only ≤ 5%, tối đa từ chối đúng)

Từ chối đúng gate-only trên 51 câu không có đáp án lọt scope; ngưỡng tối ưu riêng cho từng
cấu hình (chi tiết, biên Pareto và ±10% trong JSON `summary.sweep`).

| Luật | `local_env` | `example_heuristic` | `example_cross_encoder` |
|---|---:|---:|---:|
| gate cũ: vector ≥ 0.30 OR BM25 thô ≥ 2.0 | 0.000 | 0.000 | 0.000 |
| vector OR BM25 thô (ngưỡng tối ưu) | 0.490 | 0.431 | 0.510 |
| chỉ vector | 0.333 | 0.333 | 0.412 |
| chỉ `bm25_norm` | 0.588 | 0.588 | 0.627 |
| vector OR `bm25_norm` | 0.647 | 0.686 | 0.725 |
| 0.5·vector + 0.5·`bm25_norm` | 0.647 | 0.647 | 0.725 |
| chỉ cross-encoder | — | — | 0.706 |
| **cross-encoder AND `bm25_norm`** (`rerank_and_norm`) | — | — | **0.882** (−1.55 / 0.26) |

Không luật nào trên tín hiệu heuristic vượt ~0.69: các câu `near_miss` (chủ đề có trong Sổ
tay nhưng chi tiết thì không, ví dụ lệ phí phúc khảo, giá KTX) giống câu có đáp án về cả từ
khóa lẫn ngữ nghĩa. Cross-encoder đọc cặp (câu hỏi, đoạn) nên tách được phần lớn các câu này.

### Gate được chọn

Gate đạt khi **mọi tín hiệu đã hiệu chỉnh** đều vượt ngưỡng (`app/generation/confidence.py`):

| Tín hiệu | Ngưỡng | Khi nào dùng |
|---|---|---|
| `bm25_norm` | ≥ **0.25** (`RETRIEVAL_MIN_BM25_NORM_SCORE`) | luôn dùng |
| cosine | ≥ **0.37** với `text-embedding-3-small` (bảng theo model, `RETRIEVAL_MIN_VECTOR_SCORE` ghi đè) | model có trong bảng hoặc có ghi đè; model khác thì bỏ tín hiệu + log cảnh báo |
| cross-encoder | ≥ **−1.65** với `mmarco-mMiniLMv2-L12-H384-v1` (bảng theo model, `RETRIEVAL_MIN_RERANK_SCORE` ghi đè) | chỉ khi reranker bật và provider `cross-encoder` |

Kết quả gate thật (không mô phỏng), chạy lại bằng `eval_confidence` sau khi cài:

| Cấu hình | Từ chối đúng gate-only | Từ chối đúng e2e | Từ chối nhầm `rag_300` gate / e2e | `rag_300` nhóm hit@4 | Từ chối nhầm `ragas_100` |
|---|---:|---:|---:|---:|---:|
| `example_cross_encoder` | **0.824** | **0.839** | **0.040** / 0.173 | 0.011 | 0.040 |
| `local_env` | 0.588 | 0.625 | 0.050 / 0.180 | 0.024 | 0.060 |
| `example_heuristic` | 0.373 | 0.429 | 0.013 / 0.157 | 0.000 | 0.020 |

Theo nhóm (`example_cross_encoder`, gate-only): `in_domain_missing` 0.818, `near_miss` 0.800,
`out_of_domain` 0.889. 9 câu không có đáp án còn lọt gate, chủ yếu `near_miss`.

Lý do chọn và các phương án bị loại:

- **cross-encoder −1.65 / `bm25_norm` 0.25 thay vì điểm tối ưu −1.55 / 0.26**: điểm tối ưu nằm
  sát biên (cross-encoder ×0.9 = −1.395 → 5.3% từ chối nhầm; `bm25_norm` ×1.1 = 0.286 → 6.3%).
  Quanh điểm chọn (±10% từng ngưỡng, có sàn cosine): cross-encoder −1.485 → 0.863 / 4.7%,
  −1.815 → 0.745 / 3.3%; `bm25_norm` 0.225 → 0.745 / 4.0%, 0.275 → 0.843 / **5.3%**. Ba trong
  bốn điểm lân cận giữ ≤ 5%; phía nới `bm25_norm` chạm biên, nên không nên tăng ngưỡng này.
- **`bm25_norm` 0.25 một ngưỡng cho mọi cấu hình**: giữ từ chối nhầm `rag_300` ≤ 5% ở cả ba
  cấu hình. Multi-query đẩy `bm25_norm` lên (biến thể query ngắn hơn, lấy max) nên với reranker
  heuristic ngưỡng 0.25 khá dễ dãi (0.373); ngưỡng riêng 0.31 cho cấu hình đó chỉ đạt 0.588 —
  vẫn dưới 0.80, nên không tách thêm cấu hình ngưỡng.
- **Cosine chỉ là sàn an toàn (0.37)**: thấp hơn mọi câu có đáp án đã đo (min 0.385); đưa sàn
  lên 0.40 / 0.42 không từ chối thêm câu nào mà tăng từ chối nhầm (4.0% → 4.3% / 4.7% ở
  cross-encoder).
- **Không dùng tổng có trọng số**: không vượt AND, lại trộn cosine (phụ thuộc model) với
  `bm25_norm` nên không suy biến được khi model chưa hiệu chỉnh.

### Kiểm tra liên quan

- `bm25_norm_score` không đổi thứ hạng: `eval_retrieval --mode full` và `--mode hybrid` trên
  `ptit_rag_300`, commit nền `bcd6cd0` so với `4289a13`: 0/300 câu khác top-10 (chunk và điểm),
  hit@1/4/10, MRR giống hệt (full 0.617/0.823/0.887/0.709).
- Chi phí cross-encoder: lần đo 456 câu mất 104 s so với 48 s của heuristic (CPU, cùng máy) —
  khoảng +0.12 s mỗi câu hỏi; lần đầu tải model ~470 MB.

### Giới hạn

- **AC-03 (≥ 80% từ chối đúng) chỉ đạt khi dùng reranker cross-encoder.** `.env.example` vẫn để
  `RERANKER_PROVIDER=heuristic`; đổi mặc định là quyết định triển khai (dung lượng model,
  độ trễ CPU) chưa thực hiện trong RAG-18.
- Reranker cross-encoder lỗi thì `Reranker` âm thầm quay về heuristic; khi đó `rerank_score`
  nằm trong [0, 1] nên luôn vượt −1.65 — gate suy biến thành `bm25_norm` + cosine (an toàn về
  phía trả lời, không từ chối nhầm thêm).
- Tập không có đáp án nhỏ (56 câu, 51 lọt scope): mỗi câu ≈ 2 điểm phần trăm. Ngưỡng gắn với
  kho hiện tại (1 tài liệu); thêm tài liệu, đổi chunking/parser hoặc embedding/reranker thì đo lại.
- Scope guardrail chặn 14.7% câu `ptit_rag_300` (e2e từ chối nhầm 17.3% với cross-encoder);
  xử lý ở RAG-19.

## RAG-22 — locator Điều/Khoản/Điểm theo cấu trúc (2026-11-08)

Báo cáo: [`rag-22/`](rag-22/) — `locators_before_*.json` (commit nền `e6981f149f0a`, index
chưa backfill), `locators_after_*.json` (commit `c4bcd781e27d`, index đã chạy
`refresh_legal_metadata --apply`), `locator_diff_*.json` (ghép theo câu + `chunk_id`, phân loại
từng thay đổi). Script: [`backend/scripts/dump_citation_locators.py`](../../backend/scripts/dump_citation_locators.py).

```powershell
cd backend
python -m scripts.dump_citation_locators --dataset tests/fixtures/ptit_rag_300.json `
  --out documents/rag-eval/rag-22/locators_after_rag_300.json
python -m scripts.dump_citation_locators --diff documents/rag-eval/rag-22/locators_before_rag_300.json `
  documents/rag-eval/rag-22/locators_after_rag_300.json --out documents/rag-eval/rag-22/locator_diff_rag_300.json
```

Điều kiện đo: pipeline `full` của `eval_retrieval` (`.env` local: multi-query tắt, reranker tắt,
hybrid vector 0.80), top-10 context mỗi câu, embedding `text-embedding-3-small` từ cache (0 lần
gọi API). Index 1 tài liệu (Sổ tay D26, LlamaParse agentic, 1010 chunk), fingerprint
`d33ac7329944…` ở cả hai lần chụp (backfill chỉ ghi metadata). Dataset sha256: `ptit_rag_300`
`af2a7a06d823…`, `ptit_ragas_100` `fa9d2d64f404…`. Working tree `dirty` chỉ do các file
stat/CRLF có sẵn trên `dev`.

| Phân loại (cặp câu × context) | `ptit_rag_300` (3000) | `ptit_ragas_100` (1000) | chunk khác nhau |
|---|---|---|---|
| `unchanged` | 2308 | 771 | — |
| `removed_non_article` — bỏ Khoản/Điểm ở mục không thuộc Điều | 56 | 8 | 11 |
| `added_inherited_clause` — thêm Khoản đang mở từ chunk trước | 286 | 80 | 64 |
| `added_inline_clause` — thêm Khoản giữa dòng (có thể kèm Khoản kế thừa) | 350 | 141 | 55 |
| `other` | 0 | 0 | 0 |

Điều kiện AC-05 (citation có Điều ở bản trước giữ nguyên Điều, không mất Khoản nào): **0 vi
phạm** ở cả hai bộ. Số context có Điều không đổi (2003/3000 và 747/1000); có Khoản tăng 1045 →
1363 và 390 → 508; Khoản/Điểm nằm ngoài Điều 56 → 0 và 8 → 0.

Ví dụ: `II. BAN GIÁM ĐỐC HỌC VIỆN — Khoản 1, 2, 3, 4` → `II. BAN GIÁM ĐỐC HỌC VIỆN` (danh sách
liên hệ, không phải Khoản); `Điều 20. Nghĩa vụ của sinh viên` → `… — Khoản 5` (child bắt đầu
giữa Khoản 5); `Điều 13. Quản lý học phí — Khoản 1` → `… — Khoản 1, 2, 3` (bản parse gộp Khoản
2, 3 vào cùng đoạn với Khoản 1).

Kiểm tay đối chiếu `parsed_text`: lượt đầu (15 mẫu) phát hiện Khoản kế thừa sai khi bản parse
gộp nhiều Khoản vào một đoạn ("… Hội đồng. 5. Hai tuần …" bị gắn Khoản 1) và một chunk đánh số
lại từ 1 sau dòng tiêu đề không phải heading — đã sửa ở `c4bcd78`. Lượt sau (12 mẫu ngẫu nhiên,
seed 22) đúng cả 12; một số chunk vẫn thiếu Khoản giữa dòng khi số không liên tục (ví dụ "7."
rồi "9."), khi đó Khoản đang mở bị bỏ thay vì đoán.

**Vận hành.** Index tạo trước RAG-22 chưa có khóa `legal_*`; citation vẫn đúng quy tắc mới
nhưng không biết Khoản kế thừa. Chạy `python -m scripts.refresh_legal_metadata` (dry-run) rồi
`--apply` trên mỗi môi trường, sau đó khởi động lại backend để BM25 dựng lại snapshot. Script
chỉ ghi khi tập id và `text` chunk khớp DB; tài liệu lệch phải chunk lại.

### Giới hạn

- Khoản giữa dòng chỉ nhận khi đúng số kế tiếp, sau dấu kết câu và trước chữ hoa; danh sách
  đánh số `1.` bên trong một Điều nhưng không phải Khoản (phụ lục, danh mục) vẫn bị coi là Khoản.
- Khoản dạng `1)` không còn được nhận (0 lần trong Điều trên index hiện tại).
- Hai chunk trùng nội dung (`parent-186`/`parent-191`, cùng text và embedding) đổi chỗ trong
  top-10 của một câu giữa các lần chụp do Postgres phá hòa theo thứ tự vật lý sau `UPDATE`;
  không ảnh hưởng ghép cặp (theo `chunk_id`).

## Hạn chế đã biết

- Dataset chưa có metadata `question_type` / `source` nên các nhóm
  `by_question_type`, `by_source` hiện toàn `unknown`; 100/100 câu đều có dấu nên
  nhóm `by_diacritics` mới chỉ có `co_dau`. RAG-02 bổ sung dữ liệu sẽ điền các nhóm này.
- Các số Ragas 0.90/0.95/0.93/0.85 trong README chính đo bằng pipeline kèm sinh
  câu trả lời (LLM judge), không so sánh trực tiếp với các số retrieval thuần ở đây.
