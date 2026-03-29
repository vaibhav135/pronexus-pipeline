"use client";

import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { SearchBar } from "@/components/search-bar";
import { JobCard } from "@/components/job-card";
import { useJobs, useSearch } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const { data: jobs, isLoading } = useJobs();
  const search = useSearch();

  function handleSearch(query: string) {
    search.mutate(query, {
      onSuccess: (data) => {
        router.push(`/search/${data.job_id}`);
      },
    });
  }

  return (
    <div className="flex flex-1 flex-col items-center px-4 pt-24 pb-12 gap-12">
      {/* Hero */}
      <div className="text-center space-y-4 max-w-xl">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary font-medium mb-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          Lead Generation Pipeline
        </div>
        <h1 className="text-5xl font-bold tracking-tight text-text">
          Pro<span className="text-primary">Nexus</span>
        </h1>
        <p className="text-lg text-text-muted leading-relaxed">
          Search Google Maps, discover business owners, and find verified emails
          — all in one pipeline.
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} isLoading={search.isPending} />

      {search.isError && (
        <div className="rounded-lg bg-error/10 border border-error/20 px-4 py-3 text-sm text-error max-w-2xl w-full">
          {search.error.message}
        </div>
      )}

      {/* Recent searches */}
      <div className="w-full max-w-2xl space-y-4">
        {isLoading ? (
          <p className="text-center text-text-muted">Loading searches...</p>
        ) : jobs && jobs.length > 0 ? (
          <>
            <div className="flex items-center gap-3">
              <h2 className="text-xs font-semibold text-text-muted uppercase tracking-widest">
                Recent Searches
              </h2>
              <div className="flex-1 h-px bg-border" />
            </div>
            <div className="space-y-2">
              {jobs.map((job) => (
                <JobCard key={job.jobId} job={job} />
              ))}
            </div>
          </>
        ) : (
          <div className="text-center py-16 space-y-3">
            <Search className="mx-auto h-10 w-10 text-text-muted/40" strokeWidth={1.5} />
            <p className="text-text-muted">
              No searches yet. Enter a query above to get started.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
