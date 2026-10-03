"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ── Types ─────────────────────────────────────────────────────────────────────

type EvalRun = {
  id: number;
  dataset_id: number;
  app_version_id: number;
  status: string;
  scorer_ids: number[];
  created_at: string;
  completed_at: string | null;
};

type MetricDelta = {
  scorer_id: number | null;
  scorer_name: string;
  avg_score_a: number | null;
  avg_score_b: number | null;
  avg_score_delta: number | null;
  pass_rate_a: number | null;
  pass_rate_b: number | null;
  pass_rate_delta: number | null;
  p95_latency_a: number | null;
  p95_latency_b: number | null;
  p95_latency_delta: number | null;
  total_cost_a: number | null;
  total_cost_b: number | null;
  total_cost_delta: number | null;
};

type ComparisonItem = {
  row_id: number;
  row_input: string;
  item_id_a: number;
  item_id_b: number;
  output_a: string | null;
  output_b: string | null;
};

type Comparison = {
  run_a: EvalRun;
  run_b: EvalRun;
  metrics_delta: MetricDelta[];
  regressions: ComparisonItem[];
  improvements: ComparisonItem[];
  safe_to_ship: boolean;
  summary: string;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(n: number | null) {
  if (n == null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmt(n: number | null, decimals = 3) {
  if (n == null) return "—";
  return n.toFixed(decimals);
}

function trunc(s: string | null, max = 120) {
  if (!s) return "—";
  return s.length > max ? s.slice(0, max) + "…" : s;
}

function DeltaBadge({ delta, invert = false }: { delta: number | null; invert?: boolean }) {
  if (delta == null) return <span className="text-muted-foreground text-xs">—</span>;
  const positive = invert ? delta < 0 : delta > 0;
  const neutral = Math.abs(delta) < 0.001;
  if (neutral) return <span className="font-mono text-xs text-muted-foreground">±0</span>;
  const sign = delta > 0 ? "+" : "";
  const color = positive
    ? "text-green-600"
    : "text-red-600";
  return (
    <span className={`font-mono text-xs font-semibold ${color}`}>
      {sign}{(delta * 100).toFixed(1)}%
    </span>
  );
}

function LatencyDelta({ delta }: { delta: number | null }) {
  if (delta == null) return <span className="text-muted-foreground text-xs">—</span>;
  const neutral = Math.abs(delta) < 1;
  if (neutral) return <span className="font-mono text-xs text-muted-foreground">±0 ms</span>;
  const better = delta < 0;
  const sign = delta > 0 ? "+" : "";
  return (
    <span className={`font-mono text-xs font-semibold ${better ? "text-green-600" : "text-red-600"}`}>
      {sign}{Math.round(delta)} ms
    </span>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function CaseTable({
  items,
  runIdA,
  runIdB,
  label,
  variant,
}: {
  items: ComparisonItem[];
  runIdA: number;
  runIdB: number;
  label: string;
  variant: "regression" | "improvement";
}) {
  if (!items.length) return null;
  const color = variant === "regression" ? "text-red-600" : "text-green-600";
  const borderColor = variant === "regression" ? "border-red-200" : "border-green-200";

  return (
    <div className={`rounded-lg border ${borderColor} overflow-x-auto`}>
      <div className={`px-4 py-2 border-b ${borderColor} bg-muted/20`}>
        <p className={`text-sm font-semibold ${color}`}>
          {label} ({items.length})
        </p>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-muted/30">
          <tr>
            <th className="text-left p-3 font-medium whitespace-nowrap">Row</th>
            <th className="text-left p-3 font-medium">Input</th>
            <th className="text-left p-3 font-medium">Output A</th>
            <th className="text-left p-3 font-medium">Output B</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.row_id} className="border-t">
              <td className="p-3 font-mono text-xs whitespace-nowrap">
                <div className="flex flex-col gap-0.5">
                  <Link
                    href={`/runs/${runIdA}/items/${item.item_id_a}`}
                    className="text-primary hover:underline"
                  >
                    A#{item.row_id}
                  </Link>
                  <Link
                    href={`/runs/${runIdB}/items/${item.item_id_b}`}
                    className="text-primary hover:underline"
                  >
                    B#{item.row_id}
                  </Link>
                </div>
              </td>
              <td className="p-3 max-w-[180px]">
                <span className="text-xs text-muted-foreground">
                  {trunc(item.row_input, 80)}
                </span>
              </td>
              <td className="p-3 max-w-[220px]">
                <span className="text-xs">{trunc(item.output_a)}</span>
              </td>
              <td className="p-3 max-w-[220px]">
                <span className="text-xs">{trunc(item.output_b)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ComparePage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [runAId, setRunAId] = useState<string>("");
  const [runBId, setRunBId] = useState<string>("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<EvalRun[]>("/runs").then(setRuns);
  }, []);

  const completedRuns = runs.filter((r) => r.status === "completed");

  async function handleCompare() {
    if (!runAId || !runBId) return;
    if (runAId === runBId) {
      setError("Select two different runs.");
      return;
    }
    setLoading(true);
    setError(null);
    setComparison(null);
    try {
      const data = await apiGet<Comparison>(
        `/runs/compare?run_a=${runAId}&run_b=${runBId}`
      );
      setComparison(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <Link href="/runs" className="text-sm text-muted-foreground hover:underline">
            ← Runs
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight mt-2">Compare Runs</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Select two completed runs to see regressions, improvements, and metric deltas.
        </p>
      </div>

      {/* Selectors */}
      <div className="flex items-end gap-3 flex-wrap">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground">Baseline (Run A)</label>
          <select
            value={runAId}
            onChange={(e) => setRunAId(e.target.value)}
            className="text-sm h-9 rounded-md border border-input bg-background px-3 min-w-[180px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Select run…</option>
            {completedRuns.map((r) => (
              <option key={r.id} value={String(r.id)}>
                Run #{r.id} — Dataset #{r.dataset_id} · v#{r.app_version_id}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground">Candidate (Run B)</label>
          <select
            value={runBId}
            onChange={(e) => setRunBId(e.target.value)}
            className="text-sm h-9 rounded-md border border-input bg-background px-3 min-w-[180px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Select run…</option>
            {completedRuns.map((r) => (
              <option key={r.id} value={String(r.id)}>
                Run #{r.id} — Dataset #{r.dataset_id} · v#{r.app_version_id}
              </option>
            ))}
          </select>
        </div>

        <Button
          onClick={handleCompare}
          disabled={!runAId || !runBId || loading}
        >
          {loading ? "Comparing…" : "Compare"}
        </Button>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {comparison && (
        <>
          {/* Safe to ship banner */}
          <div
            className={`rounded-lg border px-5 py-4 flex items-start gap-3 ${
              comparison.safe_to_ship
                ? "border-green-300 bg-green-50 dark:bg-green-950/20"
                : "border-red-300 bg-red-50 dark:bg-red-950/20"
            }`}
          >
            <div className="text-xl">{comparison.safe_to_ship ? "✅" : "⚠️"}</div>
            <div>
              <p className="font-semibold text-sm">
                {comparison.safe_to_ship ? "Safe to Ship" : "Not Safe to Ship"}
              </p>
              <p className="text-sm text-muted-foreground mt-0.5">{comparison.summary}</p>
            </div>
          </div>

          {/* Run meta row */}
          <div className="grid grid-cols-2 gap-4">
            {[comparison.run_a, comparison.run_b].map((run, i) => (
              <div key={run.id} className="rounded-lg border p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary">{i === 0 ? "A — Baseline" : "B — Candidate"}</Badge>
                  <Link
                    href={`/runs/${run.id}`}
                    className="font-semibold text-sm hover:underline"
                  >
                    Run #{run.id}
                  </Link>
                </div>
                <p className="text-xs text-muted-foreground">
                  Dataset #{run.dataset_id} · App Version #{run.app_version_id}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(run.created_at).toLocaleString()}
                  {run.completed_at &&
                    ` → ${new Date(run.completed_at).toLocaleString()}`}
                </p>
              </div>
            ))}
          </div>

          {/* Metric delta table */}
          {comparison.metrics_delta.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Metric Deltas</h2>
              <div className="rounded-lg border overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 font-medium">Scorer</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Pass Rate A</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Pass Rate B</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Δ Pass Rate</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Avg Score A</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Avg Score B</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Δ Score</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">p95 Latency A</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">p95 Latency B</th>
                      <th className="text-left p-3 font-medium whitespace-nowrap">Δ Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.metrics_delta.map((m) => (
                      <tr key={m.scorer_id ?? "overall"} className="border-t">
                        <td className="p-3 font-medium text-sm">{m.scorer_name}</td>
                        <td className="p-3 font-mono text-xs">{pct(m.pass_rate_a)}</td>
                        <td className="p-3 font-mono text-xs">{pct(m.pass_rate_b)}</td>
                        <td className="p-3">
                          <DeltaBadge delta={m.pass_rate_delta} />
                        </td>
                        <td className="p-3 font-mono text-xs">{fmt(m.avg_score_a)}</td>
                        <td className="p-3 font-mono text-xs">{fmt(m.avg_score_b)}</td>
                        <td className="p-3">
                          <DeltaBadge delta={m.avg_score_delta} />
                        </td>
                        <td className="p-3 font-mono text-xs">
                          {m.p95_latency_a != null ? `${Math.round(m.p95_latency_a)} ms` : "—"}
                        </td>
                        <td className="p-3 font-mono text-xs">
                          {m.p95_latency_b != null ? `${Math.round(m.p95_latency_b)} ms` : "—"}
                        </td>
                        <td className="p-3">
                          <LatencyDelta delta={m.p95_latency_delta} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Regressions */}
          <CaseTable
            items={comparison.regressions}
            runIdA={comparison.run_a.id}
            runIdB={comparison.run_b.id}
            label="Regressions (pass in A → fail in B)"
            variant="regression"
          />

          {/* Improvements */}
          <CaseTable
            items={comparison.improvements}
            runIdA={comparison.run_a.id}
            runIdB={comparison.run_b.id}
            label="Improvements (fail in A → pass in B)"
            variant="improvement"
          />

          {comparison.regressions.length === 0 &&
            comparison.improvements.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No case-level changes detected between the two runs.
              </p>
            )}
        </>
      )}
    </div>
  );
}
