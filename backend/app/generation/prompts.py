from app.generation.citations import numbered_contexts


SYSTEM_PROMPT = """Bạn là chatbot tư vấn dựa trên tài liệu nội bộ PTIT.
Chỉ trả lời bằng tiếng Việt và chỉ sử dụng thông tin trong ngữ cảnh được cung cấp.
Mỗi nhận định thực tế phải có citation ngay sau nhận định, theo đúng dạng [1], [2].
Chỉ dùng các số citation xuất hiện trong ngữ cảnh; không tự tạo nguồn hoặc số citation.
Không nhắc tới đường dẫn file, chunk ID, document ID, điểm retrieval hoặc dữ liệu hệ thống nội bộ.
Nếu ngữ cảnh không đủ để trả lời, chỉ trả lời chính xác câu từ chối đã quy định, không kèm citation."""


def build_context_prompt(question: str, contexts: list[dict]) -> str:
    blocks = []
    for context, (citation_id, citation) in zip(contexts, numbered_contexts(contexts)):
        section = citation.get("section_path") or citation.get("heading") or "Không có tiêu đề"
        blocks.append(
            f"[{citation_id}] Nguồn: {citation['source_name']}\n"
            f"Mục: {section}\n"
            f"Nội dung: {context['text']}"
        )

    context_text = "\n\n".join(blocks)
    return (
        f"NGỮ CẢNH ĐƯỢC PHÉP SỬ DỤNG:\n{context_text}\n\n"
        f"CÂU HỎI: {question}\n\n"
        "YÊU CẦU TRẢ LỜI:\n"
        "- Trả lời trực tiếp, rõ ràng và súc tích.\n"
        "- Gắn citation [n] ngay sau từng thông tin được lấy từ tài liệu.\n"
        "- Không thêm mục tài liệu tham khảo riêng và không hiển thị đường dẫn file."
    )
