OUT_OF_SCOPE_ANSWER = (
    "Mình chỉ hỗ trợ các câu hỏi liên quan đến PTIT và nội dung trong sổ tay sinh viên. "
    "Bạn có thể hỏi về học phí, học phần, thi cử, học bổng, rèn luyện, thủ tục sinh viên "
    "hoặc điều kiện tốt nghiệp."
)

# Mẫu viết theo văn bản có dấu; bản không dấu được sinh tự động (xem matching.PatternSet).
# "sinh" bị bỏ khỏi nhóm động từ code_generation và "tạo" không khớp sau "đào" để
# "tuyển sinh/thí sinh chương trình", "đào tạo chương trình" không bị chặn nhầm.
BLOCKED_PATTERNS = (
    ("code_generation", r"\b(?:viết|(?<!đào )tạo|làm)\s+(?:cho\s+(?:tôi|mình|em)\s+)?(?:mã|code|script|chương trình)\b"),
    ("code_generation", r"\b(?:python|javascript|java|c\+\+|html|css|sql)\b.*\b(?:code|mã|script|lập trình)\b"),
    ("creative_request", r"\b(?:viết|sáng tác)\s+(?:một\s+)?(?:bài thơ|truyện|kịch bản|bài hát)\b"),
    ("general_task", r"\b(?:dịch|tóm tắt)\s+(?:đoạn|văn bản|bài viết)\s+(?:này|sau)\b"),
    ("general_task", r"\b(?:giải|làm)\s+(?:giúp\s+)?(?:bài toán|bài tập lập trình)\b"),
)

PROMPT_INJECTION_PATTERNS = (
    r"\b(?:bỏ qua|quên đi|phớt lờ|ghi đè|vô hiệu hóa|không tuân theo)\b.{0,120}\b(?:hướng dẫn|chỉ dẫn|prompt|(?:mọi|tất cả(?: các)?)\s+(?:quy tắc|yêu cầu)|(?:quy tắc|yêu cầu)\s+(?:trước|trên|hệ thống|ban đầu)|nội dung phía trên|lệnh trước)\b",
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

# Thu hẹp nhánh của bản không dấu khi dạng không dấu trùng từ thông dụng:
# (đoạn trong mẫu đã bỏ dấu, thay bằng). Mỗi đoạn phải khớp đúng một lần.
UNACCENTED_BLOCKED_OVERRIDES = (
    # "làm mã" → "lam ma" = "làm mà"; "viết mã" → "tieng viet ma" = "tiếng Việt mà".
    (r"(?:viet|(?<!dao )tao|lam)\s+", r"(?:(?<!tieng )viet|(?<!dao )tao)\s+"),
    # "viết truyện" → "viet truyen" trùng "viết truyền (đơn)" trong quy định kỷ luật.
    ("|truyen|", "|truyen(?! don)|"),
)

UNACCENTED_PROMPT_INJECTION_OVERRIDES = (
    # "quên đi" → "quen di" = "quen (làm gì)".
    ("bo qua|quen di|", "bo qua|"),
    # "hãy là" → "hay la" = "hoặc là".
    ("gia vo la|hay la|", "gia vo la|"),
    # "\bdan\b" khớp "dân", "hướng dẫn"; chỉ giữ "dan mode".
    ("|unrestricted|dan|", "|unrestricted|dan mode|"),
)
