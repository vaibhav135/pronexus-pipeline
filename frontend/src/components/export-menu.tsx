"use client";

import { Download, FileSpreadsheet, FileText, File } from "lucide-react";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import {
  Document,
  Packer,
  Paragraph,
  Table as DocxTable,
  TableRow as DocxTableRow,
  TableCell as DocxTableCell,
  TextRun,
  WidthType,
  HeadingLevel,
  BorderStyle,
} from "docx";
import { saveAs } from "file-saver";
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

const HEADERS = [
  "Business Name",
  "Owner",
  "Owner Source",
  "Email",
  "Email Type",
  "Phone",
  "City",
  "State",
  "Website",
  "Status",
];

function rowToArray(r: BusinessRow): string[] {
  return [
    r.business.name,
    r.enrichment?.owner_name ?? "",
    r.enrichment?.owner_source ?? "",
    r.enrichment?.email ?? "",
    r.enrichment?.email_type ?? "",
    r.business.phone_number ?? "",
    r.business.city ?? "",
    r.business.state ?? "",
    r.business.website ?? "",
    r.enrichStatus,
  ];
}

function downloadCSV(rows: BusinessRow[]) {
  const csvRows = rows.map(rowToArray);
  const csv = [HEADERS, ...csvRows]
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

function downloadPDF(rows: BusinessRow[]) {
  const doc = new jsPDF({ orientation: "landscape" });

  doc.setFontSize(18);
  doc.text("ProNexus Results", 14, 20);
  doc.setFontSize(10);
  doc.setTextColor(107, 114, 128);
  doc.text(`${rows.length} businesses — exported ${new Date().toLocaleDateString()}`, 14, 28);

  autoTable(doc, {
    startY: 35,
    head: [HEADERS],
    body: rows.map(rowToArray),
    styles: { fontSize: 7, cellPadding: 2 },
    headStyles: {
      fillColor: [79, 70, 229],
      textColor: [255, 255, 255],
      fontStyle: "bold",
    },
    alternateRowStyles: { fillColor: [250, 251, 252] },
    margin: { left: 14, right: 14 },
  });

  doc.save("pronexus-results.pdf");
}

async function downloadDOCX(rows: BusinessRow[]) {
  const borderNone = {
    top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  } as const;

  const borderHeader = {
    top: { style: BorderStyle.SINGLE, size: 1, color: "4F46E5" },
    bottom: { style: BorderStyle.SINGLE, size: 2, color: "4F46E5" },
    left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  } as const;

  const headerRow = new DocxTableRow({
    children: HEADERS.map(
      (h) =>
        new DocxTableCell({
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: h, bold: true, size: 16, color: "4F46E5" }),
              ],
            }),
          ],
          borders: borderHeader,
        }),
    ),
  });

  const dataRows = rows.map(
    (r) =>
      new DocxTableRow({
        children: rowToArray(r).map(
          (cell) =>
            new DocxTableCell({
              children: [
                new Paragraph({
                  children: [new TextRun({ text: cell, size: 16 })],
                }),
              ],
              borders: borderNone,
            }),
        ),
      }),
  );

  const doc = new Document({
    sections: [
      {
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: "ProNexus Results", bold: true, size: 32 }),
            ],
            heading: HeadingLevel.HEADING_1,
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: `${rows.length} businesses — exported ${new Date().toLocaleDateString()}`,
                size: 20,
                color: "6B7280",
              }),
            ],
            spacing: { after: 300 },
          }),
          new DocxTable({
            width: { size: 100, type: WidthType.PERCENTAGE },
            rows: [headerRow, ...dataRows],
          }),
        ],
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  saveAs(blob, "pronexus-results.docx");
}

export function ExportMenu({ rows, disabled }: ExportMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={disabled || rows.length === 0}
        className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-surface px-4 py-2 text-sm font-medium text-text hover:bg-muted transition-colors disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
      >
        <Download className="h-4 w-4" />
        Export
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => downloadCSV(rows)} className="gap-2">
          <FileSpreadsheet className="h-4 w-4" />
          Download CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => downloadPDF(rows)} className="gap-2">
          <File className="h-4 w-4" />
          Download PDF
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => downloadDOCX(rows)}
          className="gap-2"
        >
          <FileText className="h-4 w-4" />
          Download DOCX
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
