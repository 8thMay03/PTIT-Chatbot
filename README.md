# PTIT RAG Chatbot

Khung project RAG chatbot cho tài liệu PTIT, gồm backend FastAPI và frontend React/Vite.

## Cấu trúc

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP routes và request/response schemas
│   │   ├── core/         # Settings/env
│   │   ├── ingestion/    # Load, clean và chunk tài liệu
│   │   ├── embeddings/   # Embedding interface và model implementations
│   │   ├── vectordb/     # Vector store adapters
│   │   ├── retrieval/    # Truy vấn context từ vector store
│   │   ├── generation/   # Prompt, LLM và RAG chain
│   │   └── main.py       # FastAPI app entrypoint
│   ├── scripts/          # CLI helpers
│   └── tests/
├── data/                 # Tài liệu nguồn .md/.txt
└── frontend/             # React chat UI
```

## Chạy backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item ..\.env.example ..\.env
python -m scripts.ingest
uvicorn app.main:app --reload --port 8000
```

Backend lưu vector bằng ChromaDB trong `backend/storage/chroma`, và lưu metadata/hội thoại bằng SQLite trong `backend/storage/ptit_chatbot.db`. Backend dùng `OPENAI_API_KEY` cho cả embedding OpenAI và bước tổng hợp câu trả lời. Nếu chưa có key, đổi `EMBEDDING_PROVIDER=hash` để chạy local và API chat sẽ trả về các đoạn tài liệu liên quan nhất thay vì gọi LLM.

Retrieval dùng hybrid search: semantic vector search từ Chroma kết hợp keyword BM25 trên bảng `chunks`, sau đó hợp nhất thứ hạng bằng Reciprocal Rank Fusion. Có thể tinh chỉnh qua:

```env
HYBRID_VECTOR_WEIGHT=0.65
HYBRID_CANDIDATE_MULTIPLIER=4
HYBRID_RRF_K=60
RETRIEVAL_MIN_VECTOR_SCORE=0.30
RETRIEVAL_MIN_BM25_SCORE=2.0
QUERY_REWRITE_USE_LLM=false
```

Nếu không có chunk nào vượt ngưỡng vector hoặc BM25, chatbot không gửi context yếu cho LLM và trả về `Chưa tìm thấy thông tin này trong tài liệu.` mà không kèm citation.

Trước khi retrieval, câu hỏi tiếng Việt được chuẩn hóa và mở rộng các viết tắt phổ biến bằng rule-based rewriter. Đặt `QUERY_REWRITE_USE_LLM=true` để dùng model cấu hình trong `OPENAI_MODEL` cho bước rewrite; nếu lời gọi lỗi, hệ thống tự động dùng kết quả rule-based.

Schema SQLite ban đầu gồm:

- `documents`: tài liệu gốc trong thư mục `data/`.
- `chunks`: các đoạn văn bản đã chia nhỏ, có `vector_id` trỏ sang Chroma.
- `conversations`: phiên chat.
- `messages`: tin nhắn user/assistant trong từng phiên.
- `message_sources`: các chunk được dùng để tạo câu trả lời.

Mặc định backend dùng:

```env
DATABASE_URL=sqlite:///backend/storage/ptit_chatbot.db
```

Khi cần chuyển sang PostgreSQL, có thể đổi `DATABASE_URL` sang connection string PostgreSQL và giữ nguyên tầng repository/schema.

Mặc định project dùng OpenAI embedding `text-embedding-3-small`. Có thể đổi sang `text-embedding-3-large` trong `.env` nếu muốn chất lượng cao hơn:

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

Sau khi đổi embedding model, cần chạy lại:

```powershell
python -m scripts.ingest
```

Nếu muốn dùng embedding local bằng Sentence Transformers, cài thêm:

```powershell
pip install -e ".[ml]"
```

Rồi đổi `EMBEDDING_PROVIDER=sentence-transformers` và `EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` trong `.env`.

## Chạy frontend

```powershell
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`.

## API nhanh

- `GET /api/health`: kiểm tra server.
- `POST /api/ingest`: nạp lại tài liệu trong `data/`.
- `POST /api/chat`: hỏi đáp RAG.

Ví dụ:

```json
{
  "message": "Sinh viên bị cảnh báo học tập khi nào?",
  "top_k": 4
}
```

## Gợi ý phát triển tiếp

- Thêm parser PDF/DOCX cho tài liệu gốc.
- Thêm đăng nhập quản trị để upload tài liệu và re-index.
- Thêm reranker để cải thiện độ chính xác retrieval.
- Lưu lịch sử hội thoại theo user/session.
