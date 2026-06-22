OUT_OF_SCOPE_ANSWER = (
    "Mình chỉ hỗ trợ các câu hỏi liên quan đến PTIT và nội dung trong sổ tay sinh viên. "
    "Bạn có thể hỏi về học phí, học phần, thi cử, học bổng, rèn luyện, thủ tục sinh viên "
    "hoặc điều kiện tốt nghiệp."
)

DOMAIN_TERMS = (
    "ptit", "học viện", "nhà trường", "sinh viên", "học tập", "khóa học",
    "học kỳ", "học phần", "môn học", "tín chỉ", "chương trình đào tạo",
    "chương trình", "đào tạo", "ngành học", "mã ngành", "ngành công nghệ",
    "ngành an toàn", "ngành marketing", "đăng ký môn", "đăng ký học", "học phí",
    "lệ phí", "học bổng", "tốt nghiệp", "cảnh báo học", "điểm trung bình",
    "điểm chữ", "thang điểm", "bảng điểm", "khiếu nại điểm", "cải thiện điểm",
    "học lại", "xếp loại", "gpa", "cpa", "thi cử", "kỳ thi", "thi hộ",
    "phúc khảo", "bảo lưu", "thôi học", "nghỉ học", "chuyển ngành", "chuyển trường",
    "rèn luyện", "kỷ luật", "khen thưởng", "thẻ sinh viên", "ký túc xá", "thư viện",
    "đoàn thanh niên", "công tác sinh viên", "thủ tục", "giấy xác nhận", "chứng chỉ",
    "chuẩn đầu ra", "giảng đường", "giảng viên", "giảng dạy", "lớp học", "vào lớp",
    "khảo thí", "thực tập", "cố vấn học tập", "thời khóa biểu", "lịch học", "lịch thi",
    "địa chỉ trường", "cơ sở đào tạo", "phòng đào tạo", "trưởng khoa",
    "phó trưởng khoa", "chủ nhiệm khoa", "chủ nhiệm bộ môn", "chủ nhiệm viện",
    "chủ nhiệm phòng", "chủ nhiệm trung tâm",
)

FOLLOW_UP_PATTERNS = (
    r"^(?:còn|thế còn|vậy|trường hợp này|trường hợp đó|quy định này|quy định đó|nó)\b",
    r"^(?:bao nhiêu|khi nào|ở đâu|tại sao|như thế nào|có được không|cần gì)\b",
)

BLOCKED_PATTERNS = (
    ("code_generation", r"\b(?:viết|tạo|sinh|làm)\s+(?:cho\s+(?:tôi|mình|em)\s+)?(?:mã|code|script|chương trình)\b"),
    ("code_generation", r"\b(?:python|javascript|java|c\+\+|html|css|sql)\b.*\b(?:code|mã|script|lập trình)\b"),
    ("creative_request", r"\b(?:viết|sáng tác)\s+(?:một\s+)?(?:bài thơ|truyện|kịch bản|bài hát)\b"),
    ("general_task", r"\b(?:dịch|tóm tắt)\s+(?:đoạn|văn bản|bài viết)\s+(?:này|sau)\b"),
    ("general_task", r"\b(?:giải|làm)\s+(?:giúp\s+)?(?:bài toán|bài tập lập trình)\b"),
)

PROMPT_INJECTION_PATTERNS = (
    r"\b(?:bỏ qua|quên đi|phớt lờ|ghi đè|vô hiệu hóa|không tuân theo)\b.{0,120}\b(?:hướng dẫn|chỉ dẫn|prompt|quy tắc|yêu cầu|nội dung phía trên|lệnh trước)\b",
    r"\b(?:ignore|forget|disregard|override|bypass|do not follow)\b.{0,120}\b(?:previous|prior|above|all|system|developer|instructions?|rules?|prompts?|messages?)\b",
    r"\b(?:hiển thị|tiết lộ|in ra|đọc lại|lặp lại|cho (?:tôi|mình) xem)\b.{0,100}\b(?:system prompt|developer message|chỉ dẫn hệ thống|prompt hệ thống|quy tắc nội bộ|hướng dẫn ẩn)\b",
    r"\b(?:show|reveal|print|repeat|recite|expose|output)\b.{0,100}\b(?:system prompt|developer message|hidden instructions?|internal rules?|initial prompt)\b",
    r"\b(?:what are|tell me|list)\b.{0,60}\b(?:your instructions|your system prompt|hidden rules)\b",
    r"\b(?:jailbreak|developer mode|dan mode|do anything now|unrestricted mode)\b",
    r"\b(?:đóng vai|giả vờ là|hãy là|act as|pretend to be|roleplay as)\b.{0,100}\b(?:system|developer|không giới hạn|unrestricted|dan|không có quy tắc)\b",
    r"(?:\[|<|#{1,6}\s*)(?:system|developer|assistant)(?:\]|>|\s*:)",
    r"\b(?:api key|openai_api_key|mật khẩu|password|secret key|biến môi trường|environment variables?)\b.{0,80}\b(?:hiển thị|tiết lộ|đọc|show|reveal|print|output)\b",
    r"\b(?:hiển thị|tiết lộ|đọc|show|reveal|print|output)\b.{0,80}\b(?:api key|openai_api_key|mật khẩu|password|secret key|biến môi trường|environment variables?)\b",
    r"\b(?:decode|giải mã)\b.{0,80}\bbase(?:64|6a)\b.{0,80}\b(?:follow|execute|thực hiện|làm theo)\b",
)
