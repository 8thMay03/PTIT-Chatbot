import React, { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Plus, RefreshCw, Scissors, Search, Settings2, X } from "lucide-react";
import { datasetsApi, documentsApi, errorMessage, queryKeys } from "../api";
import Modal from "../components/Modal";
import { useToast } from "../components/Toast";
import useParseJobs from "../lib/useParseJobs";
import DatasetCard from "./DatasetCard";
import DatasetFormModal from "./DatasetFormModal";
import DeleteDatasetModal from "./DeleteDatasetModal";

export default function DatasetListView({ datasets, loading, loadError, onOpen }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [maintenanceOpen, setMaintenanceOpen] = useState(false);
  const [maintBusy, setMaintBusy] = useState(null);
  // Thao tác bảo trì đang chờ xác nhận: "rechunk" | "reindex" | null.
  const [pendingMaintenance, setPendingMaintenance] = useState(null);
  // Bảo trì toàn kho ghi đè mọi tài liệu; backend không chặn khi job parse nền
  // (upload/parse) còn chạy nên giao diện phải chờ các job đó xong.
  const { jobs: activeParseJobs, track: trackParseJobs } = useParseJobs();
  const backgroundBusy = activeParseJobs.length > 0;

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.datasets });
    queryClient.invalidateQueries({ queryKey: queryKeys.documents });
  };

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }) => datasetsApi.update(id, { enabled }),
    onSuccess: (payload) => {
      toast.success(payload.enabled ? `Đã bật dataset “${payload.name}”.` : `Đã tắt dataset “${payload.name}”.`);
      refresh();
    },
    onError: (err) => toast.error(errorMessage(err, "Không đổi được trạng thái dataset.")),
  });

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return datasets;
    return datasets.filter((d) =>
      [d.name, d.description].filter(Boolean).some((v) => v.toLowerCase().includes(needle))
    );
  }, [datasets, query]);

  const anyEnabled = datasets.some((d) => d.enabled);
  const showWarning = !loading && !loadError && datasets.length > 0 && !anyEnabled;

  async function fetchActiveParseJobs() {
    try {
      const payload = await documentsApi.parseJobs({ activeOnly: true });
      const jobs = payload?.jobs ?? [];
      trackParseJobs(jobs);
      return jobs;
    } catch {
      return [];
    }
  }

  function toggleMaintenance() {
    const opening = !maintenanceOpen;
    setMaintenanceOpen(opening);
    // Job có thể vừa được tạo ở tab/màn khác sau lần tải danh sách job gần nhất.
    if (opening) fetchActiveParseJobs();
  }

  function requestMaintenance(kind) {
    if (maintBusy || backgroundBusy) return;
    setMaintenanceOpen(false);
    setPendingMaintenance(kind);
  }

  function closeMaintenanceConfirm() {
    if (!maintBusy) setPendingMaintenance(null);
  }

  async function runMaintenance() {
    const kind = pendingMaintenance;
    if (!kind || maintBusy || backgroundBusy) return;
    setMaintBusy(kind);
    const active = await fetchActiveParseJobs();
    if (active.length > 0) {
      setMaintBusy(null);
      setPendingMaintenance(null);
      toast.warning("Còn job parse nền đang chạy; hãy chờ các job đó xong rồi thử lại.");
      return;
    }
    try {
      const payload = kind === "rechunk" ? await documentsApi.rechunk() : await documentsApi.reindex();
      const detail = `${payload.documents ?? 0} tài liệu · ${payload.chunks ?? 0} đoạn`;
      if (payload.skipped) {
        toast.warning(`Đã chia đoạn lại ${detail}. Bỏ qua ${payload.skipped} tài liệu chưa có bản parse.`);
      } else {
        toast.success(kind === "rechunk" ? `Đã chia đoạn lại ${detail}.` : `Đã nạp lại ${detail}.`);
      }
      refresh();
    } catch (err) {
      toast.error(errorMessage(err, "Không thực hiện được thao tác bảo trì."));
    } finally {
      setMaintBusy(null);
      setPendingMaintenance(null);
    }
  }

  // Phạm vi hiển thị trong hộp xác nhận; chỉ nêu số tài liệu khi mọi dataset có số liệu.
  const totalDocuments = datasets.every((d) => typeof d.document_count === "number")
    ? datasets.reduce((sum, d) => sum + d.document_count, 0)
    : null;
  const maintenanceScope =
    `mọi tài liệu của toàn bộ ${datasets.length} dataset` +
    (totalDocuments != null ? ` (${totalDocuments} tài liệu)` : "") +
    ", kể cả dataset đang tắt";
  const confirmingReindex = pendingMaintenance === "reindex";

  return (
    <div className="dataset-wrapper">
      <main className="dataset-main-content">
        <div className="datasets-view">
          <header className="dataset-view-header">
            <div className="dataset-view-title">
              <h2>Dataset</h2>
              <p>Mỗi dataset là một nhóm tài liệu. Chỉ dataset đang bật được dùng khi trả lời.</p>
            </div>
            <div className="dataset-view-toolbar">
              <div className="dataset-search-field">
                <Search size={14} className="search-icon" aria-hidden="true" />
                <label className="sr-only" htmlFor="datasets-search">Tìm dataset</label>
                <input
                  id="datasets-search"
                  type="text"
                  placeholder="Tìm dataset"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                {query && (
                  <button type="button" className="search-clear-btn" onClick={() => setQuery("")} aria-label="Xóa từ khóa tìm kiếm">
                    <X size={12} />
                  </button>
                )}
              </div>
              <div className="maintenance-menu">
                <button
                  type="button"
                  className="btn-outline-dataset"
                  onClick={toggleMaintenance}
                  aria-haspopup="menu"
                  aria-expanded={maintenanceOpen}
                  disabled={Boolean(maintBusy)}
                >
                  {maintBusy ? <Loader2 size={14} className="spin" /> : <Settings2 size={14} />}
                  <span>{maintBusy ? "Đang chạy..." : "Bảo trì"}</span>
                </button>
                {maintenanceOpen && (
                  <div className="maintenance-dropdown" role="menu">
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => requestMaintenance("rechunk")}
                      disabled={backgroundBusy}
                      title={
                        backgroundBusy
                          ? "Chờ các job parse nền đang chạy xong trước khi chia đoạn lại toàn bộ"
                          : "Chia đoạn và nhúng vector lại mọi tài liệu từ bản Markdown đã lưu, không parse lại (dùng sau khi đổi cấu hình chia đoạn)"
                      }
                    >
                      Chia đoạn lại toàn bộ
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => requestMaintenance("reindex")}
                      disabled={backgroundBusy}
                      title={
                        backgroundBusy
                          ? "Chờ các job parse nền đang chạy xong trước khi nạp lại toàn bộ"
                          : "Parse lại mọi file gốc rồi chia đoạn và nhúng vector; bản Markdown đã sửa tay được giữ nguyên"
                      }
                    >
                      Nạp lại toàn bộ
                    </button>
                  </div>
                )}
              </div>
              <button type="button" className="btn-add-file" onClick={() => { setEditing(null); setFormOpen(true); }}>
                <Plus size={15} strokeWidth={2.5} />
                <span>Tạo dataset</span>
              </button>
            </div>
          </header>

          {showWarning && (
            <div className="inline-alert is-warning" role="alert" style={{ marginBottom: 12 }}>
              <AlertTriangle size={16} />
              <span>Không có dataset nào đang bật — chatbot sẽ không có nguồn để trả lời.</span>
            </div>
          )}

          {loadError && (
            <div className="inline-alert is-error" role="alert" style={{ marginBottom: 12 }}>
              <AlertTriangle size={16} />
              <span>{loadError.title}. {loadError.detail}</span>
            </div>
          )}

          {loading ? (
            <div className="state-block" aria-busy="true">
              <div style={{ width: "100%", padding: "0 16px", display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="skeleton skeleton-row" style={{ height: 120 }} />
                ))}
              </div>
              <p>Đang tải danh sách dataset...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="state-block">
              <h3>{query ? "Không có dataset nào khớp" : "Chưa có dataset nào"}</h3>
              <p>
                {query
                  ? "Thử từ khóa khác, hoặc xóa ô tìm kiếm để xem toàn bộ."
                  : "Tạo dataset đầu tiên để tải tài liệu lên và nhóm chúng theo chủ đề."}
              </p>
              {!query && (
                <button type="button" className="btn-add-file" onClick={() => { setEditing(null); setFormOpen(true); }}>
                  <Plus size={15} />
                  <span>Tạo dataset</span>
                </button>
              )}
            </div>
          ) : (
            <div className="datasets-grid">
              {filtered.map((dataset) => (
                <DatasetCard
                  key={dataset.id}
                  dataset={dataset}
                  onOpen={() => onOpen?.(dataset.id)}
                  onEdit={() => { setEditing(dataset); setFormOpen(true); }}
                  onDelete={() => setDeleting(dataset)}
                  onToggle={() => toggleMutation.mutate({ id: dataset.id, enabled: !dataset.enabled })}
                  toggling={toggleMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      <DatasetFormModal
        open={formOpen}
        dataset={editing}
        onClose={() => { setFormOpen(false); setEditing(null); }}
        onSaved={() => { setFormOpen(false); setEditing(null); refresh(); }}
      />
      <DeleteDatasetModal
        open={Boolean(deleting)}
        dataset={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={() => { setDeleting(null); refresh(); }}
      />
      {/* Bảo trì toàn kho: luôn hỏi lại trước khi chạy lại pipeline cho mọi tài liệu. */}
      <Modal
        open={Boolean(pendingMaintenance)}
        onClose={closeMaintenanceConfirm}
        title={confirmingReindex ? "Nạp lại toàn bộ kho tài liệu?" : "Chia đoạn lại toàn bộ kho tài liệu?"}
        description={
          confirmingReindex
            ? `Sẽ parse lại file gốc của ${maintenanceScope}, rồi chia đoạn và nhúng vector lại. ` +
              "Tài liệu có Markdown sửa tay được giữ nguyên bản sửa. " +
              "Thao tác có thể mất nhiều thời gian và kết quả tìm kiếm có thể thay đổi trong lúc chạy."
            : `Sẽ chia đoạn và nhúng vector lại ${maintenanceScope}, từ bản Markdown đã lưu; file gốc không được parse lại. ` +
              "Thao tác có thể mất nhiều thời gian và kết quả tìm kiếm có thể thay đổi trong lúc chạy."
        }
        icon={<AlertTriangle size={20} />}
        tone={confirmingReindex ? "danger" : "default"}
        actions={
          <>
            <button type="button" className="ghost-btn" onClick={closeMaintenanceConfirm} disabled={Boolean(maintBusy)}>
              Hủy
            </button>
            <button
              type="button"
              className={confirmingReindex ? "danger-btn" : "primary-btn"}
              onClick={runMaintenance}
              disabled={Boolean(maintBusy) || backgroundBusy}
            >
              {maintBusy ? (
                <Loader2 size={15} className="spin" />
              ) : confirmingReindex ? (
                <RefreshCw size={15} />
              ) : (
                <Scissors size={15} />
              )}
              {confirmingReindex ? "Nạp lại toàn bộ" : "Chia đoạn lại toàn bộ"}
            </button>
          </>
        }
      >
        {backgroundBusy && !maintBusy && (
          <p role="status">Còn job parse nền đang chạy; hãy chờ các job đó xong rồi thử lại.</p>
        )}
      </Modal>
    </div>
  );
}
