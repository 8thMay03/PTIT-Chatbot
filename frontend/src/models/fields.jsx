import React, { useEffect, useId, useState } from "react";
import {
  AlertTriangle,
  ArrowDownUp,
  Binary,
  Check,
  Cloud,
  Cpu,
  Eye,
  EyeOff,
  MessageSquareText,
  Server,
  TreePine,
  Undo2,
} from "lucide-react";

/* Thành phần giao diện dùng chung cho ba loại mô hình của màn Mô hình. */

export const KIND_ICONS = { llm: MessageSquareText, embedding: Binary, reranker: ArrowDownUp };

/**
 * Id gradient riêng cho mỗi lần vẽ logo: id cố định bị trùng khi logo xuất hiện nhiều lần,
 * và bản đầu tiên nằm trong panel ẩn (`hidden`) thì các bản khác mất màu.
 */
function useGradientId(name) {
  return `mdl-${name}-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
}

function OpenAILogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.475 4.475 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1683a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4947zm-9.66-4.996a4.47 4.47 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1402-2.517zm-1.808-9.4582a4.4607 4.4607 0 0 1 2.342-1.9729v.1656l-.0047 5.5164a.79.79 0 0 0 .3927.6813l5.8429 3.3686-2.02 1.1682a.0757.0757 0 0 1-.071 0l-4.8304-2.7913a4.4944 4.4944 0 0 1-1.6515-6.1359zm15.0845-2.054a.7854.7854 0 0 0-.7807 0l-5.8428 3.3685V6.977a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.4944 4.4851 4.4703 4.4703 0 0 1-.0047.5284l-.142-.0852-4.6344-2.6599zm2.4578 4.0984a4.4703 4.4703 0 0 1-.5347 3.0137l-.142-.0852-4.783-2.7582a.7712.7712 0 0 0-.7806 0l-5.8428 3.3685V10.743a.0804.0804 0 0 1 .0332-.0615l4.877-2.815a4.4992 4.4992 0 0 1 6.1402 2.517 4.4703 4.4703 0 0 1 .0327.3995zm-8.8136 2.054a.79.79 0 0 0-.3927-.6813L8.29 8.083l2.02-1.1682a.0757.0757 0 0 1 .071 0l4.8304 2.7913a4.4944 4.4944 0 0 1 1.6515 6.1359 4.4607 4.4607 0 0 1-2.342 1.9729v-.1656l.0047-5.5164zm-1.0268.5916l2.3948 1.3824-2.3948 1.3824-2.3948-1.3824 2.3948-1.3824z" />
    </svg>
  );
}

function GeminiLogo({ size = 20 }) {
  const gradientId = useGradientId("gemini");
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4772 12 22C12 16.4772 16.4772 12 22 12C16.4772 12 12 7.52285 12 2Z"
        fill={`url(#${gradientId})`}
      />
      <defs>
        <linearGradient id={gradientId} x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4285F4" />
          <stop offset="0.33" stopColor="#9B72CB" />
          <stop offset="0.66" stopColor="#D96570" />
          <stop offset="1" stopColor="#F4B400" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// Logo nhà cung cấp lấy từ @lobehub/icons-static-svg 1.106.0 (MIT, © LobeHub,
// https://github.com/lobehub/lobe-icons). Voyage và Jina dùng
// bản một màu (currentColor) để đọc được trên cả nền sáng và tối.
function VoyageLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" fillRule="evenodd" aria-hidden="true">
      <path d="M5.407 0v.066a.974.974 0 00-.048.245c-.011.11-.016.208-.016.295 0 .339.043.715.128 1.13.097.405.274.912.531 1.524l7.125 16.366L20.011 3.39c.161-.404.333-.846.515-1.327.182-.48.273-.966.273-1.458a1.406 1.406 0 00-.096-.54V0H24v.066c-.204.207-.45.578-.74 1.114-.29.535-.606 1.195-.949 1.982L13.095 24h-1.287L3.075 3.965c-.204-.47-.418-.923-.644-1.36-.214-.437-.418-.83-.61-1.18-.194-.36-.365-.66-.515-.9A5.666 5.666 0 001 .064V0h4.407z" />
    </svg>
  );
}

function CohereLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path clipRule="evenodd" d="M8.128 14.099c.592 0 1.77-.033 3.398-.703 1.897-.781 5.672-2.2 8.395-3.656 1.905-1.018 2.74-2.366 2.74-4.18A4.56 4.56 0 0018.1 1H7.549A6.55 6.55 0 001 7.55c0 3.617 2.745 6.549 7.128 6.549z" fill="#39594D" fillRule="evenodd" />
      <path clipRule="evenodd" d="M9.912 18.61a4.387 4.387 0 012.705-4.052l3.323-1.38c3.361-1.394 7.06 1.076 7.06 4.715a5.104 5.104 0 01-5.105 5.104l-3.597-.001a4.386 4.386 0 01-4.386-4.387z" fill="#D18EE2" fillRule="evenodd" />
      <path d="M4.776 14.962A3.775 3.775 0 001 18.738v.489a3.776 3.776 0 007.551 0v-.49a3.775 3.775 0 00-3.775-3.775z" fill="#FF7759" />
    </svg>
  );
}

function JinaLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" fillRule="evenodd" aria-hidden="true">
      <path d="M6.608 21.416a4.608 4.608 0 100-9.217 4.608 4.608 0 000 9.217zM20.894 2.015c.614 0 1.106.492 1.106 1.106v9.002c0 5.13-4.148 9.309-9.217 9.37v-9.355l-.03-9.032c0-.614.491-1.106 1.106-1.106h7.158l-.123.015z" />
    </svg>
  );
}

function AzureLogo({ size = 20 }) {
  const gradientId = useGradientId("azure");
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7.242 1.613A1.11 1.11 0 018.295.857h6.977L8.03 22.316a1.11 1.11 0 01-1.052.755h-5.43a1.11 1.11 0 01-1.053-1.466L7.242 1.613z" fill={`url(#${gradientId}-0)`} />
      <path d="M18.397 15.296H7.4a.51.51 0 00-.347.882l7.066 6.595c.206.192.477.298.758.298h6.226l-2.706-7.775z" fill="#0078D4" />
      <path d="M15.272.857H7.497L0 23.071h7.775l1.596-4.73 5.068 4.73h6.665l-2.707-7.775h-7.998L15.272.857z" fill={`url(#${gradientId}-1)`} />
      <path d="M17.193 1.613a1.11 1.11 0 00-1.052-.756h-7.81.035c.477 0 .9.304 1.052.756l6.748 19.992a1.11 1.11 0 01-1.052 1.466h-.12 7.895a1.11 1.11 0 001.052-1.466L17.193 1.613z" fill={`url(#${gradientId}-2)`} />
      <defs>
        <linearGradient gradientUnits="userSpaceOnUse" id={`${gradientId}-0`} x1="8.247" x2="1.002" y1="1.626" y2="23.03">
          <stop stopColor="#114A8B" />
          <stop offset="1" stopColor="#0669BC" />
        </linearGradient>
        <linearGradient gradientUnits="userSpaceOnUse" id={`${gradientId}-1`} x1="14.042" x2="12.324" y1="15.302" y2="15.888">
          <stop stopOpacity=".3" />
          <stop offset=".071" stopOpacity=".2" />
          <stop offset=".321" stopOpacity=".1" />
          <stop offset=".623" stopOpacity=".05" />
          <stop offset="1" stopOpacity="0" />
        </linearGradient>
        <linearGradient gradientUnits="userSpaceOnUse" id={`${gradientId}-2`} x1="12.841" x2="20.793" y1="1.626" y2="22.814">
          <stop stopColor="#3CCBF4" />
          <stop offset="1" stopColor="#2892DF" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function HuggingFaceLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M2.25 11.535c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0c2.997 1.704 4.844 4.851 4.844 8.258 0 5.266-4.337 9.535-9.687 9.535S2.25 16.8 2.25 11.535z" fill="#FF9D0B" />
      <path d="M11.938 20.086c4.797 0 8.687-3.829 8.687-8.551 0-4.722-3.89-8.55-8.687-8.55-4.798 0-8.688 3.828-8.688 8.55 0 4.722 3.89 8.55 8.688 8.55z" fill="#FFD21E" />
      <path d="M11.875 15.113c2.457 0 3.25-2.156 3.25-3.263 0-.576-.393-.394-1.023-.089-.582.283-1.365.675-2.224.675-1.798 0-3.25-1.693-3.25-.586 0 1.107.79 3.263 3.25 3.263h-.003z" fill="#FF323D" />
      <path d="M14.76 9.21c.32.108.445.753.767.585.447-.233.707-.708.659-1.204a1.235 1.235 0 00-.879-1.059 1.262 1.262 0 00-1.33.394c-.322.384-.377.92-.14 1.36.153.283.638-.177.925-.079l-.002.003zm-5.887 0c-.32.108-.448.753-.768.585a1.226 1.226 0 01-.658-1.204c.048-.495.395-.913.878-1.059a1.262 1.262 0 011.33.394c.322.384.377.92.14 1.36-.152.283-.64-.177-.925-.079l.003.003zm1.12 5.34a2.166 2.166 0 011.325-1.106c.07-.02.144.06.219.171l.192.306c.069.1.139.175.209.175.074 0 .15-.074.223-.172l.205-.302c.08-.11.157-.188.234-.165.537.168.986.536 1.25 1.026.932-.724 1.275-1.905 1.275-2.633 0-.508-.306-.426-.81-.19l-.616.296c-.52.24-1.148.48-1.824.48-.676 0-1.302-.24-1.823-.48l-.589-.283c-.52-.248-.838-.342-.838.177 0 .703.32 1.831 1.187 2.56l.18.14z" fill="#3A3B45" />
      <path d="M17.812 10.366a.806.806 0 00.813-.8c0-.441-.364-.8-.813-.8a.806.806 0 00-.812.8c0 .442.364.8.812.8zm-11.624 0a.806.806 0 00.812-.8c0-.441-.364-.8-.812-.8a.806.806 0 00-.813.8c0 .442.364.8.813.8zM4.515 13.073c-.405 0-.765.162-1.017.46a1.455 1.455 0 00-.333.925 1.801 1.801 0 00-.485-.074c-.387 0-.737.146-.985.409a1.41 1.41 0 00-.2 1.722 1.302 1.302 0 00-.447.694c-.06.222-.12.69.2 1.166a1.267 1.267 0 00-.093 1.236c.238.533.81.958 1.89 1.405l.24.096c.768.3 1.473.492 1.478.494.89.243 1.808.375 2.732.394 1.465 0 2.513-.443 3.115-1.314.93-1.342.842-2.575-.274-3.763l-.151-.154c-.692-.684-1.155-1.69-1.25-1.912-.195-.655-.71-1.383-1.562-1.383-.46.007-.889.233-1.15.605-.25-.31-.495-.553-.715-.694a1.87 1.87 0 00-.993-.312zm14.97 0c.405 0 .767.162 1.017.46.216.262.333.588.333.925.158-.047.322-.071.487-.074.388 0 .738.146.985.409a1.41 1.41 0 01.2 1.722c.22.178.377.422.445.694.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.238.533-.81.958-1.889 1.405l-.239.096c-.77.3-1.475.492-1.48.494-.89.243-1.808.375-2.732.394-1.465 0-2.513-.443-3.115-1.314-.93-1.342-.842-2.575.274-3.763l.151-.154c.695-.684 1.157-1.69 1.252-1.912.195-.655.708-1.383 1.56-1.383.46.007.889.233 1.15.605.25-.31.495-.553.718-.694.244-.162.523-.265.814-.3l.176-.012z" fill="#FF9D0B" />
      <path d="M9.785 20.132c.688-.994.638-1.74-.305-2.667-.945-.928-1.495-2.288-1.495-2.288s-.205-.788-.672-.714c-.468.074-.81 1.25.17 1.971.977.721-.195 1.21-.573.534-.375-.677-1.405-2.416-1.94-2.751-.532-.332-.907-.148-.782.541.125.687 2.357 2.35 2.14 2.707-.218.362-.983-.42-.983-.42S2.953 14.9 2.43 15.46c-.52.558.398 1.026 1.7 1.803 1.308.778 1.41.985 1.225 1.28-.187.295-3.07-2.1-3.34-1.083-.27 1.011 2.943 1.304 2.745 2.006-.2.7-2.265-1.324-2.685-.537-.425.79 2.913 1.718 2.94 1.725 1.075.276 3.813.859 4.77-.522zm4.432 0c-.687-.994-.64-1.74.305-2.667.943-.928 1.493-2.288 1.493-2.288s.205-.788.675-.714c.465.074.807 1.25-.17 1.971-.98.721.195 1.21.57.534.377-.677 1.407-2.416 1.94-2.751.532-.332.91-.148.782.541-.125.687-2.355 2.35-2.137 2.707.215.362.98-.42.98-.42S21.05 14.9 21.57 15.46c.52.558-.395 1.026-1.7 1.803-1.308.778-1.408.985-1.225 1.28.187.295 3.07-2.1 3.34-1.083.27 1.011-2.94 1.304-2.743 2.006.2.7 2.263-1.324 2.685-.537.423.79-2.912 1.718-2.94 1.725-1.077.276-3.815.859-4.77-.522z" fill="#FFD21E" />
    </svg>
  );
}

const PROVIDER_ICONS = {
  llm: { openai: OpenAILogo, gemini: GeminiLogo, azure: AzureLogo, openai_compatible: Server },
  embedding: {
    openai: OpenAILogo,
    "sentence-transformers": HuggingFaceLogo,
    voyage: VoyageLogo,
    cohere: CohereLogo,
    gemini: GeminiLogo,
    jina: JinaLogo,
    openai_compatible: Server,
  },
  reranker: {
    "cross-encoder": Cpu,
    heuristic: ArrowDownUp,
    cohere: CohereLogo,
    jina: JinaLogo,
    voyage: VoyageLogo,
    pinecone: TreePine,
    tei: HuggingFaceLogo,
    rerank_api: Cloud,
  },
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
export function ApiKeyField({
  id,
  value,
  onChange,
  hasKey,
  envFallback,
  required = false,
  clearKey,
  onClearKeyChange,
  envKeyLabel,
  error,
}) {
  const [visible, setVisible] = useState(false);
  const hintId = `${id}-hint`;
  const describedBy = [error ? `${id}-error` : null, hintId].filter(Boolean).join(" ");
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
        ) : required ? (
          <StatusPill>Bắt buộc</StatusPill>
        ) : (
          <StatusPill>Không bắt buộc</StatusPill>
        )}
      </div>
      <div className="mdl-secret">
        <input
          id={id}
          type={visible ? "text" : "password"}
          className={`mdl-input ${error ? "is-invalid" : ""}`}
          value={value}
          placeholder={placeholder}
          autoComplete="new-password"
          spellCheck={false}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
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
      {error && (
        <span className="mdl-field-error" id={`${id}-error`}>
          {error}
        </span>
      )}
      <span className="mdl-field-hint" id={hintId}>
        Khoá được mã hoá trước khi lưu trên máy chủ, không lưu trong trình duyệt và không bao giờ hiển thị lại.
      </span>
      {hasKey && !required && (
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
