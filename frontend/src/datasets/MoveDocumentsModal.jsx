import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { datasetsApi, documentsApi, errorMessage, queryKeys } from "../api";
import { useToast } from "../components/Toast";
import Modal from "../components/Modal";

export default function MoveDocumentsModal({ open, documentIds, currentDatasetId, onClose, onMoved }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [targetId, setTargetId] = useState("");
  const [conflicts, setConflicts] = useState([]);

  const datasetsQuery = useQuery({
    queryKey: queryKeys.datasetList,
    queryFn: ({ signal }) => datasetsApi.list({ signal }),
    enabled: open,
  });
  const datasets = (datasetsQuery.data?.datasets ?? []).filter((d) => d.id !== currentDatasetId);
  const count = documentIds?.length ?? 0;

  const moveMutation = useMutation({
    mutationFn: () => documentsApi.move(documentIds, targetId),
    onSuccess: (payload) => {
      setConflicts([]);
      toast.success(`Đã chuyển ${payload.moved ?? count} tài liệu.`);
      queryClient.invalidateQueries({ queryKey: queryKeys.datasets });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents });
      onMoved?.(payload);
    },
    onError: (err) => {
      const message = errorMessage(err, "Không chuyển được tài liệu.");
      // 409 trùng tên: giữ hộp thoại mở và hiện danh sách file trùng.
      if (err?.status === 409) {
        setConflicts([message]);
      } else {
        toast.error(message);
      }
    },
  });

  return (
    <Modal
      open={open}
      onClose={() => !moveMutation.isPending && onClose?.()}
      title={`Chuyển ${count} tài liệu sang dataset khác`}
      description="Giữ nguyên nội dung, đoạn và embedding — không cần parse lại."
      actions={
        <>
          <button type="button" className="ghost-btn" onClick={onClose} disabled={moveMutation.isPending}>
            Hủy
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={() => { setConflicts([]); moveMutation.mutate(); }}
            disabled={!targetId || moveMutation.isPending}
          >
            {moveMutation.isPending && <Loader2 size={15} className="spin" />}
            Chuyển
          </button>
        </>
      }
    >
      {datasetsQuery.isPending ? (
        <p>Đang tải danh sách dataset...</p>
      ) : (
        <div className="move-modal-list" role="radiogroup" aria-label="Dataset đích">
          {datasets.map((dataset) => (
            <button
              key={dataset.id}
              type="button"
              role="radio"
              aria-checked={targetId === dataset.id}
              className="move-modal-option"
              onClick={() => setTargetId(dataset.id)}
              style={targetId === dataset.id ? { borderWidth: 2 } : undefined}
            >
              <input type="radio" checked={targetId === dataset.id} readOnly tabIndex={-1} />
              <span>
                <strong>{dataset.name}</strong>
                <br />
                <small>{dataset.document_count ?? 0} tài liệu</small>
              </span>
            </button>
          ))}
          {datasets.length === 0 && <p>Không còn dataset khác để chuyển tới.</p>}
        </div>
      )}
      {conflicts.length > 0 && (
        <div className="inline-alert is-error" role="alert" style={{ marginTop: 8 }}>
          {conflicts.map((message, index) => (
            <span key={index}>{message}</span>
          ))}
        </div>
      )}
    </Modal>
  );
}
