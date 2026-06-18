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
MULTI_QUERY_ENABLED=true
MULTI_QUERY_USE_LLM=false
MULTI_QUERY_COUNT=3
CONVERSATION_MEMORY_ENABLED=true
CONVERSATION_MEMORY_MAX_MESSAGES=6
CONVERSATION_MEMORY_MAX_CHARS=6000
RERANKER_ENABLED=true
RERANKER_PROVIDER=heuristic
RERANKER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
RERANKER_CANDIDATE_MULTIPLIER=3
```

Nếu không có chunk nào vượt ngưỡng vector hoặc BM25, chatbot không gửi context yếu cho LLM và trả về `Chưa tìm thấy thông tin này trong tài liệu.` mà không kèm citation.

Trước khi retrieval, câu hỏi tiếng Việt được chuẩn hóa và mở rộng các viết tắt phổ biến bằng rule-based rewriter. Đặt `QUERY_REWRITE_USE_LLM=true` để dùng model cấu hình trong `OPENAI_MODEL` cho bước rewrite; nếu lời gọi lỗi, hệ thống tự động dùng kết quả rule-based.

Multi-query retrieval giữ truy vấn đã rewrite và tạo thêm tối đa `MULTI_QUERY_COUNT` biến thể, sau đó hợp nhất kết quả bằng RRF. Đặt `MULTI_QUERY_ENABLED=false` để tắt hoặc `MULTI_QUERY_USE_LLM=true` để sinh biến thể bằng model; khi model lỗi hệ thống fallback về rule-based.

Conversation memory đọc các message gần nhất từ SQLite theo `conversation_id`, giới hạn đồng thời bằng số message và tổng ký tự. Memory chỉ giúp hiểu câu hỏi nối tiếp; dữ kiện trả lời và citation vẫn bắt buộc đến từ tài liệu retrieval. Đặt `CONVERSATION_MEMORY_ENABLED=false` để tắt.

Sau hybrid search, reranker sắp xếp lại tập candidate trước khi đưa context vào LLM. Đặt `RERANKER_ENABLED=false` để bỏ qua hoàn toàn bước này. `RERANKER_PROVIDER=heuristic` chạy ngay không cần model bổ sung. Để dùng CrossEncoder đa ngôn ngữ, cài `pip install -e ".[ml]"` rồi đặt `RERANKER_PROVIDER=cross-encoder`; nếu model lỗi, hệ thống tự động fallback về heuristic.

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

## Chạy test

```powershell
cd backend
pytest
```

Test `test_ptit_faq.py` dùng bộ câu hỏi PTIT thường gặp trong
`backend/tests/fixtures/ptit_faq.json` để kiểm tra các câu hỏi vẫn truy xuất
được đúng bằng chứng từ sổ tay sinh viên. Bộ test chạy local, không gọi LLM
hoặc API bên ngoài.

Để đánh giá pipeline RAG sau khi ingest dữ liệu:

```powershell
cd backend
python -m scripts.evaluate --top-k 4 --output evaluation-report.json
```

Evaluation báo cáo Retrieval Hit@K, MRR, tỷ lệ từ khóa đáp án, độ hợp lệ của
citation và điểm answer quality tổng hợp. Có thể đặt ngưỡng cho CI:

```powershell
python -m scripts.evaluate `
  --fail-below-hit-rate 0.8 `
  --fail-below-answer-quality 0.7
```

`answer_quality` được tính bằng 80% tỷ lệ cụm từ đáp án xuất hiện trong câu
trả lời và 20% độ hợp lệ citation. Khi có `OPENAI_API_KEY`, script đánh giá câu
trả lời sinh bởi model; nếu không có key, nó đánh giá câu trả lời trích xuất.

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
