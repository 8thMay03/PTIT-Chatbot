-- Lược đồ CSDL Chương 2 (PostgreSQL 16 + pgvector) — thiết kế theo "Mô tả bài toán và phạm vi đồ án nhóm 5".
-- Dùng cho Visual Paradigm: Tools > DB > Reverse DDL (hoặc ReverseDDL -database PostgreSQL -encoding UTF-8).
-- Khóa chính dùng UUID. Cột embedding ghi VECTOR (không kèm số chiều) vì Reverse DDL của VP không đọc được VECTOR(1536);
-- khi tạo CSDL thật dùng VECTOR(1536). VP cũng không đọc BOOLEAN/TIMESTAMPTZ/JSON nên dùng BOOL, TIMESTAMP WITH TIME ZONE, TEXT.
-- Thứ tự tạo CSDL thật: (1) CREATE EXTENSION IF NOT EXISTS vector; (2) file này; (3) 2.6-csdl-chi-muc.sql
-- (chỉ mục, chỉ mục bộ phận, FK ghép). VP chỉ cần file này.

CREATE TABLE users (
    id              UUID         NOT NULL,
    student_code    VARCHAR(20)  NOT NULL,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(254),
    password_hash   VARCHAR(255),
    auth_source     VARCHAR(10)  NOT NULL,
    role            VARCHAR(10)  NOT NULL DEFAULT 'student',
    cohort          VARCHAR(10),
    major           VARCHAR(100),
    is_active       BOOL         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    last_login_at   TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_student_code UNIQUE (student_code),
    CONSTRAINT ck_users_auth_source CHECK (auth_source IN ('password', 'shell')),
    CONSTRAINT ck_users_role CHECK (role IN ('student', 'admin'))
);

CREATE TABLE knowledge_groups (
    id              UUID         NOT NULL,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    department      VARCHAR(150) NOT NULL,
    contact         VARCHAR(255),
    is_default      BOOL         NOT NULL DEFAULT FALSE,
    is_enabled      BOOL         NOT NULL DEFAULT TRUE,
    cache_epoch     INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT pk_knowledge_groups PRIMARY KEY (id),
    CONSTRAINT uq_knowledge_groups_name UNIQUE (name)
);

CREATE TABLE documents (
    id              UUID         NOT NULL,
    group_id        UUID         NOT NULL,
    title           VARCHAR(500) NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    storage_path    VARCHAR(500) NOT NULL,
    file_type       VARCHAR(10)  NOT NULL,
    is_scanned      BOOL         NOT NULL,
    source          VARCHAR(255) NOT NULL,
    is_official     BOOL         NOT NULL DEFAULT TRUE,
    issued_date     DATE         NOT NULL,
    expiry_date     DATE,
    version         INTEGER      NOT NULL DEFAULT 1,
    supersedes_id   UUID,
    status          VARCHAR(20)  NOT NULL,
    extracted_text  TEXT,
    uploaded_by     UUID         NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_documents PRIMARY KEY (id),
    CONSTRAINT ck_documents_status CHECK (status IN ('processing', 'needs_review', 'active', 'superseded', 'deleted')),
    CONSTRAINT ck_documents_file_type CHECK (file_type IN ('pdf', 'docx', 'image')),
    CONSTRAINT ck_documents_dates CHECK (expiry_date IS NULL OR expiry_date >= issued_date),
    CONSTRAINT fk_documents_group FOREIGN KEY (group_id) REFERENCES knowledge_groups (id),
    CONSTRAINT fk_documents_supersedes FOREIGN KEY (supersedes_id) REFERENCES documents (id),
    CONSTRAINT fk_documents_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES users (id)
);

CREATE TABLE chunks (
    id              UUID         NOT NULL,
    document_id     UUID         NOT NULL,
    chunk_strategy  VARCHAR(10)  NOT NULL,
    chunk_index     INTEGER      NOT NULL,
    start_offset    INTEGER      NOT NULL,
    end_offset      INTEGER      NOT NULL,
    section_path    VARCHAR(500),
    content         TEXT         NOT NULL,
    tokenized_text  TEXT         NOT NULL,
    embedding       VECTOR       NOT NULL,
    academic_year   VARCHAR(20),
    expiry_date     DATE,
    CONSTRAINT pk_chunks PRIMARY KEY (id),
    CONSTRAINT uq_chunks_position UNIQUE (document_id, chunk_strategy, chunk_index),
    CONSTRAINT ck_chunks_strategy CHECK (chunk_strategy IN ('fixed', 'legal')),
    CONSTRAINT ck_chunks_offsets CHECK (start_offset >= 0 AND end_offset > start_offset),
    CONSTRAINT fk_chunks_document FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);

CREATE TABLE audiences (
    id              UUID         NOT NULL,
    document_id     UUID         NOT NULL,
    chunk_id        UUID,
    cohort          VARCHAR(10),
    major           VARCHAR(100),
    CONSTRAINT pk_audiences PRIMARY KEY (id),
    CONSTRAINT fk_audiences_document FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
    CONSTRAINT fk_audiences_chunk FOREIGN KEY (chunk_id) REFERENCES chunks (id) ON DELETE CASCADE
);

CREATE TABLE conversations (
    id              UUID         NOT NULL,
    user_id         UUID         NOT NULL,
    title           VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_conversations PRIMARY KEY (id),
    CONSTRAINT fk_conversations_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE messages (
    id                  UUID         NOT NULL,
    conversation_id     UUID         NOT NULL,
    role                VARCHAR(10)  NOT NULL,
    content             TEXT         NOT NULL,
    rewritten_question  TEXT,
    answer_status       VARCHAR(20),
    from_cache          BOOL         NOT NULL DEFAULT FALSE,
    related_questions   TEXT,
    latency_ms          INTEGER,
    ttft_ms             INTEGER,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_messages PRIMARY KEY (id),
    CONSTRAINT ck_messages_role CHECK (role IN ('user', 'assistant')),
    CONSTRAINT ck_messages_answer_status CHECK (answer_status IN ('answered', 'out_of_scope', 'injection', 'no_context', 'error')),
    CONSTRAINT fk_messages_conversation FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE message_sources (
    id              UUID         NOT NULL,
    message_id      UUID         NOT NULL,
    chunk_id        UUID         NOT NULL,
    citation_no     INTEGER      NOT NULL,
    excerpt         TEXT         NOT NULL,
    score           REAL,
    CONSTRAINT pk_message_sources PRIMARY KEY (id),
    CONSTRAINT fk_message_sources_message FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE,
    CONSTRAINT fk_message_sources_chunk FOREIGN KEY (chunk_id) REFERENCES chunks (id)
);

CREATE TABLE feedback (
    id              UUID         NOT NULL,
    message_id      UUID         NOT NULL,
    user_id         UUID         NOT NULL,
    rating          VARCHAR(15)  NOT NULL,
    comment         TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_feedback PRIMARY KEY (id),
    CONSTRAINT uq_feedback_message_user UNIQUE (message_id, user_id),
    CONSTRAINT ck_feedback_rating CHECK (rating IN ('helpful', 'not_helpful')),
    CONSTRAINT fk_feedback_message FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE,
    CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE answer_cache (
    id                  UUID         NOT NULL,
    question_key        VARCHAR(64)  NOT NULL,
    question_text       TEXT         NOT NULL,
    cohort              VARCHAR(10)  NOT NULL,
    major               VARCHAR(100) NOT NULL,
    answer              TEXT         NOT NULL,
    related_questions   TEXT,
    hit_count           INTEGER      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_answer_cache PRIMARY KEY (id),
    CONSTRAINT ck_answer_cache_expiry CHECK (expires_at > created_at),
    CONSTRAINT uq_answer_cache_key UNIQUE (question_key)
);

CREATE TABLE answer_cache_sources (
    cache_id        UUID         NOT NULL,
    citation_no     INTEGER      NOT NULL,
    chunk_id        UUID         NOT NULL,
    excerpt         TEXT         NOT NULL,
    CONSTRAINT pk_answer_cache_sources PRIMARY KEY (cache_id, citation_no),
    CONSTRAINT fk_acs_cache FOREIGN KEY (cache_id) REFERENCES answer_cache (id) ON DELETE CASCADE,
    CONSTRAINT fk_acs_chunk FOREIGN KEY (chunk_id) REFERENCES chunks (id) ON DELETE CASCADE
);

CREATE TABLE suggested_questions (
    id              UUID         NOT NULL,
    group_id        UUID,
    question        TEXT         NOT NULL,
    source          VARCHAR(10)  NOT NULL,
    ask_count       INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOL         NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_suggested_questions PRIMARY KEY (id),
    CONSTRAINT ck_suggested_questions_source CHECK (source IN ('faq', 'frequent')),
    CONSTRAINT fk_suggested_questions_group FOREIGN KEY (group_id) REFERENCES knowledge_groups (id)
);

CREATE TABLE app_config_overrides (
    key             VARCHAR(100) NOT NULL,
    value           TEXT,
    encrypted_value TEXT,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_app_config_overrides PRIMARY KEY (key)
);

CREATE TABLE model_profiles (
    id                  UUID         NOT NULL,
    kind                VARCHAR(20)  NOT NULL,
    name                VARCHAR(100) NOT NULL,
    provider            VARCHAR(50)  NOT NULL,
    model               VARCHAR(255),
    params              TEXT         NOT NULL,
    encrypted_api_key   TEXT,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_model_profiles PRIMARY KEY (id),
    CONSTRAINT uq_model_profiles_kind_name UNIQUE (kind, name),
    CONSTRAINT ck_model_profiles_kind CHECK (kind IN ('llm', 'embedding', 'reranker'))
);

COMMENT ON TABLE users IS 'Tài khoản sinh viên (gắn mã sinh viên) và quản trị viên — CN01';
COMMENT ON COLUMN users.student_code IS 'Mã sinh viên; quản trị viên dùng mã cán bộ';
COMMENT ON COLUMN users.password_hash IS 'Mật khẩu băm; rỗng nếu tài khoản chỉ đăng nhập qua ứng dụng vỏ';
COMMENT ON COLUMN users.auth_source IS 'password | shell (danh tính do ứng dụng vỏ truyền sang)';
COMMENT ON COLUMN users.role IS 'student | admin';
COMMENT ON COLUMN users.cohort IS 'Khóa (ví dụ D21) — dùng cho QT4';
COMMENT ON COLUMN users.major IS 'Ngành — dùng cho QT4';

COMMENT ON TABLE knowledge_groups IS 'Nhóm tri thức (ĐA Bảng 3) và phòng ban phụ trách — QT2';
COMMENT ON COLUMN knowledge_groups.department IS 'Phòng ban phụ trách, nêu khi không đủ căn cứ (QT2)';
COMMENT ON COLUMN knowledge_groups.cache_epoch IS 'Số lần hủy đệm của nhóm; tăng trong giao dịch hủy đệm. Lượt hỏi chỉ ghi đệm nếu giá trị chưa đổi từ lúc truy xuất — QT6, CN13';
COMMENT ON COLUMN knowledge_groups.is_default IS 'Nhóm mặc định: dùng phòng ban của nhóm này khi không xác định được nhóm';

COMMENT ON TABLE documents IS 'Tài liệu tri thức và các phiên bản — CN07, CN08';
COMMENT ON COLUMN documents.storage_path IS 'Đường dẫn tệp gốc trong kho tệp tài liệu';
COMMENT ON COLUMN documents.source IS 'Nguồn văn bản (đơn vị ban hành, đường dẫn công bố)';
COMMENT ON COLUMN documents.is_official IS 'Văn bản chính thức (quyết định, thông báo của phòng ban); sai = tài liệu tổng hợp. Truy xuất ưu tiên nguồn chính thức (Bảng 3)';
COMMENT ON COLUMN documents.issued_date IS 'Ngày ban hành';
COMMENT ON COLUMN documents.expiry_date IS 'Ngày hết hạn (thông báo lịch thi, hạn nộp); quá ngày thì không truy xuất — QT3';
COMMENT ON COLUMN documents.supersedes_id IS 'Phiên bản cũ bị văn bản này thay thế; một bản cũ chỉ có một bản thay chưa bị xóa (chỉ mục UNIQUE bộ phận) — CN08';
COMMENT ON COLUMN documents.status IS 'processing | needs_review | active | superseded | deleted (xóa mềm, giữ đoạn cho lịch sử)';
COMMENT ON COLUMN documents.extracted_text IS 'Nội dung trích xuất (quản trị viên kiểm tra bản scan) — CN10';

COMMENT ON TABLE chunks IS 'Đoạn văn bản chia theo Chương/Điều/Khoản, kèm vector và văn bản đã tách từ — CN12';
COMMENT ON COLUMN chunks.chunk_strategy IS 'fixed (chia cố định, RAG cơ bản) | legal (Chương/Điều/Khoản); một tài liệu có cả hai bộ đoạn để so sánh trên cùng kho (Bảng 6)';
COMMENT ON COLUMN chunks.start_offset IS 'Vị trí ký tự bắt đầu của đoạn trong documents.extracted_text; dùng xác định đoạn chứa phần văn bản gán nhãn (Bảng 7)';
COMMENT ON COLUMN chunks.end_offset IS 'Vị trí ký tự kết thúc (không gồm) trong documents.extracted_text';
COMMENT ON COLUMN chunks.section_path IS 'Vị trí trong văn bản: Chương > Điều > Khoản (dùng cho trích dẫn)';
COMMENT ON COLUMN chunks.tokenized_text IS 'Văn bản đã tách từ tiếng Việt cho BM25';
COMMENT ON COLUMN chunks.embedding IS 'Vector nhúng vector(1536) của pgvector, chỉ mục HNSW';
COMMENT ON COLUMN chunks.academic_year IS 'Năm học áp dụng';
COMMENT ON COLUMN chunks.expiry_date IS 'Ngày hết hạn của đoạn (mặc định lấy theo tài liệu)';

COMMENT ON TABLE audiences IS 'Đối tượng áp dụng (khóa, ngành) của tài liệu hoặc của riêng một đoạn — QT3, QT4, CN08';
COMMENT ON COLUMN audiences.chunk_id IS 'Rỗng: áp dụng cho cả tài liệu; có giá trị: riêng cho đoạn đó, đoạn phải thuộc document_id (FK ghép ở 2.6-csdl-chi-muc.sql)';
COMMENT ON COLUMN audiences.cohort IS 'Khóa áp dụng; rỗng = mọi khóa';
COMMENT ON COLUMN audiences.major IS 'Ngành áp dụng; rỗng = mọi ngành';

COMMENT ON TABLE conversations IS 'Hội thoại của sinh viên — CN05';
COMMENT ON TABLE messages IS 'Câu hỏi và câu trả lời trong hội thoại, kể cả câu từ chối — CN02';
COMMENT ON COLUMN messages.rewritten_question IS 'Câu hỏi sau chuẩn hóa và viết lại — CN11';
COMMENT ON COLUMN messages.answer_status IS 'answered | out_of_scope | injection | no_context | error — CN09, CN14';
COMMENT ON COLUMN messages.from_cache IS 'Câu trả lời lấy từ bộ nhớ đệm — CN13';
COMMENT ON COLUMN messages.related_questions IS 'Câu hỏi gợi ý liên quan (danh sách JSON, chỉ để hiển thị lại) — CN04';
COMMENT ON COLUMN messages.ttft_ms IS 'Thời gian đến token đầu';

COMMENT ON TABLE message_sources IS 'Nguồn trích dẫn của câu trả lời — CN03, QT1';
COMMENT ON TABLE feedback IS 'Đánh giá câu trả lời — CN06, CN09';
COMMENT ON COLUMN feedback.rating IS 'helpful | not_helpful';

COMMENT ON TABLE answer_cache IS 'Bộ nhớ đệm câu trả lời có căn cứ — CN13';
COMMENT ON COLUMN answer_cache.question_key IS 'Băm của (câu hỏi đã chuẩn hóa, viết lại + khóa + ngành); không có khóa chung — tránh trả nhầm đối tượng (QT4)';
COMMENT ON COLUMN answer_cache.cohort IS 'Khóa của sinh viên đã hỏi; sinh viên chưa có khóa, ngành thì không đọc, không ghi đệm';
COMMENT ON COLUMN answer_cache.expires_at IS 'Bằng min(created_at + 7 ngày, 00:00 ngày sau chunks.expiry_date sớm nhất của các đoạn nguồn, giờ Việt Nam)';
COMMENT ON TABLE answer_cache_sources IS 'Nguồn trích dẫn của câu trả lời đệm; dựng lại nguồn khi trúng đệm; hủy đệm theo tài liệu hoặc nhóm tri thức qua chunks → documents.group_id — QT6';

COMMENT ON TABLE suggested_questions IS 'Câu hỏi phổ biến hiển thị khi mở hội thoại mới — CN04';
COMMENT ON COLUMN suggested_questions.source IS 'faq | frequent';

COMMENT ON TABLE app_config_overrides IS 'Cấu hình hệ thống admin sửa ở màn Cấu hình (ghi đè .env), gồm cờ thực nghiệm bật/tắt từng cải tiến — Bảng 6, Bảng 7; không khóa ngoại';
COMMENT ON COLUMN app_config_overrides.key IS 'Tên cấu hình, ví dụ NORMALIZATION_ENABLED, FOLLOW_UP_REWRITE_ENABLED, RETRIEVAL_MODE (vector | bm25 | hybrid), RERANKER_ENABLED, CACHE_ENABLED, CHUNK_STRATEGY (fixed | legal)';
COMMENT ON COLUMN app_config_overrides.value IS 'Giá trị (JSON dạng văn bản); rỗng nếu là khóa bí mật';
COMMENT ON COLUMN app_config_overrides.encrypted_value IS 'Khóa bí mật (API key) đã mã hóa';
COMMENT ON COLUMN app_config_overrides.updated_at IS 'Lần đổi gần nhất; đối chiếu với thời điểm chạy thực nghiệm';
COMMENT ON TABLE model_profiles IS 'Kho mô hình LLM, embedding, reranker để chọn cấu hình thực nghiệm; không khóa ngoại';
COMMENT ON COLUMN model_profiles.kind IS 'llm | embedding | reranker';
COMMENT ON COLUMN model_profiles.params IS 'Tham số riêng của nhà cung cấp (base_url, deployment, số chiều…), JSON dạng văn bản';
COMMENT ON COLUMN model_profiles.encrypted_api_key IS 'API key đã mã hóa';
