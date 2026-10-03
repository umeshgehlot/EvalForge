"use client";

import { useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiDelete, apiGet } from "@/lib/api";

type Row = {
  id: number;
  input: string;
  expected_output: string | null;
  context: string | null;
  tags: string | null;
  metadata_json: Record<string, unknown>;
};

type PaginatedRows = {
  total: number;
  page: number;
  limit: number;
  items: Row[];
};

const LIMIT = 50;

export function RowsTable({ datasetId }: { datasetId: number }) {
  const [data, setData] = useState<PaginatedRows | null>(null);
  const [page, setPage] = useState(1);
  const [tagFilter, setTagFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(LIMIT),
      });
      if (tagFilter) params.set("tags", tagFilter);
      const result = await apiGet<PaginatedRows>(
        `/datasets/${datasetId}/rows?${params}`
      );
      setData(result);
    } finally {
      setLoading(false);
    }
  }, [datasetId, page, tagFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(rowId: number) {
    await apiDelete(`/datasets/${datasetId}/rows/${rowId}`);
    load();
  }

  const totalPages = data ? Math.ceil(data.total / LIMIT) : 1;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Input
          placeholder="Filter by tags…"
          value={tagFilter}
          onChange={(e) => {
            setTagFilter(e.target.value);
            setPage(1);
          }}
          className="max-w-xs"
        />
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total} row{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <>
          <div className="rounded-md border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left p-3 font-medium w-[40%]">Input</th>
                  <th className="text-left p-3 font-medium w-[35%]">Expected Output</th>
                  <th className="text-left p-3 font-medium">Tags</th>
                  <th className="w-10 p-3" />
                </tr>
              </thead>
              <tbody>
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-muted-foreground">
                      No rows found.
                    </td>
                  </tr>
                )}
                {data?.items.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                  >
                    <td className="p-3 align-top">
                      <p className="line-clamp-3">{row.input}</p>
                    </td>
                    <td className="p-3 align-top">
                      <p className="line-clamp-3 text-muted-foreground">
                        {row.expected_output ?? "—"}
                      </p>
                    </td>
                    <td className="p-3 align-top">
                      {row.tags ? (
                        <Badge variant="secondary">{row.tags}</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="p-3 align-top">
                      <button
                        onClick={() => handleDelete(row.id)}
                        className="text-muted-foreground hover:text-destructive transition-colors"
                        title="Delete row"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
