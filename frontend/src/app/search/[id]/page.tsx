"use client";

import { use, useState, useRef, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, CheckCircle2, RotateCcw, StopCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ResultsTable } from "@/components/results-table";
import { ExportMenu } from "@/components/export-menu";
import { useJob, subscribeToEnrichStream } from "@/lib/api";
import type { BusinessRow, EnrichResponse, EnrichStatus } from "@/lib/types";

export default function SearchResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading: jobLoading } = useJob(id);

  const [enrichments, setEnrichments] = useState<
    Record<string, { data: EnrichResponse | null; status: EnrichStatus }>
  >({});
  const [enriching, setEnriching] = useState(false);
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const cleanupRef = useRef<(() => void) | null>(null);
  const initializedRef = useRef(false);

  // Load cached enrichment data from the API response
  useEffect(() => {
    if (!data || initializedRef.current) return;
    initializedRef.current = true;

    const cached: Record<string, { data: EnrichResponse | null; status: EnrichStatus }> = {};
    let hasUnenriched = false;

    for (const item of data.businesses) {
      if (item.is_enriched) {
        cached[item.business.id] = {
          data: {
            business_id: item.business.id,
            business_name: item.business.name,
            owner_name: item.owner_name,
            owner_source: item.owner_source,
            email: item.email,
            email_type: item.email_type,
            email_source: item.email_source,
          },
          status: "enriched",
        };
      } else {
        hasUnenriched = true;
      }
    }

    setEnrichments(cached);

    // Auto-start SSE only if there are unenriched businesses
    if (hasUnenriched) {
      startSSE();
    }
  }, [data, id]);

  function startSSE() {
    setEnriching(true);

    // Mark unenriched rows as enriching
    if (data) {
      const pending: Record<string, { data: EnrichResponse | null; status: EnrichStatus }> = {};
      for (const item of data.businesses) {
        if (!item.is_enriched) {
          pending[item.business.id] = { data: null, status: "enriching" };
        }
      }
      setEnrichments((prev) => ({ ...prev, ...pending }));
    }

    const cleanup = subscribeToEnrichStream(
      id,
      (result) => {
        setEnrichments((prev) => ({
          ...prev,
          [result.business_id]: { data: result, status: "enriched" },
        }));
      },
      (completed, total) => {
        setProgress({ completed, total });
      },
      (businessId) => {
        setEnrichments((prev) => ({
          ...prev,
          [businessId]: { data: null, status: "failed" },
        }));
      },
      () => {
        setEnriching(false);
      },
    );

    cleanupRef.current = cleanup;
  }

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      cleanupRef.current?.();
    };
  }, []);

  function stopEnrich() {
    cleanupRef.current?.();
    cleanupRef.current = null;
    setEnriching(false);
    setEnrichments((prev) => {
      const updated = { ...prev };
      for (const [key, val] of Object.entries(updated)) {
        if (val.status === "enriching") {
          updated[key] = { data: null, status: "pending" };
        }
      }
      return updated;
    });
  }

  function retryFailed() {
    setEnrichments((prev) => {
      const updated = { ...prev };
      for (const [key, val] of Object.entries(updated)) {
        if (val.status === "failed") {
          updated[key] = { data: null, status: "enriching" };
        }
      }
      return updated;
    });
    startSSE();
  }

  if (jobLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-muted gap-2">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4">
        <p className="text-text-muted">Search not found</p>
        <Link href="/">
          <Button variant="outline" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Button>
        </Link>
      </div>
    );
  }

  const { job, businesses } = data;

  const rows: BusinessRow[] = businesses.map((item) => ({
    business: item.business,
    enrichment: enrichments[item.business.id]?.data ?? null,
    enrichStatus: enrichments[item.business.id]?.status ?? "pending",
  }));

  const enrichedCount = rows.filter(
    (r) => r.enrichStatus === "enriched",
  ).length;
  const failedCount = rows.filter(
    (r) => r.enrichStatus === "failed",
  ).length;
  const allDone = enrichedCount + failedCount === rows.length && rows.length > 0;

  return (
    <div className="flex flex-1 flex-col px-4 py-8 gap-6 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <Link href="/">
            <Button
              variant="ghost"
              size="icon"
              className="text-text-muted hover:text-text mt-0.5"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-text">
              {job.search_query}
            </h1>
            <div className="flex items-center gap-3 text-sm text-text-muted">
              <span>{job.results_count} businesses</span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="text-success">{enrichedCount} enriched</span>
              {failedCount > 0 && (
                <>
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span className="text-error">{failedCount} failed</span>
                </>
              )}
              {enriching && (
                <>
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span className="flex items-center gap-1 text-warning">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {progress.completed}/{progress.total}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {enriching ? (
            <Button
              onClick={stopEnrich}
              variant="outline"
              className="gap-2 border-error text-error hover:bg-error/10"
            >
              <StopCircle className="h-4 w-4" />
              Stop
            </Button>
          ) : allDone ? (
            failedCount > 0 && (
              <Button
                onClick={retryFailed}
                variant="outline"
                className="gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Retry Failed
              </Button>
            )
          ) : (
            <Button
              onClick={startSSE}
              className="gap-2 bg-primary text-primary-foreground hover:bg-primary-hover shadow-sm shadow-primary/20"
            >
              <Sparkles className="h-4 w-4" />
              Enrich Remaining
            </Button>
          )}
          <ExportMenu rows={rows} />
        </div>
      </div>

      {/* Results Table */}
      <ResultsTable rows={rows} />
    </div>
  );
}
