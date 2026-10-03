"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { apiDelete, apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CreateAppVersionDialog } from "@/components/app-versions/CreateAppVersionDialog";

type AppVersion = {
  id: number;
  name: string;
  model_name: string;
  endpoint_url: string | null;
  prompt_template: string | null;
  retriever_config: Record<string, unknown>;
  git_note: string | null;
  created_at: string;
};

export default function AppVersionsPage() {
  const [versions, setVersions] = useState<AppVersion[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await apiGet<AppVersion[]>("/app-versions");
      setVersions(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete app version "${name}"? Any eval runs referencing it will be orphaned.`))
      return;
    await apiDelete(`/app-versions/${id}`);
    load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">App Versions</h1>
          {!loading && (
            <p className="text-sm text-muted-foreground mt-1">
              {versions.length} version{versions.length !== 1 ? "s" : ""} registered
            </p>
          )}
        </div>
        <CreateAppVersionDialog onCreated={load} />
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : versions.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          No app versions registered yet. Register your first to start running evals.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {versions.map((av) => (
            <div
              key={av.id}
              className="rounded-lg border p-5 flex items-start justify-between gap-4"
            >
              <div className="flex flex-col gap-2 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold">{av.name}</span>
                  <Badge variant="secondary">{av.model_name}</Badge>
                  {av.git_note && (
                    <Badge variant="outline" className="font-mono text-xs">
                      {av.git_note}
                    </Badge>
                  )}
                </div>

                {av.endpoint_url && (
                  <p className="text-xs text-muted-foreground font-mono truncate">
                    {av.endpoint_url}
                  </p>
                )}

                {av.prompt_template && (
                  <p className="text-xs text-muted-foreground line-clamp-2 italic">
                    {av.prompt_template}
                  </p>
                )}

                <p className="text-xs text-muted-foreground">
                  Registered {new Date(av.created_at).toLocaleDateString()}
                </p>
              </div>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDelete(av.id, av.name)}
                className="text-muted-foreground hover:text-destructive shrink-0"
              >
                <Trash2 size={14} />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
