import fs from "node:fs/promises";
import path from "node:path";
import Link from "next/link";
import { FileText, Calendar, ExternalLink } from "lucide-react";

export const dynamic = "force-dynamic";

const REPORTS_DIR = process.env.HIVE_REPORTS_DIR ?? "/home/opc/hive_reports";
const DJANGO_BASE = process.env.NEXT_PUBLIC_DJANGO_BASE ?? "http://127.0.0.1:2200";

type ReportFile = {
  name: string;
  size: number;
  mtime: string;
  prettyTitle: string;
  dateLabel: string;
};

function prettyTitle(filename: string): string {
  // strip .html and trailing _YYYYMMDD_HHMM(SS) timestamps
  let s = filename.replace(/\.html?$/i, "");
  s = s.replace(/_\d{8}_\d{4,6}(_\d{8}_\d{4})?$/g, "");
  s = s.replace(/_/g, " ");
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

function dateFromName(filename: string, fallback: Date): string {
  const m = filename.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
  if (m) {
    const [_, y, mo, d, hh, mm] = m;
    void _;
    return `${y}-${mo}-${d} ${hh}:${mm}`;
  }
  return fallback.toISOString().slice(0, 16).replace("T", " ");
}

async function listReports(): Promise<ReportFile[]> {
  try {
    const names = await fs.readdir(REPORTS_DIR);
    const stats = await Promise.all(
      names
        .filter((n) => n.toLowerCase().endsWith(".html"))
        .map(async (n) => {
          const full = path.join(REPORTS_DIR, n);
          const s = await fs.stat(full);
          return {
            name: n,
            size: s.size,
            mtime: s.mtime.toISOString(),
            mtimeRaw: s.mtime,
          };
        })
    );
    return stats
      .sort((a, b) => b.mtimeRaw.getTime() - a.mtimeRaw.getTime())
      .map((s) => ({
        name: s.name,
        size: s.size,
        mtime: s.mtime,
        prettyTitle: prettyTitle(s.name),
        dateLabel: dateFromName(s.name, s.mtimeRaw),
      }));
  } catch {
    return [];
  }
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}

export default async function ReportsPage() {
  const reports = await listReports();

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
            <FileText size={20} /> REPORTS
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            HTML reports from the Hive, {reports.length} on disk
          </p>
        </div>
        <a
          href={`${DJANGO_BASE}/reports/`}
          target="_blank"
          rel="noopener noreferrer"
          className="card flex items-center gap-2 hover:border-amber-400/40 transition"
        >
          <span className="text-[11px] text-amber-400 font-medium">Open report server</span>
          <ExternalLink size={12} className="text-amber-400" />
        </a>
      </div>

      {reports.length === 0 ? (
        <div className="card border border-amber-400/20 bg-amber-400/[0.03]">
          <h2 className="text-sm font-semibold text-amber-400/80 mb-1">No reports found</h2>
          <p className="text-[11px] text-gray-500">
            Looked in <code className="text-amber-400/70">{REPORTS_DIR}</code>. If you are running
            Lucrex from the dev phone this path is Oracle-only, deploy or set
            <code className="text-amber-400/70"> HIVE_REPORTS_DIR</code> to a local folder.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {reports.map((r) => (
            <Link
              key={r.name}
              href={`/reports/${encodeURIComponent(r.name)}`}
              className="card hover:border-amber-400/40 transition group"
            >
              <div className="flex items-start gap-2">
                <div className="w-9 h-9 rounded-lg bg-amber-400/10 flex items-center justify-center flex-shrink-0">
                  <FileText size={14} className="text-amber-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium text-gray-200 group-hover:text-amber-300 transition truncate">
                    {r.prettyTitle}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                    <Calendar size={10} />
                    <span className="font-mono">{r.dateLabel}</span>
                  </div>
                  <div className="text-[9px] text-gray-600 font-mono mt-0.5">{fmtSize(r.size)}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
