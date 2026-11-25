# Câu hỏi không dấu: số đo

Task `2026-11-25-unaccented-query-retrieval`. File `baseline_*.json` là số đo nền (S-01) trước khi sửa mã ứng dụng; `folded_*.json` là số đo sau S-02 + S-03 (BM25 bỏ dấu, trọng số vector riêng, ngưỡng gate bỏ dấu) với cấu hình mặc định mới. Phần [Sau S-03](#sau-s-03-bm25-bỏ-dấu--gate) ở cuối file.

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

## Sau S-03: BM25 bỏ dấu + gate

### Thay đổi được đo

- Chỉ mục BM25 bỏ dấu song song (S-02). Câu được coi là **gõ thiếu dấu** khi có chữ không dấu mà kho chỉ chứa ở dạng có dấu (`hoc`, `phi`, `mot`); chỉ câu đó xếp theo chỉ mục bỏ dấu và có `bm25_folded_norm_score`. Mọi câu khác xếp theo chỉ mục có dấu như trước.
- `HYBRID_FOLDED_VECTOR_WEIGHT=0.3`: trọng số vector trong RRF cho câu gõ thiếu dấu (câu có dấu giữ `HYBRID_VECTOR_WEIGHT`, máy đo: 0.80).
- Gate: `bm25_folded_norm ≥ RETRIEVAL_MIN_BM25_FOLDED_NORM_SCORE` (mặc định **0.40**) thì đạt tín hiệu từ khóa và không xét `vector`; ngược lại như cũ (`bm25_norm ≥ 0.25` và cosine ≥ 0.37). Ngưỡng rerank (nếu có) vẫn áp dụng.

Thời điểm đo: 2026-11-25, 22:37 – 22:38 (+07:00), git `2bcdc84` (mã S-05; `dirty=true` chỉ vì `.agents/.../review.md` của reviewer đang sửa, không có thay đổi mã), cùng corpus 993 chunk, cùng cấu hình và lệnh như mục Cấu hình (không `--set` thêm; `folded_strip_all.json` có `--sweep`). Lượt đo đầu (21:59, `bb80179` + working tree S-03) cho kết quả giống từng câu ở cả 4 bộ.

### Kết quả (`ptit_rag_300`, n=300)

| Biến thể | Qua gate trước → sau | hit@4 trước → sau |
|---|---|---|
| Có dấu | 282 → 282 | 250 → 250 |
| Bỏ dấu | 0 → **258** | 50 → **236** |
| Bỏ dấu một phần | 10 → **254** | 173 → **234** |
| Lỗi gõ | 144 → **198** | 210 → **237** |

| `ptit_faq` (n=20) | Qua gate trước → sau | hit@4 trước → sau |
|---|---|---|
| Có dấu | 20 → 20 | 19 → 19 |
| Bỏ dấu | 0 → 20 | 5 → 17 |
| Bỏ dấu một phần | 0 → 20 | 15 → 17 |
| Lỗi gõ | 8 → 12 | 17 → 17 |

Câu không có đáp án qua gate (càng thấp càng tốt; mốc bản có dấu: 8 + 12 = 20, `out_of_domain` 0):

| Bộ | `in_domain_missing` (22) | `near_miss` (20) | `out_of_domain` (14) |
|---|---|---|---|
| Có dấu | 8 | 12 | 0 |
| Bỏ dấu | 9 | 12 | **1** |
| Bỏ dấu một phần | 9 | 11 | **1** |
| Lỗi gõ | 4 | 8 | 0 |

Câu `out_of_domain` lọt gate ở cả hai bộ là `Dai hoc Bach khoa Ha Noi co bao nhieu sinh vien?` (`bm25_folded_norm` 0.444): bỏ dấu khớp `dai hoc`, `khoa`, `ha noi`, `sinh vien`.

Lỗi gõ theo loại (`ptit_rag_300`, qua gate / hit@4, trước → sau): `strip_partial` 1/52 → 54/78, `wrong_tone` 43/68 → 64/76, `telex_leftover` 52/76 → 59/85, `char_noise` 50/66 → 56/73, `merge_words` 48/73 → 56/80, `drop_punct` 46/63 → 65/73.

Câu có dấu: 375/376 câu có cùng danh sách chunk, rank trúng và quyết định gate như baseline. Câu còn lại `noans_056` (`Tỷ giá đô la Mỹ hôm nay là bao nhiêu?`) bị coi là gõ thiếu dấu vì chữ `la` (đô la) chỉ có dạng `là` trong kho; `bm25_folded_norm` 0.277 < 0.40 nên vẫn bị từ chối.

### Chọn trọng số và ngưỡng

Lưới đo bằng `--set hybrid_folded_vector_weight=<w>` (báo cáo tạm, không commit), `ptit_rag_300` hit@4 bỏ dấu / bỏ dấu một phần: 0.8 (không đổi) 67 / 179; 0.5: 218 / 230; **0.3: 236 / 234**; 0.0: 240 / 239. Chọn 0.3: gần mức tốt nhất mà vẫn giữ phần vector cho câu diễn đạt khác tài liệu. Với trọng số ≤ 0.3, chunk đứng đầu nhờ BM25 thường không có điểm vector (135/300 câu bỏ dấu không có `vector_score` trong top-4 ở 0.3), và cosine câu không dấu thấp hơn hẳn (median 0.44 so với 0.61); vì vậy gate không xét vector khi đạt nhờ tín hiệu bỏ dấu.

Ngưỡng `bm25_folded_norm` ở trọng số 0.3 (bỏ dấu: qua gate, `in_domain_missing`+`near_miss`, `out_of_domain` | bỏ dấu một phần: tương tự):

| Ngưỡng | Bỏ dấu | Bỏ dấu một phần |
|---|---|---|
| 0.38 | 272, 11+13, 1 | 266, 11+12, 1 |
| 0.39 | 266, 10+12, 1 | 262, 10+11, 1 |
| **0.40** | **258, 9+12, 1** | **254, 9+11, 1** |
| 0.42 | 243, 7+8, 1 | 238, 7+8, 1 |
| 0.45 | 199, 4+4, 0 | 193, 4+4, 0 |

Không ngưỡng nào vừa đạt ≥ 255/300 vừa chặn hết `out_of_domain`: muốn chặn câu Bách khoa phải ≥ 0.445, khi đó chỉ còn ~200/300 câu bỏ dấu qua gate. 0.40 là điểm mà câu không đáp án trong miền lọt gần bằng bản có dấu (21 so với 20). `--sweep` với ràng buộc RAG-18 (từ chối nhầm ≤ 5%) chọn 0.36, nhưng khi đó chỉ từ chối đúng 51.8% câu không đáp án bỏ dấu.

### Chưa đo

- Reranker bật (app local đang dùng `rerank_api` Jina, chưa có ngưỡng rerank nên gate không dùng tín hiệu rerank) và multi-query bật: các lượt đo trên đều tắt hai bước này.
- LLM sửa câu bật cùng BM25 bỏ dấu.

## File

- `baseline_none.json`, `baseline_strip_all.json`, `baseline_strip_partial.json`, `baseline_typo.json`: báo cáo `eval_confidence` (schema v2), có `cases[].signals`, `cases[].perturbations`, `cases[].original_question`, `summary`.
- `folded_none.json`, `folded_strip_all.json`, `folded_strip_partial.json`, `folded_typo.json`: báo cáo `eval_confidence` schema v3 (thêm `signals.bm25_folded_norm`, `cases[].bm25_index`) sau S-03; `folded_strip_all.json` có `summary.sweep` (luật `bm25_or_folded`).
