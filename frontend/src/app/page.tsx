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
  fetchPaperPdf,
  fetchPapers,
  fetchStats,
  importPubMedPaper,
  patchPaper,
  searchDiscover,
  uploadPapers,
  type DiscoverResult,
  type Paper,
  type PaperStatus,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import "react-calendar-heatmap/dist/styles.css";

const PAGE_SIZE = 20;

function statusLabel(s: PaperStatus) {
  return s.replace("_", " ");
}

function formatAuthors(authors: string[]): string {
  if (authors.length === 0) return "Unknown authors";
  if (authors.length <= 3) return authors.join(", ");
  return `${authors.slice(0, 3).join(", ")} +${authors.length - 3} more`;
}

// ── Discover result row ────────────────────────────────────────────────────

function DiscoverRow({
  result,
  importing,
  onImport,
}: {
  result: DiscoverResult;
  importing: boolean;
  onImport: (pmid: string) => void;
}) {
  // Link priority: DOI (publisher page) > PMC (free full text) > PubMed abstract
  const primaryUrl = result.doi_url ?? result.pmc_url ?? result.pubmed_url;

  return (
    <div className="flex items-start justify-between gap-4 border-b border-zinc-100 py-4 last:border-0">
      <div className="min-w-0 flex-1">
        {/* Title — links to publisher page via DOI if available */}
        {primaryUrl ? (
          <a
            href={primaryUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-zinc-900 hover:underline"
          >
            {result.title}
          </a>
        ) : (
          <span className="font-medium text-zinc-900">{result.title}</span>
        )}

        {/* Authors + journal */}
        <p className="mt-0.5 truncate text-xs text-zinc-500">
          {formatAuthors(result.authors)}
          {result.journal && (
            <span className="ml-2 font-medium text-zinc-400">
              {result.journal}
              {result.published_date && ` · ${result.published_date.slice(0, 4)}`}
            </span>
          )}
        </p>

        {/* Abstract snippet */}
        {result.abstract && (
          <p className="mt-1 line-clamp-2 text-sm text-zinc-600">{result.abstract}</p>
        )}

        {/* Secondary links */}
        <div className="mt-1.5 flex flex-wrap gap-3 text-xs">
          {result.pmc_url && (
            <a
              href={result.pmc_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-blue-600 hover:underline"
            >
              Free full text (PMC)
            </a>
          )}
          {result.pubmed_url && (
            <a
              href={result.pubmed_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-400 hover:underline"
            >
              PubMed abstract
            </a>
          )}
          {result.doi && (
            <span className="text-zinc-300">DOI: {result.doi}</span>
          )}
        </div>
      </div>

      <div className="ml-3 shrink-0 pt-0.5">
        {result.in_library ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700">
            ✓ In library
          </span>
        ) : (
          <Button
            size="sm"
            variant="outline"
            disabled={importing}
            onClick={() => onImport(result.external_id)}
            className="whitespace-nowrap"
          >
            {importing ? "Adding…" : "Add to library"}
          </Button>
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function HomePage() {
  const { token, authReady, signOut } = useAuth();
  const qc = useQueryClient();

  // Shared search query
  const [q, setQ] = React.useState("");
  const [debouncedQ, setDebouncedQ] = React.useState("");
  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 400);
    return () => clearTimeout(t);
  }, [q]);

  // Tab state
  const [activeTab, setActiveTab] = React.useState<"library" | "discover">("library");

  // Discover: only fires on explicit submit (button or Enter), not on each keystroke
  const [discoverQ, setDiscoverQ] = React.useState("");
  const submitDiscover = React.useCallback(() => {
    const trimmed = q.trim();
    if (trimmed) {
      setDiscoverQ(trimmed);
      setDiscoverPage(0);
    }
  }, [q]);

  // Discover pagination
  const [discoverPage, setDiscoverPage] = React.useState(0);
  React.useEffect(() => {
    setDiscoverPage(0); // reset to page 1 on new query
  }, [discoverQ]);

  // Track which PMIDs are mid-import
  const [importingPmids, setImportingPmids] = React.useState<Set<string>>(new Set());

  const [linkUrl, setLinkUrl] = React.useState("");

  // ── Queries ──────────────────────────────────────────────────────────────

  const papersQuery = useQuery({
    queryKey: ["papers", token, debouncedQ],
    enabled: !!token,
    queryFn: () => fetchPapers(token!, { q: debouncedQ || undefined }),
  });

  const discoverQuery = useQuery({
    queryKey: ["discover", token, discoverQ, discoverPage],
    enabled: !!discoverQ && !!token,
    queryFn: () => searchDiscover(token!, discoverQ, PAGE_SIZE, discoverPage * PAGE_SIZE),
    staleTime: 60_000, // PubMed results are stable for 1 minute
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

  // ── Mutations ─────────────────────────────────────────────────────────────

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

  const [fetchPdfError, setFetchPdfError] = React.useState<Record<number, string>>({});
  const fetchPdf = useMutation({
    mutationFn: async (id: number) => {
      if (!token) throw new Error("Not signed in");
      return fetchPaperPdf(token, id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
    },
    onError: (err: Error, id: number) => {
      setFetchPdfError((prev) => ({ ...prev, [id]: err.message }));
    },
  });

  const importPaper = useMutation({
    mutationFn: async (pmid: string) => {
      if (!token) throw new Error("Not signed in");
      setImportingPmids((prev) => new Set(prev).add(pmid));
      try {
        return await importPubMedPaper(token, pmid);
      } finally {
        setImportingPmids((prev) => {
          const next = new Set(prev);
          next.delete(pmid);
          return next;
        });
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      // Re-fetch discover to update in_library flags
      qc.invalidateQueries({ queryKey: ["discover"] });
    },
  });

  // ── Heatmap helpers ───────────────────────────────────────────────────────

  const endDate = React.useMemo(() => new Date(), []);
  const startDate = React.useMemo(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 1);
    return d;
  }, []);

  const heatmapValues = React.useMemo(() => {
    return (heatmapQuery.data?.days ?? []).map((d) => ({ date: d.date, count: d.count }));
  }, [heatmapQuery.data]);

  // ── Auth guards ───────────────────────────────────────────────────────────

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

  // A paper can be auto-fetched if it has an arXiv ID or was imported from PubMed,
  // and doesn't already have a PDF stored.
  function canFetchPdf(p: Paper): boolean {
    return !!p.arxiv_id && !p.file_path;
  }

  const stats = statsQuery.data;
  const discoverData = discoverQuery.data;
  const totalPages = discoverData ? Math.ceil(discoverData.total / PAGE_SIZE) : 0;

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <h1 className="text-lg font-semibold text-zinc-900">Papertrail</h1>
          <Button variant="outline" size="sm" onClick={() => void signOut()}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">

        {/* Stats */}
        <section className="grid gap-4 md:grid-cols-2">
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
        </section>

        {/* ── Search section ─────────────────────────────────────────────── */}
        <section>
          <Card>
            <CardHeader className="pb-3">
              {/* Search input */}
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <svg
                    className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                  </svg>
                  <Input
                    className="pl-9 text-base"
                    placeholder={
                      activeTab === "library"
                        ? "Filter your library — title, DOI, authors, tags…"
                        : "Search PubMed — e.g. KRAS oncogene, RAS protein signaling…"
                    }
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && activeTab === "discover") submitDiscover();
                    }}
                  />
                </div>
                {activeTab === "discover" && (
                  <Button
                    onClick={submitDiscover}
                    disabled={!q.trim() || discoverQuery.isFetching}
                  >
                    {discoverQuery.isFetching ? "Searching…" : "Search PubMed"}
                  </Button>
                )}
              </div>

              {/* Tab switcher */}
              <div className="mt-3 flex gap-1 rounded-lg bg-zinc-100 p-1 w-fit">
                <button
                  onClick={() => setActiveTab("library")}
                  className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                    activeTab === "library"
                      ? "bg-white text-zinc-900 shadow-sm"
                      : "text-zinc-500 hover:text-zinc-700"
                  }`}
                >
                  My Library
                  {papersQuery.data && (
                    <span className="ml-2 rounded-full bg-zinc-200 px-1.5 py-0.5 text-xs text-zinc-600">
                      {papersQuery.data.length}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setActiveTab("discover")}
                  className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                    activeTab === "discover"
                      ? "bg-white text-zinc-900 shadow-sm"
                      : "text-zinc-500 hover:text-zinc-700"
                  }`}
                >
                  Discover on PubMed
                  {discoverData && activeTab === "discover" && (
                    <span className="ml-2 rounded-full bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                      {discoverData.total.toLocaleString()}
                    </span>
                  )}
                </button>
              </div>
            </CardHeader>

            <CardContent>
              {/* ── Library tab ──────────────────────────────────────────── */}
              {activeTab === "library" && (
                <div className="overflow-x-auto">
                  {papersQuery.isLoading && (
                    <p className="text-sm text-zinc-500">Loading papers…</p>
                  )}
                  {papersQuery.isError && (
                    <p className="text-sm text-red-600">Failed to load papers. Is the API running?</p>
                  )}
                  <table className="w-full min-w-[700px] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-zinc-200 text-zinc-600">
                        <th className="py-2 pr-4 font-medium">Title</th>
                        <th className="py-2 pr-4 font-medium">Status</th>
                        <th className="py-2 pr-4 font-medium">Keywords</th>
                        <th className="py-2 pr-4 font-medium">PDF</th>
                        <th className="py-2 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(papersQuery.data ?? []).map((p) => (
                        <tr key={p.id} className="border-b border-zinc-100">
                          <td className="max-w-xs py-2 pr-4">
                            <Link
                              href={`/paper/${p.id}`}
                              className="font-medium text-zinc-900 hover:underline"
                            >
                              {p.title}
                            </Link>
                          </td>
                          <td className="py-2 pr-4">
                            <select
                              className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs"
                              value={p.status}
                              onChange={(e) =>
                                patchStatus.mutate({
                                  id: p.id,
                                  status: e.target.value as PaperStatus,
                                })
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
                          <td className="py-2 pr-4">
                            {p.file_path ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
                                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                Saved
                              </span>
                            ) : canFetchPdf(p) ? (
                              <div>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-7 text-xs"
                                  disabled={fetchPdf.isPending && fetchPdf.variables === p.id}
                                  onClick={() => {
                                    setFetchPdfError((prev) => { const n = { ...prev }; delete n[p.id]; return n; });
                                    fetchPdf.mutate(p.id);
                                  }}
                                >
                                  {fetchPdf.isPending && fetchPdf.variables === p.id
                                    ? "Fetching…"
                                    : "⬇ Fetch PDF"}
                                </Button>
                                {fetchPdfError[p.id] && (
                                  <p className="mt-1 max-w-[160px] text-[10px] leading-tight text-red-600">
                                    {fetchPdfError[p.id]}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <span className="text-xs text-zinc-400">Upload manually</span>
                            )}
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
                    <p className="py-8 text-center text-sm text-zinc-500">
                      {debouncedQ
                        ? `No papers matching "${debouncedQ}" in your library.`
                        : "No papers yet. Upload a PDF or paste a link below."}
                    </p>
                  )}
                </div>
              )}

              {/* ── Discover tab ─────────────────────────────────────────── */}
              {activeTab === "discover" && (
                <div>
                  {/* Empty state — no query */}
                  {!debouncedQ && (
                    <div className="py-12 text-center">
                      <p className="text-sm font-medium text-zinc-600">
                        Search PubMed to discover papers
                      </p>
                      <p className="mt-1 text-sm text-zinc-400">
                        Try{" "}
                        <button
                          className="underline hover:text-zinc-600"
                          onClick={() => { setQ("KRAS oncogene"); setDiscoverQ("KRAS oncogene"); setDiscoverPage(0); }}
                        >
                          KRAS oncogene
                        </button>
                        {" "}or{" "}
                        <button
                          className="underline hover:text-zinc-600"
                          onClick={() => { setQ("RAS protein signaling"); setDiscoverQ("RAS protein signaling"); setDiscoverPage(0); }}
                        >
                          RAS protein signaling
                        </button>
                      </p>
                    </div>
                  )}

                  {/* Loading */}
                  {debouncedQ && discoverQuery.isLoading && (
                    <div className="flex items-center gap-2 py-8 text-sm text-zinc-500">
                      <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
                      </svg>
                      Searching PubMed…
                    </div>
                  )}

                  {/* Error */}
                  {discoverQuery.isError && (
                    <p className="py-6 text-sm text-red-600">
                      PubMed search failed:{" "}
                      {(discoverQuery.error as Error).message}
                    </p>
                  )}

                  {/* Results */}
                  {discoverData && discoverData.results.length > 0 && (
                    <>
                      {/* Result count + page info */}
                      <div className="mb-3 flex items-center justify-between text-xs text-zinc-500">
                        <span>
                          Showing{" "}
                          <span className="font-medium text-zinc-700">
                            {discoverPage * PAGE_SIZE + 1}–
                            {Math.min(
                              (discoverPage + 1) * PAGE_SIZE,
                              discoverData.total
                            )}
                          </span>{" "}
                          of{" "}
                          <span className="font-medium text-zinc-700">
                            {discoverData.total.toLocaleString()}
                          </span>{" "}
                          PubMed results
                        </span>
                        <span className="text-zinc-400">
                          Ranked by PubMed relevance
                        </span>
                      </div>

                      {/* Result rows */}
                      <div>
                        {discoverData.results.map((result) => (
                          <DiscoverRow
                            key={result.external_id}
                            result={result}
                            importing={importingPmids.has(result.external_id)}
                            onImport={(pmid) => importPaper.mutate(pmid)}
                          />
                        ))}
                      </div>

                      {/* Pagination */}
                      {totalPages > 1 && (
                        <div className="mt-4 flex items-center justify-between border-t border-zinc-100 pt-4">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={discoverPage === 0}
                            onClick={() => setDiscoverPage((p) => p - 1)}
                          >
                            ← Previous
                          </Button>
                          <span className="text-xs text-zinc-500">
                            Page {discoverPage + 1} of {totalPages}
                          </span>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={discoverPage >= totalPages - 1}
                            onClick={() => setDiscoverPage((p) => p + 1)}
                          >
                            Next →
                          </Button>
                        </div>
                      )}
                    </>
                  )}

                  {/* No results */}
                  {discoverData &&
                    discoverData.results.length === 0 &&
                    !discoverQuery.isLoading && (
                      <p className="py-8 text-center text-sm text-zinc-500">
                        No PubMed results for "{debouncedQ}". Try a broader search term.
                      </p>
                    )}

                  {/* Import error toast */}
                  {importPaper.isError && (
                    <p className="mt-3 text-sm text-red-600">
                      Import failed: {(importPaper.error as Error).message}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        {/* Activity + reading stats */}
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
                  <Badge
                    key={k.name}
                    variant="secondary"
                    className="cursor-pointer"
                    onClick={() => {
                      setQ(k.name);
                      setDiscoverQ(k.name);
                      setDiscoverPage(0);
                      setActiveTab("discover");
                    }}
                    title={`Search PubMed for "${k.name}"`}
                  >
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
                  <Link
                    key={p.id}
                    href={`/paper/${p.id}`}
                    className="block truncate text-zinc-800 hover:underline"
                  >
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
                  <Link
                    key={p.id}
                    href={`/paper/${p.id}`}
                    className="block truncate text-zinc-800 hover:underline"
                  >
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

        {/* Add papers */}
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
                <p className="mt-2 text-sm text-red-600">
                  {(uploadMutation.error as Error).message}
                </p>
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
      </main>
    </div>
  );
}
