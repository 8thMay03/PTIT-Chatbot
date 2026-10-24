# Plan

- Task: `2026-10-24-rag-eval-retrieval-baseline`
- Cập nhật lúc: `2026-10-25T00:07:00+07:00`

## Nhiệm vụ

- S-01 (`zcode-agent`, `done`): viết `backend/scripts/eval_retrieval.py` — 4 chế độ, chỉ số hit@1/4/10 + MRR, nhóm theo nguồn/loại câu hỏi/dấu, cache embedding, fingerprint kho, `--compare`. Phạm vi file: chỉ file mới này.
- S-02 (`zcode-agent`, `done`): viết `backend/tests/test_eval_retrieval.py` — 13 unit test thuần cho chuẩn hóa, so khớp `expected_terms`, hit@k, MRR, nhóm dấu, bảng so sánh, cache; chạy offline không cần API key.
- S-03 (`zcode-agent`, `done`): chạy baseline 4 chế độ trên index hiện tại, lưu `documents/rag-eval/baseline_<mode>.json` + README mô tả cấu hình; AC-01/02/06 kiểm chứng đạt (xem `verification.md`).
- S-04 (`zcode-agent`, `done`): commit script + test + báo cáo + trang task; cập nhật `implementation.md`, `verification.md`, `review.md` (self_review — `approved`).

## Phụ thuộc và thứ tự

S-01 → S-02 (test import module của S-01) → S-03 → S-04. Không song song.

## Hợp đồng dùng chung

- Import module trong test: `from scripts.eval_retrieval import (...)` — module chỉ import thư viện chuẩn ở top-level; mọi import `app.*` nằm trong hàm để test chạy offline.
- Schema báo cáo JSON (khóa chính): `schema_version`, `mode`, `created_at`, `git` (`commit`, `branch`, `dirty`), `dataset` (`path`, `cases`, `sha256`), `embedding` (`provider`, `model`, `cache_file`, `cache_hits`, `cache_misses`), `corpus` (`fingerprint`, `documents`, `chunks`, `embedded_chunks`), `config` (snapshot settings RAG), `eval` (`top_k`, `candidate_multiplier`…), `metrics` (`overall` + `by_*`), `cases` (chi tiết từng câu).
- Cache embedding: JSON dict `sha256(provider\x00model\x00text) -> vector`, mặc định `backend/storage/eval/embedding_cache.json` (thuộc vùng gitignore `backend/storage/`).

## Dùng chung với agent khác

- Không sửa mã nguồn app; script chỉ tái dùng `BM25Search`, `PgVectorStore`, `Retriever`, `reciprocal_rank_fusion`, `collapse_parent_results`, `fuse_multi_query_results`, `Reranker`, `VietnameseQueryRewriter`, `VietnameseMultiQueryGenerator`, `contains_prompt_injection`.
- Báo cáo baseline là artifact commit chung tại `documents/rag-eval/`; tránh ghi đè khi agent khác đã tạo — ghi đè cùng tên chỉ khi chủ đích cập nhật baseline.
