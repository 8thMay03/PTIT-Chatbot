import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownUp,
  ArrowRight,
  Binary,
  CheckCircle2,
  Info,
  KeyRound,
  Loader2,
  MessageSquareText,
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
import {
  COMPATIBLE_PRESETS,
  KINDS,
  KNOWN_EMBEDDING_DIMENSIONS,
  buildPayload,
  buildTestPayload,
  draftFromProfile,
  emptyDraft,
  isDraftDirty,
  keyRule,
  profileModelLabel,
  providerFields,
  providerName,
  validateDraft,
} from "./catalog";
import {
  ApiKeyField,
  ChoiceGroup,
  ProviderIcon,
  Section,
  StatusPill,
  TextField,
  useWarnBeforeUnload,
} from "./fields";

const KIND_ICONS = { llm: MessageSquareText, embedding: Binary, reranker: ArrowDownUp };

const ENV_KEY_LABELS = {
  llm: {
    openai: "OPENAI_API_KEY trong .env",
    gemini: "GEMINI_API_KEY trong .env",
    azure: "AZURE_OPENAI_API_KEY trong .env",
  },
  embedding: { openai: "OPENAI_API_KEY đang chạy" },
};

/** Ghi trạng thái kho mới vào cache; cấu hình chung cũng đổi khi chọn/sửa LLM, reranker. */
async function storeRegistry(queryClient, registry) {
  queryClient.setQueryData(queryKeys.modelProfiles, registry);
  await queryClient.invalidateQueries({ queryKey: queryKeys.config });
}

function dimensionMismatch(kind, profile, vectorDim) {
  return kind === "embedding" && profile.dimension != null && profile.dimension !== vectorDim;
}

// ---------------------------------------------------------------------------
// Mô hình đang dùng
// ---------------------------------------------------------------------------

function envOptionLabel(kind, registry) {
  const env = registry.env_defaults?.[kind] ?? {};
  if (kind === "reranker") return "Heuristic (có sẵn, không cần mô hình)";
  const provider = kind === "llm" ? normalizeEnvLlmProvider(env.provider) : env.provider;
  return `Cấu hình .env · ${env.model || "—"} (${providerName(kind, provider)})`;
}

function normalizeEnvLlmProvider(value) {
  const name = String(value || "").toLowerCase();
  if (name === "google") return "gemini";
  if (name === "azure_openai") return "azure";
  if (["openai", "gemini", "azure"].includes(name)) return name;
  return "openai_compatible";
}

function CurrentLine({ kind, registry, config, profilesById }) {
  if (kind === "llm") {
    const llm = config?.llm;
    if (!llm) return null;
    return (
      <>
        <span>
          Đang dùng <strong>{llm.model || "—"}</strong> · {providerName("llm", normalizeEnvLlmProvider(llm.provider))}
        </span>
        {llm.has_api_key === false && (
          <StatusPill tone="warn">
            <AlertTriangle size={12} /> Chưa có API key — chatbot sẽ không trả lời được
          </StatusPill>
        )}
      </>
    );
  }
  if (kind === "reranker") {
    const reranker = config?.reranker;
    if (!reranker) return null;
    const usesModel = reranker.provider === "cross-encoder";
    return (
      <>
        <span>
          Đang dùng <strong>{usesModel ? reranker.model : "Heuristic"}</strong>
          {usesModel && " · Cross-Encoder"}
        </span>
        {reranker.enabled === false ? (
          <StatusPill tone="warn">Đang tắt</StatusPill>
        ) : (
          <StatusPill tone="ok">Đang bật</StatusPill>
        )}
      </>
    );
  }
  const runtime = registry.embedding_runtime;
  const running = runtime.profile_id ? profilesById[runtime.profile_id] : null;
  return (
    <>
      <span>
        Đang chạy <strong>{runtime.model || "—"}</strong> · {providerName("embedding", runtime.provider)}
        {running ? ` (${running.name})` : " (.env)"}
      </span>
      <StatusPill>VECTOR_DIM = {runtime.vector_dim}</StatusPill>
    </>
  );
}

function ActiveModelCard({ kind, registry, config, profiles, profilesById }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const active = registry.active?.[kind] ?? "";
  const [selected, setSelected] = useState(active);
  const [applying, setApplying] = useState(false);
  const vectorDim = registry.embedding_runtime?.vector_dim;
  const selectId = `mdl-${kind}-active`;

  useEffect(() => setSelected(active), [active]);

  async function handleApply() {
    setApplying(true);
    try {
      const next = await modelProfilesApi.activate(kind, selected || null);
      await storeRegistry(queryClient, next);
      const profile = selected ? profilesById[selected] : null;
      const label = profile ? profile.name : envOptionLabel(kind, registry);
      if (kind === "embedding") {
        toast.success(`Đã chọn ${label}. Khởi động lại backend để áp dụng.`);
      } else {
        toast.success(`Đã chuyển ${KINDS[kind].label} sang ${label}.`);
      }
    } catch (err) {
      toast.error(`Chưa đổi được mô hình đang dùng. ${errorMessage(err, "Máy chủ từ chối yêu cầu.")}`);
    } finally {
      setApplying(false);
    }
  }

  const runtime = registry.embedding_runtime;
  const rerankerOff = kind === "reranker" && config?.reranker?.enabled === false;
  const KindIcon = KIND_ICONS[kind];

  return (
    <Section
      id={`mdl-${kind}-current`}
      icon={<KindIcon size={18} />}
      title={KINDS[kind].title}
      description={KINDS[kind].description}
      current={<CurrentLine kind={kind} registry={registry} config={config} profilesById={profilesById} />}
      footer={
        <div className="mdl-actions">
          <button
            type="button"
            className="primary-btn"
            onClick={handleApply}
            disabled={applying || selected === active}
          >
            {applying ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />}
            {applying ? "Đang áp dụng..." : "Dùng mô hình này"}
          </button>
        </div>
      }
    >
      <div className="mdl-stack">
        <div className="mdl-field">
          <label htmlFor={selectId}>Mô hình đang dùng cho hệ thống</label>
          <select
            id={selectId}
            className="mdl-input mdl-select"
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
            disabled={applying}
          >
            <option value="">{envOptionLabel(kind, registry)}</option>
            {profiles.map((profile) => {
              const mismatch = dimensionMismatch(kind, profile, vectorDim);
              return (
                <option key={profile.id} value={profile.id} disabled={mismatch && profile.id !== active}>
                  {profile.name} — {providerName(kind, profile.provider)} · {profileModelLabel(profile)}
                  {mismatch ? ` (${profile.dimension} chiều, khác VECTOR_DIM)` : ""}
                </option>
              );
            })}
          </select>
          <span className="mdl-field-hint">
            {profiles.length === 0
              ? "Chưa có mô hình nào trong kho. Thêm mô hình ở danh sách bên dưới để chọn tại đây."
              : "Chọn từ những mô hình đã cấu hình bên dưới."}
          </span>
        </div>

        {rerankerOff && (
          <div className="inline-alert is-warning">
            <AlertTriangle size={16} />
            <span>
              Reranker đang tắt nên mô hình được chọn chưa được dùng.{" "}
              <a className="mdl-inline-link" href="#settings/config">
                Bật trong Cấu hình RAG <ArrowRight size={13} />
              </a>
            </span>
          </div>
        )}

        {kind === "embedding" && runtime.load_error && (
          <div className="inline-alert is-error" role="alert">
            <AlertCircle size={16} />
            <span>
              Lần khởi động này không áp được embedding đã chọn nên vẫn chạy cấu hình <code>.env</code>:{" "}
              {runtime.load_error}
            </span>
          </div>
        )}
        {kind === "embedding" && runtime.restart_required && !runtime.load_error && (
          <div className="inline-alert is-warning" role="status">
            <RotateCw size={16} />
            <span>
              Lựa chọn mới có hiệu lực sau khi <strong>khởi động lại backend</strong>. Sau đó vào{" "}
              <strong>Dataset</strong> → <strong>Nạp lại toàn bộ</strong> để tạo lại vector cho mọi tài liệu; trước khi nạp
              lại, kết quả tìm kiếm sẽ sai lệch.
            </span>
          </div>
        )}
        {kind === "embedding" && (
          <div className="inline-alert is-info">
            <Info size={16} />
            <span>
              Số chiều của mô hình nhúng phải bằng <code>VECTOR_DIM</code> ({vectorDim}) của kho vector. Script dòng lệnh
              (<code>scripts/ingest.py</code>) vẫn dùng embedding trong <code>.env</code>.
            </span>
          </div>
        )}
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Form thêm / sửa
// ---------------------------------------------------------------------------

function ProfileEditor({ kind, profile, registry, onClose }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isEdit = Boolean(profile);
  const initial = useMemo(() => (profile ? draftFromProfile(profile) : emptyDraft(kind)), [kind, profile]);
  const [draft, setDraft] = useState(initial);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const rootRef = useRef(null);
  const idPrefix = `mdl-${kind}-form`;

  const fields = providerFields(kind, draft.provider);
  const rule = keyRule(kind, draft.provider);
  const errors = useMemo(() => validateDraft(kind, draft), [kind, draft]);
  const dirty = isDraftDirty(kind, draft, initial);
  useWarnBeforeUnload(dirty);

  useEffect(() => {
    const node = rootRef.current;
    node?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
    node?.querySelector("input")?.focus({ preventScroll: true });
  }, []);

  function update(name, value) {
    setDraft((current) => {
      const next = { ...current, [name]: value };
      // Mô hình nhúng quen thuộc: tự điền số chiều nếu ô đang trống hoặc đang là số tự điền trước đó.
      if (kind === "embedding" && name === "model") {
        const known = KNOWN_EMBEDDING_DIMENSIONS[value.trim()];
        const previousKnown = KNOWN_EMBEDDING_DIMENSIONS[current.model.trim()];
        if (known && (!current.dimension || current.dimension === String(previousKnown ?? ""))) {
          next.dimension = String(known);
        }
      }
      if (name === "apiKey" && value.trim()) next.clearApiKey = false;
      return next;
    });
    setTestResult(null);
  }

  function ensureValid() {
    if (Object.keys(errors).length === 0) return true;
    setShowErrors(true);
    const first = ["name", ...fields.map((field) => field.name)].find((name) => errors[name]);
    rootRef.current?.querySelector(`#${idPrefix}-${first}`)?.focus();
    return false;
  }

  async function handleTest() {
    if (!ensureValid()) return;
    setTesting(true);
    setTestResult(null);
    try {
      setTestResult(await modelProfilesApi.testLlm(buildTestPayload(draft, profile?.id)));
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
  const showDimWarning = kind === "embedding" && draft.dimension && !errors.dimension && dimensionValue !== vectorDim;
  const kindLabel = KINDS[kind].label;

  return (
    <div ref={rootRef}>
      <Section
        id={`${idPrefix}`}
        title={isEdit ? `Sửa ${profile.name}` : `Thêm ${kindLabel}`}
        description={
          isEdit
            ? "Thay đổi được lưu vào kho. Nếu đây là mô hình đang dùng, hệ thống áp dụng ngay sau khi lưu."
            : "Mô hình được lưu vào kho để chọn làm mô hình đang dùng ở phía trên."
        }
        footer={
          <>
            <span className="mdl-dirty" role="status">
              {dirty ? "Có thay đổi chưa lưu" : ""}
            </span>
            <div className="mdl-actions">
              {kind === "llm" && (
                <button type="button" className="ghost-btn" onClick={handleTest} disabled={testing || saving}>
                  {testing ? <Loader2 size={15} className="spin" /> : <Zap size={15} />}
                  {testing ? "Đang kiểm tra..." : "Kiểm tra kết nối"}
                </button>
              )}
              <button type="button" className="ghost-btn" onClick={onClose} disabled={saving}>
                Huỷ
              </button>
              <button
                type="button"
                className="primary-btn"
                onClick={handleSave}
                disabled={saving || (isEdit && !dirty)}
              >
                {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
                {saving ? "Đang lưu..." : isEdit ? "Lưu thay đổi" : "Thêm vào kho"}
              </button>
            </div>
          </>
        }
      >
        <div className="mdl-stack">
          <div className="mdl-grid">
            <TextField
              id={`${idPrefix}-name`}
              field={{
                label: "Tên hiển thị",
                placeholder: "Mặc định là tên mô hình",
                hint: "Tên dùng trong danh sách chọn mô hình, không trùng trong cùng mục.",
              }}
              value={draft.name}
              onChange={(value) => update("name", value)}
              error={showErrors ? errors.name : undefined}
            />
          </div>

          {KINDS[kind].providers.length > 1 ? (
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
          ) : (
            <p className="mdl-provider-note">
              <ProviderIcon kind={kind} provider={draft.provider} size={16} />
              <span>
                <strong>{KINDS[kind].providers[0].name}</strong> — {KINDS[kind].providers[0].description}
              </span>
            </p>
          )}

          {draft.provider === "openai_compatible" && (
            <div className="mdl-presets" role="group" aria-label="Điền nhanh địa chỉ máy chủ">
              <span>Điền nhanh:</span>
              {COMPATIBLE_PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  className="mdl-preset"
                  aria-pressed={draft.base_url === preset.baseUrl}
                  onClick={() => {
                    setDraft((current) => ({
                      ...current,
                      base_url: preset.baseUrl,
                      model: preset.model || current.model,
                    }));
                    setTestResult(null);
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          )}

          <div className="mdl-grid">
            {fields.map((field) => (
              <TextField
                key={`${draft.provider}-${field.name}`}
                id={`${idPrefix}-${field.name}`}
                field={field}
                value={draft[field.name]}
                onChange={(value) => update(field.name, value)}
                error={
                  showErrors || ((field.url || field.number) && String(draft[field.name]).trim())
                    ? errors[field.name]
                    : undefined
                }
              />
            ))}
          </div>

          {showDimWarning && (
            <div className="inline-alert is-warning">
              <AlertTriangle size={16} />
              <span>
                Mô hình có {dimensionValue} chiều, khác <code>VECTOR_DIM</code> ({vectorDim}) của kho vector: lưu được
                nhưng chưa chọn làm mô hình đang dùng được.
              </span>
            </div>
          )}

          {rule && (
            <ApiKeyField
              key={draft.provider}
              id={`${idPrefix}-key`}
              value={draft.apiKey}
              onChange={(value) => update("apiKey", value)}
              hasKey={Boolean(profile?.has_api_key) && profile?.provider === draft.provider}
              envFallback={rule.envFallback}
              envKeyLabel={ENV_KEY_LABELS[kind]?.[draft.provider]}
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
                    {testResult.sample_output && <> · Mô hình trả lời: “{testResult.sample_output}”</>}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </Section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Danh sách mô hình đã cấu hình
// ---------------------------------------------------------------------------

function ProfileMeta({ kind, profile }) {
  const parts = [providerName(kind, profile.provider), profileModelLabel(profile)];
  if (kind === "embedding" && profile.dimension) parts.push(`${profile.dimension} chiều`);
  // Địa chỉ máy chủ dài: chỉ hiện khi rê chuột để card giữ một dòng.
  const address = profile.base_url || profile.endpoint;
  return (
    <span className="mdl-profile-meta" title={address ? `${parts.join(" · ")}
${address}` : undefined}>
      {parts.join(" · ")}
    </span>
  );
}

function ProfileList({ kind, registry, profiles, editingId, onAdd, onEdit, onDelete, adding }) {
  const active = registry.active?.[kind];
  const runtime = registry.embedding_runtime;
  const vectorDim = runtime?.vector_dim;

  return (
    <section className="mdl-card" aria-labelledby={`mdl-${kind}-list-title`}>
      <header className="mdl-list-head">
        <div>
          <h3 id={`mdl-${kind}-list-title`}>Mô hình đã cấu hình</h3>
          <p>{profiles.length} mô hình trong kho</p>
        </div>
        <button type="button" className="ghost-btn mdl-add-btn" onClick={onAdd} disabled={adding}>
          <Plus size={15} />
          Thêm mô hình
        </button>
      </header>
      {profiles.length === 0 ? (
        <div className="mdl-empty">
          <p>Chưa có {KINDS[kind].label} nào. Thêm mô hình để chọn làm mô hình đang dùng cho hệ thống.</p>
        </div>
      ) : (
        <ul className="mdl-profile-list">
          {profiles.map((profile) => {
            const isActive = active === profile.id;
            const isRunning = kind === "embedding" && runtime?.profile_id === profile.id;
            const mismatch = dimensionMismatch(kind, profile, vectorDim);
            return (
              <li
                key={profile.id}
                className={`mdl-profile ${isActive ? "is-active" : ""} ${editingId === profile.id ? "is-editing" : ""}`}
              >
                <span className="mdl-profile-icon" aria-hidden="true">
                  <ProviderIcon kind={kind} provider={profile.provider} size={15} />
                </span>
                <div className="mdl-profile-text">
                  <strong className="mdl-profile-name" title={profile.name}>
                    {profile.name}
                  </strong>
                  <ProfileMeta kind={kind} profile={profile} />
                  {(isActive || isRunning || profile.has_api_key || mismatch) && (
                    <div className="mdl-profile-tags">
                      {isActive && (
                        <StatusPill tone="ok">{kind === "embedding" ? "Đã chọn" : "Đang dùng"}</StatusPill>
                      )}
                      {isRunning && <StatusPill tone="ok">Đang chạy</StatusPill>}
                      {profile.has_api_key && (
                        <StatusPill>
                          <KeyRound size={11} /> Đã lưu khoá
                        </StatusPill>
                      )}
                      {mismatch && <StatusPill tone="warn">Khác VECTOR_DIM</StatusPill>}
                    </div>
                  )}
                </div>
                <div className="mdl-profile-actions">
                  <button
                    type="button"
                    className="mdl-icon-btn"
                    onClick={() => onEdit(profile)}
                    aria-label={`Sửa ${profile.name}`}
                    title="Sửa"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    className="mdl-icon-btn is-danger"
                    onClick={() => onDelete(profile)}
                    disabled={isActive}
                    aria-label={`Xoá ${profile.name}`}
                    title={isActive ? "Đang được dùng — chọn mô hình khác trước khi xoá." : "Xoá"}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Panel của một loại mô hình
// ---------------------------------------------------------------------------

export default function ModelKindPanel({ kind, registry, config }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  // null: không mở form; { profile: null } thêm mới; { profile } sửa.
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const allProfiles = registry.profiles ?? [];
  const profiles = useMemo(() => allProfiles.filter((profile) => profile.kind === kind), [allProfiles, kind]);
  const profilesById = useMemo(
    () => Object.fromEntries(profiles.map((profile) => [profile.id, profile])),
    [profiles]
  );

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

  return (
    <div className="mdl-kind-layout">
      {/* Cột trái: chọn mô hình đang dùng + form; cột phải: kho mô hình. Màn hẹp xếp một cột. */}
      <div className="mdl-kind-main">
        <ActiveModelCard
          kind={kind}
          registry={registry}
          config={config}
          profiles={profiles}
          profilesById={profilesById}
        />
        {editing && (
          <ProfileEditor
            key={editing.profile?.id ?? "new"}
            kind={kind}
            profile={editing.profile}
            registry={registry}
            onClose={() => setEditing(null)}
          />
        )}
      </div>
      <div className="mdl-kind-side">
        <ProfileList
          kind={kind}
          registry={registry}
          profiles={profiles}
          editingId={editing?.profile?.id}
          adding={Boolean(editing && !editing.profile)}
          onAdd={() => setEditing({ profile: null })}
          onEdit={(profile) => setEditing({ profile })}
          onDelete={setPendingDelete}
        />
      </div>
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
    </div>
  );
}
