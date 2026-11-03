import React, { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { datasetsApi, errorMessage } from "../api";
import { useToast } from "../components/Toast";
import Modal from "../components/Modal";

export default function DeleteDatasetModal({ open, dataset, onClose, onDeleted }) {
  const toast = useToast();
  const [confirm, setConfirm] = useState("");

  useEffect(() => {
    if (open) setConfirm("");
  }, [open, dataset?.id]);

  const deleteMutation = useMutation({
    mutationFn: () => datasetsApi.remove(dataset.id),
    onSuccess: (payload) => {
      toast.success(`Đã xóa dataset “${dataset.name}” (${payload.documents ?? 0} tài liệu).`);
      onDeleted?.(payload);
    },
    onError: (err) => toast.error(errorMessage(err, "Không xóa được dataset.")),
  });

  const expected = dataset?.name ?? "";
  const canDelete = confirm === expected && !deleteMutation.isPending;

  return (
    <Modal
      open={open && Boolean(dataset)}
      onClose={() => !deleteMutation.isPending && onClose?.()}
      title={`Xóa dataset “${dataset?.name ?? ""}”?`}
      description={
        dataset
          ? `Sẽ xóa ${dataset.document_count ?? 0} tài liệu, ${dataset.chunk_count ?? 0} đoạn. Không thể hoàn tác.`
          : ""
      }
      icon={<AlertTriangle size={20} />}
      tone="danger"
      actions={
        <>
          <button type="button" className="ghost-btn" onClick={onClose} disabled={deleteMutation.isPending}>
            Hủy
          </button>
          <button type="button" className="danger-btn" onClick={() => deleteMutation.mutate()} disabled={!canDelete}>
            {deleteMutation.isPending ? <Loader2 size={15} className="spin" /> : <Trash2 size={15} />}
            Xóa
          </button>
        </>
      }
    >
      <div className="edit-form-group">
        <label htmlFor="delete-dataset-confirm">Gõ lại tên dataset để xác nhận</label>
        <input
          id="delete-dataset-confirm"
          type="text"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder={expected}
        />
      </div>
    </Modal>
  );
}
