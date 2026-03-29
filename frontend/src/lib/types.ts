// Matches backend ScrapeJob.status
export type JobStatus = "pending" | "running" | "completed" | "failed";

// Frontend row enrichment state
export type EnrichStatus = "pending" | "enriching" | "enriched" | "failed";

// Matches backend BusinessResponse
export interface Business {
  id: string;
  place_id: string;
  name: string;
  types: string[] | null;
  full_address: string | null;
  city: string | null;
  state: string | null;
  phone_number: string | null;
  website: string | null;
  latitude: number | null;
  longitude: number | null;
  rating: number | null;
  review_count: number | null;
  verified: boolean;
  is_claimed: boolean;
  created_at: string;
}

// Matches backend SearchRequest
export interface SearchRequest {
  query: string;
  limit?: number;
  offset?: number;
  country?: string;
  lang?: string;
  zoom?: number;
  lat?: string;
  lng?: string;
}

// Matches backend SearchResponse
export interface SearchResponse {
  job_id: string;
  query: string;
  results_count: number;
  businesses: Business[];
}

// Matches backend EnrichRequest
export interface EnrichRequest {
  business_id: string;
}

// Matches backend EnrichResponse
export interface EnrichResponse {
  business_id: string;
  business_name: string;
  owner_name: string | null;
  owner_source: string | null;
  email: string | null;
  email_type: string | null;
  email_source: string | null;
}

// Matches backend JobResponse
export interface JobResponse {
  id: string;
  search_query: string;
  status: JobStatus;
  results_count: number;
  last_run_at: string | null;
  created_at: string;
}

// Matches backend JobWithBusinessesResponse
export interface JobWithBusinessesResponse {
  job: JobResponse;
  businesses: Business[];
}

// Frontend-only: a row in the results table combining business + enrichment
export interface BusinessRow {
  business: Business;
  enrichment: EnrichResponse | null;
  enrichStatus: EnrichStatus;
}

// SSE event types from enrich-stream
export interface SSEProgressEvent {
  completed: number;
  total: number;
}

export interface SSEErrorEvent {
  business_id: string;
  business_name: string;
  error: string;
}
