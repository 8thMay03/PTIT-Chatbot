import { profileModelLabel, providerName } from "./catalog";

/*
 * Tóm tắt mô hình đang dùng của từng loại, cho thẻ khâu ở tab Mô hình và danh sách
 * mục Cài đặt trên mobile. Tên lấy từ lựa chọn trong kho (`registry.active`); nhà
 * cung cấp/mô hình của LLM và reranker lấy từ cấu hình đang chạy (`/api/config`).
 */

export const ENV_ROW_NAME = "Cấu hình máy chủ";

/** Tên provider LLM trong `.env`/config (`google`, `azure_openai`…) → key của kho. */
export function normalizeEnvLlmProvider(value) {
  const name = String(value || "").toLowerCase();
  if (name === "google") return "gemini";
  if (name === "azure_openai") return "azure";
  if (["openai", "gemini", "azure"].includes(name)) return name;
  return "openai_compatible";
}

function activeProfile(kind, registry) {
  const id = registry?.active?.[kind];
  if (!id) return null;
  return (registry.profiles ?? []).find((profile) => profile.id === id) ?? null;
}

function joinMeta(parts) {
  return parts.filter(Boolean).join(" · ");
}

function llmSummary(registry, config) {
  const profile = activeProfile("llm", registry);
  const env = registry?.env_defaults?.llm ?? {};
  const llm = config?.llm;
  const provider = normalizeEnvLlmProvider(llm?.provider ?? profile?.provider ?? env.provider);
  const model = llm?.model ?? (profile ? profileModelLabel(profile) : env.model);
  const status =
    llm?.has_api_key === false
      ? { tone: "warn", label: "Thiếu API key" }
      : { tone: "ok", label: "Đang chạy" };
  return {
    name: profile?.name ?? ENV_ROW_NAME,
    meta: joinMeta([providerName("llm", provider), model]),
    status,
  };
}

function embeddingSummary(registry) {
  const profile = activeProfile("embedding", registry);
  const runtime = registry?.embedding_runtime ?? {};
  const env = registry?.env_defaults?.embedding ?? {};
  let status = { tone: "ok", label: "Đang chạy" };
  if (runtime.load_error) status = { tone: "warn", label: "Lỗi khi nạp" };
  else if (runtime.restart_required) status = { tone: "warn", label: "Chưa áp dụng" };
  if (profile) {
    return {
      name: profile.name,
      meta: joinMeta([
        providerName("embedding", profile.provider),
        profile.dimension ? `${profile.dimension} chiều` : profileModelLabel(profile),
      ]),
      status,
    };
  }
  return {
    name: ENV_ROW_NAME,
    meta: joinMeta([providerName("embedding", env.provider), env.model]),
    status,
  };
}

function rerankerSummary(registry, config) {
  const profile = activeProfile("reranker", registry);
  const status =
    config?.reranker?.enabled === false
      ? { tone: "warn", label: "Đang tắt" }
      : { tone: "ok", label: "Đang bật" };
  if (profile) {
    return {
      name: profile.name,
      meta: joinMeta([providerName("reranker", profile.provider), profileModelLabel(profile)]),
      status,
    };
  }
  return { name: "Heuristic", meta: "Không cần mô hình", status };
}

/** `{ name, meta, status: { tone: "ok" | "warn", label } }`; null khi chưa có dữ liệu kho. */
export function activeModelSummary(kind, registry, config) {
  if (!registry) return null;
  if (kind === "llm") return llmSummary(registry, config);
  if (kind === "embedding") return embeddingSummary(registry);
  if (kind === "reranker") return rerankerSummary(registry, config);
  return null;
}
