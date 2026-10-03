"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { CreateDatasetDialog } from "@/components/datasets/CreateDatasetDialog";

type Dataset = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  row_count: number;
};

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await apiGet<Dataset[]>("/datasets");
      setDatasets(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Datasets</h1>
          {!loading && (
            <p className="text-sm text-muted-foreground mt-1">
              {datasets.length} dataset{datasets.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <CreateDatasetDialog onCreated={load} />
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : datasets.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          No datasets yet. Create one to get started.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((ds) => (
            <a
              key={ds.id}
              href={`/datasets/${ds.id}`}
              className="block rounded-lg border p-6 hover:bg-accent transition-colors"
            >
              <h2 className="font-semibold">{ds.name}</h2>
              {ds.description && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                  {ds.description}
                </p>
              )}
              <div className="flex items-center gap-3 mt-4">
                <span className="text-xs bg-secondary text-secondary-foreground px-2 py-1 rounded-full font-medium">
                  {ds.row_count} rows
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(ds.created_at).toLocaleDateString()}
                </span>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
