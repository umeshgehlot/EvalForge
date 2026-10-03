"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

// ── Types ─────────────────────────────────────────────────────────────────────

type Dataset = { id: number; name: string; description: string | null };

type BenchmarkMetric = {
  scorer_id: number | null;
  scorer_name: string;
  pass_rate: number | null;
  avg_score: number | null;
};

type BenchmarkPoint = {
  run_id: number;
  app_version_name: string;
  created_at: string;
  has_regression: boolean;
  metrics: BenchmarkMetric[];
};

// ── Constants ─────────────────────────────────────────────────────────────────

const LINE_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

// ── Custom dot (red + warning label on regression, normal otherwise) ──────────

function LineDot(props: {
  cx?: number; cy?: number;
  payload?: BenchmarkPoint & { [key: string]: unknown };
  color?: string;
}) {
  const { cx, cy, payload, color } = props;
  if (cx == null || cy == null) return null;
  if (payload?.has_regression) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={7} fill="#ef4444" stroke="#fff" strokeWidth={2} />
        <text x={cx} y={cy - 12} textAnchor="middle" fontSize={10} fill="#ef4444" fontWeight="bold">⚠</text>
      </g>
    );
  }
  return <circle cx={cx} cy={cy} r={4} fill={color ?? "#6366f1"} stroke="#fff" strokeWidth={1.5} />;
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({
  active, payload, label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: BenchmarkPoint & { [key: string]: unknown } }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload as BenchmarkPoint | undefined;
  return (
    <div className="rounded-lg border bg-background shadow-md p-3 text-sm min-w-[200px]">
      <p className="font-semibold mb-1">{label}</p>
      {point && (
        <p className="text-xs text-muted-foreground mb-2">
          {point.app_version_name}
          {point.has_regression && (
            <span className="ml-2 text-red-500 font-semibold">⚠ Regression</span>
          )}
        </p>
      )}
      {payload.map((p) => (
        <div key={p.name} className="flex justify-between gap-4">
          <span className="text-muted-foreground">{p.name}</span>
          <span className="font-mono font-semibold">{p.value.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BenchmarkPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [points, setPoints] = useState<BenchmarkPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet<Dataset[]>("/datasets").then(setDatasets);
  }, []);

  useEffect(() => {
    if (!selectedDatasetId) { setPoints([]); return; }
    setLoading(true);
    apiGet<BenchmarkPoint[]>(`/runs/benchmark?dataset_id=${selectedDatasetId}`)
      .then(setPoints)
      .finally(() => setLoading(false));
  }, [selectedDatasetId]);

  // Collect unique scorer names across all points
  const scorerNames: string[] = [];
  for (const pt of points) {
    for (const m of pt.metrics) {
      if (!scorerNames.includes(m.scorer_name)) scorerNames.push(m.scorer_name);
    }
  }

  // Build chart data: each point is a run, each scorer gets a column
  const chartData = points.map((pt, i) => {
    const row: Record<string, unknown> = {
      name: `Run #${pt.run_id}`,
      run_id: pt.run_id,
      app_version_name: pt.app_version_name,
      created_at: pt.created_at,
      has_regression: pt.has_regression,
    };
    for (const m of pt.metrics) {
      if (m.pass_rate != null) {
        row[m.scorer_name] = +(m.pass_rate * 100).toFixed(1);
      }
    }
    return row;
  });

  const regressionRuns = points.filter((p) => p.has_regression);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Benchmark</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track your RAG app's eval history over time — spot regressions before they ship.
        </p>
      </div>

      {/* Dataset selector */}
      <div className="flex flex-col gap-1.5 max-w-xs">
        <label className="text-xs font-medium text-muted-foreground">Dataset</label>
        <select
          value={selectedDatasetId}
          onChange={(e) => setSelectedDatasetId(e.target.value)}
          className="text-sm h-9 rounded-md border border-input bg-background px-3 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option value="">Select a dataset…</option>
          {datasets.map((d) => (
            <option key={d.id} value={String(d.id)}>
              #{d.id} — {d.name}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!loading && selectedDatasetId && points.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No completed runs found for this dataset.
        </p>
      )}

      {points.length > 0 && (
        <>
          {/* Regression warning */}
          {regressionRuns.length > 0 && (
            <div className="rounded-lg border border-red-300 bg-red-50 dark:bg-red-950/20 px-5 py-4 flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <p className="font-semibold text-sm text-red-700 dark:text-red-400">
                  Regression Detected
                </p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {regressionRuns.map((r) => `Run #${r.run_id} (${r.app_version_name})`).join(", ")}{" "}
                  showed a significant pass-rate drop vs the previous run on this dataset.
                </p>
              </div>
            </div>
          )}

          {/* Pass-rate chart */}
          <div>
            <h2 className="text-base font-semibold mb-3">Pass Rate Over Runs (%)</h2>
            <div className="rounded-lg border p-4">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData} margin={{ top: 8, right: 24, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {scorerNames.map((name, i) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      stroke={LINE_COLORS[i % LINE_COLORS.length]}
                      strokeWidth={2}
                      dot={(props) => (
                        <LineDot {...props} color={LINE_COLORS[i % LINE_COLORS.length]} />
                      )}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <p className="text-xs text-muted-foreground mt-2 text-center">
                ⚠ Red dot = regression (pass rate dropped &gt;5% from previous run)
              </p>
            </div>
          </div>

          {/* Run summary table */}
          <div>
            <h2 className="text-base font-semibold mb-3">Run History</h2>
            <div className="rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3 font-medium">Run</th>
                    <th className="text-left p-3 font-medium">App Version</th>
                    <th className="text-left p-3 font-medium">Date</th>
                    {scorerNames.map((n) => (
                      <th key={n} className="text-left p-3 font-medium whitespace-nowrap">
                        {n}
                      </th>
                    ))}
                    <th className="text-left p-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((pt) => (
                    <tr key={pt.run_id} className="border-t">
                      <td className="p-3 font-mono text-xs">
                        <Link
                          href={`/runs/${pt.run_id}`}
                          className="text-primary hover:underline"
                        >
                          #{pt.run_id}
                        </Link>
                      </td>
                      <td className="p-3 text-xs">{pt.app_version_name}</td>
                      <td className="p-3 text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(pt.created_at).toLocaleDateString()}
                      </td>
                      {scorerNames.map((name) => {
                        const m = pt.metrics.find((x) => x.scorer_name === name);
                        return (
                          <td key={name} className="p-3 font-mono text-xs">
                            {m?.pass_rate != null ? `${(m.pass_rate * 100).toFixed(1)}%` : "—"}
                          </td>
                        );
                      })}
                      <td className="p-3">
                        {pt.has_regression ? (
                          <Badge variant="destructive" className="text-xs">regression</Badge>
                        ) : (
                          <Badge variant="outline" className="text-green-600 border-green-600 text-xs">ok</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
