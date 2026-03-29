import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Building2,
} from "lucide-react";
import type { SearchJob, JobStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  JobStatus,
  { style: string; icon: React.ElementType }
> = {
  pending: { style: "bg-muted text-muted-foreground", icon: Clock },
  running: {
    style: "bg-warning/15 text-warning border-warning/30",
    icon: Loader2,
  },
  completed: {
    style: "bg-success/15 text-success border-success/30",
    icon: CheckCircle2,
  },
  failed: {
    style: "bg-error/15 text-error border-error/30",
    icon: XCircle,
  },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface JobCardProps {
  job: SearchJob;
}

export function JobCard({ job }: JobCardProps) {
  const config = STATUS_CONFIG[job.status];
  const Icon = config.icon;

  return (
    <Link href={`/search/${job.jobId}`}>
      <Card className="group hover:border-primary/30 hover:shadow-md hover:shadow-primary/5 transition-all cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between gap-4 py-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex-shrink-0 flex items-center justify-center h-9 w-9 rounded-lg bg-primary/8 text-primary">
              <Building2 className="h-4 w-4" />
            </div>
            <div className="space-y-0.5 min-w-0">
              <CardTitle className="text-sm font-medium truncate">
                {job.query}
              </CardTitle>
              <CardDescription className="text-xs text-text-muted">
                {formatDate(job.createdAt)} &middot; {job.resultsCount}{" "}
                businesses
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge variant="outline" className={`text-xs gap-1 ${config.style}`}>
              <Icon
                className={`h-3 w-3 ${job.status === "running" ? "animate-spin" : ""}`}
              />
              {job.status}
            </Badge>
            <ChevronRight className="h-4 w-4 text-text-muted/40 group-hover:text-primary transition-colors" />
          </div>
        </CardHeader>
      </Card>
    </Link>
  );
}
