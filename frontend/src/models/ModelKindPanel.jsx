import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCog,
  Info,
  KeyRound,
  Loader2,
  Pencil,
  Plus,
  RotateCw,
  Save,
  Trash2,
  Zap,
} from "lucide-react";
import { errorMessage, modelProfilesApi, queryKeys } from "../api";
import Modal from "../components/Modal";
import { useToast } from "../components/Toast";
import { ENV_ROW_NAME, normalizeEnvLlmProvider } from "./activeModels";
import {
  KINDS,
  KNOWN_EMBEDDING_DIMENSIONS,
  buildEmbeddingTestPayload,
  buildListModelsPayload,
  buildPayload,
  buildRerankerTestPayload,
  buildTestPayload,
  canListModels,
  canTestConnection,
  compatiblePresets,
  draftFromProfile,
  emptyDraft,
  isDraftDirty,
  keyRule,
  listModelsBlocker,
  modelListSignature,
  profileModelLabel,
  providerFields,
  providerName,
  validateDraft,
} from "./catalog";
import {
  ApiKeyField,
  ChoiceGroup,
  KIND_ICONS,
  ModelField,
  ProviderIcon,
  StatusPill,
  TextField,
  useWarnBeforeUnload,
} from "./fields";
import ProfileDialog from "./ProfileDialog";

// Hàng `.env` không có id trong kho; dùng khoá riêng cho trạng thái "đang áp dụng".
const ENV_ROW_ID = "__env__";

/** Ghi trạng thái kho mới vào cache; cấu hình chung cũng đổi khi chọn/sửa LLM, reranker. */
async function storeRegistry(queryClient, registry) {
  queryClient.setQueryData(queryKeys.modelProfiles, registry);
  await queryClient.invalidateQueries({ queryKey: queryKeys.config });
}

/** Mô hình nhiều chiều hơn kho vector không chọn dùng được; ít chiều hơn thì vector được đệm 0. */
function dimensionMismatch(kind, profile, vectorDim) {
  return kind === "embedding" && profile.dimension != null && vectorDim != null && profile.dimension > vectorDim;
}

const IDLE_LISTING = { status: "idle", models: [], message: null, signature: null };

/** Đổi một trường của bản nháp; mô hình nhúng quen thuộc thì tự điền số chiều. */
function applyDraftChange(kind, current, name, value) {
  const next = { ...current, [name]: value };
  // Tự điền số chiều nếu ô đang trống hoặc đang là số tự điền trước đó.
  if (kind === "embedding" && name === "model") {
    const known = KNOWN_EMBEDDING_DIMENSIONS[value.trim()];
    const previousKnown = KNOWN_EMBEDDING_DIMENSIONS[current.model.trim()];
    if (known && (!current.dimension || current.dimension === String(previousKnown ?? ""))) {
      next.dimension = String(known);
    }
  }
  if (name === "apiKey" && value.trim()) next.clearApiKey = false;
  return next;
}

/** Id của ô nhập theo tên lỗi (`apiKey` là ô khoá). */
function fieldInputId(idPrefix, name) {
  return `${idPrefix}-${name === "apiKey" ? "key" : name}`;
}

/** Hàng đầu danh sách: cấu hình `.env` của máy chủ (reranker: Heuristic có sẵn). */
function envRow(kind, registry) {
  const env = registry.env_defaults?.[kind] ?? {};
  if (kind === "reranker") {
    return { name: "Heuristic", tag: "Có sẵn", meta: "Không cần mô hình, chạy nhanh", label: "Heuristic" };
  }
  const provider = kind === "llm" ? normalizeEnvLlmProvider(env.provider) : env.provider;
  return {
    name: ENV_ROW_NAME,
    tag: ".env",
    meta: [providerName(kind, provider), env.model || "—"].join(" · "),
    label: "cấu hình .env",
  };
}

// ---------------------------------------------------------------------------
// Cảnh báo của từng loại
// ---------------------------------------------------------------------------

function KindNotices({ kind, registry, config }) {
  const notices = [];
  if (kind === "llm" && config?.llm?.has_api_key === false) {
    notices.push(
      <div key="key" className="inline-alert is-warning" role="alert">
        <AlertTriangle size={16} />
        <span>
          Mô hình đang dùng chưa có API key nên chatbot sẽ không trả lời được. Sửa mô hình để thêm khoá, hoặc đặt khoá
          trong <code>.env</code>.
        </span>
      </div>
    );
  }
  if (kind === "reranker" && config?.reranker?.enabled === false) {
    notices.push(
      <div key="off" className="inline-alert is-warning">
        <AlertTriangle size={16} />
        <span>
          Reranker đang tắt nên mô hình được chọn chưa được dùng.{" "}
          <a className="mdl-inline-link" href="#settings/reranker">
            Bật trong mục Xếp hạng lại <ArrowRight size={13} />
          </a>
        </span>
      </div>
    );
  }
  const runtime = registry.embedding_runtime;
  if (kind === "embedding" && runtime.load_error) {
    notices.push(
      <div key="load" className="inline-alert is-error" role="alert">
        <AlertCircle size={16} />
        <span>
          Lần khởi động này không áp được embedding đã chọn nên vẫn chạy cấu hình <code>.env</code>:{" "}
          {runtime.load_error}
        </span>
      </div>
    );
  }
  if (kind === "embedding" && runtime.restart_required && !runtime.load_error) {
    notices.push(
      <div key="restart" className="inline-alert is-warning" role="status">
        <RotateCw size={16} />
        <span>
          Lựa chọn mới có hiệu lực sau khi <strong>khởi động lại backend</strong>. Sau đó vào <strong>Dataset</strong> →{" "}
          <strong>Nạp lại toàn bộ</strong> để tạo lại vector cho mọi tài liệu; trước khi nạp lại, kết quả tìm kiếm sẽ sai
          lệch.
        </span>
      </div>
    );
  }
  if (notices.length === 0) return null;
  return <div className="mdl-list-notices">{notices}</div>;
}

// ---------------------------------------------------------------------------
// Hàng trong danh sách
// ---------------------------------------------------------------------------

function ModelRow({ name, meta, metaTitle, icon, tags, isActive, isEnv = false, useButton, actions }) {
  return (
    <li className={`mdl-row ${isActive ? "is-active" : ""} ${isEnv ? "is-env" : ""}`} aria-current={isActive || undefined}>
      <span className="mdl-row-mark" aria-hidden="true" />
      <span className="mdl-row-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="mdl-row-text">
        <div className="mdl-row-title">
          <strong className="mdl-row-name" title={name}>
            {name}
          </strong>
          {tags}
        </div>
        <span className="mdl-row-meta" title={metaTitle}>
          {meta}
        </span>
      </div>
      <div className="mdl-row-actions">
        {useButton}
        {actions}
      </div>
    </li>
  );
}

function UseButton({ name, onClick, applying, disabled, title }) {
  return (
    <button
      type="button"
      className="ghost-btn mdl-use-btn"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={`Dùng ${name}`}
    >
      {applying ? <Loader2 size={14} className="spin" /> : null}
      Dùng
    </button>
  );
}

function profileMeta(kind, profile) {
  const parts = [providerName(kind, profile.provider), profileModelLabel(profile)];
  if (kind === "embedding" && profile.dimension) parts.push(`${profile.dimension} chiều`);
  return parts.join(" · ");
}

// ---------------------------------------------------------------------------
// Form thêm / sửa (trong hộp thoại)
// ---------------------------------------------------------------------------

function ProfileEditor({ kind, profile, registry, hidden, onClose }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isEdit = Boolean(profile);
  const initial = useMemo(() => (profile ? draftFromProfile(profile) : emptyDraft(kind)), [kind, profile]);
  const [draft, setDraft] = useState(initial);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  // Danh sách mô hình lấy từ nhà cung cấp; chỉ hiện khi khớp provider/Base URL/khoá hiện tại.
  const [listing, setListing] = useState(IDLE_LISTING);
  const [modelMode, setModelMode] = useState("select");
  const listRequestRef = useRef(0);
  const rootRef = useRef(null);
  const idPrefix = `mdl-${kind}-form`;

  const fields = providerFields(kind, draft.provider);
  const rule = keyRule(kind, draft.provider);
  const hasStoredKey = Boolean(profile?.has_api_key) && profile?.provider === draft.provider;
  const errors = useMemo(() => validateDraft(kind, draft, { hasStoredKey }), [kind, draft, hasStoredKey]);
  const dirty = isDraftDirty(kind, draft, initial);
  useWarnBeforeUnload(dirty);
  const listable = canListModels(kind, draft.provider);
  const listSignature = modelListSignature(kind, draft);
  const currentListing = listable && listing.signature === listSignature ? listing : IDLE_LISTING;

  useEffect(() => {
    rootRef.current?.querySelector("input")?.focus({ preventScroll: true });
  }, []);

  function update(name, value) {
    setDraft((current) => applyDraftChange(kind, current, name, value));
    setTestResult(null);
  }

  /**
   * Lấy danh sách mô hình từ nhà cung cấp. `auto` (rời ô Base URL/khoá): bỏ qua im lặng nếu
   * thiếu thông tin hoặc đã tải cho đúng cấu hình này.
   */
  async function loadModels({ auto = false } = {}) {
    if (!listable) return;
    const signature = listSignature;
    const blocker = listModelsBlocker(kind, draft, { hasStoredKey });
    if (blocker) {
      if (!auto) setListing({ status: "error", models: [], message: blocker, signature });
      return;
    }
    if (listing.signature === signature && (listing.status === "loading" || (auto && listing.status !== "idle"))) {
      return;
    }
    const requestId = ++listRequestRef.current;
    setListing({ status: "loading", models: [], message: null, signature });
    try {
      const result = await modelProfilesApi.listModels(buildListModelsPayload(kind, draft, profile?.id));
      if (requestId !== listRequestRef.current) return;
      if (!result.success) {
        setListing({ status: "error", models: [], message: result.message, signature });
        return;
      }
      const models = result.models ?? [];
      setListing({ status: "ok", models, message: result.message, signature });
      setModelMode("select");
      // Máy chủ chỉ phục vụ một mô hình (HF TEI…): điền luôn nếu ô đang trống.
      // Bỏ qua nếu admin đã đổi provider/Base URL/khoá trong lúc chờ.
      if (models.length === 1) {
        setDraft((current) =>
          current.model.trim() || modelListSignature(kind, current) !== signature
            ? current
            : applyDraftChange(kind, current, "model", models[0])
        );
      }
    } catch (err) {
      if (requestId !== listRequestRef.current) return;
      setListing({
        status: "error",
        models: [],
        message: errorMessage(err, "Máy chủ từ chối yêu cầu."),
        signature,
      });
    }
  }

  /** Rời ô Base URL hoặc ô khoá có giá trị: tự lấy danh sách. */
  function autoLoadModels(value) {
    if (String(value ?? "").trim()) loadModels({ auto: true });
  }

  function ensureValid() {
    if (Object.keys(errors).length === 0) return true;
    setShowErrors(true);
    const first = ["name", ...fields.map((field) => field.name), "apiKey"].find((name) => errors[name]);
    rootRef.current?.querySelector(`#${fieldInputId(idPrefix, first)}`)?.focus();
    return false;
  }

  async function handleTest() {
    if (!ensureValid()) return;
    setTesting(true);
    setTestResult(null);
    try {
      let result;
      if (kind === "reranker") result = await modelProfilesApi.testReranker(buildRerankerTestPayload(draft, profile?.id));
      else if (kind === "embedding")
        result = await modelProfilesApi.testEmbedding(buildEmbeddingTestPayload(draft, profile?.id));
      else result = await modelProfilesApi.testLlm(buildTestPayload(draft, profile?.id));
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: errorMessage(err, "Máy chủ từ chối yêu cầu kiểm tra.") });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    if (!ensureValid()) return;
    setSaving(true);
    try {
      const payload = buildPayload(kind, draft, { isEdit });
      const next = isEdit
        ? await modelProfilesApi.update(profile.id, payload)
        : await modelProfilesApi.create(payload);
      await storeRegistry(queryClient, next);
      const isActive = isEdit && next.active?.[kind] === profile.id;
      let message = isEdit ? `Đã lưu ${payload.name}.` : `Đã thêm ${payload.name} vào kho.`;
      if (isActive && kind !== "embedding") message += " Hệ thống đã áp dụng thay đổi.";
      if (isActive && kind === "embedding") message += " Khởi động lại backend để áp dụng.";
      toast.success(message);
      onClose();
    } catch (err) {
      toast.error(`Chưa lưu được mô hình. ${errorMessage(err, "Máy chủ từ chối cấu hình này.")}`);
    } finally {
      setSaving(false);
    }
  }

  const vectorDim = registry.embedding_runtime?.vector_dim;
  const dimensionValue = Number(draft.dimension);
  const hasDimension = kind === "embedding" && draft.dimension && !errors.dimension && vectorDim != null;
  const showDimWarning = hasDimension && dimensionValue > vectorDim;
  const kindLabel = KINDS[kind].label;
  const isActiveProfile = isEdit && registry.active?.[kind] === profile.id;
  // Chỉ báo khi lưu có hệ quả ngay với mô hình đang dùng.
  let description;
  if (isActiveProfile) {
    description =
      kind === "embedding"
        ? "Mô hình đã chọn: thay đổi có hiệu lực sau khi khởi động lại backend."
        : "Mô hình đang dùng: lưu xong áp dụng ngay.";
  }
  const busy = saving || testing;

  return (
    <ProfileDialog
      id={idPrefix}
      title={isEdit ? `Sửa ${profile.name}` : `Thêm ${kindLabel}`}
      description={description}
      hidden={hidden}
      onClose={() => !saving && onClose()}
      onDismiss={dirty || busy ? undefined : onClose}
      footer={
        <>
          <span className="mdl-dirty" role="status">
            {dirty ? "Có thay đổi chưa lưu" : ""}
          </span>
          <div className="mdl-actions">
            {canTestConnection(kind, draft.provider) && (
              <button type="button" className="ghost-btn" onClick={handleTest} disabled={busy}>
                {testing ? <Loader2 size={15} className="spin" /> : <Zap size={15} />}
                {testing ? "Đang kiểm tra..." : "Kiểm tra kết nối"}
              </button>
            )}
            <button type="button" className="ghost-btn" onClick={onClose} disabled={saving}>
              Huỷ
            </button>
            <button type="button" className="primary-btn" onClick={handleSave} disabled={saving || (isEdit && !dirty)}>
              {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
              {saving ? "Đang lưu..." : isEdit ? "Lưu thay đổi" : "Thêm vào kho"}
            </button>
          </div>
        </>
      }
    >
      <div className="mdl-stack" ref={rootRef}>
        <TextField
          id={`${idPrefix}-name`}
          field={{ label: "Tên hiển thị", placeholder: "Mặc định là tên mô hình" }}
          value={draft.name}
          onChange={(value) => update("name", value)}
          error={showErrors ? errors.name : undefined}
        />

        <ChoiceGroup
          kind={kind}
          name={`${idPrefix}-provider`}
          legend="Nhà cung cấp"
          options={KINDS[kind].providers}
          value={draft.provider}
          onChange={(provider) => {
            setDraft((current) => ({ ...current, provider }));
            setShowErrors(false);
            setTestResult(null);
          }}
        />

        {draft.provider === "openai_compatible" && (
          <div className="mdl-presets" role="group" aria-label="Điền nhanh địa chỉ máy chủ">
            <span>Điền nhanh:</span>
            {compatiblePresets(kind).map((preset) => (
              <button
                key={preset.key}
                type="button"
                className="mdl-preset"
                aria-pressed={draft.base_url === preset.baseUrl}
                onClick={() => {
                  setDraft((current) => {
                    const model = preset.model || current.model;
                    const known = kind === "embedding" ? KNOWN_EMBEDDING_DIMENSIONS[model] : undefined;
                    return {
                      ...current,
                      base_url: preset.baseUrl,
                      model,
                      ...(known && !current.dimension ? { dimension: String(known) } : {}),
                    };
                  });
                  setTestResult(null);
                }}
              >
                {preset.label}
              </button>
            ))}
          </div>
        )}

        <div className="mdl-grid">
          {fields.map((field) => {
            const fieldError =
              showErrors || ((field.url || field.number) && String(draft[field.name]).trim())
                ? errors[field.name]
                : undefined;
            if (field.name === "model" && listable) {
              return (
                <ModelField
                  key={`${draft.provider}-${field.name}`}
                  id={`${idPrefix}-${field.name}`}
                  field={field}
                  value={draft.model}
                  onChange={(value) => update("model", value)}
                  error={fieldError}
                  listing={currentListing}
                  onLoad={() => loadModels()}
                  mode={modelMode}
                  onModeChange={setModelMode}
                />
              );
            }
            return (
              <TextField
                key={`${draft.provider}-${field.name}`}
                id={`${idPrefix}-${field.name}`}
                field={field}
                value={draft[field.name]}
                onChange={(value) => update(field.name, value)}
                onBlur={field.name === "base_url" && listable ? (event) => autoLoadModels(event.target.value) : undefined}
                error={fieldError}
              />
            );
          })}
        </div>

        {showDimWarning && (
          <div className="inline-alert is-warning">
            <AlertTriangle size={16} />
            <span>
              Mô hình có {dimensionValue} chiều, nhiều hơn <code>VECTOR_DIM</code> ({vectorDim}) của kho vector: lưu
              được nhưng chưa chọn làm mô hình đang dùng được. Chọn số chiều nhỏ hơn nếu mô hình hỗ trợ.
            </span>
          </div>
        )}



        {rule && (
          <ApiKeyField
            key={draft.provider}
            id={`${idPrefix}-key`}
            value={draft.apiKey}
            onChange={(value) => update("apiKey", value)}
            hasKey={hasStoredKey}
            required={Boolean(rule.required)}
            error={showErrors ? errors.apiKey : undefined}
            onBlur={listable ? (event) => autoLoadModels(event.target.value) : undefined}
            clearKey={draft.clearApiKey}
            onClearKeyChange={(clearApiKey) => setDraft((current) => ({ ...current, clearApiKey }))}
          />
        )}

        {testResult && (
          <div
            className={`mdl-test-result ${testResult.success ? "is-ok" : "is-error"}`}
            role={testResult.success ? "status" : "alert"}
          >
            {testResult.success ? <CheckCircle2 size={17} /> : <AlertCircle size={17} />}
            <div>
              <strong>{testResult.success ? "Kết nối thành công" : "Kết nối thất bại"}</strong>
              <p>{testResult.message}</p>
              {(testResult.latency_ms != null || testResult.sample_output) && (
                <p className="mdl-test-meta">
                  {testResult.latency_ms != null && <>Thời gian phản hồi: {Math.round(testResult.latency_ms)} ms</>}
                  {testResult.sample_output &&
                    (kind !== "llm" ? (
                      <> · {testResult.sample_output}</>
                    ) : (
                      <> · Mô hình trả lời: “{testResult.sample_output}”</>
                    ))}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </ProfileDialog>
  );
}

// ---------------------------------------------------------------------------
// Panel của một loại mô hình
// ---------------------------------------------------------------------------

/**
 * Một danh sách cho một loại mô hình: hàng `.env` (reranker: Heuristic) rồi các mô hình
 * trong kho. Bấm "Dùng" trên hàng nào thì hệ thống đổi sang mô hình đó; với embedding
 * cần xác nhận vì phải khởi động lại backend và nạp lại tài liệu. Thêm/sửa mở hộp thoại ở giữa màn hình.
 */
export default function ModelKindPanel({ kind, registry, config, active = true }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  // null: không mở form; { profile: null } thêm mới; { profile } sửa.
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  // id đang áp dụng (ENV_ROW_ID cho hàng `.env`) và lựa chọn embedding chờ xác nhận.
  const [applyingId, setApplyingId] = useState(null);
  const [pendingActivate, setPendingActivate] = useState(null);

  const allProfiles = registry.profiles ?? [];
  const profiles = useMemo(() => allProfiles.filter((profile) => profile.kind === kind), [allProfiles, kind]);
  const activeId = registry.active?.[kind] ?? null;
  const runtime = registry.embedding_runtime;
  const vectorDim = runtime?.vector_dim;
  const env = envRow(kind, registry);
  const KindIcon = KIND_ICONS[kind];

  async function activate(target) {
    setApplyingId(target.id ?? ENV_ROW_ID);
    try {
      const next = await modelProfilesApi.activate(kind, target.id);
      await storeRegistry(queryClient, next);
      if (kind === "embedding") {
        toast.success(`Đã chọn ${target.label}. Khởi động lại backend để áp dụng.`);
      } else {
        toast.success(`Đã chuyển ${KINDS[kind].label} sang ${target.label}.`);
      }
    } catch (err) {
      toast.error(`Chưa đổi được mô hình đang dùng. ${errorMessage(err, "Máy chủ từ chối yêu cầu.")}`);
    } finally {
      setApplyingId(null);
    }
  }

  function requestActivate(target) {
    if (kind === "embedding") setPendingActivate(target);
    else activate(target);
  }

  async function confirmDelete() {
    const target = pendingDelete;
    setDeleting(true);
    try {
      const next = await modelProfilesApi.remove(target.id);
      await storeRegistry(queryClient, next);
      if (editing?.profile?.id === target.id) setEditing(null);
      toast.success(`Đã xoá ${target.name} khỏi kho.`);
      setPendingDelete(null);
    } catch (err) {
      toast.error(`Chưa xoá được mô hình. ${errorMessage(err, "Máy chủ từ chối yêu cầu.")}`);
    } finally {
      setDeleting(false);
    }
  }

  const applying = applyingId !== null;
  const activeTag = <StatusPill tone="ok">{kind === "embedding" ? "Đã chọn" : "Đang dùng"}</StatusPill>;
  const runningTag = <StatusPill>Đang chạy</StatusPill>;

  return (
    <>
      <section className="mdl-card mdl-list-card" aria-labelledby={`mdl-${kind}-list-title`}>
        <header className="mdl-card-head">
          <span className="mdl-card-icon" aria-hidden="true">
            <KindIcon size={18} />
          </span>
          <div className="mdl-card-heading">
            <h3 id={`mdl-${kind}-list-title`}>{KINDS[kind].title}</h3>
            <p>{KINDS[kind].description}</p>
          </div>
          <button
            type="button"
            className="ghost-btn mdl-add-btn"
            onClick={() => setEditing({ profile: null })}
            disabled={Boolean(editing)}
          >
            <Plus size={15} />
            Thêm mô hình
          </button>
        </header>

        <KindNotices kind={kind} registry={registry} config={config} />

        <ul className="mdl-rows" aria-label={`Danh sách ${KINDS[kind].label}`}>
          <ModelRow
            isEnv
            name={env.name}
            meta={env.meta}
            icon={kind === "reranker" ? <ProviderIcon kind="reranker" provider="heuristic" size={15} /> : <FileCog size={15} />}
            isActive={activeId === null}
            tags={
              <>
                <StatusPill>{env.tag}</StatusPill>
                {activeId === null && activeTag}
                {kind === "embedding" && !runtime?.profile_id && runningTag}
              </>
            }
            useButton={
              activeId !== null && (
                <UseButton
                  name={env.name}
                  applying={applyingId === ENV_ROW_ID}
                  disabled={applying}
                  onClick={() => requestActivate({ id: null, label: env.label })}
                />
              )
            }
          />
          {profiles.map((profile) => {
            const isActive = activeId === profile.id;
            const isRunning = kind === "embedding" && runtime?.profile_id === profile.id;
            const mismatch = dimensionMismatch(kind, profile, vectorDim);
            const meta = profileMeta(kind, profile);
            const address = profile.base_url || profile.endpoint;
            return (
              <ModelRow
                key={profile.id}
                name={profile.name}
                meta={meta}
                metaTitle={address ? `${meta}\n${address}` : undefined}
                icon={<ProviderIcon kind={kind} provider={profile.provider} size={15} />}
                isActive={isActive}
                tags={
                  <>
                    {isActive && activeTag}
                    {isRunning && runningTag}
                    {profile.has_api_key && (
                      <StatusPill>
                        <KeyRound size={11} /> Đã lưu khoá
                      </StatusPill>
                    )}
                    {mismatch && <StatusPill tone="warn">Vượt VECTOR_DIM</StatusPill>}
                  </>
                }
                useButton={
                  !isActive && (
                    <UseButton
                      name={profile.name}
                      applying={applyingId === profile.id}
                      disabled={applying || mismatch}
                      title={mismatch ? `${profile.dimension} chiều, kho vector dùng ${vectorDim}.` : undefined}
                      onClick={() => requestActivate({ id: profile.id, label: profile.name })}
                    />
                  )
                }
                actions={
                  <>
                    <button
                      type="button"
                      className="mdl-icon-btn"
                      onClick={() => setEditing({ profile })}
                      aria-label={`Sửa ${profile.name}`}
                      title="Sửa"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      type="button"
                      className="mdl-icon-btn is-danger"
                      onClick={() => setPendingDelete(profile)}
                      disabled={isActive}
                      aria-label={`Xoá ${profile.name}`}
                      title={isActive ? "Đang được dùng — chọn mô hình khác trước khi xoá." : "Xoá"}
                    >
                      <Trash2 size={14} />
                    </button>
                  </>
                }
              />
            );
          })}
        </ul>

        {profiles.length === 0 && (
          <p className="mdl-empty">
            Chưa có {KINDS[kind].label} nào trong kho. Bấm &ldquo;Thêm mô hình&rdquo; để cấu hình rồi chọn dùng tại đây.
          </p>
        )}

        {kind === "embedding" && (
          <p className="mdl-list-foot">
            <Info size={14} aria-hidden="true" />
            <span>
              Kho vector dùng <code>VECTOR_DIM = {vectorDim}</code>: mô hình ít chiều hơn được thêm số 0 cho đủ, mô hình
              nhiều chiều hơn lưu được nhưng không chọn dùng được. Script dòng lệnh (<code>scripts/ingest.py</code>) vẫn dùng embedding trong <code>.env</code>.
            </span>
          </p>
        )}
      </section>

      {editing && (
        <ProfileEditor
          key={editing.profile?.id ?? "new"}
          kind={kind}
          profile={editing.profile}
          registry={registry}
          hidden={!active}
          onClose={() => setEditing(null)}
        />
      )}

      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => !deleting && setPendingDelete(null)}
        title="Xoá mô hình?"
        description={
          pendingDelete ? `“${pendingDelete.name}” và API key đã lưu của nó sẽ bị xoá khỏi kho. Không thể hoàn tác.` : ""
        }
        icon={<AlertTriangle size={20} />}
        tone="danger"
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setPendingDelete(null)} disabled={deleting}>
              Huỷ
            </button>
            <button type="button" className="danger-btn" onClick={confirmDelete} disabled={deleting}>
              {deleting ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
              Xoá
            </button>
          </>
        }
      />

      <Modal
        open={Boolean(pendingActivate)}
        onClose={() => setPendingActivate(null)}
        title="Đổi mô hình nhúng?"
        description={
          pendingActivate
            ? `Chọn ${pendingActivate.label} có hiệu lực sau khi khởi động lại backend. Sau đó cần vào Dataset → Nạp lại toàn bộ để tạo lại vector; trước khi nạp lại, kết quả tìm kiếm sẽ sai lệch.`
            : ""
        }
        icon={<RotateCw size={20} />}
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={() => setPendingActivate(null)}>
              Huỷ
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                const target = pendingActivate;
                setPendingActivate(null);
                activate(target);
              }}
            >
              <CheckCircle2 size={15} />
              Chọn mô hình này
            </button>
          </>
        }
      />
    </>
  );
}
