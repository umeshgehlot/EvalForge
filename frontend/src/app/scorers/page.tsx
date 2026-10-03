"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { apiDelete, apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CreateScorerDialog } from "@/components/scorers/CreateScorerDialog";
import { TestScorerDialog } from "@/components/scorers/TestScorerDialog";

type Scorer = {
  id: number;
  name: string;
  scorer_type: string;
  config_json: Record<string, unknown>;
  prompt_template: string | null;
};

const TYPE_META: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  exact_match:        { label: "Deterministic",  variant: "secondary" },
  keyword_coverage:   { label: "Deterministic",  variant: "secondary" },
  json_validity:      { label: "Deterministic",  variant: "secondary" },
  llm_judge:          { label: "LLM-as-Judge",   variant: "default" },
  ragas_faithfulness: { label: "Programmatic",   variant: "outline" },
};

const SCORER_DESCRIPTIONS: Record<string, string> = {
  exact_match:        "Case-insensitive string equality between output and expected.",
  keyword_coverage:   "% of expected keywords found in output.",
  json_validity:      "Checks whether output is parseable as valid JSON.",
  llm_judge:          "LLM rates answer correctness 1–5 with chain-of-thought reasoning.",
  ragas_faithfulness: "Decomposes answer into claims, verifies each against retrieved context.",
};

export default function ScorersPage() {
  const [scorers, setScorers] = useState<Scorer[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await apiGet<Scorer[]>("/scorers");
      setScorers(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete scorer "${name}"?`)) return;
    await apiDelete(`/scorers/${id}`);
    load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Scorers</h1>
          {!loading && (
            <p className="text-sm text-muted-foreground mt-1">
              {scorers.length} scorer{scorers.length !== 1 ? "s" : ""} configured
            </p>
          )}
        </div>
        <CreateScorerDialog onCreated={load} />
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : scorers.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          No scorers configured. Run{" "}
          <code className="bg-muted px-1 rounded text-xs">alembic upgrade head</code> to
          seed the 5 default scorers.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {scorers.map((s) => {
            const meta = TYPE_META[s.scorer_type] ?? { label: s.scorer_type, variant: "outline" as const };
            const description = SCORER_DESCRIPTIONS[s.scorer_type] ?? "";
            return (
              <div
                key={s.id}
                className="rounded-lg border p-5 flex items-start justify-between gap-4"
              >
                <div className="flex flex-col gap-1.5 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold">{s.name}</span>
                    <Badge variant={meta.variant}>{meta.label}</Badge>
                  </div>
                  {description && (
                    <p className="text-sm text-muted-foreground">{description}</p>
                  )}
                  <p className="text-xs font-mono text-muted-foreground">
                    {JSON.stringify(s.config_json)}
                  </p>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <TestScorerDialog
                    scorerId={s.id}
                    scorerName={s.name}
                    scorerType={s.scorer_type}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(s.id, s.name)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
