/**
 * "Lần lưu gần nhất" dạng tương đối, giờ địa phương của trình duyệt:
 * `14:02 hôm nay`, `14:02 hôm qua`, `14:02 15/11`, `14:02 15/11/2025`.
 *
 * Giá trị đến từ `updated_at` của `GET /config` (ISO 8601 có múi giờ) hoặc `null`
 * khi chưa từng lưu; dữ liệu hỏng cũng hiện "chưa lưu lần nào" thay vì bịa mốc.
 */
const pad = (value) => String(value).padStart(2, "0");

export const NEVER_SAVED = "chưa lưu lần nào";

export function formatLastSaved(value, now = new Date()) {
  if (!value) return NEVER_SAVED;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return NEVER_SAVED;

  const clock = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (sameDay) return `${clock} hôm nay`;

  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate();
  if (isYesterday) return `${clock} hôm qua`;

  const day = `${pad(date.getDate())}/${pad(date.getMonth() + 1)}`;
  if (date.getFullYear() === now.getFullYear()) return `${clock} ${day}`;
  return `${clock} ${day}/${date.getFullYear()}`;
}
