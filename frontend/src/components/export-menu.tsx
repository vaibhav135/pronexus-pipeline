"use client";

import { Download, FileSpreadsheet, FileText, File } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { BusinessRow } from "@/lib/types";

interface ExportMenuProps {
  rows: BusinessRow[];
  disabled?: boolean;
}

function downloadCSV(rows: BusinessRow[]) {
  const headers = [
    "Business Name",
    "Verified",
    "Owner",
    "Owner Source",
    "Email",
    "Email Type",
    "Email Source",
    "Phone",
    "City",
    "State",
    "Full Address",
    "Website",
    "Rating",
    "Reviews",
    "Enrich Status",
  ];

  const csvRows = rows.map((r) => [
    r.business.name,
    r.business.verified ? "Yes" : "No",
    r.enrichment?.owner_name ?? "",
    r.enrichment?.owner_source ?? "",
    r.enrichment?.email ?? "",
    r.enrichment?.email_type ?? "",
    r.enrichment?.email_source ?? "",
    r.business.phone_number ?? "",
    r.business.city ?? "",
    r.business.state ?? "",
    r.business.full_address ?? "",
    r.business.website ?? "",
    r.business.rating?.toString() ?? "",
    r.business.review_count?.toString() ?? "",
    r.enrichStatus,
  ]);

  const csv = [headers, ...csvRows]
    .map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","),
    )
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "pronexus-results.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function ExportMenu({ rows, disabled }: ExportMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={disabled || rows.length === 0}
        className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-surface px-4 py-2 text-sm font-medium text-text hover:bg-muted transition-colors disabled:opacity-50 disabled:pointer-events-none"
      >
        <Download className="h-4 w-4" />
        Export
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => downloadCSV(rows)} className="gap-2">
          <FileSpreadsheet className="h-4 w-4" />
          Download CSV
        </DropdownMenuItem>
        <DropdownMenuItem disabled className="gap-2">
          <File className="h-4 w-4" />
          Download PDF (coming soon)
        </DropdownMenuItem>
        <DropdownMenuItem disabled className="gap-2">
          <FileText className="h-4 w-4" />
          Download DOCX (coming soon)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
