# PTIT RAG Chatbot

Khung project RAG chatbot cho tài liệu PTIT, gồm backend FastAPI và frontend React/Vite.

## Cấu trúc

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP routes
│   │   ├── core/         # Settings/env
│   │   └── rag/          # Loader, chunker, embeddings, vector store, LLM
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

Nếu có `OPENAI_API_KEY`, backend sẽ dùng OpenAI để tổng hợp câu trả lời. Nếu chưa có key, API vẫn chạy và trả về các đoạn tài liệu liên quan nhất.

Mặc định project dùng embedding `hash` để chạy nhanh khi dựng khung. Khi muốn dùng embedding đa ngôn ngữ tốt hơn, cài thêm:

```powershell
pip install -e ".[ml]"
```

Rồi đổi `EMBEDDING_PROVIDER=sentence-transformers` trong `.env`.

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
