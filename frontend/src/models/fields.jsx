import React, { useEffect, useState } from "react";
import { AlertTriangle, ArrowDownUp, Binary, Check, Cloud, Cpu, Eye, EyeOff, HardDrive, Server, Undo2 } from "lucide-react";

/* Thành phần giao diện dùng chung cho ba tab của màn Mô hình. */

function OpenAILogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.475 4.475 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1683a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4947zm-9.66-4.996a4.47 4.47 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1402-2.517zm-1.808-9.4582a4.4607 4.4607 0 0 1 2.342-1.9729v.1656l-.0047 5.5164a.79.79 0 0 0 .3927.6813l5.8429 3.3686-2.02 1.1682a.0757.0757 0 0 1-.071 0l-4.8304-2.7913a4.4944 4.4944 0 0 1-1.6515-6.1359zm15.0845-2.054a.7854.7854 0 0 0-.7807 0l-5.8428 3.3685V6.977a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.4944 4.4851 4.4703 4.4703 0 0 1-.0047.5284l-.142-.0852-4.6344-2.6599zm2.4578 4.0984a4.4703 4.4703 0 0 1-.5347 3.0137l-.142-.0852-4.783-2.7582a.7712.7712 0 0 0-.7806 0l-5.8428 3.3685V10.743a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.1402 2.517 4.4703 4.4703 0 0 1 .0327.3995zm-8.8136 2.054a.79.79 0 0 0-.3927-.6813L8.29 8.083l2.02-1.1682a.0757.0757 0 0 1 .071 0l4.8304 2.7913a4.4944 4.4944 0 0 1 1.6515 6.1359 4.4607 4.4607 0 0 1-2.342 1.9729v-.1656l.0047-5.5164zm-1.0268.5916l2.3948 1.3824-2.3948 1.3824-2.3948-1.3824 2.3948-1.3824z" />
    </svg>
  );
}

function GeminiLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4772 12 22C12 16.4772 16.4772 12 22 12C16.4772 12 12 7.52285 12 2Z"
        fill="url(#mdl-gemini-grad)"
      />
      <defs>
        <linearGradient id="mdl-gemini-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4285F4" />
          <stop offset="0.33" stopColor="#9B72CB" />
          <stop offset="0.66" stopColor="#D96570" />
          <stop offset="1" stopColor="#F4B400" />
        </linearGradient>
      </defs>
    </svg>
  );
}

const PROVIDER_ICONS = {
  llm: { openai: OpenAILogo, gemini: GeminiLogo, azure: Cloud, openai_compatible: Server },
  embedding: { openai: OpenAILogo, "sentence-transformers": HardDrive },
  reranker: { "cross-encoder": Cpu, heuristic: ArrowDownUp },
};

export function ProviderIcon({ kind, provider, size = 18 }) {
  const Icon = PROVIDER_ICONS[kind]?.[provider] ?? Binary;
  return <Icon size={size} />;
}

export function useWarnBeforeUnload(active) {
  useEffect(() => {
    if (!active) return undefined;
    function onBeforeUnload(event) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [active]);
}

export function StatusPill({ tone = "muted", children }) {
  return <span className={`mdl-pill is-${tone}`}>{children}</span>;
}

export function Section({ id, icon, title, description, current, children, footer }) {
  return (
    <section className="mdl-card" aria-labelledby={`${id}-title`} id={id}>
      <header className="mdl-card-head">
        {icon && (
          <span className="mdl-card-icon" aria-hidden="true">
            {icon}
          </span>
        )}
        <div className="mdl-card-heading">
          <h3 id={`${id}-title`}>{title}</h3>
          {description && <p>{description}</p>}
          {current && <div className="mdl-current">{current}</div>}
        </div>
      </header>
      {children && <div className="mdl-card-body">{children}</div>}
      {footer && <footer className="mdl-card-foot">{footer}</footer>}
    </section>
  );
}

export function ChoiceGroup({ kind, name, legend, options, value, onChange }) {
  return (
    <fieldset className="mdl-choice-group">
      <legend>{legend}</legend>
      <div className="mdl-choices">
        {options.map(({ key, name: label, description }) => (
          <label key={key} className={`mdl-choice ${value === key ? "is-selected" : ""}`}>
            <input type="radio" name={name} value={key} checked={value === key} onChange={() => onChange(key)} />
            <span className="mdl-choice-icon" aria-hidden="true">
              <ProviderIcon kind={kind} provider={key} />
            </span>
            <span className="mdl-choice-text">
              <strong>{label}</strong>
              <span>{description}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function TextField({ id, field, value, onChange, error }) {
  const listId = field.suggestions ? `${id}-suggestions` : undefined;
  const hintId = `${id}-hint`;
  const describedBy = [error ? `${id}-error` : null, field.hint ? hintId : null].filter(Boolean).join(" ");
  return (
    <div className="mdl-field">
      <label htmlFor={id}>
        {field.label}
        {!field.required && <span className="mdl-optional">Tuỳ chọn</span>}
      </label>
      <input
        id={id}
        type="text"
        inputMode={field.number ? "numeric" : undefined}
        className={`mdl-input ${error ? "is-invalid" : ""}`}
        value={value}
        placeholder={field.placeholder}
        list={listId}
        spellCheck={false}
        autoComplete="off"
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy || undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {listId && (
        <datalist id={listId}>
          {field.suggestions.map((item) => (
            <option key={item} value={item} />
          ))}
        </datalist>
      )}
      {error && (
        <span className="mdl-field-error" id={`${id}-error`}>
          {error}
        </span>
      )}
      {field.hint && (
        <span className="mdl-field-hint" id={hintId}>
          {field.hint}
        </span>
      )}
    </div>
  );
}

/**
 * Ô API key của một profile. Khoá đã lưu không bao giờ hiển thị lại; để trống khi sửa
 * là giữ khoá cũ, "Xoá khoá đã lưu" để quay về khoá `.env` (nếu nhà cung cấp cho phép).
 */
export function ApiKeyField({ id, value, onChange, hasKey, envFallback, clearKey, onClearKeyChange, envKeyLabel }) {
  const [visible, setVisible] = useState(false);
  const hintId = `${id}-hint`;
  const keepsStoredKey = hasKey && !clearKey;
  let placeholder = "Dán API key";
  if (keepsStoredKey) placeholder = "Để trống để giữ khoá đã lưu";
  else if (envFallback) placeholder = `Để trống để dùng ${envKeyLabel}`;

  return (
    <div className="mdl-field">
      <div className="mdl-field-label-row">
        <label htmlFor={id}>API key</label>
        {keepsStoredKey ? (
          <StatusPill tone="ok">
            <Check size={12} /> Đã lưu khoá
          </StatusPill>
        ) : envFallback ? (
          <StatusPill>Dùng {envKeyLabel} nếu để trống</StatusPill>
        ) : (
          <StatusPill>Không bắt buộc</StatusPill>
        )}
      </div>
      <div className="mdl-secret">
        <input
          id={id}
          type={visible ? "text" : "password"}
          className="mdl-input"
          value={value}
          placeholder={placeholder}
          autoComplete="new-password"
          spellCheck={false}
          aria-describedby={hintId}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          type="button"
          className="mdl-secret-toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? "Ẩn API key" : "Hiện API key"}
          aria-pressed={visible}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      <span className="mdl-field-hint" id={hintId}>
        Khoá được mã hoá trước khi lưu trên máy chủ, không lưu trong trình duyệt và không bao giờ hiển thị lại.
      </span>
      {hasKey && (
        <button
          type="button"
          className="mdl-link-btn"
          aria-pressed={clearKey}
          onClick={() => onClearKeyChange(!clearKey)}
          disabled={Boolean(value.trim())}
        >
          {clearKey ? (
            <>
              <Undo2 size={13} /> Giữ khoá đã lưu
            </>
          ) : (
            <>
              <AlertTriangle size={13} /> Xoá khoá đã lưu khi lưu
            </>
          )}
        </button>
      )}
    </div>
  );
}
