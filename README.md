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

Backend dùng `OPENAI_API_KEY` cho cả embedding OpenAI và bước tổng hợp câu trả lời. Nếu chưa có key, đổi `EMBEDDING_PROVIDER=hash` để chạy local và API chat sẽ trả về các đoạn tài liệu liên quan nhất thay vì gọi LLM.

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
