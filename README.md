# PTIT RAG Chatbot

PTIT RAG Chatbot là hệ thống hỏi đáp tiếng Việt dành cho sinh viên Học viện Công nghệ Bưu chính Viễn thông (PTIT). Hệ thống sử dụng kiến trúc Retrieval-Augmented Generation (RAG) để tìm kiếm thông tin trong tài liệu nội bộ, chọn các đoạn bằng chứng phù hợp và tạo câu trả lời có trích dẫn nguồn.

Thay vì để mô hình trả lời hoàn toàn từ kiến thức có sẵn, chatbot chỉ sinh câu trả lời dựa trên context được truy xuất từ kho tài liệu. Cách tiếp cận này giúp giảm hallucination, tăng khả năng kiểm chứng và phù hợp với các câu hỏi về quy chế, học phí, học phần, thi cử, thủ tục sinh viên và tốt nghiệp.

## Tính năng chính

- Hỏi đáp tiếng Việt trong phạm vi tài liệu PTIT.
- Nạp tài liệu Markdown và TXT, chia nhỏ theo cấu trúc tiêu đề.
- Parent-child chunking để vừa tìm kiếm chính xác vừa giữ đủ ngữ cảnh.
- Hybrid retrieval kết hợp vector search và BM25.
- Multi-query, Reciprocal Rank Fusion và reranking kết quả.
- Guardrail chặn câu hỏi ngoài phạm vi và prompt injection.
- Confidence gate từ chối trả lời khi không tìm thấy bằng chứng đủ mạnh.
- Câu trả lời có citation tới tài liệu, mục, Điều, Khoản hoặc Điểm.
- Streaming câu trả lời trên giao diện web.
- Quản lý tài liệu trên giao diện: tải lên, xem trước, tải xuống và xóa.
- Lưu lịch sử hội thoại và thông tin debug retrieval.
- Đánh giá chất lượng bằng Ragas.

## Tech stack

| Thành phần | Công nghệ |
|---|---|
| Frontend | React 18, Vite 5, Lucide React |
| Backend API | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| LLM | Đa provider: OpenAI (`gpt-4.1-mini`), Google Gemini, Azure OpenAI, OpenAI-Compatible (Ollama, vLLM) |
| Embedding | OpenAI `text-embedding-3-small`; hỗ trợ Sentence Transformers hoặc hash embedding |
| Vector database | **`pgvector`** (Tích hợp trực tiếp trong PostgreSQL 16 với HNSW Index) |
| Keyword retrieval | BM25 với `rank-bm25` |
| Data storage & Migration | PostgreSQL 16 với `pgvector` (Production) / SQLite (Dev), SQLAlchemy 2.0, Alembic, Psycopg 3 |
| Reranking | Heuristic reranker hoặc CrossEncoder |
| Evaluation | Ragas, pytest |
| Deployment | Docker, Docker Compose, Nginx |

## Kiến trúc hệ thống

### Luồng nạp dữ liệu

```mermaid
flowchart LR
    A["Tài liệu PTIT<br/>Markdown / TXT"] --> B["Loader & Cleaner"]
    B --> C["Parent-child Chunking"]
    C --> D["Embedding"]
    D --> E[("PostgreSQL 16<br/>All-in-One: Metadata + pgvector HNSW")]
    C --> F["BM25 Index"]
```

- Tài liệu trong thư mục `data/` được đọc và làm sạch.
- Nội dung được chia thành parent chunk và child chunk, giữ metadata về tiêu đề và vị trí.
- Child chunk được embedding và lưu trực tiếp vào cột `embedding` (kiểu `vector(1536)`) trên bảng `chunks` trong PostgreSQL.
- Toàn bộ tài liệu, metadata, trích dẫn và vector embeddings được ghi trong một **transaction duy nhất** của PostgreSQL (đồng bộ tuyệt đối).

### Luồng xử lý câu hỏi

```mermaid
flowchart TD
    U["Người dùng"] --> UI["React Chat UI"]
    UI --> API["FastAPI"]
    API --> GR{"Scope & Security<br/>Guardrail"}

    GR -->|"Ngoài phạm vi"| REFUSE["Câu từ chối cố định"]
    GR -->|"Hợp lệ"| QR["Query Rewrite & Multi-query"]

    QR --> VS["Vector Search (pgvector HNSW)"]
    QR --> BM["BM25 Search"]
    VS --> RRF["Reciprocal Rank Fusion"]
    BM --> RRF
    RRF --> RR["Reranker"]
    RR --> PC["Khôi phục Parent Context"]
    PC --> CF{"Confidence Gate"}

    CF -->|"Context yếu"| NOCTX["Không tìm thấy thông tin"]
    CF -->|"Context đủ mạnh"| LLM["LLM sinh câu trả lời<br/>theo System Prompt"]
    LLM --> CIT["Chuẩn hóa Citation"]
    CIT --> API
    API -->|"NDJSON Streaming"| UI

    API --> DB[("PostgreSQL<br/>Hội thoại, Tin nhắn, Trích dẫn")]
```

Quy trình chính:

1. Guardrail kiểm tra phạm vi PTIT và dấu hiệu prompt injection.
2. Câu hỏi hợp lệ được chuẩn hóa và tạo nhiều truy vấn tìm kiếm.
3. Vector search và BM25 chạy song song trên kho tài liệu.
4. Kết quả được hợp nhất bằng RRF và sắp xếp lại bằng reranker.
5. Confidence gate kiểm tra độ mạnh của context.
6. LLM chỉ sử dụng context được cung cấp để trả lời.
7. Citation được kiểm tra, chuẩn hóa và trả về giao diện theo dạng streaming.

## Cấu trúc dự án

```text
PTIT Chatbot/
├── backend/
│   ├── alembic/          # Alembic schema migrations
│   │   ├── versions/     # Các revision migration (0001_initial_schema...)
│   │   └── env.py        # Cấu hình dynamic DB URL và metadata
│   ├── alembic.ini       # File cấu hình Alembic
│   ├── app/
│   │   ├── api/          # API routes và request/response schema
│   │   ├── core/         # Cấu hình hệ thống & connection pooling
│   │   ├── db/           # PostgreSQL/SQLAlchemy models, repositories, session
│   │   ├── embeddings/   # Các embedding provider
│   │   ├── generation/   # RAG chain, prompt, LLM và citation
│   │   ├── guardrails/   # Scope filter và prompt-injection protection
│   │   ├── ingestion/    # Đọc, làm sạch và chia tài liệu
│   │   ├── parsers/      # Interface, registry, text, Docling và LlamaParse parser
│   │   ├── retrieval/    # BM25, hybrid retrieval, RRF và reranker
│   │   └── vectordb/     # ChromaDB adapter
│   ├── scripts/          # Ingest, data migration (SQLite -> Postgres) và evaluation
│   └── tests/            # Unit test, integration test và evaluation dataset
├── data/                 # Tài liệu PTIT
├── frontend/             # React/Vite web application
├── docker-compose.yml    # Compose orchestration (PostgreSQL, Backend, Frontend)
├── .env.example          # Mẫu biến môi trường Production & Dev
└── README.md
```

## Cách chạy dự án

### Yêu cầu

- Python 3.10 trở lên.
- Node.js 18 trở lên.
- npm.
- OpenAI API key nếu sử dụng OpenAI cho embedding, sinh câu trả lời hoặc đánh giá Ragas.
- Docker Desktop nếu chạy bằng Docker Compose.

### 1. Cấu hình môi trường

Tại thư mục gốc:

```powershell
Copy-Item .env.example .env
```

Cập nhật cấu hình trong `.env`:

```env
# 1. Sử dụng OpenAI (mặc định)
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1-mini

# 2. Sử dụng Google Gemini
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your-gemini-api-key
# GEMINI_MODEL=gemini-1.5-flash

# 3. Sử dụng Azure OpenAI
# LLM_PROVIDER=azure
# AZURE_OPENAI_API_KEY=your-azure-api-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
# AZURE_OPENAI_API_VERSION=2024-02-15-preview

# 4. Sử dụng mô hình cục bộ / OpenAI-Compatible (Ollama, vLLM, LocalAI)
# LLM_PROVIDER=openai_compatible
# OPENAI_COMPATIBLE_BASE_URL=http://localhost:11434/v1
# OPENAI_COMPATIBLE_API_KEY=ollama
# OPENAI_COMPATIBLE_MODEL=llama3

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

Hệ thống cho phép chuyển đổi provider linh hoạt qua biến môi trường `LLM_PROVIDER` mà không cần thay đổi bất kỳ dòng code nào trong RAG chain.

Các cấu hình RAG mặc định đã được khai báo trong `.env.example`.

### 2. Chạy backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,docling]"
python -m scripts.ingest
uvicorn app.main:app --reload --port 8000
```

Tài liệu hỗ trợ: `.md`, `.txt`, `.pdf`, `.docx`. File PDF/DOCX được [Docling](https://github.com/docling-project/docling) chuyển sang Markdown (giữ heading và bảng), kết quả cache tại `backend/storage/converted/` theo hash nội dung file, nên chỉ chuyển đổi lại khi file thay đổi. Lần chạy đầu Docling sẽ tải model layout/bảng từ HuggingFace. PDF scan không có lớp text cần bật `DOCLING_OCR_ENABLED=true`. File `.doc` (Word 97-2003) chưa được hỗ trợ, hãy lưu lại dưới dạng `.docx`.

#### Hai bước: parse và chia đoạn

Ingest tách thành hai bước để có thể kiểm tra, sửa Markdown và chia đoạn lại mà không phải parse lại:

1. **Parse**: parser (+ chuẩn hóa heading) tạo Markdown và lưu vào `documents.parsed_text`; tài liệu chuyển trạng thái `parsed`. Các đoạn cũ (nếu có) vẫn phục vụ hỏi đáp cho tới khi chia đoạn lại. Parse lại ra đúng nội dung cũ thì tài liệu giữ `active`.
2. **Chia đoạn**: đọc `parsed_text`, chia đoạn, tạo embeddings rồi thay toàn bộ đoạn của tài liệu trong một transaction; trạng thái chuyển `active`. Bước này không đọc file gốc hay gọi parser. Nếu Markdown bị parse lại/sửa trong lúc đang chia đoạn, API trả 409 và giữ nguyên các đoạn cũ.

Upload (`POST /api/documents`) **chỉ parse** và dừng ở `parsed`: mở tài liệu, kiểm tra bản Markdown rồi bấm **Chia đoạn**. Upload được parse trong vùng tạm trước khi thay file nguồn; nếu conversion hoặc transaction PostgreSQL thất bại, file cũ và dữ liệu đã lưu được giữ nguyên, upload mới thất bại không để lại file trong kho tài liệu.

Khi parser đọc sai, nút **Sửa Markdown** mở màn soạn Markdown thô cạnh bản render để đối chiếu. Lưu chỉ ghi `parsed_text` (đánh dấu `metadata.markdown_edited`) và đưa tài liệu về `parsed`; kho tri thức dùng bản mới sau khi bấm Chia đoạn. **Nạp lại toàn bộ** và `--stage parse` giữ nguyên bản sửa tay; **Parse lại** một tài liệu thì ghi đè bản sửa tay (giao diện cảnh báo trước).

| API | Bước |
| --- | --- |
| `POST /api/documents` | Tải lên + parse |
| `POST /api/documents/{id}/parse?parser_name=` | Parse lại một tài liệu |
| `GET` / `PUT /api/documents/{id}/markdown` | Đọc / lưu Markdown sửa tay (`PUT` nhận `base_hash` để tránh ghi đè thay đổi của người khác, lệch thì 409) |
| `POST /api/documents/{id}/chunk` | Chia đoạn + embed một tài liệu |
| `POST /api/ingest/chunk` | Chia đoạn lại mọi tài liệu từ Markdown đã lưu, ví dụ sau khi đổi `CHUNK_SIZE`; trả thêm `skipped` |
| `POST /api/ingest` | Nạp lại toàn bộ: parse + chia đoạn mọi file trong `DOCUMENTS_PATH` |

Tài liệu được index trước migration `0004_document_parsed_text` chưa có `parsed_text`: vẫn xem và hỏi đáp bình thường, nhưng phải parse lại (hoặc Nạp lại toàn bộ một lần) trước khi chia đoạn riêng hoặc sửa Markdown; `POST /api/ingest/chunk` bỏ qua và báo số tài liệu này.

Rebuild toàn bộ chỉ thay knowledge base sau khi mọi tài liệu có định dạng hỗ trợ đã đọc thành công và có nội dung. Nếu một file lỗi hoặc rỗng, rebuild dừng và giữ nguyên dữ liệu đã index; `POST /api/ingest` trả HTTP 422 kèm tên file cần xử lý. Chuẩn hóa bảng chỉ rút gọn khoảng trắng, giữ nguyên các ô có giá trị giống nhau.

Parser nằm riêng trong `backend/app/parsers/`: `base.py` định nghĩa interface `DocumentParser` và lỗi `DocumentParseError`, `registry.py` chọn implementation theo định dạng hoặc tên, `text.py` đọc MD/TXT, `docling.py` parse PDF/DOCX và quản lý cache. Bước parse chỉ gọi `read_document_text()` để nhận text/Markdown và lưu vào `documents.parsed_text`; bước chia đoạn đọc lại bản đã lưu để chunking, embedding và lưu dữ liệu.

Để thêm parser, implement `name`, `extensions` (các suffix chữ thường dạng `.pdf`) và `parse(path, *, convert=True) -> str | None`, rồi đăng ký instance trong `app/parsers/__init__.py`. Loader và upload lấy danh sách định dạng từ registry; các định dạng binary mới được parser tự kiểm tra nội dung. Với `convert=False`, parser chỉ đọc trực tiếp hoặc dùng cache, không chạy conversion nặng.

```python
from app.parsers import read_document_text, registry

registry.register(MyPdfParser())  # Giữ parser mặc định hiện có cho các suffix trùng.
text = read_document_text(path, parser_name="my_pdf")
# Khi đăng ký, thêm default=True nếu muốn parser mới trở thành mặc định.
```

Upload dùng parser mặc định theo định dạng (hoặc parser chọn trong modal khi có nhiều lựa chọn); sau đó có thể parse lại một tài liệu bằng parser khác trong giao diện quản lý tài liệu (`GET /api/documents/{id}/parsers`, `POST /api/documents/{id}/parse?parser_name=...`). Parser đã dùng được lưu trong `documents.metadata.parser`, nên màn xem tài liệu, preview và rebuild toàn bộ tiếp tục đọc tài liệu đó bằng đúng parser này; nếu parser không còn được đăng ký thì dùng parser mặc định và ghi cảnh báo. `app.ingestion.converters` giữ các public import cũ để tương thích, còn parser mới được triển khai trong `app.parsers`.

Docling chạy nhanh hơn nhiều trên GPU NVIDIA. `pip install` mặc định có thể kéo torch bản CPU, khi đó cài lại torch bản CUDA (chọn bản cu khớp driver, xem `nvidia-smi`), rồi kiểm tra bằng `python -c "import torch; print(torch.cuda.is_available())"`:

```powershell
pip install --force-reinstall --no-deps torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

`DOCLING_DEVICE=auto` (mặc định) tự dùng GPU khi có; đặt `cpu` để ép chạy CPU.

### LlamaParse (tùy chọn)

[LlamaParse](https://developers.llamaindex.ai/llamaparse/) là parser PDF/DOCX chạy trên cloud của LlamaIndex, dùng **bên cạnh** Docling cho các file Docling xử lý chưa tốt (file scan, bảng phức tạp, watermark). Docling vẫn là parser mặc định; LlamaParse chỉ xuất hiện trong danh sách parser khi được bật:

```powershell
pip install -e ".[llamaparse]"
```

```env
LLAMAPARSE_ENABLED=true
LLAMA_CLOUD_API_KEY=llx-...
LLAMAPARSE_TIER=cost_effective   # fast | cost_effective | agentic | agentic_plus
```

- Mở tài liệu trong giao diện, chọn parse lại bằng **LlamaParse**. File được tải lên LlamaCloud và tính credit theo trang (tham khảo bảng giá: fast 1, cost_effective 3, agentic 10, agentic_plus 45 credit/trang).
- Markdown được cache tại `backend/storage/converted/llamaparse/` theo hash file + tier + version + ngôn ngữ; xem lại tài liệu hoặc rebuild không gọi API lại trừ khi file hoặc cấu hình đổi.
- Lỗi key (401), hết credit (402), giới hạn tần suất (429), timeout (`LLAMAPARSE_TIMEOUT_SECONDS`, mặc định 900 giây) trả HTTP 422 với thông báo rõ ràng. SDK tự retry lỗi tạm thời (`LLAMAPARSE_MAX_RETRIES`).
- Dùng region EU: đặt `LLAMAPARSE_BASE_URL` theo hướng dẫn của LlamaCloud.

Backend:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

Có thể nạp tài liệu mới trực tiếp trên giao diện **Tài liệu**, hoặc khi file trong `data/` thay đổi thì chạy lại:

```powershell
cd backend
python -m scripts.ingest                 # parse + chia đoạn toàn bộ (mặc định, --stage all)
python -m scripts.ingest --stage parse   # chỉ parse và lưu Markdown, giữ nguyên các đoạn hiện có
python -m scripts.ingest --stage chunk   # chia đoạn lại từ Markdown đã lưu, không parse lại
```

### 3. Chạy frontend

Mở terminal mới:

```powershell
cd frontend
npm install
npm run dev
```

Giao diện chạy tại `http://localhost:5173`.

Nếu backend không chạy tại địa chỉ mặc định, tạo `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### Chạy bằng Docker Compose (PostgreSQL Production Ready)

Hệ thống đi kèm cấu hình Docker Compose đầy đủ bao gồm **PostgreSQL 16**, **FastAPI Backend** (tự động chạy Alembic migrations khi khởi động), và **React Frontend**:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Sau khi các service khởi động thành công (PostgreSQL đạt trạng thái `healthy` trước khi backend khởi chạy):

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check (bao gồm trạng thái kết nối DB): `http://localhost:8000/api/health`

Nạp lại tài liệu khi có thay đổi (thêm `--stage parse` hoặc `--stage chunk` để chạy riêng từng bước):

```powershell
docker compose exec backend python -m scripts.ingest
```

Backend dev mount trực tiếp `backend/app` và `backend/alembic`, nên khi code có migration mới mà container không khởi động lại thì chạy `docker compose exec backend python -m alembic upgrade head`.

Dừng hệ thống:

```powershell
docker compose down
```

Xóa toàn bộ dữ liệu (PostgreSQL volume `postgres_data` và ChromaDB storage):

```powershell
docker compose down -v
```

---

## Quản lý Database & Migrations (Alembic)

Dự án sử dụng **Alembic** để quản lý phiên bản cơ sở dữ liệu (schema migrations).

### 1. Áp dụng migrations (Upgrade)

Chạy migration lên phiên bản mới nhất:

```powershell
cd backend
alembic upgrade head
```

Hoặc qua Docker:

```powershell
docker compose exec backend alembic upgrade head
```

### 2. Tạo migration mới (Autogenerate)

Khi chỉnh sửa SQLAlchemy models trong `backend/app/db/models.py`:

```powershell
cd backend
alembic revision --autogenerate -m "ten_migration_mo_ta"
```

### 3. Kiểm tra trạng thái và lịch sử migration

```powershell
cd backend
alembic current
alembic history --verbose
```

---

## Chuyển dữ liệu từ SQLite sang PostgreSQL

Nếu bạn đã có dữ liệu lịch sử hội thoại, tin nhắn hoặc tài liệu trong SQLite (`backend/storage/ptit_chatbot.db`) và muốn chuyển sang PostgreSQL:

```powershell
cd backend
# 1. Quét thử và thống kê dữ liệu nguồn (Dry-run):
python -m scripts.migrate_sqlite_to_postgres --dry-run

# 2. Thực hiện chuyển dữ liệu thực tế:
python -m scripts.migrate_sqlite_to_postgres `
  --sqlite-path storage/ptit_chatbot.db `
  --postgres-url postgresql+psycopg://ptit_user:ptit_password@localhost:5432/ptit_chatbot
```

Tham số tùy chọn:
- `--truncate-target`: Xóa trắng các bảng target trên PostgreSQL trước khi insert.
- `--dry-run`: Chỉ quét và in số lượng bản ghi mà không ghi vào PostgreSQL.

---

## Hướng dẫn Backup & Restore PostgreSQL

### 1. Sao lưu cơ sở dữ liệu (Backup)

**Cách 1: Sao lưu qua Docker Compose (Khuyên dùng)**

```powershell
# Tạo bản backup nhị phân nén (custom format .dump)
docker compose exec -T postgres pg_dump -U ptit_user -d ptit_chatbot -F c -b -v > backup_ptit_chatbot.dump

# Hoặc tạo bản backup dạng Plain SQL text (.sql)
docker compose exec -T postgres pg_dump -U ptit_user -d ptit_chatbot --clean --if-exists > backup_ptit_chatbot.sql
```

**Cách 2: Sao lưu trực tiếp bằng CLI (khi có pg_dump cục bộ)**

```powershell
pg_dump -h localhost -p 5432 -U ptit_user -d ptit_chatbot -F c -b -v -f backup_ptit_chatbot.dump
```

### 2. Phục hồi cơ sở dữ liệu (Restore)

**Cách 1: Phục hồi từ file .dump qua Docker Compose**

```powershell
# Phục hồi từ bản dump nén (.dump)
cat backup_ptit_chatbot.dump | docker compose exec -T postgres pg_restore -U ptit_user -d ptit_chatbot --clean --if-exists --no-owner --no-privileges
```

**Cách 2: Phục hồi từ file Plain SQL (.sql)**

```powershell
cat backup_ptit_chatbot.sql | docker compose exec -T postgres psql -U ptit_user -d ptit_chatbot
```


## Kiểm thử

Chạy toàn bộ unit test:

```powershell
cd backend
pytest
```

Chạy riêng các test liên quan đến guardrail và generation:

```powershell
pytest tests/test_guardrails.py tests/test_rag_chain.py tests/test_prompts.py
```

## Đánh giá bằng Ragas

Cài dependency đánh giá:

```powershell
cd backend
pip install -e ".[eval]"
```

Chạy evaluation:

```powershell
python scripts/evaluate_ragas.py
```

Mặc định:

- Dataset: `backend/tests/fixtures/data.json`
- Số context lấy về: `top_k=4`
- Judge model: giá trị `RAGAS_JUDGE_MODEL` trong `.env`
- Embedding model: giá trị `RAGAS_EMBEDDING_MODEL` trong `.env`
- Báo cáo chi tiết: `backend/report.json`

Đánh giá trên dataset khác:

```powershell
python scripts/evaluate_ragas.py `
  --dataset tests/fixtures/ptit_ragas_100.json `
  --top-k 4 `
  --output report-100.json
```

## Kết quả metrics

Kết quả Ragas mới nhất được đo trên 50 câu hỏi, sử dụng `top_k=4`:

| Metric | Điểm | Ý nghĩa |
|---|---:|---|
| Context Precision | **0.90** | Mức độ liên quan và thứ hạng của context được truy xuất |
| Context Recall | **0.95** | Khả năng truy xuất đủ thông tin cần thiết từ tài liệu |
| Faithfulness | **0.93** | Mức độ các nhận định trong câu trả lời được context hỗ trợ |
| Answer Relevancy | **0.85** | Mức độ câu trả lời tập trung vào đúng câu hỏi |

Evaluation hoàn thành với `0` lỗi.

```text
context_precision    0.90
context_recall       0.95
faithfulness         0.93
answer_relevancy     0.85
```
