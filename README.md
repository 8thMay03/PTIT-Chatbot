# PTIT RAG Chatbot

Chatbot hỏi đáp tiếng Việt dựa trên tài liệu nội bộ của Học viện Công nghệ Bưu chính Viễn thông (PTIT). Hệ thống sử dụng Retrieval-Augmented Generation (RAG), kết hợp semantic search, BM25, multi-query và reranking để tìm bằng chứng trước khi sinh câu trả lời có citation.

Project gồm backend FastAPI, giao diện React/Vite, ChromaDB để lưu vector và SQLite để lưu tài liệu, chunk cùng lịch sử hội thoại.

## Tính năng chính

- Nạp tài liệu Markdown và TXT, làm sạch và chia chunk theo cấu trúc heading.
- Giữ metadata gồm tài liệu, tiêu đề, đường dẫn mục và vị trí chunk.
- Hybrid retrieval kết hợp vector search và BM25 bằng Reciprocal Rank Fusion.
- BM25 được xây một lần trong bộ nhớ, tái sử dụng giữa các truy vấn và tự vô hiệu hóa sau khi ingest.
- Chuẩn hóa câu hỏi tiếng Việt, mở rộng viết tắt và xử lý câu hỏi nối tiếp.
- Multi-query retrieval để tăng khả năng tìm đúng bằng chứng.
- Rerank bằng heuristic hoặc CrossEncoder đa ngôn ngữ.
- Confidence gate từ chối trả lời khi context không đủ mạnh.
- Trả lời bằng tiếng Việt kèm citation, không công khai đường dẫn hay ID nội bộ.
- Ghi nhớ các tin nhắn gần nhất trong cùng một cuộc hội thoại.
- Streaming câu trả lời từ backend và hiệu ứng hiển thị từng ký tự trên giao diện.
- Lưu thông tin debug của từng bước retrieval để phân tích lỗi.
- Đánh giá deterministic và đánh giá ngữ nghĩa bằng Ragas.

## Kiến trúc

```mermaid
flowchart LR
    D["Tài liệu Markdown/TXT"] --> I["Clean & chunk theo heading"]
    I --> E["Embedding"]
    E --> V["ChromaDB"]
    I --> S["SQLite"]

    Q["Câu hỏi"] --> W["Rewrite & multi-query"]
    W --> VS["Vector search"]
    W --> B["BM25 in-memory"]
    V --> VS
    S --> B
    VS --> RRF["Reciprocal Rank Fusion"]
    B --> RRF
    RRF --> RR["Reranker"]
    RR --> C["Confidence gate"]
    C --> L["LLM + citation"]
    L --> UI["React streaming UI"]
```

Luồng xử lý một câu hỏi:

1. Chuẩn hóa câu hỏi và bổ sung ngữ cảnh hội thoại khi cần.
2. Sinh một hoặc nhiều biến thể truy vấn.
3. Chạy vector search và BM25 cho từng truy vấn.
4. Hợp nhất kết quả bằng RRF, sau đó rerank candidate.
5. Loại context yếu bằng ngưỡng confidence.
6. Sinh câu trả lời từ context đã chọn và gắn citation.
7. Stream nội dung về frontend, sau đó lưu câu trả lời và nguồn vào SQLite.

## Cấu trúc thư mục

```text
PTIT Chatbot/
├── backend/
│   ├── app/
│   │   ├── api/          # Routes và schema HTTP
│   │   ├── core/         # Cấu hình môi trường
│   │   ├── db/           # SQLAlchemy models và repositories
│   │   ├── embeddings/   # OpenAI, Sentence Transformers, hash embedding
│   │   ├── generation/   # Prompt, LLM, citation, rewrite và RAG chain
│   │   ├── ingestion/    # Loader, cleaner, chunker và ingest pipeline
│   │   ├── retrieval/    # BM25, hybrid search, multi-query và reranker
│   │   ├── vectordb/     # ChromaDB adapter
│   │   └── main.py       # FastAPI entry point
│   ├── scripts/          # Ingest và evaluation CLI
│   └── tests/            # Unit tests và evaluation fixtures
├── data/                 # Kho tài liệu nguồn
├── frontend/             # React/Vite chat UI
├── .env.example
└── README.md
```

## Yêu cầu

- Python 3.10 trở lên.
- Node.js 18 trở lên và npm.
- OpenAI API key nếu dùng OpenAI embedding, sinh câu trả lời hoặc Ragas.

Không bắt buộc API key nếu chạy local với `EMBEDDING_PROVIDER=hash`. Khi đó chatbot trả về các đoạn trích liên quan thay vì câu trả lời do LLM tổng hợp.

## Cài đặt nhanh

### 1. Cấu hình môi trường

Tại thư mục gốc của project:

```powershell
Copy-Item .env.example .env
```

Để dùng OpenAI, cập nhật tối thiểu:

```env
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

Để chạy hoàn toàn local mà không cần API key:

```env
OPENAI_API_KEY=
EMBEDDING_PROVIDER=hash
```

### 2. Cài và chạy backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m scripts.ingest
uvicorn app.main:app --reload --port 8000
```

Backend chạy tại `http://localhost:8000`; Swagger UI nằm tại `http://localhost:8000/docs`.

### 3. Cài và chạy frontend

Mở terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

Giao diện chạy tại `http://localhost:5173` và mặc định gọi backend ở `http://localhost:8000/api`.

Nếu backend dùng địa chỉ khác, tạo `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Nạp dữ liệu

Đặt tài liệu `.md` hoặc `.txt` trong thư mục `data/`, sau đó chạy:

```powershell
cd backend
python -m scripts.ingest
```

Mặc định dữ liệu được lưu tại:

- Vector: `backend/storage/chroma`
- Metadata và hội thoại: `backend/storage/ptit_chatbot.db`

Pipeline sẽ xây lại Chroma collection và cập nhật bảng `documents`, `chunks`. BM25 không được dựng ở mỗi request: index được tạo lười ở lần tìm kiếm đầu tiên, dùng lại trong bộ nhớ và được đánh dấu cần rebuild sau một lần ingest thành công.

Sau khi thay đổi embedding provider hoặc model, cần ingest lại toàn bộ tài liệu.

## Chạy bằng Docker

Tạo file cấu hình rồi build và chạy cả frontend lẫn backend:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- Giao diện: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

Ở lần chạy đầu tiên, backend tự ingest tài liệu nếu volume lưu trữ còn trống. ChromaDB và SQLite được giữ trong named volume `backend_storage`, còn thư mục `data/` được mount read-only vào container.

Sau khi thay đổi tài liệu, chạy ingest lại:

```powershell
docker compose exec backend python -m scripts.ingest
```

Dừng hệ thống nhưng giữ dữ liệu:

```powershell
docker compose down
```

Muốn xóa luôn vector và lịch sử hội thoại để ingest mới hoàn toàn:

```powershell
docker compose down -v
```

### Embedding local bằng Sentence Transformers

```powershell
cd backend
pip install -e ".[ml]"
```

```env
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Nếu không tải được Sentence Transformer, implementation hiện tại fallback về hash embedding.

## Cấu hình RAG

Các giá trị mặc định quan trọng trong `.env.example`:

```env
CHUNK_SIZE=900
CHUNK_OVERLAP=150

HYBRID_VECTOR_WEIGHT=0.65
HYBRID_CANDIDATE_MULTIPLIER=4
HYBRID_RRF_K=60

RETRIEVAL_MIN_VECTOR_SCORE=0.30
RETRIEVAL_MIN_BM25_SCORE=2.0

QUERY_REWRITE_USE_LLM=false
MULTI_QUERY_ENABLED=true
MULTI_QUERY_USE_LLM=false
MULTI_QUERY_COUNT=3

RERANKER_ENABLED=true
RERANKER_PROVIDER=heuristic
RERANKER_CANDIDATE_MULTIPLIER=3
RERANKER_VECTOR_WEIGHT=0.45
RERANKER_BM25_WEIGHT=0.35
RERANKER_LEXICAL_WEIGHT=0.20

CONVERSATION_MEMORY_ENABLED=true
CONVERSATION_MEMORY_MAX_MESSAGES=6
CONVERSATION_MEMORY_MAX_CHARS=6000
```

`QUERY_REWRITE_USE_LLM` và `MULTI_QUERY_USE_LLM` mặc định tắt để giảm latency và chi phí. Khi bật, hệ thống tự fallback về rule-based nếu lời gọi model thất bại.

Để dùng CrossEncoder:

```env
RERANKER_PROVIDER=cross-encoder
RERANKER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
```

Cần cài optional dependency `.[ml]`. Nếu model reranker lỗi, hệ thống fallback về heuristic.

## API

### Health check

```http
GET /api/health
```

### Ingest tài liệu

```http
POST /api/ingest
```

### Chat thông thường

```http
POST /api/chat
Content-Type: application/json
```

```json
{
  "message": "Sinh viên bị cảnh báo học tập khi nào?",
  "conversation_id": null,
  "top_k": 4
}
```

Response:

```json
{
  "conversation_id": "...",
  "answer": "... [1]",
  "sources": [
    {
      "citation_id": 1,
      "source_name": "so-tay-sinh-vien-d21.md",
      "heading": "Điều 33. Cảnh báo kết quả học tập",
      "section_path": "..."
    }
  ]
}
```

### Chat streaming

```http
POST /api/chat/stream
Content-Type: application/json
Accept: application/x-ndjson
```

Endpoint trả các JSON event phân cách bằng newline:

```json
{"type":"start","conversation_id":"..."}
{"type":"delta","content":"Sinh viên"}
{"type":"delta","content":" bị cảnh báo..."}
{"type":"done","answer":"Sinh viên bị cảnh báo... [1]","sources":[],"conversation_id":"..."}
```

Frontend sử dụng các `delta` để hiển thị hiệu ứng sinh câu trả lời từng ký tự. Event `done` chứa câu trả lời đã chuẩn hóa citation và danh sách nguồn cuối cùng.

## Conversation memory và debug retrieval

Khi request tiếp theo gửi lại `conversation_id`, backend đọc các tin nhắn gần nhất trong SQLite để hiểu câu hỏi nối tiếp. Lịch sử chỉ được dùng để giải nghĩa truy vấn, không được phép trở thành nguồn dữ kiện cho câu trả lời.

Mỗi user message lưu `retrieval_debug` trong JSON metadata, gồm:

- Câu hỏi gốc và câu hỏi sau rewrite.
- Danh sách multi-query.
- Candidate trước rerank.
- Chunk được chọn sau rerank.
- Điểm vector, BM25, RRF và rerank.
- Kết quả confidence gate.

Dữ liệu debug không được trả qua public chat response.

## Kiểm thử

```powershell
cd backend
pytest
```

Các test bao phủ chunking, embedding, Chroma, hybrid retrieval, BM25 cache, query rewriting, multi-query, reranker, confidence, citation, conversation memory, schema API và RAG chain.

## Đánh giá chất lượng

### Evaluation deterministic

Evaluator mặc định sử dụng `tests/fixtures/ptit_faq.json` và báo cáo Retrieval Hit@K, MRR, keyword recall, citation validity và answer quality.

```powershell
cd backend
python -m scripts.evaluate `
  --dataset tests/fixtures/ptit_faq.json `
  --top-k 4 `
  --output evaluation-report.json
```

Có thể dùng làm quality gate trong CI:

```powershell
python -m scripts.evaluate `
  --fail-below-hit-rate 0.80 `
  --fail-below-answer-quality 0.70
```

Không có API key thì evaluator chấm câu trả lời trích xuất; có API key thì chấm kết quả do model sinh.

### Evaluation bằng Ragas

Cài dependency:

```powershell
cd backend
pip install -e ".[eval]"
```

Project có bộ 100 câu hỏi được đối chiếu với tài liệu nguồn tại `tests/fixtures/ptit_ragas_100.json`.

```powershell
python -m scripts.evaluate_ragas `
  --dataset tests/fixtures/ptit_ragas_100.json `
  --top-k 4 `
  --judge-model gpt-4.1-mini `
  --output ragas-report-100.json
```

Các metric:

- `context_precision`: context được lấy về có liên quan và được xếp hạng tốt hay không.
- `faithfulness`: các nhận định trong câu trả lời có được context hỗ trợ hay không.
- `answer_correctness`: câu trả lời có đúng so với reference answer hay không.
- `ragas_score`: trung bình các metric hợp lệ phía trên.

Thêm `--fail-below 0.75` để trả exit code lỗi khi chất lượng thấp hơn ngưỡng. Ragas dùng LLM làm judge nên cần `OPENAI_API_KEY` và phát sinh chi phí API.

## Database

SQLite mặc định gồm các bảng:

- `documents`: tài liệu nguồn và content hash.
- `chunks`: nội dung chunk, metadata và vector ID.
- `conversations`: phiên hội thoại.
- `messages`: tin nhắn user/assistant cùng metadata debug.
- `message_sources`: chunk được dùng để tạo từng câu trả lời.

Có thể đổi `DATABASE_URL` sang PostgreSQL vì tầng truy cập dữ liệu sử dụng SQLAlchemy. Khi đổi database, cần cài thêm driver tương ứng.

## Lưu ý triển khai

- `POST /api/ingest` hiện chưa có xác thực; không nên công khai endpoint này trên Internet.
- Cần giới hạn quyền truy cập theo `user_id`/`conversation_id` trước khi dùng cho nhiều người dùng thật.
- Cấu hình CORS bằng `CORS_ORIGINS`; không dùng wildcard trong production nếu gửi credential.
- Không commit `.env`, API key, thư mục storage hay dữ liệu hội thoại.
- Nên chạy nhiều worker, reverse proxy hỗ trợ streaming và đặt `X-Accel-Buffering: no` nếu dùng Nginx.
- Tài liệu sổ tay khóa 2021 có thể không phản ánh quy định hiện hành; cần cập nhật nguồn và ingest lại khi quy định thay đổi.

## Công nghệ sử dụng

- Backend: FastAPI, Pydantic, SQLAlchemy, OpenAI SDK.
- Retrieval: ChromaDB, rank-bm25, Reciprocal Rank Fusion.
- ML tùy chọn: Sentence Transformers, CrossEncoder.
- Frontend: React 18, Vite, Lucide React.
- Evaluation: pytest và Ragas.
