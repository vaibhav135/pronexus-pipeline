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

// Matches backend SearchResponse
export interface SearchResponse {
  job_id: string;
  query: string;
  results_count: number;
  businesses: Business[];
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

// Frontend-only: a row in the results table combining business + enrichment
export interface BusinessRow {
  business: Business;
  enrichment: EnrichResponse | null;
  enrichStatus: EnrichStatus;
}

// Stored search for the home page job list
export interface SearchJob {
  jobId: string;
  query: string;
  status: JobStatus;
  resultsCount: number;
  businesses: Business[];
  createdAt: string;
}
