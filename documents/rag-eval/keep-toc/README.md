# Giữ mục lục trong index — eval retrieval

Task: [`.agents/tasks/2026-11-12-keep-toc-chunks`](../../../.agents/tasks/2026-11-12-keep-toc-chunks/task.md).

Thay đổi: cleaner không còn bỏ section "MỤC LỤC"; Sổ tay D26 có thêm 7 chunk mục lục (`metadata.is_toc = true`), tổng 1010 → 1017 chunk.

| File | Index | Dataset |
|---|---|---|
| `before_{bm25,hybrid}.json` | cũ, fingerprint `d33ac7329944` | `ptit_ragas_100.json` |
| `after_{bm25,hybrid}.json` | mới, fingerprint `a43f1dd48c7f` | `ptit_ragas_100.json` |
| `after_rag300_{bm25,hybrid}.json` | mới | `ptit_rag_300.json` |

## Kết quả `ptit_ragas_100`

| Chế độ | hit@1 | hit@4 | hit@10 | MRR |
|---|---:|---:|---:|---:|
| bm25 trước | 0.710 | 0.830 | 0.890 | 0.769 |
| bm25 sau | 0.700 | 0.830 | 0.890 | 0.764 |
| hybrid trước | 0.660 | 0.820 | 0.890 | 0.734 |
| hybrid sau | 0.660 | 0.820 | 0.890 | 0.734 |

- bm25 chỉ đổi 1 câu (`headquarters_address` rank 1 → 2, top-1 mới không phải mục lục: do IDF thay đổi khi thêm chunk).
- Chunk mục lục không vào top-4 câu nào; không có câu nào được tính "trúng" nhờ chunk mục lục.

## `ptit_rag_300` (chỉ bản sau)

- bm25: hit@1 0.680, hit@4 0.840, hit@10 0.890, MRR 0.758; hybrid: 0.623 / 0.827 / 0.890 / 0.714.
- Mục lục vào top-4 ở 6 câu (bm25) / 5 câu (hybrid), đa số rank 3–4; số hit đến từ chunk mục lục = 0.
