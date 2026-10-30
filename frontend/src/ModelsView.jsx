import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowDownUp, Binary, Cpu, HardDrive, Loader2, MessageSquareText, RefreshCw } from "lucide-react";
import { configApi, describeError, modelProfilesApi, queryKeys } from "./api";
import { KINDS, KIND_ORDER } from "./models/catalog";
import ModelKindPanel from "./models/ModelKindPanel";

/*
 * Màn Mô hình: ba tab con LLM model / Embedding model / Rerank model.
 *
 * Mỗi tab có kho cấu hình mô hình (thêm/sửa/xoá) và ô chọn mô hình đang dùng lấy từ
 * kho đó (/api/model-profiles). LLM và reranker đổi có hiệu lực ngay; embedding nạp
 * một lần lúc khởi động nên lựa chọn chỉ có hiệu lực sau khi backend khởi động lại.
 */

const TAB_ICONS = { llm: MessageSquareText, embedding: Binary, reranker: ArrowDownUp };
const TAB_STORAGE_KEY = "ptit_models_tab";

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

function readStoredTab() {
  try {
    const value = localStorage.getItem(TAB_STORAGE_KEY);
    return KIND_ORDER.includes(value) ? value : "llm";
  } catch {
    return "llm";
  }
}

export default function ModelsView() {
  const [tab, setTab] = useState(readStoredTab);
  const tabRefs = useRef({});

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
      localStorage.setItem(TAB_STORAGE_KEY, tab);
      // Dọn dữ liệu của màn cũ: danh sách "nhà cung cấp đã thêm" chỉ từng tồn tại trên giao diện.
      localStorage.removeItem("ptit_added_providers");
    } catch {
      /* storage bị chặn — chỉ mất phần ghi nhớ tab */
    }
  }, [tab]);

  function onTabKeyDown(event) {
    const offset = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!offset) return;
    event.preventDefault();
    const index = (KIND_ORDER.indexOf(tab) + offset + KIND_ORDER.length) % KIND_ORDER.length;
    const next = KIND_ORDER[index];
    setTab(next);
    tabRefs.current[next]?.focus();
  }

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
        <div className="mdl-subtabs" role="tablist" aria-label="Loại mô hình">
          {KIND_ORDER.map((kind) => {
            const Icon = TAB_ICONS[kind];
            const count = registry.profiles.filter((profile) => profile.kind === kind).length;
            return (
              <button
                key={kind}
                ref={(node) => {
                  tabRefs.current[kind] = node;
                }}
                type="button"
                role="tab"
                id={`mdl-tab-${kind}`}
                aria-selected={tab === kind}
                aria-controls={`mdl-panel-${kind}`}
                tabIndex={tab === kind ? 0 : -1}
                className={`mdl-subtab ${tab === kind ? "is-active" : ""}`}
                onClick={() => setTab(kind)}
                onKeyDown={onTabKeyDown}
              >
                <Icon size={15} />
                {KINDS[kind].label}
                <span className="mdl-subtab-count">{count}</span>
              </button>
            );
          })}
        </div>
        {/* Giữ các panel mounted để không mất form đang nhập dở khi đổi tab. */}
        {KIND_ORDER.map((kind) => (
          <div
            key={kind}
            role="tabpanel"
            id={`mdl-panel-${kind}`}
            aria-labelledby={`mdl-tab-${kind}`}
            hidden={tab !== kind}
          >
            <ModelKindPanel kind={kind} registry={registry} config={config} />
          </div>
        ))}
      </>
    );
  }

  return (
    <div className="models-page-wrapper">
      <div className="settings-subtabs-header">
        <div className="config-header-title-box">
          <div className="config-header-icon-box red-gradient">
            <Cpu size={18} />
          </div>
          <div>
            <h2 className="config-main-title">Mô hình AI</h2>
            <p className="config-main-desc">
              Cấu hình các mô hình LLM, embedding và rerank, rồi chọn mô hình hệ thống đang dùng cho từng khâu.
            </p>
          </div>
        </div>
      </div>
      <div className="mdl-page">
        <div className="mdl-wrap">{body}</div>
      </div>
    </div>
  );
}
