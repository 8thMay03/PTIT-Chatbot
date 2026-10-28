import {
  Award,
  BookOpen,
  ClipboardCheck,
  FileSearch,
  FileText,
  GraduationCap,
  HeartHandshake,
  PenLine,
  Quote,
  SearchX,
  Wallet,
} from "lucide-react";

/**
 * Nội dung trang landing. Bố cục theo Figma "AI Chat landing page UI kit"
 * (frame 2002:456) nhưng mọi câu chữ mô tả đúng khả năng hiện có của PTIT Chatbot:
 * không logo đối tác, không lời chứng thực, không số liệu chưa có nguồn.
 */

export const REPO_URL = "https://github.com/8thMay03/PTIT-Chatbot";

/** Chip trên khung soạn câu hỏi: bấm để điền câu gợi ý. */
export const COMPOSER_TOPICS = [
  { label: "Học phí", icon: Wallet, question: "Học phí của sinh viên được quy định như thế nào?" },
  { label: "Học bổng", icon: Award, question: "Điều kiện để được xét học bổng khuyến khích học tập là gì?" },
  { label: "Tốt nghiệp", icon: GraduationCap, question: "Điều kiện để được xét tốt nghiệp là gì?" },
  { label: "Cảnh báo học tập", icon: ClipboardCheck, question: "Khi nào sinh viên bị cảnh báo kết quả học tập?" },
];

export const COMPOSER_SUGGESTION = "Sinh viên được khen thưởng trong những trường hợp nào?";

/** Dải chủ đề thay cho dải logo đối tác của thiết kế. */
export const TOPIC_STRIP = [
  { label: "Quy chế đào tạo", icon: BookOpen },
  { label: "Học phí", icon: Wallet },
  { label: "Học bổng", icon: Award },
  { label: "Thi cử", icon: ClipboardCheck },
  { label: "Rèn luyện", icon: HeartHandshake },
  { label: "Tốt nghiệp", icon: GraduationCap },
  { label: "Thủ tục", icon: FileText },
];

/** Nhãn nghiêng trong thẻ "Đúng phạm vi học vụ" (màu và góc theo thiết kế). */
export const SCOPE_TAGS = [
  { label: "Cảnh báo học tập", tone: "dark", style: { left: "6%", bottom: "84px", rotate: "15deg" } },
  { label: "Học bổng", tone: "pink", style: { left: "2%", bottom: "18px", rotate: "-18.6deg" } },
  { label: "Rèn luyện", tone: "blue", style: { left: "19%", bottom: "26px", rotate: "-20.1deg" } },
  { label: "Học phí", tone: "orange", style: { left: "35%", bottom: "0px", rotate: "0deg" } },
  { label: "Học phần", tone: "cyan", style: { left: "43%", bottom: "70px", rotate: "-26.1deg" } },
  { label: "Thi cử", tone: "blue", style: { left: "52%", bottom: "50px", rotate: "-26.5deg" } },
  { label: "Tốt nghiệp", tone: "yellow", style: { left: "59%", bottom: "0px", rotate: "0deg" } },
  { label: "Thủ tục", tone: "grey", style: { left: "65%", bottom: "48px", rotate: "-24.4deg" } },
  { label: "Đăng ký học", tone: "dark", style: { left: "79%", bottom: "12px", rotate: "15deg" } },
];

/** Các bước ở carousel "Cách hoạt động" (thay khối lời chứng thực của thiết kế). */
export const STEPS = [
  {
    icon: PenLine,
    title: "Bạn đặt câu hỏi",
    text: "Gõ câu hỏi bằng tiếng Việt, như khi hỏi phòng đào tạo hay cố vấn học tập.",
  },
  {
    icon: FileSearch,
    title: "Tìm trong tài liệu chính thức",
    text: "Hệ thống tìm các đoạn liên quan trong quy chế, quy định và sổ tay sinh viên do quản trị viên nạp.",
  },
  {
    icon: Quote,
    title: "Trả lời kèm trích dẫn",
    text: "Câu trả lời chỉ dựa trên các đoạn tìm được và gắn số trích dẫn tới nguồn để bạn đối chiếu.",
  },
  {
    icon: SearchX,
    title: "Nói rõ khi không biết",
    text: "Không tìm thấy thông tin phù hợp thì chatbot báo chưa có trong tài liệu, thay vì tự đoán.",
  },
];

export const FAQ = [
  {
    question: "PTIT Chatbot là gì?",
    answer:
      "Trợ lý hỏi đáp học vụ cho sinh viên PTIT: trả lời câu hỏi về quy chế đào tạo, học phí, học bổng, thi cử, rèn luyện và thủ tục dựa trên tài liệu đã nạp vào hệ thống, kèm trích dẫn nguồn.",
  },
  {
    question: "Chatbot lấy thông tin từ đâu?",
    answer:
      "Từ các văn bản do quản trị viên hệ thống nạp vào kho tài liệu (quy chế, quy định, sổ tay sinh viên). Danh sách có thể chưa đầy đủ hoặc chưa có văn bản mới ban hành.",
  },
  {
    question: "Tôi có thể hỏi những gì?",
    answer:
      "Các câu hỏi học vụ trong phạm vi tài liệu: học phí, học phần, đăng ký học, thi cử, học bổng, rèn luyện, cảnh báo học tập, điều kiện tốt nghiệp… Câu hỏi ngoài phạm vi có thể bị từ chối.",
  },
  {
    question: "Câu trả lời có luôn chính xác không?",
    answer:
      "Không. Chatbot có thể trả lời sai, thiếu hoặc hiểu nhầm câu hỏi. Hãy mở trích dẫn để đối chiếu văn bản gốc trước khi làm thủ tục quan trọng; thông tin chính thức luôn là văn bản và thông báo do Học viện ban hành.",
  },
  {
    question: "Có cần tài khoản không?",
    answer:
      "Không bắt buộc. Khách hỏi được ngay và lịch sử gắn với trình duyệt. Đăng nhập để xem lịch sử trên mọi thiết bị; hội thoại khách trên trình duyệt hiện tại được chuyển vào tài khoản khi bạn đăng nhập.",
  },
  {
    question: "Hội thoại của tôi được lưu thế nào?",
    answer:
      "Hội thoại được lưu trên máy chủ để hiển thị lịch sử, và quản trị viên hệ thống có thể xem để kiểm tra chất lượng trả lời. Không nhập mật khẩu, số giấy tờ tuỳ thân hay thông tin nhạy cảm vào khung chat.",
  },
];

/** Câu nền mờ phía sau khung soạn (trang trí); một số từ khoá tô màu như thiết kế. */
export const BACKGROUND_TEXT = [
  ["PTIT Chatbot trả lời câu hỏi về ", null],
  ["quy chế đào tạo", "yellow"],
  [", học phí, học bổng và thủ tục sinh viên dựa trên tài liệu chính thức đã được nạp vào hệ thống. Mỗi câu trả lời gắn ", null],
  ["trích dẫn", "red"],
  [" tới điều, khoản liên quan để bạn tự kiểm tra lại. Hỏi tiếp dựa trên câu trước mà không cần nhắc lại toàn bộ; đăng nhập để ", null],
  ["lịch sử", "blue"],
  [" theo bạn trên mọi thiết bị. Không tìm thấy thông tin phù hợp thì chatbot nói rõ thay vì tự đoán. ", null],
  ["Sổ tay sinh viên", "yellow"],
  [", quy định thi cử, rèn luyện, ", null],
  ["cảnh báo học tập", "red"],
  [" và điều kiện tốt nghiệp — tra cứu nhanh thay vì lật từng trang văn bản. Câu hỏi ngoài phạm vi học vụ có thể bị từ chối. ", null],
  ["PTIT", "blue"],
  [" Chatbot trả lời câu hỏi về quy chế đào tạo, học phí, học bổng và thủ tục sinh viên dựa trên tài liệu chính thức. Mỗi câu trả lời gắn trích dẫn để bạn đối chiếu văn bản gốc.", null],
];
