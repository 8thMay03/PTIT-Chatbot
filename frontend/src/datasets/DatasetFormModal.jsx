import React, { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { datasetsApi, errorMessage } from "../api";
import { useToast } from "../components/Toast";
import Modal from "../components/Modal";

export default function DatasetFormModal({ open, dataset, onClose, onSaved }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [nameError, setNameError] = useState("");

  useEffect(() => {
    if (open) {
      setName(dataset?.name ?? "");
      setDescription(dataset?.description ?? "");
      setNameError("");
    }
  }, [open, dataset]);

  const saveMutation = useMutation({
    mutationFn: () =>
      dataset
        ? datasetsApi.update(dataset.id, { name: name.trim(), description: description.trim() || null, clearDescription: !description.trim() })
        : datasetsApi.create({ name: name.trim(), description: description.trim() || undefined }),
    onSuccess: (payload) => {
      toast.success(dataset ? `Đã lưu dataset “${payload.name}”.` : `Đã tạo dataset “${payload.name}”.`);
      onSaved?.(payload);
    },
    onError: (err) => {
      const message = errorMessage(err, "Không lưu được dataset.");
      if (err?.status === 409 || /đã tồn tại/i.test(message)) {
        setNameError(message);
      } else {
        toast.error(message);
      }
    },
  });

  const nameLen = name.trim().length;
  const canSave = nameLen >= 1 && nameLen <= 100 && !saveMutation.isPending;

  return (
    <Modal
      open={open}
      onClose={() => !saveMutation.isPending && onClose?.()}
      title={dataset ? "Đổi tên & mô tả" : "Tạo dataset"}
      actions={
        <>
          <button type="button" className="ghost-btn" onClick={onClose} disabled={saveMutation.isPending}>
            Hủy
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={() => { setNameError(""); saveMutation.mutate(); }}
            disabled={!canSave}
          >
            {saveMutation.isPending && <Loader2 size={15} className="spin" />}
            {dataset ? "Lưu" : "Tạo"}
          </button>
        </>
      }
    >
      <div className="edit-form-group">
        <label htmlFor="dataset-name-input">Tên dataset ({nameLen}/100)</label>
        <input
          id="dataset-name-input"
          type="text"
          value={name}
          maxLength={120}
          onChange={(e) => { setName(e.target.value); setNameError(""); }}
          placeholder="Ví dụ: Sổ tay sinh viên"
        />
        {nameError && <span className="field-error" role="alert">{nameError}</span>}
        <label htmlFor="dataset-desc-input" style={{ marginTop: 12 }}>
          Mô tả ({description.trim().length}/500, không bắt buộc)
        </label>
        <textarea
          id="dataset-desc-input"
          value={description}
          maxLength={600}
          rows={3}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Ví dụ: Sổ tay K2024, D26"
        />
      </div>
    </Modal>
  );
}
