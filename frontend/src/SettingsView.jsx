import React, { useCallback, useEffect, useState } from "react";
import { ArrowLeft, FlaskConical } from "lucide-react";
import ConfigView from "./ConfigView";
import ModelsView from "./ModelsView";
import ThemePicker from "./components/ThemePicker";
import { SettingsIndex, SettingsSidebar } from "./settings/SettingsNav";
import RetrievalTestPanel from "./settings/RetrievalTestPanel";
import { formatLastSaved } from "./settings/relativeTime";
import {
  ADMIN_ANSWER_SECTIONS,
  ADMIN_MODEL_SECTIONS,
  modelKindForSection,
} from "./lib/appRoute";

const EMPTY_DRAFT = {
  values: null,
  saved: null,
  calibrated: {},
  config: null,
  changedKeys: [],
  dirtySections: [],
};

/**
 * Trang Cài đặt quản trị: danh mục dọc ba nhóm, form một cột theo pipeline và
 * bảng "Thử với câu hỏi" cạnh form (drawer khi hẹp).
 *
 * `section` đến từ hash `#settings/<key>` do AdminShell quản lý. Trên desktop mọi
 * mục của nhóm "Hệ thống trả lời" là anchor trong cùng một form; trên mobile
 * `#settings` là danh sách, mỗi mục là một trang riêng có nút quay lại.
 */
export default function SettingsView({
  section = null,
  onSectionChange,
  onBackToList,
  theme,
  onThemeChange,
}) {
  const [draftState, setDraftState] = useState(EMPTY_DRAFT);
  const [activeKey, setActiveKey] = useState(section ?? "retrieval");
  const [testOpen, setTestOpen] = useState(false);

  const showAnswer = section === null || ADMIN_ANSWER_SECTIONS.includes(section);
  const showModels = ADMIN_MODEL_SECTIONS.includes(section);
  const showAppearance = section === "appearance";
  const modelKind = modelKindForSection(section);

  useEffect(() => {
    setActiveKey(section ?? "retrieval");
    setTestOpen(false);
  }, [section]);

  const handleSelect = useCallback(
    (key) => {
      setActiveKey(key);
      onSectionChange?.(key);
    },
    [onSectionChange]
  );

  const handleDraftState = useCallback((next) => {
    setDraftState(next);
  }, []);

  const lastSavedLabel = draftState.config
    ? formatLastSaved(draftState.config.updated_at)
    : "Đang tải…";

  const answerTitle = "Hệ thống trả lời";
  const title = showAnswer ? answerTitle : showModels ? "Mô hình" : "Giao diện";
  const description = showAnswer
    ? "Truy xuất, ngưỡng tin cậy và sinh câu trả lời. Áp dụng sau khi lưu."
    : showModels
    ? "Kho mô hình cho từng khâu; mỗi loại có nút thêm, sửa, xoá riêng."
    : "Chọn chế độ hiển thị phù hợp với bạn.";

  return (
    <section
      className={`settings-page ${section ? "has-section" : "is-index"}`}
      aria-label="Cài đặt"
    >
      <div className={`settings-shell ${showAnswer ? "is-answer" : ""}`}>
        <SettingsSidebar
          activeKey={activeKey}
          dirtySections={draftState.dirtySections}
          onSelect={handleSelect}
        />

        <div className="settings-main">
          <SettingsIndex
            dirtySections={draftState.dirtySections}
            onSelect={handleSelect}
          />

          {section && (
            <button type="button" className="settings-back" onClick={onBackToList}>
              <ArrowLeft size={16} aria-hidden="true" />
              Quay lại Cài đặt
            </button>
          )}

          <div className="settings-content">
            <header className="settings-head">
              <div className="settings-head-copy">
                <div className="settings-head-title-row">
                  <h2>{title}</h2>
                  {showAnswer && (
                    <span className="settings-saved">
                      Lần lưu gần nhất: <strong>{lastSavedLabel}</strong>
                    </span>
                  )}
                </div>
                <p>{description}</p>
              </div>
              {showAnswer && (
                <button
                  type="button"
                  className="settings-test-trigger"
                  onClick={() => setTestOpen(true)}
                  aria-haspopup="dialog"
                >
                  <FlaskConical size={15} aria-hidden="true" />
                  Thử với câu hỏi
                </button>
              )}
            </header>

            <div className="settings-content-body">
              {/* Giữ các form mounted để không mất bản nháp khi đổi mục. */}
              <div className="settings-panel" id="settings-panel-answer" hidden={!showAnswer}>
                <ConfigView
                  activeSection={section ?? "retrieval"}
                  onSectionActive={setActiveKey}
                  onDraftState={handleDraftState}
                />
              </div>

              <div className="settings-panel" id="settings-panel-models" hidden={!showModels}>
                <ModelsView kind={modelKind ?? "llm"} />
              </div>

              <div
                className="settings-panel appearance-panel"
                id="settings-panel-appearance"
                hidden={!showAppearance}
              >
                <ThemePicker theme={theme} onThemeChange={onThemeChange} />
              </div>
            </div>
          </div>
        </div>

        <RetrievalTestPanel
          hidden={!showAnswer}
          open={testOpen && showAnswer}
          onClose={() => setTestOpen(false)}
          config={draftState.config}
          draft={draftState.values}
          changedKeys={draftState.changedKeys}
        />
      </div>
    </section>
  );
}
