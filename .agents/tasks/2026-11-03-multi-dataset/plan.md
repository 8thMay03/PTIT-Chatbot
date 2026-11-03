# Plan: 2026-11-03-multi-dataset

## Quyết định cần người dùng xác nhận

Mỗi mục đã có phương án đề xuất. Nếu người dùng không chọn khác, coordinator dùng phương án đề xuất.

| ID | Câu hỏi | Đề xuất | Lý do |
| --- | --- | --- | --- |
| D-01 | Một tài liệu thuộc một hay nhiều dataset? | **Đúng một dataset.** Muốn dùng ở hai nơi thì tải lên hai lần. | Chunk và embedding gắn với tài liệu. Cho tài liệu thuộc nhiều dataset sẽ làm phức tạp việc xóa, bật/tắt và lọc retrieval. |
| D-02 | Bật/tắt dataset có ảnh hưởng chatbot không? | **Có.** Chatbot chỉ truy xuất từ dataset đang bật. | Đây là giá trị chính của việc chia dataset. Toggle hiện tại không ảnh hưởng gì nên dễ gây hiểu nhầm. |
| D-03 | Sinh viên có chọn dataset khi chat không? | **Chưa làm trong task này.** Retriever vẫn nhận `dataset_ids` để làm sau. | Cần thêm UI ở trang chat và thay đổi `ChatRequest`. Nên tách thành task riêng sau khi admin đã chia dataset ổn định. |
| D-04 | Toggle “Bật/Tắt” từng tài liệu (hiện chỉ lưu trong phiên)? | **Gỡ khỏi bảng.** Thay bằng toggle thật ở cấp dataset. | Hai toggle, một thật một giả, dễ làm admin hiểu sai. Nếu cần tắt từng tài liệu, làm `documents.enabled` thật ở task sau, dùng lại bộ lọc của S-03. |
| D-05 | Mỗi dataset có cấu hình parser/chunk riêng không? | **Chưa.** Vẫn dùng cấu hình chung ở Settings. | Embedding dùng chung một chiều vector (1536). Cấu hình chunk riêng cần thêm UI và bước kiểm chứng eval, nên để task sau. |
| D-06 | Dataset mặc định | ID cố định `default`, tên “Mặc định”. **Đổi tên được, không xóa được.** Upload không ghi dataset sẽ vào đây. | Giữ API cũ tương thích và có chỗ chứa toàn bộ tài liệu hiện có khi migrate. |
| D-07 | Xóa dataset còn tài liệu | **Cho phép.** Xóa luôn tài liệu, đoạn và file nguồn sau khi admin **gõ lại tên dataset** để xác nhận. | Bắt xóa từng tài liệu trước thì quá chậm. Bước gõ tên tránh xóa nhầm khi thao tác không hoàn tác được. |

## Thiết kế kỹ thuật

### Mô hình dữ liệu (S-01)

```text
datasets
  id           varchar PK        -- "default" hoặc uuid4().hex (dùng làm tên thư mục)
  name         varchar(100) NOT NULL UNIQUE   -- kiểm tra trùng không phân biệt hoa/thường ở tầng app
  description  text NULL
  enabled      boolean NOT NULL DEFAULT true
  created_at, updated_at timestamptz

documents
  + dataset_id varchar NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT
  + INDEX idx_documents_dataset_id (dataset_id)
```

- `ON DELETE RESTRICT`: xóa dataset phải đi qua pipeline để dọn file nguồn và vector store ngoài. DB không tự cascade âm thầm.
- Migration `backend/alembic/versions/0008_datasets.py`: tạo bảng nếu chưa có (`init_db()` có thể đã tạo trước, xem `0005`/`0007`). Chèn dòng `default` nếu chưa có. Thêm cột nullable, backfill `'default'`, đặt NOT NULL, rồi thêm FK và index. `downgrade` bỏ FK/index/cột rồi bỏ bảng.
- `ensure_default_dataset(session)` chạy idempotent trong `init_db()`. Nhờ vậy SQLite test (dùng `create_all`) và DB mới đều có dataset mặc định.

### Lưu file và định danh (S-02)

- File tải lên mới: `DOCUMENTS_PATH/datasets/<dataset_id>/<tên đã sanitize>`. File cũ (`data/raw`, `data/processed`, gốc `data/`) **giữ nguyên chỗ** và thuộc `default`.
- **ID tài liệu mới = `uuid4().hex`** thay cho `sha256(source_path)`. Tài liệu cũ giữ ID. Lý do: chuyển dataset làm đổi `source_path`. Nếu ID suy ra từ đường dẫn, một file mới tải vào đúng đường dẫn cũ sẽ trùng ID và ghi đè tài liệu đã chuyển đi.
- **ID chunk mới dựa trên `document_id`**: `<document_id>::chunk-N`, `<document_id>::parent-P`, `<document_id>::parent-P::child-C`, thay cho `<source_path>::...`, vì cùng lý do trên. Chunk cũ giữ ID tới lần chia đoạn kế tiếp. Hiện nay chia đoạn lại đã xóa rồi chèn chunk, nên `message_sources.chunk_id` vốn đã bị `SET NULL`; đổi cách sinh ID không làm tình trạng này tệ hơn.
- Khóa job upload: `upload:<dataset_id>:<tên file>`. `ParseJob` có thêm `dataset_id`. Job upload kết thúc sau khi dataset đã bị xóa thì `_save_parsed` báo `DocumentStateError`, job chuyển `failed`.
- **Nạp lại toàn bộ** (`ingest_documents` / `replace_knowledge_base`) vẫn xóa rồi dựng lại mọi tài liệu từ đĩa. Bước này phải giữ `id` và `dataset_id` theo `source_path`, thông qua hàm mới `get_document_identities(session) -> {source_path: (id, dataset_id)}`, tương tự cách đang giữ parser và Markdown sửa tay. File chưa có dòng DB nằm trong `datasets/<id>/` sẽ vào dataset đó nếu dataset còn tồn tại, còn lại vào `default`.
- **Chuyển tài liệu** (`move_documents(document_ids, target_id)`):
  - Chạy theo kiểu tất cả hoặc không gì cả.
  - Trả 409 nếu ở đích đã có tài liệu trùng tên file (so sánh cả lô với nhau và với tài liệu sẵn có), hoặc tài liệu đang có job parse.
  - Cập nhật `dataset_id`, `source_path`, `metadata.source` của tài liệu và `metadata.source` của từng chunk. Không nhúng lại.
  - Đổi tên file sang thư mục đích, dùng cơ chế backup/rollback giống `publish_upload`. Commit lỗi thì trả file về chỗ cũ.
  - Cuối cùng gọi `invalidate_bm25_cache()`.
- **Xóa dataset**: lấy danh sách tài liệu và vector ID, xóa tài liệu và dataset trong một transaction. Sau commit, xóa file nguồn, thư mục `datasets/<id>`, vector ngoài (nếu có), rồi invalidate BM25.
- **Gia cố `resolve_source_path`**: chỉ fallback `rglob` theo tên file với đường dẫn cũ **không** nằm dưới `datasets/`, và chỉ khi có **đúng một** kết quả. `delete_source_file` chỉ xóa đúng đường dẫn đã resolve, nằm trong `DOCUMENTS_PATH`. Nếu không, khi đã có file trùng tên ở nhiều dataset, xóa tài liệu mất file có thể xóa nhầm file của dataset khác.
- Thao tác theo dataset:
  - `chunk_documents(dataset_id=None)`: có tham số thì chỉ chia đoạn tài liệu của dataset đó.
  - `enqueue_dataset_parse(dataset_id)`: đưa mỗi tài liệu vào job parse nền với parser đã lưu. Bỏ qua tài liệu có `markdown_edited` và tài liệu đang có job, rồi trả về số tài liệu bị bỏ qua.

### Lọc retrieval theo dataset (S-03)

- `VectorStore.search(query_embedding, top_k, dataset_ids=None)` và `BM25Search.search(query, top_k, dataset_ids=None)`. `Retriever.retrieve` và `RagChain.retrieve_context`/`iter_retrieve_context` nhận và truyền tiếp `dataset_ids`. `retrieval_debug` ghi thêm `dataset_ids`.
- Quy tắc: chỉ lấy chunk của dataset `enabled = true`. Nếu có `dataset_ids` thì lấy giao của hai tập.
- `PgVectorStore`: **đường nhanh**. Khi không có dataset nào tắt và không có `dataset_ids`, giữ nguyên câu SQL hiện tại (không join) để baseline và query plan HNSW không đổi. Khi cần lọc thì join `documents` + `datasets` kèm `WHERE`. Trên Postgres, khi pgvector ≥ 0.8, bật `SET LOCAL hnsw.iterative_scan = relaxed_order` cho truy vấn có lọc (xem rủi ro RK-01). Nhánh SQLite (test) cũng lọc theo cùng quy tắc.
- `BM25Search._load_chunks` chỉ nạp chunk thuộc dataset đang bật, snapshot có thêm `dataset_id`. Bộ lọc `dataset_ids` chạy trước khi cắt `top_k`. Bật/tắt, chuyển tài liệu hay xóa dataset đều gọi `invalidate_bm25_cache()`.
- Chat (`/api/chat`, `/api/chat/stream`) không đổi request. `dataset_ids=None` nghĩa là dùng mọi dataset đang bật. Nếu mọi dataset đều tắt thì không có context và guardrail hiện có xử lý như câu hỏi không đủ nguồn.

### Hợp đồng API (S-04)

Mọi route mới gắn `require_admin`. Thông báo lỗi `detail` viết bằng tiếng Việt như các route hiện có.

```text
DatasetItem = {
  id, name, description|null, enabled, is_default,
  document_count, chunk_count,
  pending_count,      # tài liệu status != "active" (đã parse, chờ chia đoạn)
  size_bytes|null,    # tổng metadata.size_bytes, tính ở Python (parsed_text vẫn deferred)
  created_at, updated_at
}

GET    /api/datasets                       -> { datasets: DatasetItem[] }   # "default" đầu tiên, sau đó theo tên
POST   /api/datasets  {name, description?} -> 201 DatasetItem | 409 trùng tên | 422
GET    /api/datasets/{id}                  -> DatasetItem | 404
PATCH  /api/datasets/{id} {name?, description?, enabled?} -> DatasetItem | 404 | 409 trùng tên | 422
DELETE /api/datasets/{id}                  -> { id, deleted: true, documents: n } | 404 | 409 (default / còn job parse)
POST   /api/datasets/{id}/chunk            -> ChunkAllResponse {documents, chunks, skipped, collection} | 404 | 409
POST   /api/datasets/{id}/parse            -> { jobs: ParseJobItem[], skipped_edited: n, skipped_busy: n } | 404

GET    /api/documents?dataset_id=<id>      -> DocumentListResponse (không có tham số: mọi tài liệu như cũ) | 404 dataset
POST   /api/documents  (form: file, parser_name?, dataset_id?) -> 202 ParseJobItem | 404 dataset | 409 | 413 | 400
POST   /api/documents/move {document_ids: str[1..500], dataset_id} -> { moved: n, dataset_id } | 404 | 409 (trùng tên ở đích, tài liệu đang parse)
POST   /api/retrieval/test  + dataset_ids?: str[]

DocumentItem  + dataset_id: str
ParseJobItem  + dataset_id: str | null
```

Validate tên: trim, 1–100 ký tự, không chứa ký tự điều khiển. Mô tả tối đa 500 ký tự.

## Thiết kế giao diện (S-05 → S-07)

### Điều hướng

- `#documents` → danh sách dataset. `#documents/<datasetId>` → tài liệu của dataset. ID hợp lệ khớp `^[A-Za-z0-9_-]{1,64}$`; hash không hợp lệ quay về danh sách.
- `readAdminRoute`/`adminRouteHash` trả thêm `datasetId`. `legacyHashToAdmin("documents")` giữ nguyên.
- Khi vào một dataset, `AdminShell` dùng `history.pushState` để nút Back trở về danh sách. Các thay đổi route khác vẫn dùng `replaceState` như hiện nay.
- Mở chi tiết tài liệu và trình sửa Markdown vẫn là state trong `DatasetView`, chưa có hash riêng.

### Trang danh sách dataset (mới)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Dataset                                   [🔍 Tìm dataset] [Bảo trì ▾] [+ Tạo dataset] │
│ Mỗi dataset là một nhóm tài liệu. Chỉ dataset đang bật được dùng khi trả lời.│
├─────────────────────────────────────────────────────────────────────────────┤
│ ⚠ Không có dataset nào đang bật — chatbot sẽ không có nguồn để trả lời.     │  (chỉ khi cần)
├────────────────────────┬────────────────────────┬────────────────────────┤
│ ▣ Sổ tay sinh viên  ⋯ │ ▣ Quy chế đào tạo   ⋯ │ ▣ Mặc định         ⋯ │
│ Sổ tay K2024, D26      │ Quy chế tín chỉ...     │ Tài liệu chưa phân loại│
│ 12 tài liệu · 840 đoạn │ 5 tài liệu · 310 đoạn  │ 3 tài liệu · 95 đoạn   │
│ 24 MB                  │ 6 MB                   │ 1 MB                   │
│ ⚠ 2 chờ chia đoạn      │                        │                        │
│ [● Đang dùng] 03/11    │ [○ Đã tắt]   01/11     │ [● Đang dùng] 28/10    │
└────────────────────────┴────────────────────────┴────────────────────────┘
```

- Thẻ có thể bấm (cả thẻ là link tới `#documents/<id>`). Menu `⋯` gồm: Đổi tên & mô tả, Bật/Tắt, Xóa. Dataset mặc định không có mục Xóa.
- “Bảo trì ▾” chứa hai thao tác toàn kho chuyển từ trang tài liệu sang: **Chia đoạn lại toàn bộ** và **Nạp lại toàn bộ**, kèm mô tả như tooltip hiện tại.
- Lưới: 3 cột ở ≥1280px, 2 cột ở 768px, 1 cột ở 360px. Dùng token có sẵn trong `styles/tokens.css`, bo góc và viền giống `dataset-table-card`.
- Có trạng thái đang tải (thẻ skeleton), rỗng (chỉ còn “Mặc định” trống → gợi ý tạo dataset/tải tài liệu) và lỗi (`describeError`).
- Hộp thoại:
  - `DatasetFormModal`: tên và mô tả, đếm ký tự, báo lỗi 409 ngay dưới ô tên.
  - `DeleteDatasetModal`: hiển thị “Sẽ xóa N tài liệu, M đoạn”, ô nhập tên dataset, nút Xóa chỉ bật khi gõ khớp.

### Trang tài liệu của dataset (sửa `DatasetView.jsx`)

```text
Dataset / Sổ tay sinh viên                                   [● Đang dùng khi trả lời]
Sổ tay K2024, D26                                                         [✎ Sửa]
12 tài liệu · 840 đoạn · 2 chờ chia đoạn · 24 MB
[Chia đoạn lại dataset] [Parse lại dataset] [🔍 Tìm tài liệu] [+ Thêm tài liệu]
┌──────────────────────────────────────────────────────────────────────────┐
│ ☐ Tên tài liệu      Ngày tải lên   Trạng thái   Số đoạn  Dung lượng  Thao tác │
│ ...  (bảng như hiện tại; bỏ cột Bật/Tắt theo D-04)                          │
└──────────────────────────────────────────────────────────────────────────┘
Đã chọn 3 tài liệu   [Bỏ chọn] [Chuyển sang dataset…] [Xóa đã chọn]
```

- Giữ mọi thao tác theo dòng và cơ chế job nền hiện có. Banner job nền chỉ đếm job có `dataset_id` của dataset đang mở.
- Upload và kéo thả gửi `dataset_id` của dataset đang mở. Toast nêu tên dataset.
- `MoveDocumentsModal`: danh sách radio các dataset khác (tên + số tài liệu). Nếu nhận 409 thì hiện danh sách tên file trùng và không đóng hộp thoại.
- “Parse lại dataset” hỏi xác nhận, ghi rõ tài liệu có Markdown sửa tay sẽ được giữ.
- Mở `#documents/<id>` không tồn tại (404) → về danh sách kèm toast “Dataset không còn tồn tại”.
- `DocumentView` và `MarkdownEditorView`: nhãn quay lại thành “Quay lại <tên dataset>”.

## Phân công

Mặc định một agent (`claude-code`) làm tuần tự trên nhánh `feat/multi-dataset`. Sau khi S-04 chốt hợp đồng, có thể tách S-05…S-07 cho agent frontend riêng; phạm vi file dưới đây không chồng nhau.

### S-01 — Model, migration, repository dataset

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: bảng `datasets`, cột `documents.dataset_id`, dataset mặc định, các hàm repository (CRUD, thống kê, `get_document_identities`, `move_documents` phần DB, `delete_dataset` phần DB, lọc `list_documents(dataset_id)`). Phục vụ `AC-01`, nền cho `AC-02`…`AC-06`.
- Phạm vi file được sửa: `backend/app/db/models.py`, `backend/app/db/repositories.py`, `backend/app/db/session.py`, `backend/alembic/versions/0008_datasets.py` (mới), `backend/tests/test_dataset_repositories.py` (mới), `backend/tests/test_document_repositories.py`, `backend/tests/test_database_postgres.py`.
- Phụ thuộc: D-01, D-06 đã chốt.
- Đầu ra/bàn giao: `Dataset` model, `DEFAULT_DATASET_ID`, chữ ký hàm repository ghi trong `implementation.md`.
- Người nhận: `claude-code` (S-02, S-03, S-04).

### S-02 — Ingestion theo dataset: lưu file, định danh, chuyển, xóa, rebuild

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: upload vào `datasets/<id>/`, ID tài liệu uuid, ID chunk theo `document_id`, `ParseJob.dataset_id`, rebuild giữ dataset/ID, `move_documents`, `delete_dataset`, chia đoạn/parse theo dataset, gia cố `resolve_source_path`/`delete_source_file`. Phục vụ `AC-03`, `AC-04`, `AC-06`, phần xóa của `AC-02`.
- Phạm vi file được sửa: `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/uploads.py`, `backend/app/ingestion/jobs.py`, `backend/app/ingestion/loaders.py` (nếu cần), `backend/scripts/ingest.py` (nếu cần), `backend/tests/test_dataset_ingestion.py` (mới), `backend/tests/test_document_pipeline.py`, `backend/tests/test_document_uploads.py`, `backend/tests/test_parse_jobs.py`, `backend/tests/test_ingest_script.py`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: các phương thức pipeline/job mới kèm mã lỗi (`DocumentStateError`, `DatasetConflict`…) để S-04 ánh xạ sang HTTP.
- Người nhận: `claude-code` (S-04).

### S-03 — Lọc retrieval theo dataset

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: lọc dataset đang bật và `dataset_ids` ở vector store, BM25, retriever, rag chain, giữ đường nhanh khi không cần lọc. Phục vụ `AC-05`.
- Phạm vi file được sửa: `backend/app/vectordb/base.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/retrieval/bm25.py`, `backend/app/retrieval/retriever.py`, `backend/app/generation/rag_chain.py`, `backend/tests/test_dataset_retrieval.py` (mới), `backend/tests/test_pgvector_store.py`, `backend/tests/test_hybrid_retrieval.py`, `backend/tests/test_rag_chain.py`.
- Phụ thuộc: S-01. Chạy song song được với S-02 vì không chung file.
- Đầu ra/bàn giao: chữ ký `search(..., dataset_ids=None)`, `retrieve(..., dataset_ids=None)`. Kết quả so sánh eval ghi ở `verification.md`.
- Người nhận: `claude-code` (S-04, verifier).

### S-04 — API dataset và mở rộng API tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: các route và schema theo mục “Hợp đồng API”, ánh xạ lỗi, `dataset_id` trong `DocumentItem`/`ParseJobItem`, `dataset_ids` cho `/retrieval/test`. Phục vụ `AC-02`, `AC-03`, `AC-04`, `AC-06`.
- Phạm vi file được sửa: `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/tests/test_dataset_api.py` (mới), `backend/tests/test_document_api.py`, `backend/tests/test_api_schemas.py`, `backend/tests/test_admin_auth.py` (nếu cần cập nhật).
- Phụ thuộc: S-02, S-03.
- Đầu ra/bàn giao: hợp đồng API đã chốt (cập nhật mục trên nếu đổi). Đây là **mốc 1**: backend merge riêng được, UI cũ vẫn chạy vì mọi tài liệu ở `default`.
- Người nhận: agent frontend (S-05).

### S-05 — Frontend: API client, query key, route

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `datasetsApi` (list/get/create/update/remove/chunk/parse), `documentsApi.list({datasetId})`, `upload(file, {parserName, datasetId})`, `move(ids, datasetId)`; query key `datasets`, `datasetList`, `dataset(id)`, `documentList(datasetId)`; route `#documents/<id>` có pushState trong `AdminShell`. Phục vụ phần điều hướng của `AC-08`.
- Phạm vi file được sửa: `frontend/src/api/datasets.js` (mới), `frontend/src/api/documents.js`, `frontend/src/api/index.js`, `frontend/src/api/queryClient.js`, `frontend/src/lib/appRoute.js`, `frontend/src/lib/appRoute.test.js`, `frontend/src/admin/AdminShell.jsx`, `frontend/src/admin/AdminApp.test.jsx` (nếu cần).
- Phụ thuộc: hợp đồng S-04 (bắt đầu được với mock khi hợp đồng đã chốt).
- Đầu ra/bàn giao: `AdminShell` render `<DatasetsPage datasetId onOpenDataset onBackToList />`.
- Người nhận: S-06, S-07.

### S-06 — Frontend: trang danh sách dataset và hộp thoại dataset

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `DatasetsPage` (chọn danh sách hay chi tiết), `DatasetListView`, `DatasetCard`, `DatasetFormModal`, `DeleteDatasetModal`, menu Bảo trì, CSS responsive sáng/tối. Phục vụ `AC-07`.
- Phạm vi file được sửa: `frontend/src/datasets/DatasetsPage.jsx`, `frontend/src/datasets/DatasetListView.jsx`, `frontend/src/datasets/DatasetCard.jsx`, `frontend/src/datasets/DatasetFormModal.jsx`, `frontend/src/datasets/DeleteDatasetModal.jsx`, `frontend/src/datasets/DatasetListView.test.jsx` (đều mới), `frontend/src/styles/datasets.css` (mới), `frontend/src/styles/index.css` (thêm import).
- Phụ thuộc: S-05.
- Đầu ra/bàn giao: `DatasetsPage` truyền `dataset` (DatasetItem) và `onBack` vào `DatasetView`.
- Người nhận: S-07, verifier.

### S-07 — Frontend: trang tài liệu trong dataset

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `DatasetView` nhận `dataset`; danh sách/upload/banner job theo dataset; header thống kê và breadcrumb; nút chia đoạn/parse theo dataset; bulk “Chuyển sang dataset…” (`MoveDocumentsModal`); gỡ toggle phiên (D-04) và hai nút toàn kho (đã chuyển sang Bảo trì); nhãn quay lại trong `DocumentView`/`MarkdownEditorView`. Phục vụ `AC-08`.
- Phạm vi file được sửa: `frontend/src/DatasetView.jsx`, `frontend/src/DatasetView.parseJobs.test.jsx`, `frontend/src/datasets/MoveDocumentsModal.jsx` (mới), `frontend/src/datasets/MoveDocumentsModal.test.jsx` (mới), `frontend/src/DocumentView.jsx` (chỉ prop nhãn quay lại), `frontend/src/styles/dataset.css`, `frontend/src/styles/responsive.css` (nếu cần).
- Phụ thuộc: S-05. Dùng `DatasetsPage` của S-06 để tích hợp (có thể làm song song với S-06 vì không chung file).
- Đầu ra/bàn giao: trang tài liệu hoạt động trong dataset, ảnh chụp ở 360/768/1280 sáng/tối lưu tại `evidence/`.
- Người nhận: verifier.

### S-08 — Tài liệu dự án

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: cập nhật README: bảng API (route dataset, `dataset_id`), mục hướng dẫn dùng màn Dataset và cấu trúc `data/datasets/<id>/`.
- Phạm vi file được sửa: `README.md`.
- Phụ thuộc: S-04, S-07.
- Đầu ra/bàn giao: README khớp hành vi mới.
- Người nhận: reviewer.

### S-09 — Kiểm chứng và review

- Agent: `claude-code`
- Trạng thái: `in_progress`
- Mục tiêu: chạy kiểm tra cho `AC-01`…`AC-09`, ghi `verification.md`, review diff và ghi `review.md`.
- Phạm vi file được sửa: `.agents/tasks/2026-11-03-multi-dataset/verification.md`, `.agents/tasks/2026-11-03-multi-dataset/review.md`, `.agents/tasks/2026-11-03-multi-dataset/evidence/`.
- Phụ thuộc: S-01…S-08 đã tích hợp.
- Đầu ra/bàn giao: kết luận verification và review.
- Người nhận: coordinator.

## Hợp đồng dùng chung

- API/schema: xem mục “Hợp đồng API”. Bên cung cấp S-04, bên sử dụng S-05…S-07. Đổi hợp đồng thì S-04 cập nhật mục này và gửi `MSG-*` trong `implementation.md`.
- Hằng số chung: `DEFAULT_DATASET_ID = "default"` (backend `app/db/models.py`, frontend `api/datasets.js`).
- File mã nguồn dùng chung và người sửa:
  - `backend/app/db/repositories.py`: chỉ S-01 sửa. S-02/S-04 cần hàm mới thì gửi yêu cầu cho S-01.
  - `backend/app/api/routes.py`, `schemas.py`: chỉ S-04.
  - `frontend/src/admin/AdminShell.jsx`, `api/*`: chỉ S-05.
  - `frontend/src/DatasetView.jsx`: chỉ S-07.
- Lượt ghi năm file task: coordinator ghi `task.md`/`plan.md`. Mỗi S-* chỉ ghi mục của mình trong `implementation.md`. S-09 ghi `verification.md` và `review.md`. Ghi tuần tự, đọc bản mới nhất trước khi sửa.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi kiểm chứng: `AC-01`…`AC-09`.
  - Backend: `cd backend && python -m pytest`.
  - Migration: chạy `alembic upgrade head` rồi `downgrade -1` rồi `upgrade head` trên bản sao DB Postgres có dữ liệu (docker compose). Kiểm tra số tài liệu/chunk/embedding trước và sau.
  - Eval `AC-05`: `cd backend && python -m scripts.eval_retrieval --mode bm25|vector|hybrid`, so với `documents/rag-eval/baseline_*.json`. Cần Postgres + embedding key; thiếu môi trường thì ghi `blocked`, không ghi `passed`.
  - Frontend: `cd frontend && npm test && npm run build && node scripts/check-bundle.mjs`.
  - Thủ công: tạo 2 dataset, tải cùng một tên file vào cả hai, chuyển tài liệu, tắt một dataset rồi hỏi chat câu chỉ dataset đó trả lời được, xóa dataset. Chụp màn hình 360/768/1280 sáng/tối.
- Reviewer: `claude-code`; phạm vi review: toàn bộ diff `feat/multi-dataset` so với `dev`. Trọng tâm: migration, xóa file (RK-02), transaction chuyển/xóa, bộ lọc retrieval, quyền admin.
- Hình thức review: `self_review` (nếu có agent khác review thì đổi thành `independent`).
- Người xử lý nhận xét: agent của S-* tương ứng; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. S-01 (nền DB). Chạy `pytest` để bảo đảm không vỡ test cũ.
2. S-02 và S-03 song song (không chung file), đều dựa trên S-01.
3. S-04 tích hợp S-02 + S-03. **Mốc 1**: backend chạy đủ test, UI cũ vẫn dùng được với dataset mặc định.
4. S-05 → S-06 và S-07 song song → tích hợp `DatasetsPage` + `DatasetView`. **Mốc 2**.
5. S-08 cập nhật README.
6. S-09: verifier chạy kiểm tra trên bản đã tích hợp. Reviewer ghi `R-*`, agent phụ trách sửa, verifier chạy lại phần bị ảnh hưởng, reviewer xác nhận.
7. Coordinator đối chiếu `AC-*` và review `approved` rồi đóng task, merge `feat/multi-dataset` vào `dev` khi người dùng yêu cầu.

## Rủi ro và điều chỉnh kế hoạch

- RK-01: lọc `WHERE` với HNSW. pgvector lọc **sau** khi lấy `ef_search` ứng viên, nên khi phần lớn chunk thuộc dataset đã tắt có thể trả ít hơn `top_k`. Xử lý: giữ đường nhanh khi không cần lọc; bật `hnsw.iterative_scan` (pgvector ≥ 0.8) cho truy vấn có lọc; nếu phiên bản thấp hơn thì tăng `hnsw.ef_search` trong transaction. Verifier kiểm tra bằng test có dataset tắt chiếm đa số. Phụ trách: S-03.
- RK-02 (**nghiêm trọng**): `resolve_source_path` hiện tìm file theo tên bằng `rglob`. Khi đã có file trùng tên ở nhiều dataset, xóa hoặc tải một tài liệu bị mất file có thể đụng file của dataset khác. Xử lý theo mục “Gia cố `resolve_source_path`”, kèm test riêng. Phụ trách: S-02.
- RK-03: ID tài liệu/chunk cũ (theo đường dẫn) và mới (uuid / theo `document_id`) cùng tồn tại. Script trong `documents/rag-eval/*/experiments/` có thể giả định định dạng ID cũ. Xử lý: không đổi ID đã có; ghi chú trong README; verifier chạy lại eval. Phụ trách: S-02/S-09.
- RK-04: backend đã cập nhật mã nhưng chưa chạy migration thì `init_db()` (`create_all`) tạo bảng `datasets` nhưng không thêm cột `documents.dataset_id`, làm truy vấn lỗi. `docker-entrypoint.sh` đã chạy `alembic upgrade head` trước. Dev chạy tay thì README nhắc chạy migration. Migration phải chịu được trường hợp bảng đã có sẵn. Phụ trách: S-01/S-08.
- RK-05: job parse của tài liệu đang chuyển dataset sẽ ghi lại `source_path` cũ (đường dẫn chốt lúc enqueue). Xử lý: `move` trả 409 khi tài liệu có job đang chạy; xóa dataset cũng 409 khi còn job. Phụ trách: S-02/S-04.
- RK-06: BM25 tính IDF trên tập chunk đang bật, nên bật/tắt dataset làm điểm BM25 thay đổi nhẹ. Đây là hành vi mong muốn, ghi trong README. Khi mọi dataset bật thì không đổi so với baseline.
- RK-07: `DatasetView.jsx` dài 1090 dòng. Sửa lớn dễ làm vỡ luồng job nền đã có test. Xử lý: giữ file, chỉ thêm prop `dataset` và tách phần mới sang `frontend/src/datasets/`; chạy lại `DatasetView.parseJobs.test.jsx`. Phụ trách: S-07.
- RK-08: đổi tên/di chuyển file trên Windows có thể lỗi khi file đang bị mở (trình xem PDF inline). Xử lý: bắt `OSError`, rollback DB và trả 409 “File đang được sử dụng”. Phụ trách: S-02.
