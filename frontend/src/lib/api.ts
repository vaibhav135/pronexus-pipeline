import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import type {
  SearchRequest,
  SearchResponse,
  EnrichRequest,
  EnrichResponse,
  SearchJob,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Raw fetch functions ---

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

async function postEnrich(req: EnrichRequest): Promise<EnrichResponse> {
  const res = await fetch(`${API_BASE}/api/enrich`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Enrichment failed");
  }
  return res.json();
}

// --- Local storage for search history (no backend endpoint for job list) ---

const JOBS_STORAGE_KEY = "pronexus_jobs";

function loadJobs(): SearchJob[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(JOBS_STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveJobs(jobs: SearchJob[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(JOBS_STORAGE_KEY, JSON.stringify(jobs));
}

function addJob(job: SearchJob) {
  const jobs = loadJobs();
  // Replace if same query exists, otherwise prepend
  const idx = jobs.findIndex((j) => j.query === job.query);
  if (idx >= 0) {
    jobs[idx] = job;
  } else {
    jobs.unshift(job);
  }
  saveJobs(jobs);
}

// --- React Query Hooks ---

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => loadJobs(),
  });
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => {
      const jobs = loadJobs();
      return jobs.find((j) => j.jobId === jobId) ?? null;
    },
    enabled: !!jobId,
  });
}

export function useSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (query: string) => postSearch({ query }),
    onSuccess: (data) => {
      const job: SearchJob = {
        jobId: data.job_id,
        query: data.query,
        status: "completed",
        resultsCount: data.results_count,
        businesses: data.businesses,
        createdAt: new Date().toISOString(),
      };
      addJob(job);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.setQueryData(["jobs", data.job_id], job);
    },
  });
}

export function useEnrich() {
  return useMutation({
    mutationFn: (businessId: string) =>
      postEnrich({ business_id: businessId }),
  });
}
