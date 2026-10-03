"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

type Metric = {
  scorer_id: number | null;
  avg_score: number | null;
  pass_rate: number | null;
  p95_latency: number | null;
  total_cost: number | null;
};

type Scorer = { id: number; name: string };

type Props = {
  metrics: Metric[];
  scorers: Scorer[];
};

const BAR_COLORS = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4",
];

export function ScoreChart({ metrics, scorers }: Props) {
  if (!metrics.length) return null;

  const scorerMap = Object.fromEntries(scorers.map((s) => [String(s.id), s]));

  const data = metrics.map((m) => ({
    name: m.scorer_id
      ? (scorerMap[String(m.scorer_id)]?.name ?? `#${m.scorer_id}`)
      : "Overall",
    passRate: m.pass_rate != null ? +(m.pass_rate * 100).toFixed(1) : 0,
    avgScore: m.avg_score != null ? +(m.avg_score * 100).toFixed(1) : 0,
  }));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-medium mb-2 text-muted-foreground">
          Pass Rate (%) per Scorer
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(v: number) => [`${v}%`, "Pass Rate"]}
              contentStyle={{
                fontSize: 12,
                borderRadius: 6,
                border: "1px solid hsl(var(--border))",
              }}
            />
            <Bar dataKey="passRate" radius={[4, 4, 0, 0]}>
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={BAR_COLORS[i % BAR_COLORS.length]}
                  fillOpacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="text-sm font-medium mb-2 text-muted-foreground">
          Avg Score (%) per Scorer
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(v: number) => [`${v}%`, "Avg Score"]}
              contentStyle={{
                fontSize: 12,
                borderRadius: 6,
                border: "1px solid hsl(var(--border))",
              }}
            />
            <Bar dataKey="avgScore" radius={[4, 4, 0, 0]}>
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={BAR_COLORS[i % BAR_COLORS.length]}
                  fillOpacity={0.5}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
