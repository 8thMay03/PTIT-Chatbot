-- Chỉ mục và ràng buộc bổ sung cho lược đồ 2.6 (PostgreSQL 16 + pgvector).
-- Thứ tự: (1) CREATE EXTENSION IF NOT EXISTS vector; (2) 2.6-csdl.sql; (3) file này.
-- Không import vào VP (Reverse DDL không đọc vector(1536), USING hnsw, WHERE).

-- Số chiều thật của vector nhúng (text-embedding-3-small).
ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(1536);

-- Tối đa một nhóm tri thức mặc định; dữ liệu khởi tạo luôn có một nhóm mặc định (QT2).
CREATE UNIQUE INDEX uq_knowledge_groups_default ON knowledge_groups (is_default) WHERE is_default;

-- audiences.chunk_id phải thuộc đúng audiences.document_id (FK ghép).
ALTER TABLE chunks ADD CONSTRAINT uq_chunks_id_document UNIQUE (id, document_id);
ALTER TABLE audiences ADD CONSTRAINT fk_audiences_chunk_document
    FOREIGN KEY (chunk_id, document_id) REFERENCES chunks (id, document_id) ON DELETE CASCADE;

-- Truy xuất (bước 5): vector, lọc tài liệu đang hiệu lực, lọc chiến lược chia đoạn, đối tượng áp dụng.
CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
-- chunks(document_id, chunk_strategy) đã có chỉ mục nhờ uq_chunks_position.
CREATE INDEX ix_documents_group_status ON documents (group_id, status);  -- lọc active; hủy đệm theo nhóm cả bản đã bị thay
CREATE INDEX ix_documents_expiry ON documents (expiry_date) WHERE expiry_date IS NOT NULL;
CREATE INDEX ix_audiences_document ON audiences (document_id);
CREATE INDEX ix_audiences_chunk ON audiences (chunk_id) WHERE chunk_id IS NOT NULL;
CREATE INDEX ix_audiences_cohort_major ON audiences (cohort, major);

-- Hủy bộ nhớ đệm theo tài liệu / nhóm tri thức (QT6, 2.5.4, 2.5.5) và dọn đệm hết hạn (CN13).
CREATE INDEX ix_answer_cache_sources_chunk ON answer_cache_sources (chunk_id);
CREATE INDEX ix_answer_cache_expires ON answer_cache (expires_at);

-- Lịch sử hội thoại (CN05).
CREATE INDEX ix_conversations_user ON conversations (user_id, updated_at DESC);
CREATE INDEX ix_messages_conversation ON messages (conversation_id, created_at);
CREATE INDEX ix_message_sources_message ON message_sources (message_id);
CREATE INDEX ix_message_sources_chunk ON message_sources (chunk_id);

-- Xem phản hồi (CN09) và đo p50/p95 theo thời gian (Bảng 7).
CREATE INDEX ix_messages_status_time ON messages (answer_status, created_at) WHERE answer_status IS NOT NULL;
CREATE INDEX ix_feedback_rating_time ON feedback (rating, created_at);
CREATE INDEX ix_feedback_user ON feedback (user_id);

-- Khóa ngoại còn lại.
-- Một bản cũ chỉ có một bản thay chưa bị xóa; bản mới lỗi thì xóa mềm và tạo bản thay khác (CN08).
CREATE UNIQUE INDEX uq_documents_supersedes ON documents (supersedes_id)
    WHERE supersedes_id IS NOT NULL AND status <> 'deleted';
CREATE INDEX ix_documents_uploaded_by ON documents (uploaded_by);
CREATE INDEX ix_suggested_questions_group ON suggested_questions (group_id) WHERE is_active;
