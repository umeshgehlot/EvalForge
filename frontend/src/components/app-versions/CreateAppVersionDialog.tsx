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

export function CreateAppVersionDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [modelName, setModelName] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [retrieverConfig, setRetrieverConfig] = useState("{}");
  const [gitNote, setGitNote] = useState("");

  function reset() {
    setName("");
    setModelName("");
    setEndpointUrl("");
    setPromptTemplate("");
    setRetrieverConfig("{}");
    setGitNote("");
    setError("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    let parsedConfig: unknown = {};
    try {
      parsedConfig = JSON.parse(retrieverConfig || "{}");
    } catch {
      setError("Retriever config must be valid JSON.");
      return;
    }

    setLoading(true);
    try {
      await apiPost("/app-versions", {
        name: name.trim(),
        model_name: modelName.trim(),
        endpoint_url: endpointUrl.trim(),
        prompt_template: promptTemplate.trim() || null,
        retriever_config: parsedConfig,
        git_note: gitNote.trim() || null,
      });
      setOpen(false);
      reset();
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create app version");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus size={14} className="mr-2" />
          Register Version
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Register App Version</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="av-name">Name *</Label>
            <Input
              id="av-name"
              placeholder="e.g. v1 - GPT-4o-mini + pgvector"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="av-model">Model Name *</Label>
            <Input
              id="av-model"
              placeholder="e.g. gpt-4o-mini"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="av-url">Endpoint URL *</Label>
            <Input
              id="av-url"
              placeholder="e.g. http://localhost:8002/ask"
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">
              The eval runner will POST{" "}
              <code className="bg-muted px-1 rounded">{"{ question }"}</code> to
              this URL and expect{" "}
              <code className="bg-muted px-1 rounded">
                {"{ answer, retrieved_chunks, latency_ms, tokens }"}
              </code>
              .
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="av-prompt">Prompt Template (optional)</Label>
            <Textarea
              id="av-prompt"
              placeholder="The system prompt or prompt template used by this app version…"
              value={promptTemplate}
              onChange={(e) => setPromptTemplate(e.target.value)}
              rows={3}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="av-retriever">Retriever Config (JSON, optional)</Label>
            <Textarea
              id="av-retriever"
              placeholder='{"top_k": 5, "index": "pgvector"}'
              value={retrieverConfig}
              onChange={(e) => setRetrieverConfig(e.target.value)}
              rows={2}
              className="font-mono text-xs"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="av-git">Git Note (optional)</Label>
            <Input
              id="av-git"
              placeholder="e.g. commit sha or branch name"
              value={gitNote}
              onChange={(e) => setGitNote(e.target.value)}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" disabled={!name.trim() || !modelName.trim() || !endpointUrl.trim() || loading}>
            {loading ? "Registering…" : "Register"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
