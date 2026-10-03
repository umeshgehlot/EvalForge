"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { apiGet, apiPost } from "@/lib/api";

type Dataset = { id: number; name: string };
type AppVersion = { id: number; name: string; model_name: string };
type Scorer = { id: number; name: string; scorer_type: string };

export function CreateRunDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [appVersions, setAppVersions] = useState<AppVersion[]>([]);
  const [scorers, setScorers] = useState<Scorer[]>([]);

  const [datasetId, setDatasetId] = useState("");
  const [appVersionId, setAppVersionId] = useState("");
  const [selectedScorers, setSelectedScorers] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!open) return;
    Promise.all([
      apiGet<Dataset[]>("/datasets"),
      apiGet<AppVersion[]>("/app-versions"),
      apiGet<Scorer[]>("/scorers"),
    ]).then(([d, a, s]) => {
      setDatasets(d);
      setAppVersions(a);
      setScorers(s);
      if (d.length) setDatasetId(String(d[0].id));
      if (a.length) setAppVersionId(String(a[0].id));
    });
  }, [open]);

  function toggleScorer(id: number) {
    setSelectedScorers((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function reset() {
    setDatasetId("");
    setAppVersionId("");
    setSelectedScorers(new Set());
    setError("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!datasetId || !appVersionId) {
      setError("Select a dataset and an app version.");
      return;
    }
    if (selectedScorers.size === 0) {
      setError("Select at least one scorer.");
      return;
    }
    setLoading(true);
    try {
      await apiPost("/runs", {
        dataset_id: Number(datasetId),
        app_version_id: Number(appVersionId),
        scorer_ids: Array.from(selectedScorers),
      });
      setOpen(false);
      reset();
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create run");
    } finally {
      setLoading(false);
    }
  }

  const selectClass =
    "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus size={14} className="mr-2" />
          New Run
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Start Eval Run</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="run-dataset">Dataset</Label>
            <select
              id="run-dataset"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              className={selectClass}
              required
            >
              <option value="">— select —</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="run-av">App Version</Label>
            <select
              id="run-av"
              value={appVersionId}
              onChange={(e) => setAppVersionId(e.target.value)}
              className={selectClass}
              required
            >
              <option value="">— select —</option>
              {appVersions.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.model_name})
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label>Scorers</Label>
            <div className="border rounded-md p-3 flex flex-col gap-2 max-h-48 overflow-y-auto">
              {scorers.length === 0 ? (
                <p className="text-sm text-muted-foreground">No scorers configured.</p>
              ) : (
                scorers.map((s) => (
                  <label key={s.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedScorers.has(s.id)}
                      onChange={() => toggleScorer(s.id)}
                      className="h-4 w-4"
                    />
                    <span className="text-sm">{s.name}</span>
                    <span className="text-xs text-muted-foreground ml-auto">
                      {s.scorer_type}
                    </span>
                  </label>
                ))
              )}
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button
            type="submit"
            disabled={!datasetId || !appVersionId || selectedScorers.size === 0 || loading}
          >
            {loading ? "Starting…" : "Start Run"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
