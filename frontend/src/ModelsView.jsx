import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, LockKeyhole, RefreshCw } from "lucide-react";
import { configApi, describeError, modelProfilesApi, queryKeys } from "./api";
import { KIND_ORDER } from "./models/catalog";
import ModelKindCards from "./models/ModelKindCards";
import ModelKindPanel from "./models/ModelKindPanel";

/*
 * Tab Mô hình: ba thẻ khâu (LLM / Embedding / Reranker) ở đầu trang, bên dưới là danh
 * sách mô hình của loại đang xem. Loại đang xem do route quyết định
 * (`#settings/models-llm`…), nên cả ba panel được giữ mounted và chỉ ẩn panel khác.
 *
 * Mỗi danh sách gồm cấu hình `.env` và kho mô hình (/api/model-profiles); bấm "Dùng"
 * để chọn mô hình đang dùng; đổi có hiệu lực ngay. Đổi embedding thì vector cũ cần được
 * nhúng lại (banner trong panel embedding và màn Dataset).
 */

const LEGACY_TAB_STORAGE_KEY = "ptit_models_tab";

/** Điền mặc định cho trường thiếu để một response lệch hợp đồng không làm vỡ cả màn. */
function normalizeRegistry(data) {
  if (!data) return null;
  return {
    ...data,
    profiles: Array.isArray(data.profiles) ? data.profiles : [],
    active: { llm: null, embedding: null, reranker: null, ...(data.active ?? {}) },
    embedding_runtime: { profile_id: null, restart_required: false, load_error: null, ...(data.embedding_runtime ?? {}) },
    env_defaults: data.env_defaults ?? {},
  };
}

export default function ModelsView({ kind = "llm", onKindSelect }) {
  const activeKind = KIND_ORDER.includes(kind) ? kind : "llm";

  const registryQuery = useQuery({
    queryKey: queryKeys.modelProfiles,
    queryFn: ({ signal }) => modelProfilesApi.list({ signal }),
  });
  // Cấu hình đang chạy (mô hình LLM, trạng thái bật reranker) dùng chung cache với tab Cấu hình RAG.
  const configQuery = useQuery({
    queryKey: queryKeys.config,
    queryFn: ({ signal }) => configApi.get({ signal }),
  });

  const registry = normalizeRegistry(registryQuery.data);
  const config = configQuery.data ?? null;

  useEffect(() => {
    try {
      // Dọn khoá của màn cũ: tab con và danh sách "nhà cung cấp đã thêm" không còn
      // tồn tại trên giao diện (loại mô hình giờ do route quyết định).
      localStorage.removeItem(LEGACY_TAB_STORAGE_KEY);
      localStorage.removeItem("ptit_added_providers");
    } catch {
      /* storage bị chặn */
    }
  }, []);

  let body;
  if (registryQuery.isPending && !registry) {
    body = (
      <div className="model-mgmt-loading" aria-busy="true">
        <div className="model-mgmt-spinner" />
        <p>Đang đọc kho mô hình...</p>
      </div>
    );
  } else if (registryQuery.error && !registry) {
    const loadError = describeError(registryQuery.error, {
      fallbackTitle: "Không đọc được kho mô hình",
      fallbackDetail: "Máy chủ trả về lỗi khi đọc cấu hình mô hình.",
    });
    body = (
      <div className="state-block is-error">
        <span className="state-icon">
          <AlertTriangle size={24} />
        </span>
        <h3>{loadError.title}</h3>
        <p>{loadError.detail} Màn này cần dữ liệu thật của máy chủ trước khi cho phép thay đổi.</p>
        <button
          type="button"
          className="primary-btn"
          onClick={() => registryQuery.refetch()}
          disabled={registryQuery.isFetching}
        >
          {registryQuery.isFetching ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
          Thử lại
        </button>
      </div>
    );
  } else {
    body = (
      <>
        {!registry.secret_encryption_enabled && (
          <div className="inline-alert is-warning" role="alert">
            <AlertTriangle size={16} />
            <span>
              Máy chủ chưa có <code>CONFIG_ENCRYPTION_KEY</code> hợp lệ nên sẽ từ chối lưu API key. Mô hình không cần khoá
              (hoặc dùng khoá trong <code>.env</code>) vẫn lưu bình thường.
            </span>
          </div>
        )}
        {/* Giữ các panel mounted để không mất form đang nhập dở khi đổi mục. */}
        {KIND_ORDER.map((panelKind) => (
          <div key={panelKind} id={`mdl-panel-${panelKind}`} hidden={activeKind !== panelKind}>
            <ModelKindPanel kind={panelKind} registry={registry} config={config} active={activeKind === panelKind} />
          </div>
        ))}
        <p className="mdl-foot-note">
          <LockKeyhole size={14} aria-hidden="true" />
          <span>
            Kho mô hình lưu trong cơ sở dữ liệu; API key được mã hoá và không hiển thị lại. Hàng <code>.env</code> là cấu
            hình mặc định của máy chủ, dùng khi chưa chọn mô hình nào trong kho.
          </span>
        </p>
      </>
    );
  }

  return (
    <div className="models-page-wrapper">
      <div className="mdl-page">
        <div className="mdl-wrap">
          <ModelKindCards activeKind={activeKind} registry={registry} config={config} onSelect={onKindSelect} />
          {body}
        </div>
      </div>
    </div>
  );
}
