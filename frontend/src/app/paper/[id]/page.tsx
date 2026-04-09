"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiJson, markPaperOpen, patchPaper } from "@/lib/api";
import type { Paper } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function PaperDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { token } = useAuth();
  const qc = useQueryClient();
  const [kwInput, setKwInput] = React.useState("");

  const q = useQuery({
    queryKey: ["paper", id, token],
    enabled: !!token && Number.isFinite(id),
    queryFn: async () => {
      const p = await apiJson<Paper>(`/v1/papers/${id}`, { token: token! });
      return p;
    },
  });

  React.useEffect(() => {
    if (q.data?.keywords?.length) {
      setKwInput(q.data.keywords.map((k) => k.name).join(", "));
    }
  }, [q.data?.keywords]);

  const saveKeywords = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Not signed in");
      const names = kwInput
        .split(/[,;]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      return patchPaper(token, id, { keyword_names: names });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["paper", id] });
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  React.useEffect(() => {
    if (!token || !Number.isFinite(id)) return;
    markPaperOpen(token, id).catch(() => {});
  }, [token, id]);

  if (!token) {
    return (
      <div className="p-8">
        <p className="text-zinc-600">Please <Link href="/login" className="underline">sign in</Link>.</p>
      </div>
    );
  }

  if (q.isLoading) return <div className="p-8 text-zinc-600">Loading…</div>;
  if (q.isError || !q.data) {
    return (
      <div className="p-8">
        <p className="text-red-600">Could not load paper.</p>
        <Link href="/" className="mt-4 inline-block text-sm underline">
          Back
        </Link>
      </div>
    );
  }

  const p = q.data;
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between gap-4">
        <Button variant="outline" asChild>
          <Link href="/">← Library</Link>
        </Button>
        <Badge variant="secondary">{p.status.replace("_", " ")}</Badge>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">{p.title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-zinc-700">
          <p>
            <span className="font-medium text-zinc-900">Authors:</span> {p.authors || "—"}
          </p>
          {p.doi && (
            <p>
              <span className="font-medium text-zinc-900">DOI:</span> {p.doi}
            </p>
          )}
          {p.arxiv_id && (
            <p>
              <span className="font-medium text-zinc-900">arXiv:</span> {p.arxiv_id}
            </p>
          )}
          <div className="flex flex-wrap gap-1">
            {p.keywords.length === 0 ? (
              <span className="text-zinc-500">No keywords yet.</span>
            ) : (
              p.keywords.map((k) => (
                <Badge key={k.id} variant="outline">
                  {k.name}
                </Badge>
              ))
            )}
          </div>
          <div className="space-y-2 border-t border-zinc-100 pt-4">
            <Label htmlFor="kw">Keywords / tags (comma-separated)</Label>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <Input
                id="kw"
                value={kwInput}
                onChange={(e) => setKwInput(e.target.value)}
                placeholder="e.g. nlp, transformers, survey"
              />
              <Button type="button" variant="secondary" disabled={saveKeywords.isPending} onClick={() => saveKeywords.mutate()}>
                {saveKeywords.isPending ? "Saving…" : "Save tags"}
              </Button>
            </div>
            {saveKeywords.isError && (
              <p className="text-sm text-red-600">{(saveKeywords.error as Error).message}</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
