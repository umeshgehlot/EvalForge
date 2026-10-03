"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";
import Link from "next/link";
import { apiDelete, apiGet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { UploadModal } from "@/components/datasets/UploadModal";
import { RowsTable } from "@/components/datasets/RowsTable";

type Dataset = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  row_count: number;
};

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const datasetId = parseInt(id);

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  async function loadDataset() {
    try {
      const data = await apiGet<Dataset>(`/datasets/${datasetId}`);
      setDataset(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDataset();
  }, [refreshKey]);

  function handleUploaded() {
    setRefreshKey((k) => k + 1);
  }

  async function handleDeleteDataset() {
    if (!confirm(`Delete dataset "${dataset?.name}" and all its rows? This cannot be undone.`))
      return;
    await apiDelete(`/datasets/${datasetId}`);
    window.location.href = "/datasets";
  }

  if (loading) return <p className="text-muted-foreground text-sm">Loading…</p>;
  if (!dataset) return <p className="text-destructive text-sm">Dataset not found.</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <Link
            href="/datasets"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
          >
            <ArrowLeft size={14} />
            Datasets
          </Link>
          <h1 className="text-2xl font-bold tracking-tight">{dataset.name}</h1>
          {dataset.description && (
            <p className="text-sm text-muted-foreground">{dataset.description}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {dataset.row_count} rows · created{" "}
            {new Date(dataset.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <UploadModal datasetId={datasetId} onUploaded={handleUploaded} />
          <Button
            variant="outline"
            size="sm"
            onClick={handleDeleteDataset}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 size={14} className="mr-2" />
            Delete
          </Button>
        </div>
      </div>

      <RowsTable key={refreshKey} datasetId={datasetId} />
    </div>
  );
}
