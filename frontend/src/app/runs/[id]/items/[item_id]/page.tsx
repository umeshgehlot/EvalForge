"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

// ── Types ─────────────────────────────────────────────────────────────────────

type RunItem = {
  id: number;
  run_id: number;
  row_id: number;
  row_input: string;
  row_expected: string | null;
  row_context: string | null;
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
  retrieved_chunks_json: Array<{ text: string; source: string; score: number | null }>;
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

const SPAN_COLORS: Record<string, string> = {
  "rag.total":     "bg-blue-500",
  "rag.retrieval": "bg-emerald-500",
  "rag.generate":  "bg-violet-500",
};
function spanColor(name: string) {
  return SPAN_COLORS[name] ?? "bg-orange-400";
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string | null;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <div className="rounded-md border bg-muted/30 p-3 min-h-[60px]">
        {value ? (
          <p className={`text-sm whitespace-pre-wrap ${mono ? "font-mono text-xs" : ""}`}>
            {value}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground italic">—</p>
        )}
      </div>
    </div>
  );
}

function TraceViewer({ spans }: { spans: TraceSpan[] }) {
  if (!spans.length)
    return <p className="text-sm text-muted-foreground italic">No trace spans recorded.</p>;

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
    <div className="flex flex-col gap-2">
      <p className="text-xs text-muted-foreground">
        Total duration: {duration} ms
      </p>
      {spans.map((span) => {
        const left = (((span.start_ms ?? tMin) - tMin) / duration) * 100;
        const width = Math.max(
          0.5,
          (((span.end_ms ?? tMax) - (span.start_ms ?? tMin)) / duration) * 100
        );
        const d = depth(span);
        const spanDuration = (span.end_ms ?? 0) - (span.start_ms ?? 0);

        // Format metadata for display
        const meta = span.metadata_json;
        const metaEntries = Object.entries(meta).filter(([, v]) => v !== undefined);

        return (
          <div key={span.id} className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <div
                className="text-xs font-mono text-foreground whitespace-nowrap w-36 shrink-0"
                style={{ paddingLeft: `${d * 16}px` }}
              >
                {span.span_name}
              </div>
              <div className="relative flex-1 h-6 bg-muted rounded overflow-hidden">
                <div
                  className={`absolute h-full rounded ${spanColor(span.span_name)} opacity-80`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                />
              </div>
              <span className="text-xs font-mono text-muted-foreground w-20 text-right shrink-0">
                {spanDuration} ms
              </span>
            </div>
            {/* Span metadata */}
            {metaEntries.length > 0 && (
              <div
                className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground"
                style={{ paddingLeft: `${d * 16 + 144 + 8}px` }}
              >
                {metaEntries.map(([k, v]) => (
                  <span key={k}>
                    <span className="font-mono">{k}</span>:{" "}
                    <span className="font-mono">{String(v)}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Section wrapper ────────────────────────────────────────────────────────────

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-base font-semibold border-b pb-1">{title}</h2>
      {children}
    </section>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CaseDetailPage() {
  const { id: runId, item_id: itemId } = useParams<{
    id: string;
    item_id: string;
  }>();

  const [item, setItem] = useState<RunItem | null>(null);
  const [scorers, setScorers] = useState<Scorer[]>([]);
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiGet<RunItem>(`/runs/${runId}/items/${itemId}`),
      apiGet<Scorer[]>("/scorers"),
      apiGet<TraceSpan[]>(`/runs/${runId}/items/${itemId}/traces`),
    ]).then(([i, s, sp]) => {
      setItem(i);
      setScorers(s);
      setSpans(sp);
      setLoading(false);
    });
  }, [runId, itemId]);

  if (loading)
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!item)
    return <p className="text-sm text-destructive">Item not found.</p>;

  const scorerMap = Object.fromEntries(scorers.map((s) => [String(s.id), s]));

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/runs" className="hover:underline">Runs</Link>
        <span>›</span>
        <Link href={`/runs/${runId}`} className="hover:underline">
          Run #{runId}
        </Link>
        <span>›</span>
        <span>Row #{item.row_id}</span>
      </div>

      {/* Title + meta */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">
            Case Detail — Row #{item.row_id}
          </h1>
          {item.pass_fail == null ? null : item.pass_fail ? (
            <Badge variant="outline" className="text-green-600 border-green-600">
              pass
            </Badge>
          ) : (
            <Badge variant="destructive">fail</Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          {item.latency_ms != null && `${item.latency_ms} ms · `}
          {item.token_in != null &&
            `${item.token_in} tokens in · ${item.token_out} tokens out`}
          {item.row_tags && ` · tags: ${item.row_tags}`}
        </p>
      </div>

      {/* Input / Expected / Output */}
      <Section title="Input & Output">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Input" value={item.row_input} />
          <Field label="Expected Output" value={item.row_expected} />
        </div>
        <Field label="Model Output" value={item.output} />
        {item.row_context && (
          <Field label="Context" value={item.row_context} mono />
        )}
      </Section>

      {/* Scorer results */}
      {Object.keys(item.scorer_results_json).length > 0 && (
        <Section title="Scorer Results">
          <div className="flex flex-col gap-3">
            {Object.entries(item.scorer_results_json).map(([sid, result]) => {
              const scorer = scorerMap[sid];
              return (
                <div
                  key={sid}
                  className="rounded-lg border p-4 flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-sm">
                      {scorer?.name ?? `Scorer #${sid}`}
                    </p>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">
                        {result.score.toFixed(3)}
                      </span>
                      {result.passed ? (
                        <Badge
                          variant="outline"
                          className="text-green-600 border-green-600 text-xs"
                        >
                          pass
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="text-xs">
                          fail
                        </Badge>
                      )}
                    </div>
                  </div>
                  {result.reasoning && (
                    <p className="text-sm text-muted-foreground">
                      {result.reasoning}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* Trace waterfall */}
      <Section title="Trace">
        <TraceViewer spans={spans} />
      </Section>

      {/* Retrieved chunks */}
      {item.retrieved_chunks_json?.length > 0 && (
        <Section title={`Retrieved Chunks (${item.retrieved_chunks_json.length})`}>
          <div className="flex flex-col gap-3">
            {item.retrieved_chunks_json.map((chunk, i) => (
              <div key={i} className="rounded-lg border p-3 flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-mono">{chunk.source}</span>
                  {chunk.score != null && (
                    <span className="font-mono">
                      score: {chunk.score.toFixed(4)}
                    </span>
                  )}
                </div>
                <p className="text-sm leading-relaxed">{chunk.text}</p>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
