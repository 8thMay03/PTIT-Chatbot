# Sửa chính tả và dấu câu hỏi bằng LLM: số đo

Task `2026-11-21-llm-query-correction`. Đo bằng `scripts/eval_confidence.py` (chạy từ `backend/`), mỗi bộ chạy hai lần: cờ `QUERY_CORRECTION_ENABLED` tắt và bật.

```bash
python -m scripts.eval_confidence \
  --dataset tests/fixtures/ptit_rag_300.json --dataset tests/fixtures/ptit_faq.json \
  --dataset tests/fixtures/ptit_no_answer_56.json \
  --set query_correction_enabled=<false|true> --perturb <none|strip_all|typo> --seed 20261121 \
  --output ../documents/rag-eval/query-correction/<off|on>_<perturb>.json
```

## Cấu hình

- Thời điểm đo: 2026-11-21, 15:19 – 16:02 (+07:00). Git `f3d01bd` + working tree của task (`dirty=true`).
- LLM sửa câu: `openai_compatible` / `qwen3.8-27b`, tắt thinking (`chat_template_kwargs.enable_thinking=false`), `temperature=0`.
- Ngưỡng kiểm tra đầu ra: Levenshtein ≤ `max(3, 20% độ dài khóa)`, độ dài ≤ 2 lần câu gốc (không chỉnh sau khi đo).
- `QUERY_REWRITE_USE_LLM=false`, `MULTI_QUERY_ENABLED=false`, `MULTI_QUERY_USE_LLM=false`, reranker tắt, top_k 4.
- Embedding `text-embedding-3-small`; gate `min_vector_score=0.37` (calibrated), `min_bm25_norm_score=0.25`.
- Corpus: 1 tài liệu, 1017 chunk, fingerprint `a43f1dd48c7f…`.
- Bộ lỗi gõ: sinh lúc chạy bằng `scripts/typo_variants.py`, seed `20261121`, mỗi câu 1–3 loại lỗi trộn (không gây lỗi trên chữ có số hoặc viết hoa toàn bộ).

## Kết quả chính

| `ptit_rag_300` (n=300) | Qua gate, cờ tắt | Qua gate, cờ bật | hit@4, cờ tắt | hit@4, cờ bật | LLM sửa | Bị bỏ (1 / 2 / 3) | LLM lỗi |
|---|---|---|---|---|---|---|---|
| Có dấu | 284 | 284 | 249 | 249 | 0 | 0 / 0 / 0 | 7 (HTTP 429) |
| Bỏ dấu | 0 | **281** | 40 | **245** | 299 | 1 / 0 / 0 | 0 |
| Lỗi gõ | 144 | **283** | 211 | **248** | 284 | 0 / 0 / 0 | 0 |

Mục tiêu tham khảo (qua gate ≥ 255/300, hit@4 ≥ 224/300) đạt ở cả bản bỏ dấu và bản lỗi gõ.

| `ptit_faq` (n=20) | Gate tắt → bật | hit@4 tắt → bật |
|---|---|---|
| Có dấu | 20 → 20 | 19 → 19 |
| Bỏ dấu | 0 → 20 | 6 → 19 |
| Lỗi gõ | 8 → 20 | 17 → 19 |

Câu không có đáp án (`ptit_no_answer_56`), số câu qua gate (càng thấp càng tốt):

| Bộ | `in_domain_missing` (22) tắt → bật | `near_miss` (20) tắt → bật | `out_of_domain` (14) tắt → bật |
|---|---|---|---|
| Có dấu | 7 → 7 | 14 → 14 | 0 → 0 |
| Bỏ dấu | 0 → 8 | 0 → 12 | 0 → 0 |
| Lỗi gõ | 2 → 7 | 5 → 14 | 0 → 0 |

`out_of_domain` vẫn bị từ chối 14/14 ở mọi bộ. Với cờ bật, câu không có đáp án bỏ dấu/lỗi gõ quay về đúng mức của bản có dấu (cờ tắt từ chối nhiều hơn chỉ vì gate từ chối mọi câu sai chính tả).

## Bộ lỗi gõ theo loại lỗi (`ptit_rag_300`)

Một câu có thể mang nhiều loại lỗi nên tổng số câu lớn hơn 300.

| Loại lỗi | n | Gate tắt → bật | hit@4 tắt → bật |
|---|---|---|---|
| `strip_partial` (bỏ dấu một phần) | 104 | 1 → 100 | 54 → 85 |
| `wrong_tone` (sai dấu thanh) | 100 | 43 → 94 | 67 → 80 |
| `telex_leftover` (sót phím Telex) | 103 | 51 → 96 | 75 → 91 |
| `char_noise` (thêm/bớt/đổi chỗ ký tự) | 104 | 48 → 101 | 68 → 81 |
| `merge_words` (dính chữ) | 101 | 48 → 94 | 71 → 81 |
| `drop_punct` (bỏ dấu câu) | 91 | 46 → 84 | 64 → 71 |

16 câu lỗi gõ không được sửa (`unchanged`): 14 câu chỉ thiếu dấu câu (LLM giữ nguyên, không ảnh hưởng truy xuất) và 2 câu sót Telex mà LLM bỏ sót (`naof`, `Truwowngf`).

## Thời gian sửa câu (mọi câu, gồm cả lần chờ retry)

| Bộ | median | p90 | p95 | max | Số câu > 2 s |
|---|---|---|---|---|---|
| Có dấu | 453 ms | 5 539 ms | 12 191 ms | 27 256 ms | 67/376 |
| Bỏ dấu | 462 ms | 7 916 ms | 12 853 ms | 20 369 ms | 80/376 |
| Lỗi gõ | 457 ms | 7 242 ms | 11 820 ms | 21 660 ms | 60/376 |

Phần đuôi dài đến từ endpoint: lần chạy có dấu gặp 24 lần HTTP 429 (vượt giới hạn request/phút), 7 câu hết retry và rơi về câu gốc (`llm_error`). Các câu chậm còn lại không có lỗi trong log, tức endpoint trả chậm. Script gọi liên tục khoảng 1 câu/2 s nên dễ chạm giới hạn hơn tải thật.

## Câu đúng bị LLM sửa (AC-04)

Cờ bật, bản có dấu (376 câu của 3 fixture): **0 câu bị LLM đổi** (369 `unchanged`, 7 `llm_error` dùng câu gốc). Gate và hit@4 của bản có dấu không đổi (284 → 284, 249 → 249).

## Rủi ro quan sát được

- Câu không dấu vốn mơ hồ: ở bản bỏ dấu, 332/375 câu sửa khôi phục đúng nguyên văn câu gốc. 43 câu còn lại khác câu gốc, có câu sai nghĩa (`Hoc vien` → `Học viên` thay vì `Học viện`, `chuyen nganh` → `chuyển ngành`, `Giao vu` → `Giao vụ`). Bộ kiểm tra đầu ra không chặn được vì chỉ khác dấu. Truy xuất vẫn trúng nhờ các chữ còn lại; câu trả lời sinh từ câu gốc nên không lộ câu sửa sai cho người dùng.
- Ở bản lỗi gõ, LLM đôi khi sửa thiếu (`sowr`, `iKnh` còn nguyên) hoặc thêm chữ (`Bậc Cao học` → `Bác sĩ cao học`) mà vẫn nằm trong ngưỡng.
- Câu duy nhất bị bỏ do điều kiện 1 là câu LLM viết lại sai nghĩa (`So voi he cu nhan thi he ky su …` → `So với hệ cũ, hệ tín chỉ …`), tức kiểm tra đầu ra bỏ đúng câu cần bỏ.
- Kết quả có thể không lặp lại hoàn toàn dù `temperature=0` (LLM qua API, có lỗi 429 tùy thời điểm).

## File

- `off_none.json`, `on_none.json`: câu gốc có dấu.
- `off_strip_all.json`, `on_strip_all.json`: bỏ hết dấu.
- `off_typo.json`, `on_typo.json`: bộ lỗi gõ seed `20261121`.

Mỗi file có `cases[].correction` (lý do, câu sửa, đầu ra thô, thời gian), `cases[].perturbations`, `cases[].original_question` và `summary.correction` (theo bộ, theo loại lỗi, danh sách câu bị đổi).
