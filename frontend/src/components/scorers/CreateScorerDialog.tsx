"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiPost } from "@/lib/api";

const SCORER_TYPES = [
  { value: "exact_match",        label: "Exact Match",            hint: '{"threshold": 1.0}' },
  { value: "keyword_coverage",   label: "Keyword Coverage",       hint: '{"threshold": 0.7}' },
  { value: "json_validity",      label: "JSON Validity",          hint: '{"threshold": 1.0}' },
  { value: "llm_judge",          label: "LLM Correctness Judge",  hint: '{"model": "gpt-4o-mini", "threshold": 0.6}' },
  { value: "ragas_faithfulness", label: "RAGAS Faithfulness",     hint: '{"model": "gpt-4o-mini", "threshold": 0.7}' },
];

export function CreateScorerDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [scorerType, setScorerType] = useState("exact_match");
  const [configJson, setConfigJson] = useState('{"threshold": 1.0}');
  const [promptTemplate, setPromptTemplate] = useState("");

  function handleTypeChange(val: string) {
    setScorerType(val);
    const hint = SCORER_TYPES.find((t) => t.value === val)?.hint ?? "{}";
    setConfigJson(hint);
  }

  function reset() {
    setName("");
    setScorerType("exact_match");
    setConfigJson('{"threshold": 1.0}');
    setPromptTemplate("");
    setError("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    let config: unknown;
    try {
      config = JSON.parse(configJson || "{}");
    } catch {
      setError("Config must be valid JSON.");
      return;
    }

    setLoading(true);
    try {
      await apiPost("/scorers", {
        name: name.trim(),
        scorer_type: scorerType,
        config_json: config,
        prompt_template: promptTemplate.trim() || null,
      });
      setOpen(false);
      reset();
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create scorer");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus size={14} className="mr-2" />
          Add Scorer
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Custom Scorer</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="sc-name">Name</Label>
            <Input
              id="sc-name"
              placeholder="e.g. Strict Keyword Match"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="sc-type">Scorer Type</Label>
            <select
              id="sc-type"
              value={scorerType}
              onChange={(e) => handleTypeChange(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {SCORER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="sc-config">Config (JSON)</Label>
            <Textarea
              id="sc-config"
              value={configJson}
              onChange={(e) => setConfigJson(e.target.value)}
              rows={2}
              className="font-mono text-xs"
            />
          </div>

          {(scorerType === "llm_judge") && (
            <div className="flex flex-col gap-2">
              <Label htmlFor="sc-prompt">Custom Judge Prompt (optional)</Label>
              <Textarea
                id="sc-prompt"
                placeholder="Override the default judge prompt…"
                value={promptTemplate}
                onChange={(e) => setPromptTemplate(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" disabled={!name.trim() || loading}>
            {loading ? "Creating…" : "Create"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
