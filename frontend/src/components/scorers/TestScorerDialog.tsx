"use client";

import { useState } from "react";
import { FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { apiPost } from "@/lib/api";

type TestResult = {
  score: number;
  passed: boolean;
  label: string;
  reasoning: string;
  raw: Record<string, unknown>;
};

export function TestScorerDialog({
  scorerId,
  scorerName,
  scorerType,
}: {
  scorerId: number;
  scorerName: string;
  scorerType: string;
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [expected, setExpected] = useState("");
  const [chunks, setChunks] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState("");

  const needsChunks = scorerType === "ragas_faithfulness";
  const needsExpected = ["exact_match", "keyword_coverage", "llm_judge"].includes(scorerType);

  async function handleTest() {
    setError("");
    setResult(null);

    let retrieved_chunks: unknown[] | undefined;
    if (chunks.trim()) {
      try {
        retrieved_chunks = JSON.parse(chunks);
      } catch {
        setError("Retrieved chunks must be valid JSON array.");
        return;
      }
    }

    setLoading(true);
    try {
      const res = await apiPost<TestResult>(`/scorers/${scorerId}/test`, {
        input,
        output,
        expected: expected.trim() || null,
        retrieved_chunks: retrieved_chunks ?? null,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-muted-foreground">
          <FlaskConical size={13} className="mr-1" />
          Test
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto max-w-2xl">
        <DialogHeader>
          <DialogTitle>Test — {scorerName}</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-2">
            <Label>Input (question)</Label>
            <Textarea
              placeholder="What is the transformer architecture?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={2}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label>Output (model answer)</Label>
            <Textarea
              placeholder="The transformer is…"
              value={output}
              onChange={(e) => setOutput(e.target.value)}
              rows={3}
            />
          </div>

          {needsExpected && (
            <div className="flex flex-col gap-2">
              <Label>Expected Output (reference)</Label>
              <Textarea
                placeholder="The correct answer is…"
                value={expected}
                onChange={(e) => setExpected(e.target.value)}
                rows={2}
              />
            </div>
          )}

          {needsChunks && (
            <div className="flex flex-col gap-2">
              <Label>Retrieved Chunks (JSON array)</Label>
              <Textarea
                placeholder='[{"text": "The transformer uses attention...", "source": "transformers.txt"}]'
                value={chunks}
                onChange={(e) => setChunks(e.target.value)}
                rows={3}
                className="font-mono text-xs"
              />
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button onClick={handleTest} disabled={!input || !output || loading}>
            {loading ? "Running scorer…" : "Run Scorer"}
          </Button>

          {result && (
            <div className="rounded-lg border p-4 flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <Badge variant={result.passed ? "default" : "destructive"}>
                  {result.label.toUpperCase()}
                </Badge>
                <span className="font-mono text-sm font-semibold">
                  {result.score.toFixed(3)}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{result.reasoning}</p>
              {Object.keys(result.raw).length > 0 && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground">Raw output</summary>
                  <pre className="mt-2 bg-muted p-2 rounded overflow-auto text-xs">
                    {JSON.stringify(result.raw, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
