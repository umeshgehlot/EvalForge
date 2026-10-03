"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronDown, ChevronRight } from "lucide-react";
import { apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { ScoreChart } from "@/components/runs/ScoreChart";

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

type StatusData = {
  id: number;
  status: string;
  items_done: number;
  items_total: number;
  progress: number;
};

type Metric = {
  id: number;
  run_id: number;
  scorer_id: number | null;
  avg_score: number | null;
  pass_rate: number | null;
  p95_latency: number | null;
  total_cost: number | null;
};

type RunItem = {
  id: number;
  run_id: number;
  row_id: number;
  row_input: string;
  row_expected: string | null;
  row_tags: string | null;
  output: string | null;
  latency_ms: number | null;
  token_in: number | null;
  token_out: number | null;
  pass_fail: boolean | null;
  scorer_results_json: Record<
    string,
    { score: number; passed: boolean; label: string; reasoning: string }
  >;
};

type PaginatedItems = {
  items: RunItem[];
  total: number;
  page: number;
  limit: number;
};

type Scorer = { id: number; name: string; scorer_type: string };

type TraceSpan = {
  id: number;
  run_item_id: number;
  span_name: string;
  parent_id: number | null;
  start_ms: number | null;
  end_ms: number | null;
  metadata_json: Record<string, unknown>;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function trunc(s: string | null, max = 100) {
  if (!s) return "—";
  return s.length > max ? s.slice(0, max) + "…" : s;
}

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "destructive"
> = {
  pending: "secondary",
  running: "default",
  completed: "outline",
  failed: "destructive",
};

const SPAN_COLORS: Record<string, string> = {
  "rag.total":     "bg-blue-500",
  "rag.retrieval": "bg-emerald-500",
  "rag.generate":  "bg-violet-500",
};
function spanColor(name: string) {
  return SPAN_COLORS[name] ?? "bg-orange-400";
}

// ── Trace Viewer ──────────────────────────────────────────────────────────────

function TraceViewer({ spans }: { spans: TraceSpan[] }) {
  if (!spans.length)
    return <p className="text-xs text-muted-foreground p-3">No trace spans recorded.</p>;

  const starts = spans.map((s) => s.start_ms ?? 0);
  const ends = spans.map((s) => s.end_ms ?? 0);
  const tMin = Math.min(...starts);
  const tMax = Math.max(...ends);
  const duration = tMax - tMin || 1;

  const byId: Record<number, TraceSpan> = Object.fromEntries(
    spans.map((s) => [s.id, s])
  );
  function depth(span: TraceSpan): number {
    if (span.parent_id == null || !byId[span.parent_id]) return 0;
    return 1 + depth(byId[span.parent_id]);
  }

  return (
    <div className="p-3 flex flex-col gap-1.5 bg-muted/30 rounded-b-lg border-t">
      <p className="text-xs font-medium text-muted-foreground mb-1">
        Trace · {duration} ms total
      </p>
      {spans.map((span) => {
        const left = (((span.start_ms ?? tMin) - tMin) / duration) * 100;
        const width = Math.max(
          0.5,
          (((span.end_ms ?? tMax) - (span.start_ms ?? tMin)) / duration) * 100
        );
        const d = depth(span);
        const spanDuration = (span.end_ms ?? 0) - (span.start_ms ?? 0);
        return (
          <div key={span.id} className="flex items-center gap-2">
            <div
              className="text-xs font-mono text-muted-foreground whitespace-nowrap w-32 shrink-0 truncate"
              style={{ paddingLeft: `${d * 12}px` }}
              title={span.span_name}
            >
              {span.span_name}
            </div>
            <div className="relative flex-1 h-5 bg-muted rounded overflow-hidden">
              <div
                className={`absolute h-full rounded ${spanColor(span.span_name)} opacity-80`}
                style={{ left: `${left}%`, width: `${width}%` }}
              />
            </div>
            <span className="text-xs font-mono text-muted-foreground w-16 text-right shrink-0">
              {spanDuration} ms
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);

  const [run, setRun] = useState<EvalRun | null>(null);
  const [status, setStatus] = useState<StatusData | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [items, setItems] = useState<RunItem[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [scorers, setScorers] = useState<Scorer[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Filters
  const [filterPassFail, setFilterPassFail] = useState<"all" | "pass" | "fail">("all");
  const [filterTag, setFilterTag] = useState("");

  // Trace viewer
  const [expandedTraces, setExpandedTraces] = useState<
    Record<number, TraceSpan[] | null>
  >({});

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    Promise.all([
      apiGet<EvalRun>(`/runs/${runId}`),
      apiGet<Scorer[]>("/scorers"),
    ]).then(([r, s]) => {
      setRun(r);
      setScorers(s);
      setLoading(false);
    });
  }, [runId]);

  function fetchLive() {
    apiGet<StatusData>(`/runs/${runId}/status`).then(setStatus);
    apiGet<Metric[]>(`/runs/${runId}/metrics`).then(setMetrics);
  }

  useEffect(() => { fetchLive(); }, [runId]);

  useEffect(() => {
    if (!status) return;
    if (status.status === "running" || status.status === "pending") {
      pollRef.current = setInterval(fetchLive, 2000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [status?.status]);

  useEffect(() => {
    const pf =
      filterPassFail === "pass" ? "true" :
      filterPassFail === "fail" ? "false" : "";
    const tagParam = filterTag ? `&tag=${encodeURIComponent(filterTag)}` : "";
    const pfParam = pf ? `&pass_fail=${pf}` : "";
    apiGet<PaginatedItems>(
      `/runs/${runId}/results?page=${page}&limit=50${pfParam}${tagParam}`
    ).then((d) => {
      setItems(d.items);
      setTotalItems(d.total);
    });
  }, [runId, page, filterPassFail, filterTag]);

  async function toggleTrace(item: RunItem) {
    if (item.id in expandedTraces) {
      setExpandedTraces((prev) => { const n = { ...prev }; delete n[item.id]; return n; });
      return;
    }
    setExpandedTraces((prev) => ({ ...prev, [item.id]: null }));
    const spans = await apiGet<TraceSpan[]>(`/runs/${runId}/items/${item.id}/traces`);
    setExpandedTraces((prev) => ({ ...prev, [item.id]: spans }));
  }

  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!run) return <p className="text-sm text-destructive">Run not found.</p>;

  const scorerMap = Object.fromEntries(scorers.map((s) => [String(s.id), s]));
  const totalPages = Math.ceil(totalItems / 50);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <Link href="/runs" className="text-sm text-muted-foreground hover:underline">
            ← Runs
          </Link>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <h1 className="text-2xl font-bold tracking-tight">Run #{run.id}</h1>
          {status && (
            <Badge variant={STATUS_VARIANT[status.status] ?? "outline"}>
              {status.status}
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Dataset #{run.dataset_id} · App Version #{run.app_version_id} · Started{" "}
          {new Date(run.created_at).toLocaleString()}
          {run.completed_at &&
            ` · Completed ${new Date(run.completed_at).toLocaleString()}`}
        </p>
      </div>

      {/* Progress bar */}
      {status && (status.status === "running" || status.status === "pending") && (
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              {status.items_done} / {status.items_total} rows evaluated
            </span>
            <span className="font-mono">{pct(status.progress)}</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${status.progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Metric cards + charts (two-column layout) */}
      {metrics.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: summary cards */}
          <div className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold">Summary</h2>
            <div className="grid grid-cols-2 gap-3">
              {metrics.map((m) => {
                const scorer = m.scorer_id ? scorerMap[String(m.scorer_id)] : null;
                return (
                  <div key={m.id} className="rounded-lg border p-4 flex flex-col gap-2">
                    <p className="text-xs font-medium text-muted-foreground truncate">
                      {scorer ? scorer.name : "Overall"}
                    </p>
                    <div className="flex flex-col gap-0.5 text-sm">
                      {m.avg_score != null && (
                        <span>
                          <span className="text-muted-foreground text-xs">Score </span>
                          <span className="font-mono font-semibold">
                            {m.avg_score.toFixed(3)}
                          </span>
                        </span>
                      )}
                      {m.pass_rate != null && (
                        <span>
                          <span className="text-muted-foreground text-xs">Pass </span>
                          <span className="font-mono font-semibold">
                            {pct(m.pass_rate)}
                          </span>
                        </span>
                      )}
                      {m.p95_latency != null && (
                        <span>
                          <span className="text-muted-foreground text-xs">p95 </span>
                          <span className="font-mono font-semibold">
                            {Math.round(m.p95_latency)} ms
                          </span>
                        </span>
                      )}
                      {m.total_cost != null && (
                        <span>
                          <span className="text-muted-foreground text-xs">Cost </span>
                          <span className="font-mono font-semibold">
                            ${m.total_cost.toFixed(4)}
                          </span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: charts */}
          <div className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold">Score Distribution</h2>
            <ScoreChart metrics={metrics} scorers={scorers} />
          </div>
        </div>
      )}

      {/* Results table */}
      <div>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h2 className="text-lg font-semibold">
            Results
            {totalItems > 0 && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                ({totalItems} rows)
              </span>
            )}
          </h2>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <select
              value={filterPassFail}
              onChange={(e) => {
                setFilterPassFail(e.target.value as "all" | "pass" | "fail");
                setPage(1);
              }}
              className="text-sm h-8 rounded-md border border-input bg-background px-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="all">All</option>
              <option value="pass">Pass only</option>
              <option value="fail">Fail only</option>
            </select>
            <input
              type="text"
              placeholder="Filter by tag…"
              value={filterTag}
              onChange={(e) => { setFilterTag(e.target.value); setPage(1); }}
              className="text-sm h-8 rounded-md border border-input bg-background px-2 w-32 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>

        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {status?.status === "pending" || status?.status === "running"
              ? "Evaluation in progress…"
              : "No results match the current filters."}
          </p>
        ) : (
          <>
            <div className="rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3 font-medium w-8" />
                    <th className="text-left p-3 font-medium whitespace-nowrap">Row</th>
                    <th className="text-left p-3 font-medium">Input</th>
                    <th className="text-left p-3 font-medium">Output</th>
                    <th className="text-left p-3 font-medium whitespace-nowrap">Latency</th>
                    <th className="text-left p-3 font-medium whitespace-nowrap">Pass/Fail</th>
                    {run.scorer_ids.map((sid) => (
                      <th key={sid} className="text-left p-3 font-medium whitespace-nowrap">
                        {scorerMap[String(sid)]?.name ?? `#${sid}`}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const traceOpen = item.id in expandedTraces;
                    const traceSpans = expandedTraces[item.id];

                    return (
                      <Fragment key={item.id}>
                        <tr className="border-t hover:bg-muted/20">
                          {/* Trace toggle */}
                          <td
                            className="p-3 text-muted-foreground cursor-pointer"
                            onClick={() => toggleTrace(item)}
                          >
                            {traceOpen ? (
                              <ChevronDown size={14} />
                            ) : (
                              <ChevronRight size={14} />
                            )}
                          </td>

                          {/* Row # links to case detail */}
                          <td className="p-3 font-mono text-xs">
                            <Link
                              href={`/runs/${run.id}/items/${item.id}`}
                              className="text-primary hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              #{item.row_id}
                            </Link>
                          </td>

                          <td className="p-3 max-w-[180px]">
                            <span className="text-xs text-muted-foreground">
                              {trunc(item.row_input, 80)}
                            </span>
                          </td>

                          <td className="p-3 max-w-[200px]">
                            <span className="text-xs">{trunc(item.output)}</span>
                          </td>

                          <td className="p-3 font-mono text-xs whitespace-nowrap">
                            {item.latency_ms != null ? `${item.latency_ms} ms` : "—"}
                          </td>

                          <td className="p-3">
                            {item.pass_fail == null ? (
                              <span className="text-muted-foreground text-xs">—</span>
                            ) : item.pass_fail ? (
                              <Badge variant="outline" className="text-green-600 border-green-600 text-xs">pass</Badge>
                            ) : (
                              <Badge variant="destructive" className="text-xs">fail</Badge>
                            )}
                          </td>

                          {run.scorer_ids.map((sid) => {
                            const res = item.scorer_results_json?.[String(sid)];
                            return (
                              <td key={sid} className="p-3 whitespace-nowrap">
                                {res ? (
                                  <span
                                    className="font-mono text-xs"
                                    title={res.reasoning}
                                  >
                                    {res.score.toFixed(2)}
                                    <span className="ml-1 text-muted-foreground">
                                      ({res.label})
                                    </span>
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground text-xs">—</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>

                        {traceOpen && (
                          <tr className="border-t bg-muted/10">
                            <td colSpan={5 + run.scorer_ids.length + 1} className="p-0">
                              {traceSpans === null ? (
                                <p className="text-xs text-muted-foreground p-3">
                                  Loading traces…
                                </p>
                              ) : (
                                <TraceViewer spans={traceSpans} />
                              )}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-3">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="text-sm px-3 py-1 rounded border hover:bg-muted disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="text-sm px-3 py-1 rounded border hover:bg-muted disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
