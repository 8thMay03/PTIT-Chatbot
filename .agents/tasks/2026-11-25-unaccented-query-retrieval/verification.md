# Verification: 2026-11-25-unaccented-query-retrieval

- Verifier: `agent-backend`.
- Trạng thái tổng: `failed` (V-01, V-02, V-03 `passed`; V-04, V-05 `failed` theo tiêu chí hiện tại; V-06 … V-08 chưa chạy).
- Bản được kiểm tra: V-01 trên `b8c2ff3` + thay đổi S-01; V-02 … V-05 trên `bb80179` + working tree S-03 (commit S-03 ngay sau lượt đo).
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

### V-02 — AC-02

- Người thực hiện / thời gian: agent-backend / `2026-11-25T21:59:29+07:00`.
- Loại: đo tự động.
- Lệnh / thao tác: lệnh chuẩn, `folded_none`, so từng câu với `baseline_none.json`.
- Kỳ vọng: gate, hit@4 `ptit_rag_300`/`ptit_faq` như baseline; câu không đáp án qua gate không tăng.
- Kết quả thực tế: `ptit_rag_300` 282/250, `ptit_faq` 20/19, không đáp án 8/12/0, giống baseline. 375/376 câu cùng chunk/rank/gate; `noans_056` đổi chunk (bị coi là thiếu dấu vì `la`), vẫn bị từ chối.
- Trạng thái: `passed`.
- Bằng chứng: `documents/rag-eval/unaccented-query/folded_none.json`, README mục "Sau S-03".

### V-03 — AC-03

- Người thực hiện / thời gian: agent-backend / `2026-11-25T21:59:46+07:00`.
- Lệnh / thao tác: lệnh chuẩn, `folded_strip_all`.
- Kỳ vọng: `ptit_rag_300` qua gate ≥ 255, hit@4 ≥ 224; `ptit_faq` qua gate ≥ 18.
- Kết quả thực tế: 258, 236; `ptit_faq` 20.
- Trạng thái: `passed`.
- Bằng chứng: `folded_strip_all.json`.

### V-04 — AC-04

- Người thực hiện / thời gian: agent-backend / `2026-11-25T21:59:46+07:00`.
- Lệnh / thao tác: lệnh chuẩn, `folded_strip_all` (và `folded_strip_partial` để tham khảo).
- Kỳ vọng: `out_of_domain` bỏ dấu bị từ chối 14/14; `in_domain_missing` + `near_miss` qua gate ≤ 20.
- Kết quả thực tế: `out_of_domain` 13/14 bị từ chối (lọt `Dai hoc Bach khoa Ha Noi co bao nhieu sinh vien?`, `bm25_folded_norm` 0.444); `in_domain_missing` + `near_miss` = 9 + 12 = 21. Bỏ dấu một phần: 9 + 11 = 20, `out_of_domain` lọt 1 (cùng câu).
- Trạng thái: `failed`.
- Bằng chứng: `folded_strip_all.json`, `folded_strip_partial.json`; bảng ngưỡng trong README (không ngưỡng nào đạt đồng thời AC-03).

### V-05 — AC-05

- Người thực hiện / thời gian: agent-backend / `2026-11-25T22:00:28+07:00`.
- Lệnh / thao tác: lệnh chuẩn, `folded_strip_partial`, `folded_typo`.
- Kỳ vọng: `strip_partial` qua gate ≥ 255; `typo` không thấp hơn baseline ở mọi loại lỗi.
- Kết quả thực tế: `strip_partial` 254/300 (thiếu 1); `typo` mọi loại tăng cả gate và hit@4 (README).
- Trạng thái: `failed` (phần `strip_partial`); phần `typo` đạt.
- Bằng chứng: `folded_strip_partial.json`, `folded_typo.json`.

### V-06 … V-08 — AC-06 … AC-08

- Trạng thái: `not_run` (chờ S-05). Ghi chú AC-08: pytest backend toàn bộ sau S-03 `1704 passed, 24 skipped`, nhưng test fallback LLM (AC-06) chưa viết.

## Lỗi, kiểm tra lại và phần chưa xác minh

- V-04, V-05 thất bại theo tiêu chí hiện tại (lệch 1 câu mỗi tiêu chí, xem trên); chờ user quyết định nới tiêu chí theo số đo hay làm S-04.
- V-06 … V-08 chưa chạy. Chưa đo với reranker/multi-query bật.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03.
- Tiêu chí chưa đạt/chưa xác minh: AC-04, AC-05 (thất bại sát ngưỡng), AC-06 … AC-08 (chưa chạy).
- Đề xuất: chờ user quyết định AC-04/AC-05/S-04, rồi làm S-05.
