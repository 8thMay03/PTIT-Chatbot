import React, { useEffect, useId, useRef, useState } from "react";
import { Database, Download, Loader2, LogOut, SlidersHorizontal, Trash2, UserRound, X } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { conversationsApi, errorMessage, queryKeys } from "../api";
import { useAuthSession, useLogout, userInitial } from "../auth/session";
import Modal from "../components/Modal";
import { useToast } from "../components/Toast";
import { downloadTextFile, exportFileName, conversationsToMarkdown, fetchAllConversations } from "../lib/exportConversations";
import { isApplePlatform } from "../lib/keyboard";

export const SETTINGS_SECTIONS = ["general", "account", "data"];

const SECTION_META = {
  general: { label: "Chung", icon: SlidersHorizontal },
  account: { label: "Tài khoản", icon: UserRound },
  data: { label: "Dữ liệu & lịch sử", icon: Database },
};

const THEME_OPTIONS = [
  { value: "light", label: "Sáng" },
  { value: "dark", label: "Tối" },
  { value: "system", label: "Theo hệ thống" },
];

const FONT_SCALE_OPTIONS = [
  { value: "sm", label: "Nhỏ" },
  { value: "md", label: "Vừa" },
  { value: "lg", label: "Lớn" },
];

// Bố cục danh mục trái từ 768px; hẹp hơn thì các nhóm xếp thành một danh sách.
const STACKED_QUERY = "(max-width: 767px)";

/**
 * Nhóm nút chọn một giá trị (radiogroup): Tab vào nút đang chọn, mũi tên đổi lựa chọn.
 */
function Segmented({ label, options, value, onChange }) {
  const refs = useRef([]);
  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value)
  );

  function onKeyDown(event) {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const next = (selectedIndex + step + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  }

  return (
    <div className="ss-segmented" role="radiogroup" aria-label={label} onKeyDown={onKeyDown}>
      {options.map((option, index) => {
        const checked = index === selectedIndex;
        return (
          <button
            key={option.value}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            className={checked ? "is-on" : ""}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function Switch({ checked, onChange, labelledBy, describedBy }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      className={`ss-switch ${checked ? "is-on" : ""}`.trim()}
      onClick={() => onChange(!checked)}
    >
      <span aria-hidden="true" />
    </button>
  );
}

/** Một dòng tùy chọn: tiêu đề + mô tả bên trái, điều khiển bên phải. */
function PrefRow({ id, title, description, children, footer }) {
  return (
    <div className="ss-row">
      <div className="ss-row-main">
        <div className="ss-row-text">
          <div className="ss-row-title" id={`${id}-title`}>
            {title}
          </div>
          {description && (
            <div className="ss-row-desc" id={`${id}-desc`}>
              {description}
            </div>
          )}
        </div>
        <div className="ss-row-control">{children}</div>
      </div>
      {footer}
    </div>
  );
}

function GeneralSection({ idPrefix, theme, onThemeChange, preferences }) {
  const [saveState, setSaveState] = useState(null);
  const submitShortcut = `${isApplePlatform() ? "⌘" : "Ctrl"} + Enter`;

  function update(key, value) {
    setSaveState(preferences.setPreference(key, value) ? "saved" : "failed");
  }

  return (
    <>
      <PrefRow
        id={`${idPrefix}-theme`}
        title="Giao diện"
        description="Theo hệ thống sẽ tự đổi sáng/tối theo máy."
      >
        <Segmented
          label="Giao diện"
          options={THEME_OPTIONS}
          value={theme}
          onChange={(value) => {
            onThemeChange(value);
            setSaveState("saved");
          }}
        />
      </PrefRow>
      <PrefRow
        id={`${idPrefix}-font`}
        title="Cỡ chữ"
        description="Áp dụng cho câu hỏi, câu trả lời, trích dẫn và ô nhập."
        footer={
          <p className="ss-preview" aria-label="Xem trước cỡ chữ">
            Theo Điều 5, sinh viên có điểm trung bình học kỳ từ 2,5 trở lên được xét học bổng khuyến khích
            học tập. <span className="citation-chip">1</span>
          </p>
        }
      >
        <Segmented
          label="Cỡ chữ"
          options={FONT_SCALE_OPTIONS}
          value={preferences.fontScale}
          onChange={(value) => update("fontScale", value)}
        />
      </PrefRow>
      <PrefRow
        id={`${idPrefix}-enter`}
        title="Gửi bằng Enter"
        description={`Tắt: Enter để xuống dòng, ${submitShortcut} để gửi.`}
      >
        <Switch
          checked={preferences.enterToSend}
          onChange={(value) => update("enterToSend", value)}
          labelledBy={`${idPrefix}-enter-title`}
          describedBy={`${idPrefix}-enter-desc`}
        />
      </PrefRow>
      <PrefRow
        id={`${idPrefix}-reasoning`}
        title="Giữ mở quá trình suy luận"
        description="Tắt: panel tự thu gọn khi câu trả lời bắt đầu hiện."
      >
        <Switch
          checked={preferences.keepReasoningOpen}
          onChange={(value) => update("keepReasoningOpen", value)}
          labelledBy={`${idPrefix}-reasoning-title`}
          describedBy={`${idPrefix}-reasoning-desc`}
        />
      </PrefRow>
      <p className={`ss-saved ${saveState === "failed" ? "is-warning" : ""}`.trim()} role="status">
        {saveState === "saved" && "✓ Đã lưu trên thiết bị này"}
        {saveState === "failed" && "Không lưu được trên thiết bị này; chỉ áp dụng đến khi tải lại trang."}
      </p>
    </>
  );
}

function AccountSection({ user, onLoggedOut }) {
  const logout = useLogout();
  const toast = useToast();
  const [pending, setPending] = useState(false);

  async function handleLogout() {
    if (pending) return;
    setPending(true);
    try {
      await logout();
      onLoggedOut?.();
    } catch (error) {
      toast.error(errorMessage(error, "Không đăng xuất được."));
      setPending(false);
    }
  }

  return (
    <div className="ss-card">
      <div className="ss-account">
        <span className="user-avatar" aria-hidden="true">
          {userInitial(user)}
        </span>
        <div className="ss-account-text">
          <div className="ss-row-title">{user.full_name}</div>
          <div className="ss-row-desc">{user.email}</div>
        </div>
        <button type="button" className="ghost-btn" onClick={handleLogout} disabled={pending}>
          {pending ? <Loader2 size={15} className="spin" aria-hidden="true" /> : <LogOut size={15} aria-hidden="true" />}
          Đăng xuất
        </button>
      </div>
    </div>
  );
}

function DataSection({ idPrefix, isAuthenticated, onHistoryCleared }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  // Cùng query với danh sách trên thanh bên nên thường đã có sẵn trong cache.
  const listQuery = useQuery({
    queryKey: queryKeys.conversationList,
    queryFn: ({ signal }) => conversationsApi.list({ limit: 50, signal }),
  });
  const total = listQuery.data?.total ?? 0;
  const [exportProgress, setExportProgress] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const exportAbortRef = useRef(null);
  const confirmCancelRef = useRef(null);
  const deleteTriggerRef = useRef(null);

  useEffect(() => () => exportAbortRef.current?.abort(), []);

  useEffect(() => {
    if (confirming) confirmCancelRef.current?.focus();
  }, [confirming]);

  async function handleExport() {
    if (exportProgress) return;
    const controller = new AbortController();
    exportAbortRef.current = controller;
    setExportProgress({ done: 0, total });
    try {
      const conversations = await fetchAllConversations(conversationsApi, {
        signal: controller.signal,
        onProgress: (done, count) => setExportProgress({ done, total: count }),
      });
      downloadTextFile(exportFileName(), conversationsToMarkdown(conversations));
      toast.success(`Đã tải ${conversations.length} hội thoại về máy.`);
    } catch (error) {
      if (!controller.signal.aborted) toast.error(errorMessage(error, "Không tải được lịch sử."));
    } finally {
      if (exportAbortRef.current === controller) exportAbortRef.current = null;
      setExportProgress(null);
    }
  }

  function cancelConfirm() {
    setConfirming(false);
    deleteTriggerRef.current?.focus();
  }

  async function handleDeleteAll() {
    if (deleting) return;
    setDeleting(true);
    try {
      const result = await conversationsApi.removeAll();
      await queryClient.resetQueries({ queryKey: queryKeys.conversations });
      onHistoryCleared?.();
      toast.success(`Đã xoá ${result?.deleted ?? 0} hội thoại.`);
      setConfirming(false);
    } catch (error) {
      toast.error(errorMessage(error, "Không xoá được lịch sử hội thoại."));
    } finally {
      setDeleting(false);
    }
  }

  const empty = !listQuery.isPending && total === 0;

  return (
    <>
      <div className="ss-card">
        <PrefRow
          id={`${idPrefix}-export`}
          title="Tải lịch sử về máy"
          description="Tệp Markdown gồm câu hỏi, câu trả lời và nguồn trích dẫn của mọi hội thoại."
        >
          <button
            type="button"
            className="ghost-btn"
            onClick={handleExport}
            disabled={Boolean(exportProgress) || empty}
            aria-describedby={`${idPrefix}-export-desc`}
          >
            {exportProgress ? (
              <Loader2 size={15} className="spin" aria-hidden="true" />
            ) : (
              <Download size={15} aria-hidden="true" />
            )}
            {exportProgress ? `Đang tải ${exportProgress.done}/${exportProgress.total}` : "Tải xuống"}
          </button>
        </PrefRow>
      </div>

      <div className="ss-danger" role="group" aria-labelledby={`${idPrefix}-danger-title`}>
        <h4 id={`${idPrefix}-danger-title`}>Vùng nguy hiểm</h4>
        <PrefRow
          id={`${idPrefix}-delete`}
          title="Xoá toàn bộ hội thoại"
          description={
            empty
              ? "Chưa có hội thoại nào."
              : isAuthenticated
                ? "Xoá vĩnh viễn mọi hội thoại của tài khoản này, trên mọi thiết bị."
                : "Xoá vĩnh viễn mọi hội thoại của phiên ẩn danh trên trình duyệt này."
          }
        >
          {!confirming && (
            <button
              ref={deleteTriggerRef}
              type="button"
              className="ss-danger-btn"
              onClick={() => setConfirming(true)}
              disabled={empty || listQuery.isPending}
            >
              <Trash2 size={15} aria-hidden="true" />
              Xoá toàn bộ…
            </button>
          )}
        </PrefRow>
        {confirming && (
          <div
            className="ss-confirm"
            role="alertdialog"
            aria-labelledby={`${idPrefix}-confirm-text`}
            aria-describedby={`${idPrefix}-confirm-text`}
          >
            <p id={`${idPrefix}-confirm-text`}>
              Xoá vĩnh viễn <strong>{total} hội thoại</strong>? Thao tác này không thể hoàn tác.
            </p>
            <div className="ss-confirm-actions">
              <button
                ref={confirmCancelRef}
                type="button"
                className="ghost-btn"
                onClick={cancelConfirm}
                disabled={deleting}
              >
                Huỷ
              </button>
              <button type="button" className="danger-btn" onClick={handleDeleteAll} disabled={deleting}>
                {deleting && <Loader2 size={15} className="spin" aria-hidden="true" />}
                Xoá vĩnh viễn
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

/**
 * Hộp thoại Cài đặt của sinh viên (student-settings, D-06).
 *
 * Từ 768px: danh mục trái (Chung, Tài khoản khi đã đăng nhập, Dữ liệu & lịch sử)
 * và nội dung mục đang chọn. Hẹp hơn: toàn màn hình, các nhóm xếp thành danh sách.
 * Tùy chọn nhóm Chung tự lưu trên thiết bị (theme qua `useTheme`, phần còn lại qua
 * `usePreferences` của App).
 */
export default function StudentSettingsDialog({
  open,
  initialSection = "general",
  onClose,
  theme,
  onThemeChange,
  preferences,
  onLoggedOut,
  onHistoryCleared,
}) {
  const session = useAuthSession();
  const idPrefix = `ss${useId().replace(/:/g, "")}`;
  const sections = SETTINGS_SECTIONS.filter((key) => key !== "account" || session.isAuthenticated);
  const [active, setActive] = useState(initialSection);
  const bodyRef = useRef(null);

  // Mở lại (hoặc mở từ lối vào khác) thì về đúng mục được yêu cầu.
  useEffect(() => {
    if (open) setActive(initialSection);
  }, [open, initialSection]);

  const current = sections.includes(active) ? active : "general";

  // Bố cục danh sách: cuộn tới nhóm được yêu cầu.
  useEffect(() => {
    if (!open || typeof window.matchMedia !== "function") return;
    if (!window.matchMedia(STACKED_QUERY).matches) return;
    bodyRef.current?.querySelector(`[data-section="${initialSection}"]`)?.scrollIntoView?.({ block: "start" });
  }, [open, initialSection]);

  function handleLoggedOut() {
    onLoggedOut?.();
    onClose?.();
  }

  const titleId = `${idPrefix}-title`;

  function renderSection(key) {
    if (key === "general") {
      return (
        <GeneralSection
          idPrefix={`${idPrefix}-general`}
          theme={theme}
          onThemeChange={onThemeChange}
          preferences={preferences}
        />
      );
    }
    if (key === "account") return <AccountSection user={session.user} onLoggedOut={handleLoggedOut} />;
    return (
      <DataSection
        idPrefix={`${idPrefix}-data`}
        isAuthenticated={session.isAuthenticated}
        onHistoryCleared={onHistoryCleared}
      />
    );
  }

  return (
    <Modal open={open} onClose={onClose} labelledBy={titleId} className="student-settings">
      <header className="ss-head">
        <h2 id={titleId}>Cài đặt</h2>
        <button type="button" className="ss-close" onClick={onClose} aria-label="Đóng cài đặt" title="Đóng">
          <X size={18} aria-hidden="true" />
        </button>
      </header>
      <nav className="ss-nav" aria-label="Mục cài đặt">
        {sections.map((key) => {
          const { label, icon: Icon } = SECTION_META[key];
          return (
            <button
              key={key}
              type="button"
              className={`ss-nav-item ${key === current ? "is-active" : ""}`.trim()}
              aria-current={key === current ? "true" : undefined}
              aria-controls={`${idPrefix}-section-${key}`}
              onClick={() => setActive(key)}
            >
              <Icon size={16} aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </nav>
      <div className="ss-body" ref={bodyRef}>
        {sections.map((key) => (
          <section
            key={key}
            id={`${idPrefix}-section-${key}`}
            data-section={key}
            className={`ss-section ${key === current ? "is-active" : ""}`.trim()}
            aria-labelledby={`${idPrefix}-section-${key}-title`}
          >
            <h3 id={`${idPrefix}-section-${key}-title`}>{SECTION_META[key].label}</h3>
            {renderSection(key)}
          </section>
        ))}
      </div>
    </Modal>
  );
}
