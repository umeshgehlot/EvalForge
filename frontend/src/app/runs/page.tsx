"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { apiDelete, apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CreateRunDialog } from "@/components/runs/CreateRunDialog";

type EvalRun = {
  id: number;
  dataset_id: number;
  app_version_id: number;
  status: string;
  scorer_ids: number[];
  created_at: string;
  completed_at: string | null;
};

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  pending:   "secondary",
  running:   "default",
  completed: "outline",
  failed:    "destructive",
};

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString();
}

export default function RunsPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await apiGet<EvalRun[]>("/runs");
      setRuns(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: number) {
    if (!confirm(`Delete run #${id}? This will remove all results.`)) return;
    await apiDelete(`/runs/${id}`);
    load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Eval Runs</h1>
          {!loading && (
            <p className="text-sm text-muted-foreground mt-1">
              {runs.length} run{runs.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Link href="/runs/compare">
            <Button variant="outline" size="sm">Compare Runs</Button>
          </Link>
          <CreateRunDialog onCreated={load} />
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : runs.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          No eval runs yet. Click <strong>New Run</strong> to start one.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {runs.map((r) => (
            <div
              key={r.id}
              className="rounded-lg border p-5 flex items-start justify-between gap-4"
            >
              <div className="flex flex-col gap-1.5 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <a
                    href={`/runs/${r.id}`}
                    className="font-semibold hover:underline"
                  >
                    Run #{r.id}
                  </a>
                  <Badge variant={STATUS_VARIANT[r.status] ?? "outline"}>
                    {r.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Dataset #{r.dataset_id} · App Version #{r.app_version_id} ·{" "}
                  {r.scorer_ids.length} scorer{r.scorer_ids.length !== 1 ? "s" : ""}
                </p>
                <p className="text-xs text-muted-foreground">
                  Started {fmtDate(r.created_at)}
                  {r.completed_at && ` · Completed ${fmtDate(r.completed_at)}`}
                </p>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                <a href={`/runs/${r.id}`}>
                  <Button variant="outline" size="sm">
                    View
                  </Button>
                </a>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDelete(r.id)}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 size={14} />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
