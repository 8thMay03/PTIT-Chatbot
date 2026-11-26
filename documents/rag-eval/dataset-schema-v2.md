# Schema test case v2

Định dạng dùng chung cho mọi bộ câu đánh giá RAG. Loader:
[`backend/scripts/eval_dataset.py`](../../backend/scripts/eval_dataset.py) — dùng bởi
`eval_retrieval`, `eval_confidence`, `evaluate.py`, `evaluate_ragas`. Ví dụ đầy đủ:
[`backend/tests/fixtures/eval_schema_v2_example.json`](../../backend/tests/fixtures/eval_schema_v2_example.json).

```powershell
cd backend
python -m scripts.eval_dataset validate tests\fixtures\eval_schema_v2_example.json
python -m scripts.eval_dataset convert tests\fixtures\ptit_faq.json --out ptit_faq.v2.json
```

## Vì sao có v2

- Cùng trường `expected_terms` mang hai nghĩa: `eval_retrieval`/`eval_confidence` tính trúng khi
  context chứa **một** term, `evaluate.py` khi **một context chứa đủ** mọi term.
- Năm fixture dùng năm kiểu trường khác nhau (`question`/`user_input`, `reference_answer`/`reference`,
  `evidence` chuỗi tự do, `answerable/category/probe_terms`).
- Không diễn đạt được: câu multi-hop (nhiều bước bằng chứng), cách viết tương đương (`05 ngày` /
  `5 ngày`), neo theo Điều/Khoản, loại câu hỏi, split dev/test, claim bắt buộc cho câu tổng hợp/global.

## Cấu trúc file

```json
{
  "schema_version": 2,
  "name": "ptit_multihop_v1",
  "description": "…",
  "corpus": { "documents": ["Sổ tay sinh viên D26 _1_.pdf"], "fingerprint": "…" },
  "cases": [ … ]
}
```

| Trường header | Bắt buộc | Ghi chú |
|---|---|---|
| `schema_version` | có | phải là `2`; file không có trường này được đọc như v1 |
| `name` | không | mặc định tên file; ghi vào báo cáo `dataset.name` |
| `description` | không | |
| `corpus` | không | object tự do; nên ghi tài liệu và fingerprint kho lúc gắn nhãn |
| `cases` | có | mảng không rỗng |

## Một câu (case)

| Trường | Bắt buộc | Kiểu / giá trị |
|---|---|---|
| `id` | có | chuỗi, duy nhất trong file |
| `query` | có | câu hỏi |
| `query_type` | không (mặc định `unknown`) | `single_hop`, `multi_hop`, `comparison`, `conditional`, `aggregation`, `global` |
| `answerable` | không (mặc định `true`) | bool |
| `split` | không (mặc định `unknown`) | `dev` (được dùng để tune) hoặc `test` (held-out) |
| `ground_truth` | có khi `answerable` | câu trả lời tham chiếu (LLM judge / Ragas) |
| `required_claims` | không | các ý bắt buộc phải có trong câu trả lời; cấm khi không có đáp án |
| `evidence` | không | danh sách nhóm bằng chứng (dưới); cấm khi không có đáp án |
| `reference_contexts` | không | `[{doc_id?, page?, chunk_id?, content}]` — `content` **trích nguyên văn**; chỉ để tham khảo/Ragas, **không dùng để chấm** |
| `unanswerable` | có khi `answerable: false` | `{category, reason?, probe_terms?}` |
| `metadata` | không | object tự do: `difficulty`, `created_by`, `reviewed_by`, `source`… |

Khóa không có trong bảng bị **từ chối** (bắt lỗi gõ như `expected_terms` trong file v2).

Quy tắc chéo:

- `multi_hop` và `comparison` có `evidence` thì cần **ít nhất 2 nhóm**. Câu gắn `multi_hop` mà chỉ
  có một nhóm thường là câu tra cứu một dữ kiện bị gắn nhãn sai.
- Câu có đáp án nhưng không có `evidence` (ví dụ câu `global`) vẫn hợp lệ: retrieval bỏ qua câu
  đó (báo cáo ghi `dataset.skipped_no_evidence`), chỉ chấm bằng `ground_truth`/`required_claims`.
- Validate gom mọi lỗi, ghi theo vị trí và id câu: `cases[3] (q_abc).evidence[0].terms[1]: …`.

## Nhóm bằng chứng

```json
{
  "doc_id": "Sổ tay sinh viên D26 _1_.pdf",
  "anchor": { "article": "Điều 34. Thực tập cuối khóa", "clause": 3 },
  "terms": [["ít nhất 75%", "tối thiểu 75%"], "tổng số tín chỉ"],
  "note": "ghi chú cho người gắn nhãn"
}
```

Một context **thỏa** nhóm khi đồng thời:

1. `doc_id` (nếu có) bằng `source_name` của context — so sánh sau chuẩn hóa, không phân biệt hoa
   thường, bỏ đuôi `.pdf/.docx/.md/...`;
2. `anchor` (nếu có) khớp Điều/Khoản của context:
   - `article`: `"Điều 34"`, `34`, hoặc `"Điều 34. <tên Điều>"`. **Sổ tay D26 gộp nhiều quy chế,
     mỗi quy chế đánh số Điều lại từ 1** (có ít nhất 4 "Điều 12" khác nhau), nên neo theo số đơn
     thuần là mơ hồ — hãy ghi kèm tên Điều. Tên được so như chuỗi con của nhãn Điều của context.
   - `clause` (tùy chọn): số Khoản, phải nằm trong `legal_clauses` của context.
   - Điều/Khoản lấy từ metadata `legal_article`/`legal_clauses` (RAG-22); chunk cũ chưa có khóa
     này thì tính lại từ heading/section_path/text như citation.
3. Mọi slot trong `terms` đều có mặt trong text context (chuẩn hóa NFKC + bỏ thẻ HTML + casefold).
   Mỗi slot là một chuỗi hoặc mảng **cách viết tương đương** — khớp một cách là đủ.

Nhóm phải có `terms` hoặc `anchor`. Nên dùng **cả hai**: anchor xác định đúng chỗ, terms xác định
đúng dữ kiện. Chỉ dùng anchor thì mọi chunk của Điều đó đều tính là trúng.

Lưu ý về `clause`: chất lượng `legal_clauses` phụ thuộc bản parse. Trên index LlamaParse hiện tại,
chunk "3. Khối lượng học tập" của Điều 12 (Đăng ký học tập) có `legal_clauses` rỗng vì dòng "3."
là heading. Kiểm tra bằng `eval_retrieval` trước khi neo Khoản; nếu không khớp, neo Điều + terms.

## Chỉ số

Với từng nhóm, rank của nhóm = vị trí context đầu tiên (từ 1) thỏa nhóm.

| Chỉ số | Định nghĩa | Dùng cho |
|---|---|---|
| hit@k, MRR | rank nhỏ nhất trong các nhóm | tương thích các báo cáo cũ |
| coverage@k | tỉ lệ nhóm có rank ≤ k | mức phủ bằng chứng |
| **all_groups@k** | tỉ lệ câu có **mọi** nhóm rank ≤ k | chỉ số chính cho multi-hop/so sánh |
| `evaluate.py` hit | mọi nhóm nằm trong top-k | |
| `evaluate.py` keyword recall | tỉ lệ slot (của mọi nhóm) xuất hiện trong câu trả lời | |

## Đọc file v1

File không có `schema_version` (mảng câu, hoặc object bọc `data/samples/cases/questions`) được
chuẩn hóa trong bộ nhớ, **giữ nguyên ngữ nghĩa cũ của từng script**:

| Trường v1 | → v2 |
|---|---|
| `question` / `user_input` | `query` |
| `expected_terms` | `per_term` (`eval_retrieval`, `eval_confidence`, `convert`): mỗi term một nhóm → trúng khi một term xuất hiện, coverage theo term như cũ. `single_group` (`evaluate.py`): mọi term là slot của một nhóm → một context phải chứa đủ, như cũ |
| `reference_answer` / `reference` | `ground_truth` |
| `reference_context` | `reference_contexts: [{content}]` |
| `answerable`, `category`, `why_unanswerable`, `probe_terms` | `answerable`, `unanswerable.{category, reason, probe_terms}` |
| `question_type` | `query_type` (giá trị tự do trong bộ nhớ; khi convert, giá trị ngoài enum chuyển vào `metadata.legacy_question_type`) |
| `difficulty`, `source` | `metadata.difficulty`, `metadata.source` |
| khóa khác (`evidence` của `table_questions`, `answer_terms`, …) | giữ trong `metadata` khi convert |

Kiểm chứng (task `2026-11-27-eval-schema-v2`): `eval_retrieval` bm25/hybrid trên `ptit_ragas_100`,
`ptit_rag_300` và `eval_confidence` mặc định cho kết quả từng câu giống hệt trước khi đổi loader.

`convert` không tự gắn `query_type`, `split` hay neo Điều — các trường đó cần người gắn nhãn. Một
file v1 convert xong rồi đọc ở `evaluate.py` sẽ theo ngữ nghĩa v2 (mỗi term một nhóm, các nhóm có
thể nằm ở context khác nhau) thay vì "một context chứa đủ" của v1.

## Ví dụ một câu đầy đủ

```json
{
  "id": "ex_multi_hop_internship_july",
  "query": "Muốn đi thực tập cuối khóa đợt tháng 07 thì phải tích lũy được ít nhất bao nhiêu phần trăm tín chỉ?",
  "query_type": "multi_hop",
  "split": "test",
  "ground_truth": "Học viện xét thực tập cuối khóa hai đợt (tháng 01 và tháng 07); điều kiện là tích lũy ít nhất 75% tổng số tín chỉ của chương trình.",
  "evidence": [
    { "anchor": { "article": "Điều 34. Thực tập cuối khóa", "clause": 4 }, "terms": [["tháng 07"]] },
    { "anchor": { "article": "Điều 34. Thực tập cuối khóa", "clause": 3 }, "terms": [["ít nhất 75%"]] }
  ],
  "metadata": { "difficulty": "medium", "created_by": "human" }
}
```

Hướng dẫn viết câu tốt:

- Câu hỏi không chứa sẵn đáp án ("có được đăng ký quá 14 tín chỉ không?" lộ con số; hỏi "tối đa
  bao nhiêu tín chỉ?").
- Term là cụm đặc trưng của dữ kiện (≥ 6 ký tự, không quá phổ biến), viết đúng như văn bản gốc kể
  cả lỗi chính tả của bản gốc; thêm cách viết tương đương thay vì nới term.
- Câu sinh tự động (Ragas…) ghi `metadata.created_by` và chỉ đưa vào `test` sau khi người kiểm
  (`metadata.reviewed_by`).
