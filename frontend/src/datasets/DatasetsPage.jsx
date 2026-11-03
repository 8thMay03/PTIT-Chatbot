import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { datasetsApi, queryKeys, describeError } from "../api";
import { useToast } from "../components/Toast";
import DatasetView from "../DatasetView";
import DatasetListView from "./DatasetListView";

export default function DatasetsPage({ datasetId, onOpenDataset, onBackToList }) {
  const toast = useToast();
  const datasetsQuery = useQuery({
    queryKey: queryKeys.datasetList,
    queryFn: ({ signal }) => datasetsApi.list({ signal }),
  });
  const datasets = datasetsQuery.data?.datasets ?? [];

  const dataset = datasetId ? datasets.find((d) => d.id === datasetId) ?? null : null;
  const listLoaded = !datasetsQuery.isPending && !datasetsQuery.error;

  useEffect(() => {
    if (datasetId && listLoaded && !dataset) {
      toast.warning("Dataset không còn tồn tại.");
      onBackToList?.();
    }
  }, [datasetId, listLoaded, dataset, onBackToList, toast]);

  if (datasetId) {
    if (datasetsQuery.isPending || (!dataset && !listLoaded)) {
      return (
        <div className="dataset-wrapper">
          <main className="dataset-main-content">
            <div className="state-block" aria-busy="true">
              <p>Đang tải dataset...</p>
            </div>
          </main>
        </div>
      );
    }
    if (datasetsQuery.error && !dataset) {
      const err = describeError(datasetsQuery.error, {
        fallbackTitle: "Không tải được dataset",
        fallbackDetail: "Máy chủ trả về lỗi khi lấy danh sách dataset.",
      });
      return (
        <div className="dataset-wrapper">
          <main className="dataset-main-content">
            <div className="inline-alert is-error" role="alert">
              <span>{err.title}. {err.detail}</span>
            </div>
            <button type="button" className="ghost-btn" onClick={onBackToList}>
              Về danh sách Dataset
            </button>
          </main>
        </div>
      );
    }
    if (!dataset) return null;
    return <DatasetView dataset={dataset} onBack={onBackToList} />;
  }

  return (
    <DatasetListView
      datasets={datasets}
      loading={datasetsQuery.isPending}
      loadError={
        datasetsQuery.error
          ? describeError(datasetsQuery.error, {
              fallbackTitle: "Không tải được danh sách dataset",
              fallbackDetail: "Máy chủ trả về lỗi khi lấy danh sách dataset.",
            })
          : null
      }
      onOpen={onOpenDataset}
    />
  );
}
