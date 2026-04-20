export const apiBase = () => process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const base = apiBase;

export type PaperStatus = "to_read" | "reading" | "completed";

export type Paper = {
  id: number;
  title: string;
  authors: string;
  doi: string | null;
  arxiv_id: string | null;
  status: PaperStatus;
  file_path: string | null;
  created_at: string;
  completed_at: string | null;
  last_opened_at: string | null;
  user_id: number;
  keywords: { id: number; name: string }[];
};

export type HeatmapDay = { date: string; count: number };

export type MeStats = {
  total_read: number;
  active_keyword_count: number;
  top_keywords: { name: string; count: number }[];
  recently_read: Paper[];
  recently_opened: Paper[];
};

type AuthBridge = {
  getAccessToken: () => string | null;
  setAccessToken: (t: string | null) => void;
};

let authBridge: AuthBridge | null = null;

export function configureAuthApi(bridge: AuthBridge) {
  authBridge = bridge;
}

function authHeaders(token: string | null): HeadersInit {
  const h: Record<string, string> = {};
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function tryRefresh(): Promise<string | null> {
  const res = await fetch(`${base()}/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { access_token: string };
  authBridge?.setAccessToken(data.access_token);
  return data.access_token;
}

export async function apiJson<T>(
  path: string,
  opts: RequestInit & { token?: string | null } = {},
  retryAfterRefresh = true
): Promise<T> {
  const { token, ...init } = opts;
  const url = `${base()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      ...authHeaders(token ?? null),
      ...(init.headers as Record<string, string>),
    },
  });
  if (res.status === 401 && retryAfterRefresh && token) {
    const newTok = await tryRefresh();
    if (newTok) {
      return apiJson<T>(path, { ...opts, token: newTok }, false);
    }
  }
  if (!res.ok) {
    const text = await res.text();
    let message = text || res.statusText;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) {
        const first = body.detail[0];
        if (first && typeof first === "object" && "msg" in first && typeof first.msg === "string") {
          message = first.msg;
        }
      }
    } catch {
      /* use raw text */
    }
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function register(email: string, username: string, password: string) {
  return apiJson<{ access_token: string }>("/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, username, password }),
  });
}

export async function login(identifier: string, password: string) {
  return apiJson<{ access_token: string }>("/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, password }),
  });
}

export async function logoutSession(token: string | null) {
  await fetch(`${base()}/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { ...authHeaders(token) },
  });
}

export async function logoutAllDevices(token: string) {
  return apiJson<{ ok: boolean }>("/v1/auth/logout-all", { method: "POST", token });
}

export async function fetchPapers(
  token: string,
  params: { q?: string; status?: PaperStatus } = {}
) {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.status) sp.set("status", params.status);
  const q = sp.toString();
  return apiJson<Paper[]>(`/v1/papers${q ? `?${q}` : ""}`, { token });
}

export async function createPaperFromUrl(token: string, url: string) {
  return apiJson<Paper>("/v1/papers", {
    method: "POST",
    token,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function uploadPapers(token: string, files: File[]) {
  const fd = new FormData();
  for (const f of files) fd.append("file", f);
  const res = await fetch(`${base()}/v1/papers`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(token),
    body: fd,
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data as Paper | Paper[];
}

export async function patchPaper(
  token: string,
  id: number,
  body: Partial<{ status: PaperStatus; title: string; keyword_names: string[] }>
) {
  return apiJson<Paper>(`/v1/papers/${id}`, {
    method: "PATCH",
    token,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deletePaper(token: string, id: number) {
  return apiJson<void>(`/v1/papers/${id}`, { method: "DELETE", token });
}

export async function markPaperOpen(token: string, id: number) {
  return apiJson<Paper>(`/v1/papers/${id}/open`, { method: "POST", token });
}

export async function fetchHeatmap(token: string) {
  return apiJson<{ days: HeatmapDay[] }>("/v1/me/heatmap", { token });
}

export async function fetchStats(token: string) {
  return apiJson<MeStats>("/v1/me/stats", { token });
}

// ── PubMed discovery ───────────────────────────────────────────────────────

export type DiscoverResult = {
  source: string;
  external_id: string; // PMID
  title: string;
  authors: string[];
  abstract: string | null;
  journal: string | null;
  published_date: string | null;
  doi: string | null;
  doi_url: string | null;   // https://doi.org/{doi} — publisher landing page
  pmc_url: string | null;   // PMC full text if open-access copy exists
  pubmed_url: string | null;
  in_library: boolean;
};

export type DiscoverResponse = {
  query: string;
  source: string;
  total: number;
  offset: number;
  results: DiscoverResult[];
};

export async function searchDiscover(
  token: string,
  q: string,
  limit = 20,
  offset = 0
): Promise<DiscoverResponse> {
  const sp = new URLSearchParams({
    q,
    limit: String(limit),
    offset: String(offset),
  });
  return apiJson<DiscoverResponse>(`/v1/discover?${sp}`, { token });
}

export async function importPubMedPaper(token: string, pmid: string): Promise<Paper> {
  return apiJson<Paper>("/v1/discover/import", {
    method: "POST",
    token,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pmid }),
  });
}

export async function fetchPaperPdf(token: string, id: number): Promise<Paper> {
  return apiJson<Paper>(`/v1/papers/${id}/fetch-pdf`, { method: "POST", token });
}
