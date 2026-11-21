import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, FlaskConical } from "lucide-react";
import { configApi, modelProfilesApi, queryKeys } from "./api";
import ConfigView from "./ConfigView";
import ModelsView from "./ModelsView";
import ThemePicker from "./components/ThemePicker";
import { SettingsIndex, SettingsTabs, settingsGroupOf } from "./settings/SettingsNav";
import PipelineSteps from "./settings/PipelineSteps";
import RetrievalTestPanel from "./settings/RetrievalTestPanel";
import { pipelineSummary } from "./settings/pipelineSummary";
import { activeModelSummary } from "./models/activeModels";
import { KIND_ORDER } from "./models/catalog";
import { formatLastSaved } from "./settings/relativeTime";
import { ADMIN_ANSWER_SECTIONS, modelKindForSection } from "./lib/appRoute";

const EMPTY_DRAFT = {
  values: null,
  saved: null,
  calibrated: {},
  config: null,
  changedKeys: [],
  dirtySections: [],
};

const GROUP_DESCRIPTIONS = {
  answer: "Điều chỉnh cách chatbot tìm tài liệu và trả lời sinh viên. Áp dụng sau khi lưu.",
  models: "Mô hình cho từng khâu trả lời. Đổi mô hình có hiệu lực ngay, riêng mô hình nhúng cần khởi động lại.",
  personal: "Chọn chế độ hiển thị phù hợp với bạn.",
};

/**
 * Trang Cài đặt quản trị (bố cục "Đường ống trả lời"): header + ba tab nhóm.
 * Tab "Hệ thống trả lời" mở đầu bằng dải bốn bước theo pipeline, form của bước
 * đang chọn hiện bên dưới; "Thử với câu hỏi" là ngăn kéo bên phải.
 *
 * `section` đến từ hash `#settings/<key>` do AdminShell quản lý. Trên mobile
 * `#settings` là danh sách mục, mỗi mục là một trang riêng có nút quay lại.
 */
export default function SettingsView({
  section = null,
  onSectionChange,
  onBackToList,
  theme,
  onThemeChange,
}) {
  const [draftState, setDraftState] = useState(EMPTY_DRAFT);
  const [testOpen, setTestOpen] = useState(false);

  const group = settingsGroupOf(section);
  const showAnswer = group === "answer";
  const showModels = group === "models";
  const showAppearance = group === "personal";
  const answerSection = ADMIN_ANSWER_SECTIONS.includes(section) ? section : "retrieval";
  const modelKind = modelKindForSection(section);

  useEffect(() => {
    setTestOpen(false);
  }, [section]);

  const handleSelect = useCallback((key) => onSectionChange?.(key), [onSectionChange]);
  const handleDraftState = useCallback((next) => setDraftState(next), []);
  const closeTest = useCallback(() => setTestOpen(false), []);

  const summaries = useMemo(
    () => pipelineSummary(draftState.values, draftState.config, draftState.calibrated),
    [draftState.values, draftState.config, draftState.calibrated]
  );

  // Danh sách mục trên mobile cũng hiện mô hình đang dùng; dùng chung cache với ModelsView.
  const registryQuery = useQuery({
    queryKey: queryKeys.modelProfiles,
    queryFn: ({ signal }) => modelProfilesApi.list({ signal }),
  });
  const configQuery = useQuery({
    queryKey: queryKeys.config,
    queryFn: ({ signal }) => configApi.get({ signal }),
  });
  const indexSummaries = useMemo(() => {
    const next = { ...summaries };
    KIND_ORDER.forEach((kind) => {
      const model = activeModelSummary(kind, registryQuery.data, configQuery.data);
      if (model) next[`models-${kind}`] = model.status.tone === "warn" ? [model.name, model.status.label] : [model.name];
    });
    return next;
  }, [summaries, registryQuery.data, configQuery.data]);

  const lastSavedLabel = draftState.config
    ? formatLastSaved(draftState.config.updated_at)
    : "Đang tải…";

  return (
    <section
      className={`settings-page ${section ? "has-section" : "is-index"}`}
      aria-label="Cài đặt"
    >
      <SettingsIndex
        dirtySections={draftState.dirtySections}
        summaries={indexSummaries}
        onSelect={handleSelect}
      />

      <div className="settings-main">
        <header className="settings-head">
          {section && (
            <button type="button" className="settings-back" onClick={onBackToList}>
              <ArrowLeft size={16} aria-hidden="true" />
              Quay lại Cài đặt
            </button>
          )}
          <div className="settings-head-row">
            <div className="settings-head-copy">
              <h1 className="settings-title" id="settings-title">
                Cài đặt
              </h1>
              <p>{GROUP_DESCRIPTIONS[group]}</p>
            </div>
            {showAnswer && (
              <div className="settings-head-actions">
                <span className="settings-saved">
                  Lần lưu gần nhất: <strong>{lastSavedLabel}</strong>
                </span>
                <button
                  type="button"
                  className="settings-test-trigger"
                  onClick={() => setTestOpen(true)}
                  aria-haspopup="dialog"
                >
                  <FlaskConical size={15} aria-hidden="true" />
                  Thử với câu hỏi
                </button>
              </div>
            )}
          </div>
          <SettingsTabs
            group={group}
            dirty={draftState.dirtySections.length > 0}
            onSelect={handleSelect}
          />
        </header>

        <div className="settings-content-body">
          {/* Giữ các form mounted để không mất bản nháp khi đổi tab. */}
          <div className="settings-panel" id="settings-panel-answer" hidden={!showAnswer}>
            <ConfigView
              activeSection={answerSection}
              onDraftState={handleDraftState}
              lead={
                <PipelineSteps
                  activeKey={answerSection}
                  summaries={summaries}
                  dirtySections={draftState.dirtySections}
                  onSelect={handleSelect}
                />
              }
            />
          </div>

          <div className="settings-panel" id="settings-panel-models" hidden={!showModels}>
            <ModelsView kind={modelKind ?? "llm"} onKindSelect={handleSelect} />
          </div>

          <div
            className="settings-panel appearance-panel"
            id="settings-panel-appearance"
            hidden={!showAppearance}
          >
            <section className="settings-card appearance-card" aria-labelledby="appearance-title">
              <header className="settings-card-head">
                <h2 id="appearance-title">Chế độ hiển thị</h2>
                <p>Áp dụng ngay, không cần lưu.</p>
              </header>
              <ThemePicker theme={theme} onThemeChange={onThemeChange} />
            </section>
          </div>
        </div>
      </div>

      <RetrievalTestPanel
        hidden={!showAnswer}
        open={testOpen && showAnswer}
        onClose={closeTest}
        config={draftState.config}
        draft={draftState.values}
        changedKeys={draftState.changedKeys}
      />
    </section>
  );
}
