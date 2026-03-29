"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import type { BusinessRow, EnrichStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  EnrichStatus,
  { style: string; icon: React.ElementType; label: string }
> = {
  pending: {
    style: "bg-muted text-muted-foreground",
    icon: Clock,
    label: "Pending",
  },
  enriching: {
    style: "bg-warning/15 text-warning border-warning/30",
    icon: Loader2,
    label: "Enriching",
  },
  enriched: {
    style: "bg-success/15 text-success border-success/30",
    icon: CheckCircle2,
    label: "Enriched",
  },
  failed: {
    style: "bg-error/15 text-error border-error/30",
    icon: XCircle,
    label: "Failed",
  },
};

const SOURCE_STYLES: Record<string, string> = {
  website_httpx: "bg-primary/10 text-primary border-primary/30",
  website_jina: "bg-primary/10 text-primary border-primary/30",
  tavily_search: "bg-secondary/10 text-secondary border-secondary/30",
  exa_search: "bg-secondary/10 text-secondary border-secondary/30",
  prospeo: "bg-warning/10 text-warning border-warning/30",
  hunter: "bg-warning/10 text-warning border-warning/30",
};

function LoadingCell() {
  return <Skeleton className="h-4 w-20 rounded" />;
}

function EmptyCell() {
  return <span className="text-text-muted/50">—</span>;
}

interface ResultsTableProps {
  rows: BusinessRow[];
  isLoading?: boolean;
}

export function ResultsTable({ rows, isLoading }: ResultsTableProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-surface shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Business</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Owner</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Email</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Phone</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Location</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Website</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 4 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 7 }).map((_, j) => (
                  <TableCell key={j}>
                    <LoadingCell />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-text-muted">
        No results found.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface shadow-sm overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent border-b border-border">
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Business</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Owner</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Email</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Phone</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Location</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Website</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-text-muted">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => {
            const biz = row.business;
            const enr = row.enrichment;
            const isEnriching = row.enrichStatus === "enriching";
            const statusConf = STATUS_CONFIG[row.enrichStatus];
            const StatusIcon = statusConf.icon;

            return (
              <TableRow key={biz.id} className="hover:bg-muted/50 transition-colors">
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text">{biz.name}</span>
                    {biz.verified && (
                      <ShieldCheck className="h-3.5 w-3.5 text-success flex-shrink-0" />
                    )}
                  </div>
                  {biz.rating && (
                    <span className="text-xs text-text-muted">
                      {String(biz.rating)} stars &middot; {biz.review_count ?? 0} reviews
                    </span>
                  )}
                </TableCell>

                <TableCell>
                  {isEnriching ? (
                    <LoadingCell />
                  ) : enr?.owner_name ? (
                    <div className="space-y-1">
                      <span className="text-sm">{enr.owner_name}</span>
                      {enr.owner_source && (
                        <Badge
                          variant="outline"
                          className={`text-[10px] block w-fit ${SOURCE_STYLES[enr.owner_source] ?? "bg-muted text-muted-foreground"}`}
                        >
                          {enr.owner_source}
                        </Badge>
                      )}
                    </div>
                  ) : (
                    <EmptyCell />
                  )}
                </TableCell>

                <TableCell>
                  {isEnriching ? (
                    <LoadingCell />
                  ) : enr?.email ? (
                    <div className="space-y-1">
                      <span className="text-sm">{enr.email}</span>
                      {enr.email_type && (
                        <Badge
                          variant="outline"
                          className={`text-[10px] block w-fit ${
                            enr.email_type === "personal"
                              ? "bg-success/10 text-success border-success/30"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {enr.email_type}
                        </Badge>
                      )}
                    </div>
                  ) : (
                    <EmptyCell />
                  )}
                </TableCell>

                <TableCell className="text-sm">
                  {biz.phone_number ?? <EmptyCell />}
                </TableCell>

                <TableCell className="text-sm">
                  {biz.city && biz.state ? (
                    `${biz.city}, ${biz.state}`
                  ) : (
                    <EmptyCell />
                  )}
                </TableCell>

                <TableCell>
                  {biz.website ? (
                    <a
                      href={biz.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-secondary hover:text-secondary-hover transition-colors"
                    >
                      {new URL(biz.website).hostname}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <EmptyCell />
                  )}
                </TableCell>

                <TableCell>
                  <Badge
                    variant="outline"
                    className={`gap-1 text-xs ${statusConf.style}`}
                  >
                    <StatusIcon
                      className={`h-3 w-3 ${row.enrichStatus === "enriching" ? "animate-spin" : ""}`}
                    />
                    {statusConf.label}
                  </Badge>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
