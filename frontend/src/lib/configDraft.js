/**
 * Gộp giá trị cấu hình mới từ máy chủ vào bản nháp đang sửa.
 *
 * Trường người dùng đã sửa cục bộ (`current[key] !== previousServer[key]`) được
 * giữ nguyên; trường còn lại nhận giá trị mới. Nhờ vậy lưu ở tab Mô hình cập nhật
 * ngay tab Cấu hình RAG mà không xoá bản nháp đang sửa ở tab đó.
 */
export function mergeConfigDraft(current, previousServer, nextServer) {
  if (!previousServer) return { ...nextServer };

  const merged = { ...nextServer };
  Object.keys(nextServer).forEach((key) => {
    if (current[key] !== previousServer[key]) {
      merged[key] = current[key];
    }
  });
  return merged;
}
