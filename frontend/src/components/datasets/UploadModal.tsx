"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiUpload } from "@/lib/api";

export function UploadModal({
  datasetId,
  onUploaded,
}: {
  datasetId: number;
  onUploaded: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ inserted: number } | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const res = await apiUpload<{ inserted: number }>(
        `/datasets/${datasetId}/rows/upload`,
        file
      );
      setResult(res);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  function handleClose() {
    setOpen(false);
    setFile(null);
    setResult(null);
    setError("");
  }

  return (
    <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : handleClose())}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Upload size={14} className="mr-2" />
          Upload CSV
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload Dataset Rows</DialogTitle>
        </DialogHeader>

        {result ? (
          <div className="flex flex-col gap-4 py-2">
            <p className="text-sm font-medium text-green-600">
              ✓ Inserted {result.inserted} rows successfully.
            </p>
            <Button onClick={handleClose}>Done</Button>
          </div>
        ) : (
          <div className="flex flex-col gap-4 py-2">
            <p className="text-xs text-muted-foreground leading-relaxed">
              CSV columns:{" "}
              <code className="bg-muted px-1 rounded text-xs">
                input, expected_output, context, tags, difficulty
              </code>
              <br />
              Also accepts JSONL or JSON array format.
            </p>

            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => inputRef.current?.click()}
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-muted/50 transition-colors select-none"
            >
              {file ? (
                <p className="text-sm font-medium">{file.name}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Drag &amp; drop a file here, or click to select
                </p>
              )}
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.json,.jsonl"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button onClick={handleUpload} disabled={!file || loading}>
              {loading ? "Uploading…" : "Upload"}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
