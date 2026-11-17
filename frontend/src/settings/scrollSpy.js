/**
 * Chọn mục đang xem của form "Hệ thống trả lời" từ vị trí cuộn.
 *
 * Mục đang xem là mục cuối cùng có tiêu đề đã qua vạch `activeLine` tính từ đỉnh khung
 * cuộn. Cuộn tới đáy thì luôn là mục cuối: mục cuối thường quá ngắn để tiêu đề lên tới
 * đỉnh khung, nên nếu chỉ xét vị trí thì bấm "Sinh câu trả lời" sẽ đánh dấu nhầm mục
 * trước nó.
 *
 * `offsets` là vị trí đỉnh từng mục trong nội dung cuộn (px), theo thứ tự `keys`.
 */
export const ACTIVE_LINE_PX = 64;
const BOTTOM_TOLERANCE_PX = 2;

export function pickActiveSection({
  keys,
  offsets,
  scrollTop,
  clientHeight,
  scrollHeight,
  activeLine = ACTIVE_LINE_PX,
}) {
  if (!keys?.length) return null;
  const atBottom = scrollTop > 0 && scrollHeight - clientHeight - scrollTop <= BOTTOM_TOLERANCE_PX;
  if (atBottom) return keys[keys.length - 1];

  let active = keys[0];
  keys.forEach((key, index) => {
    if (offsets[index] <= scrollTop + activeLine) active = key;
  });
  return active;
}
