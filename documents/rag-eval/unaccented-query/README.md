# Câu hỏi không dấu: số đo

Task `2026-11-25-unaccented-query-retrieval`. File `baseline_*.json` là số đo nền (S-01) trước khi sửa mã ứng dụng; các bước sau sẽ thêm `folded_*.json` (S-03) và `restore_*.json` (S-04, nếu làm).

## Cấu hình

- Thời điểm đo: 2026-11-25, 21:18 – 21:22 (+07:00). Git `b8c2ff3` (nhánh `feat/unaccented-query-retrieval`, `dirty=true`: chỉ đổi script đo, chưa đổi mã ứng dụng).
- Corpus: 1 tài liệu (Sổ tay sinh viên D26), **993 chunk**, fingerprint `d9cd1ad2e80f…`. Khác corpus 1017 chunk của `query-correction/` nên không so số tuyệt đối với bộ đó.
- Embedding `text-embedding-3-small`; gate `min_vector_score=0.37` (calibrated), `min_bm25_norm_score=0.25`, không có tín hiệu rerank.
- `QUERY_CORRECTION_ENABLED=false`, `QUERY_REWRITE_USE_LLM=false`, `MULTI_QUERY_ENABLED=false`, `MULTI_QUERY_USE_LLM=false`, reranker tắt, top_k 4. Không gọi LLM.
- Biến thể câu hỏi sinh lúc chạy bằng `scripts/typo_variants.py`, seed `20261121`:
  - `strip_all`: bỏ hết dấu.
  - `strip_partial` (chế độ mới của task này): bỏ dấu một nửa số chữ có dấu. Áp được cho 376/376 câu của 3 fixture.
  - `typo`: 1–3 loại lỗi gõ trộn mỗi câu.

```bash
# từ backend/
python -m scripts.eval_confidence \
  --dataset tests/fixtures/ptit_rag_300.json --dataset tests/fixtures/ptit_faq.json \
  --dataset tests/fixtures/ptit_no_answer_56.json \
  --set query_correction_enabled=false --set query_rewrite_use_llm=false \
  --set multi_query_enabled=false --set multi_query_use_llm=false --set reranker_enabled=false \
  --perturb <none|strip_all|strip_partial|typo> --seed 20261121 \
  --output ../documents/rag-eval/unaccented-query/baseline_<perturb>.json
```

## Gate và hit@4 (`eval_confidence`, pipeline đầy đủ theo luật)

`vec≥`, `bm25≥`: số câu có tín hiệu top-1 vượt ngưỡng gate (0.37 / 0.25). `bm25 trống`: không context nào trong top-4 có điểm BM25.

| `ptit_rag_300` (n=300) | Qua gate | hit@4 | vec≥ | bm25≥ | bm25 trống | cosine median | bm25_norm median |
|---|---|---|---|---|---|---|---|
| Có dấu | 282 | 250 | 300 | 282 | 5 | 0.610 | 0.435 |
| Bỏ dấu | **0** | **50** | 289 | **0** | 161 | 0.441 | 0.000 |
| Bỏ dấu một phần | **10** | 173 | 299 | 10 | 37 | 0.524 | 0.142 |
| Lỗi gõ | 144 | 210 | 298 | 144 | 24 | 0.558 | 0.239 |

| `ptit_faq` (n=20) | Qua gate | hit@4 |
|---|---|---|
| Có dấu | 20 | 19 |
| Bỏ dấu | 0 | 5 |
| Bỏ dấu một phần | 0 | 15 |
| Lỗi gõ | 8 | 17 |

Câu không có đáp án (`ptit_no_answer_56`), số câu qua gate (càng thấp càng tốt):

| Bộ | `in_domain_missing` (22) | `near_miss` (20) | `out_of_domain` (14) |
|---|---|---|---|
| Có dấu | 8 | 12 | 0 |
| Bỏ dấu | 0 | 0 | 0 |
| Bỏ dấu một phần | 0 | 0 | 0 |
| Lỗi gõ | 2 | 6 | 0 |

Mốc cho AC-02/AC-04: bản có dấu cho 8 + 12 = **20** câu không đáp án trong miền qua gate; bản bỏ dấu sau khi sửa không được vượt mốc này.

### Lỗi gõ theo loại (`ptit_rag_300`)

| Loại lỗi | n | Qua gate | hit@4 |
|---|---|---|---|
| `strip_partial` | 104 | 1 | 52 |
| `wrong_tone` | 100 | 43 | 68 |
| `telex_leftover` | 103 | 52 | 76 |
| `char_noise` | 104 | 50 | 66 |
| `merge_words` | 101 | 48 | 73 |
| `drop_punct` | 91 | 46 | 63 |

## Tách phần do BM25 và do vector (`eval_retrieval`, `ptit_rag_300`)

Chỉ truy xuất, không gate. `bm25`/`vector`: một nhánh, gộp về chunk cha; `hybrid`: `Retriever.retrieve` (RRF, `hybrid_vector_weight=0.8`).

| Chế độ | Biến thể | hit@1 | hit@4 | hit@10 | MRR |
|---|---|---|---|---|---|
| bm25 | có dấu | 205 | 255 | 270 | 0.763 |
| bm25 | bỏ dấu | 17 | 46 | 68 | 0.106 |
| bm25 | bỏ dấu một phần | 140 | 212 | 233 | 0.581 |
| vector | có dấu | 173 | 226 | 253 | 0.659 |
| vector | bỏ dấu | 23 | 51 | 78 | 0.126 |
| vector | bỏ dấu một phần | 106 | 158 | 190 | 0.442 |
| hybrid | có dấu | 196 | 244 | 267 | 0.728 |
| hybrid | bỏ dấu | 33 | 64 | 95 | 0.165 |
| hybrid | bỏ dấu một phần | 140 | 188 | 221 | 0.545 |

```bash
# từ backend/; báo cáo JSON (~2 MB/file) để ở backend/storage/eval/unaccented-query/ (không commit)
python -m scripts.eval_retrieval --mode <bm25|vector|hybrid> --dataset tests/fixtures/ptit_rag_300.json \
  --perturb <none|strip_all|strip_partial> --seed 20261121 \
  --output ../backend/storage/eval/unaccented-query/retrieval_<mode>_<perturb>.json
```

(`--output` tương đối được tính từ gốc repo.)

## Nhận xét

- Gate trượt hoàn toàn với câu bỏ dấu chỉ vì BM25: `bm25_norm ≥ 0.25` ở 0/300 câu, trong khi cosine vẫn vượt 0.37 ở 289/300.
- **Embedding cũng hỏng với câu bỏ dấu, không chỉ BM25**: nhánh vector riêng tụt hit@4 từ 226 xuống 51 (gần bằng BM25 bỏ dấu, 46). Cosine vẫn cao (median 0.441) nhưng chunk trả về sai, nên tín hiệu vector của gate **không phân biệt được** câu bỏ dấu trúng hay trật. Thêm BM25 bỏ dấu (S-02) chỉ sửa được nhánh keyword; với `hybrid_vector_weight=0.8`, nhánh vector sai có thể vẫn kéo thứ hạng xuống. Khả năng cao phải làm S-04 (khôi phục dấu trước khi embed) hoặc giảm trọng số vector cho câu bỏ dấu; S-03 sẽ đo để quyết.
- Bỏ dấu một phần nặng hơn dự kiến: qua gate 10/300 dù BM25 riêng còn hit@4 212. Chữ còn dấu vẫn khớp nên thứ hạng không quá tệ, nhưng `bm25_norm` (tỉ lệ phủ term có trọng số idf) giảm một nửa nên rơi dưới 0.25.
- Câu không đáp án bỏ dấu đang bị từ chối hết (0/56) chỉ vì gate từ chối mọi câu bỏ dấu, không phải do gate phân biệt tốt. Sau khi sửa, số này sẽ tăng; mốc chấp nhận là 20 (bằng bản có dấu).

## File

- `baseline_none.json`, `baseline_strip_all.json`, `baseline_strip_partial.json`, `baseline_typo.json`: báo cáo `eval_confidence` (schema v2), có `cases[].signals`, `cases[].perturbations`, `cases[].original_question`, `summary`.
