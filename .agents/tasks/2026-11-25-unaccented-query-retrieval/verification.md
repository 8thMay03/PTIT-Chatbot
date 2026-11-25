# Verification: 2026-11-25-unaccented-query-retrieval

- Verifier: `agent-backend`.
- Trạng thái tổng: `not_run` (V-01 `passed`, còn lại chưa chạy).
- Bản được kiểm tra: V-01 trên `b8c2ff3` + thay đổi S-01 (working tree nhánh `feat/unaccented-query-retrieval`).
- Môi trường: Windows 11, `backend/.venv`, Postgres (Docker), corpus D26 đã index, embedding `text-embedding-3-small`.

## Kiểm chứng tiêu chí

V-01 … V-08 tương ứng AC-01 … AC-08 trong `task.md`; lệnh đo chuẩn:

```bash
python -m scripts.eval_confidence \
  --dataset tests/fixtures/ptit_rag_300.json --dataset tests/fixtures/ptit_faq.json \
  --dataset tests/fixtures/ptit_no_answer_56.json \
  --set query_correction_enabled=false --perturb <none|strip_all|strip_partial|typo> --seed 20261121 \
  --output ../documents/rag-eval/unaccented-query/<baseline|folded|restore>_<perturb>.json
```

### V-01 — AC-01

- Người thực hiện / thời gian: agent-backend / `2026-11-25T21:18:55+07:00` – `2026-11-25T21:30:00+07:00`.
- Loại: đo tự động + test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: lệnh chuẩn ở trên với `<baseline>` × 4 chế độ (đủ `--set` tắt LLM/multi-query/reranker, ghi trong README); `python -m pytest -q -p no:cacheprovider` (Postgres Docker lên).
- Kỳ vọng: có báo cáo cho 3 fixture × 4 chế độ, `strip_partial` hoạt động; test đạt.
- Kết quả thực tế: 4 báo cáo `documents/rag-eval/unaccented-query/baseline_{none,strip_all,strip_partial,typo}.json` (corpus 993 chunk, `text-embedding-3-small`, cache embedding 752/752 hit ở bản `none`). `ptit_rag_300` qua gate / hit@4: có dấu 282/250, bỏ dấu 0/50, bỏ dấu một phần 10/173, lỗi gõ 144/210. `ptit_no_answer_56` có dấu qua gate: 8 `in_domain_missing`, 12 `near_miss`, 0 `out_of_domain`. Pytest: `1686 passed, 24 skipped`.
- Trạng thái: `passed`.
- Bằng chứng: `documents/rag-eval/unaccented-query/README.md`, các file `baseline_*.json`.

### V-02 … V-08 — AC-02 … AC-08

- Trạng thái: `not_run` (chờ S-02 … S-05).

## Lỗi, kiểm tra lại và phần chưa xác minh

- V-02 … V-08 chưa chạy.

## Kết luận

- Tiêu chí đã đạt: AC-01.
- Tiêu chí chưa đạt/chưa xác minh: AC-02 … AC-08 (chưa triển khai).
- Đề xuất: tiếp tục S-02.
