import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, HardDrive, Loader2, RefreshCw } from "lucide-react";
import { configApi, describeError, modelProfilesApi, queryKeys } from "./api";
import { KIND_ORDER } from "./models/catalog";
import ModelKindPanel from "./models/ModelKindPanel";

/*
 * Màn Mô hình: mỗi mục trong danh mục Settings ứng với một loại mô hình
 * (LLM / Embedding / Reranker). Loại đang xem do route quyết định
 * (`#settings/models-llm`…), nên cả ba panel được giữ mounted và chỉ ẩn panel khác.
 *
 * Mỗi panel có kho cấu hình mô hình (thêm/sửa/xoá) và ô chọn mô hình đang dùng lấy từ
 * kho đó (/api/model-profiles). LLM và reranker đổi có hiệu lực ngay; embedding nạp
 * một lần lúc khởi động nên lựa chọn chỉ có hiệu lực sau khi backend khởi động lại.
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

export default function ModelsView({ kind = "llm" }) {
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
        <div className="mdl-notices">
          <div className="inline-alert is-info">
            <HardDrive size={16} />
            <span>
              Kho mô hình và lựa chọn mô hình đang dùng được lưu vào cơ sở dữ liệu; API key được mã hoá trước khi lưu.
              Chưa chọn mô hình nào thì hệ thống dùng cấu hình trong <code>.env</code>.
            </span>
          </div>
          {!registry.secret_encryption_enabled && (
            <div className="inline-alert is-warning" role="alert">
              <AlertTriangle size={16} />
              <span>
                Máy chủ chưa có <code>CONFIG_ENCRYPTION_KEY</code> hợp lệ nên sẽ từ chối lưu API key. Mô hình không cần
                khoá (hoặc dùng khoá trong <code>.env</code>) vẫn lưu bình thường.
              </span>
            </div>
          )}
        </div>
        {/* Giữ các panel mounted để không mất form đang nhập dở khi đổi mục. */}
        {KIND_ORDER.map((panelKind) => (
          <div key={panelKind} id={`mdl-panel-${panelKind}`} hidden={activeKind !== panelKind}>
            <ModelKindPanel kind={panelKind} registry={registry} config={config} />
          </div>
        ))}
      </>
    );
  }

  return (
    <div className="models-page-wrapper">
      <div className="mdl-page">
        <div className="mdl-wrap">{body}</div>
      </div>
    </div>
  );
}
