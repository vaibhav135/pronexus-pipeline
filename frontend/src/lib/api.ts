import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import type {
  SearchRequest,
  SearchResponse,
  EnrichResponse,
  JobResponse,
  JobWithBusinessesResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Raw fetch functions ---

async function fetchJobs(): Promise<JobResponse[]> {
  const res = await fetch(`${API_BASE}/api/jobs`);
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

async function fetchJob(jobId: string): Promise<JobWithBusinessesResponse> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to fetch job");
  return res.json();
}

async function postSearch(req: SearchRequest): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Search failed");
  }
  return res.json();
}

async function postEnrich(businessId: string): Promise<EnrichResponse> {
  const res = await fetch(`${API_BASE}/api/enrich`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ business_id: businessId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Enrichment failed");
  }
  return res.json();
}

// --- React Query Hooks ---

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  });
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => fetchJob(jobId),
    enabled: !!jobId,
  });
}

export function useSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (req: SearchRequest) => postSearch(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useEnrich() {
  return useMutation({
    mutationFn: postEnrich,
  });
}

// --- SSE for bulk enrichment ---

export function subscribeToEnrichStream(
  jobId: string,
  onResult: (result: EnrichResponse) => void,
  onProgress: (completed: number, total: number) => void,
  onError: (businessId: string, businessName: string, error: string) => void,
  onDone: () => void,
): () => void {
  const eventSource = new EventSource(
    `${API_BASE}/api/jobs/${jobId}/enrich-stream`,
  );

  eventSource.addEventListener("result", (e) => {
    const data: EnrichResponse = JSON.parse(e.data);
    onResult(data);
  });

  eventSource.addEventListener("progress", (e) => {
    const data = JSON.parse(e.data);
    onProgress(data.completed, data.total);
  });

  eventSource.addEventListener("error", (e) => {
    // SSE "error" can be a connection error (no data) or our custom event
    if (e instanceof MessageEvent && e.data) {
      const data = JSON.parse(e.data);
      onError(data.business_id, data.business_name, data.error);
    }
  });

  eventSource.addEventListener("done", () => {
    eventSource.close();
    onDone();
  });

  return () => eventSource.close();
}
