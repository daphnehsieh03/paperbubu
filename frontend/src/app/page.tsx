"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import CalendarHeatmap from "react-calendar-heatmap";
import { Tooltip } from "react-tooltip";
import * as React from "react";
import { useDropzone } from "react-dropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createPaperFromUrl,
  deletePaper,
  fetchHeatmap,
  fetchPapers,
  fetchStats,
  patchPaper,
  uploadPapers,
  type Paper,
  type PaperStatus,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import "react-calendar-heatmap/dist/styles.css";

function statusLabel(s: PaperStatus) {
  return s.replace("_", " ");
}

export default function HomePage() {
  const { token, authReady, signOut } = useAuth();
  const qc = useQueryClient();
  const [q, setQ] = React.useState("");
  const [debouncedQ, setDebouncedQ] = React.useState("");
  const [linkUrl, setLinkUrl] = React.useState("");

  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const papersQuery = useQuery({
    queryKey: ["papers", token, debouncedQ],
    enabled: !!token,
    queryFn: () => fetchPapers(token!, { q: debouncedQ || undefined }),
  });

  const heatmapQuery = useQuery({
    queryKey: ["heatmap", token],
    enabled: !!token,
    queryFn: () => fetchHeatmap(token!),
  });

  const statsQuery = useQuery({
    queryKey: ["stats", token],
    enabled: !!token,
    queryFn: () => fetchStats(token!),
  });

  const linkImport = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Not signed in");
      return createPaperFromUrl(token, linkUrl.trim());
    },
    onSuccess: () => {
      setLinkUrl("");
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      if (!token) throw new Error("Not signed in");
      return uploadPapers(token, files);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const onDrop = React.useCallback(
    (accepted: File[]) => {
      if (accepted.length) uploadMutation.mutate(accepted);
    },
    [uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  });

  const patchStatus = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: PaperStatus }) => {
      if (!token) throw new Error("Not signed in");
      return patchPaper(token, id, { status });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["heatmap"] });
    },
  });

  const removePaper = useMutation({
    mutationFn: async (id: number) => {
      if (!token) throw new Error("Not signed in");
      await deletePaper(token, id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["heatmap"] });
    },
  });

  const endDate = React.useMemo(() => new Date(), []);
  const startDate = React.useMemo(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 1);
    return d;
  }, []);

  const heatmapValues = React.useMemo(() => {
    const days = heatmapQuery.data?.days ?? [];
    return days.map((d) => ({ date: d.date, count: d.count }));
  }, [heatmapQuery.data]);

  if (!authReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 text-zinc-600">
        Loading…
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-50 p-6">
        <h1 className="text-2xl font-semibold text-zinc-900">Research Paper Tracker</h1>
        <p className="max-w-md text-center text-zinc-600">
          Sign in to import PDFs, track reading, and see your activity heatmap.
        </p>
        <Button asChild>
          <Link href="/login">Sign in or register</Link>
        </Button>
      </div>
    );
  }

  const stats = statsQuery.data;

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <h1 className="text-lg font-semibold text-zinc-900">Papertrail</h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void signOut()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
        <section className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-600">Papers completed</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{stats?.total_read ?? "—"}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-600">Keywords in use</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{stats?.active_keyword_count ?? "—"}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-600">Library search</CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                placeholder="Title, DOI, authors, tags…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Reading activity</CardTitle>
              <p className="text-sm text-zinc-600">Completions per day (UTC)</p>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <CalendarHeatmap
                startDate={startDate}
                endDate={endDate}
                values={heatmapValues}
                classForValue={(v) => {
                  if (!v || !v.count) return "color-empty";
                  if (v.count >= 4) return "color-github-4";
                  if (v.count >= 3) return "color-github-3";
                  if (v.count >= 2) return "color-github-2";
                  return "color-github-1";
                }}
                tooltipDataAttrs={(v) => {
                  const date = v?.date ?? "";
                  const count = v?.count ?? 0;
                  return {
                    "data-tooltip-id": "heatmap-tip",
                    "data-tooltip-content": date ? `${date}: ${count} completed` : "",
                  };
                }}
              />
              <Tooltip id="heatmap-tip" />
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Top keywords</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {(stats?.top_keywords ?? []).length === 0 && (
                  <p className="text-sm text-zinc-500">Add keywords when editing a paper.</p>
                )}
                {(stats?.top_keywords ?? []).map((k) => (
                  <Badge key={k.name} variant="secondary">
                    {k.name} ({k.count})
                  </Badge>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Recently read</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {(stats?.recently_read ?? []).map((p: Paper) => (
                  <Link key={p.id} href={`/paper/${p.id}`} className="block truncate text-zinc-800 hover:underline">
                    {p.title}
                  </Link>
                ))}
                {(stats?.recently_read ?? []).length === 0 && (
                  <p className="text-zinc-500">Mark a paper completed to see it here.</p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Recently opened</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {(stats?.recently_opened ?? []).map((p: Paper) => (
                  <Link key={p.id} href={`/paper/${p.id}`} className="block truncate text-zinc-800 hover:underline">
                    {p.title}
                  </Link>
                ))}
                {(stats?.recently_opened ?? []).length === 0 && (
                  <p className="text-zinc-500">Open a paper detail page to populate this list.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Upload PDFs</CardTitle>
              <p className="text-sm text-zinc-600">Drag and drop or click to select (multiple allowed)</p>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`cursor-pointer rounded-lg border-2 border-dashed p-10 text-center text-sm transition-colors ${
                  isDragActive ? "border-zinc-900 bg-zinc-100" : "border-zinc-300 bg-zinc-50"
                }`}
              >
                <input {...getInputProps()} />
                {uploadMutation.isPending ? "Uploading…" : "Drop PDFs here, or click to browse"}
              </div>
              {uploadMutation.isError && (
                <p className="mt-2 text-sm text-red-600">{(uploadMutation.error as Error).message}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Import from link</CardTitle>
              <p className="text-sm text-zinc-600">Paste an arXiv or DOI URL</p>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="url">URL</Label>
                <Input
                  id="url"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="https://arxiv.org/abs/..."
                />
              </div>
              <Button
                type="button"
                disabled={!linkUrl.trim() || linkImport.isPending}
                onClick={() => linkImport.mutate()}
              >
                {linkImport.isPending ? "Importing…" : "Import"}
              </Button>
              {linkImport.isError && (
                <p className="text-sm text-red-600">{(linkImport.error as Error).message}</p>
              )}
            </CardContent>
          </Card>
        </section>

        <section>
          <Card>
            <CardHeader>
              <CardTitle>Paper library</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              {papersQuery.isLoading && <p className="text-sm text-zinc-500">Loading papers…</p>}
              {papersQuery.isError && (
                <p className="text-sm text-red-600">Failed to load papers. Is the API running?</p>
              )}
              <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 text-zinc-600">
                    <th className="py-2 pr-4 font-medium">Title</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium">Keywords</th>
                    <th className="py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(papersQuery.data ?? []).map((p) => (
                    <tr key={p.id} className="border-b border-zinc-100">
                      <td className="max-w-xs py-2 pr-4">
                        <Link href={`/paper/${p.id}`} className="font-medium text-zinc-900 hover:underline">
                          {p.title}
                        </Link>
                      </td>
                      <td className="py-2 pr-4">
                        <select
                          className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs"
                          value={p.status}
                          onChange={(e) =>
                            patchStatus.mutate({ id: p.id, status: e.target.value as PaperStatus })
                          }
                        >
                          <option value="to_read">{statusLabel("to_read")}</option>
                          <option value="reading">{statusLabel("reading")}</option>
                          <option value="completed">{statusLabel("completed")}</option>
                        </select>
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex flex-wrap gap-1">
                          {p.keywords.map((k) => (
                            <Badge key={k.id} variant="outline" className="text-[10px]">
                              {k.name}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="py-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => {
                            if (confirm("Delete this paper?")) removePaper.mutate(p.id);
                          }}
                        >
                          Delete
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(papersQuery.data ?? []).length === 0 && !papersQuery.isLoading && (
                <p className="py-6 text-center text-sm text-zinc-500">No papers yet. Upload a PDF or paste a link.</p>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
