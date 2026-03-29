"use client";

import { use, useState, useCallback } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ResultsTable } from "@/components/results-table";
import { ExportMenu } from "@/components/export-menu";
import { useJob, useEnrich } from "@/lib/api";
import type { BusinessRow, EnrichResponse, EnrichStatus } from "@/lib/types";

export default function SearchResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: job, isLoading: jobLoading } = useJob(id);
  const enrich = useEnrich();

  const [enrichments, setEnrichments] = useState<
    Record<string, { data: EnrichResponse | null; status: EnrichStatus }>
  >({});

  const enrichBusiness = useCallback(
    async (businessId: string) => {
      setEnrichments((prev) => ({
        ...prev,
        [businessId]: { data: null, status: "enriching" },
      }));

      try {
        const result = await enrich.mutateAsync(businessId);
        setEnrichments((prev) => ({
          ...prev,
          [businessId]: { data: result, status: "enriched" },
        }));
      } catch {
        setEnrichments((prev) => ({
          ...prev,
          [businessId]: { data: null, status: "failed" },
        }));
      }
    },
    [enrich],
  );

  const [bulkEnriching, setBulkEnriching] = useState(false);

  const enrichAll = useCallback(async () => {
    if (!job?.businesses) return;
    setBulkEnriching(true);

    for (const biz of job.businesses) {
      if (enrichments[biz.id]?.status === "enriched") continue;
      await enrichBusiness(biz.id);
    }

    setBulkEnriching(false);
  }, [job, enrichments, enrichBusiness]);

  if (jobLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-muted gap-2">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading...
      </div>
    );
  }

  if (!job) {
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

  const rows: BusinessRow[] = (job.businesses ?? []).map((biz) => ({
    business: biz,
    enrichment: enrichments[biz.id]?.data ?? null,
    enrichStatus: enrichments[biz.id]?.status ?? "pending",
  }));

  const enrichedCount = rows.filter(
    (r) => r.enrichStatus === "enriched",
  ).length;
  const allEnriched = enrichedCount === rows.length && rows.length > 0;

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
              {job.query}
            </h1>
            <div className="flex items-center gap-3 text-sm text-text-muted">
              <span>{job.resultsCount} businesses</span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span>{enrichedCount} enriched</span>
              {bulkEnriching && (
                <>
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span className="flex items-center gap-1 text-warning">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Enriching...
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={enrichAll}
            disabled={bulkEnriching || allEnriched}
            className="gap-2 bg-primary text-primary-foreground hover:bg-primary-hover shadow-sm shadow-primary/20"
          >
            {allEnriched ? (
              <>
                <CheckCircle2 className="h-4 w-4" />
                All Enriched
              </>
            ) : bulkEnriching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Enriching...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Enrich All
              </>
            )}
          </Button>
          <ExportMenu rows={rows} />
        </div>
      </div>

      {/* Progress bar */}
      {rows.length > 0 && (
        <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-primary h-full rounded-full transition-all duration-500"
            style={{
              width: `${(enrichedCount / rows.length) * 100}%`,
            }}
          />
        </div>
      )}

      {/* Results Table */}
      <ResultsTable rows={rows} />
    </div>
  );
}
