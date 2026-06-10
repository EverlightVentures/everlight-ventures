import Link from "next/link";
import { ArrowLeft, ExternalLink, FileText } from "lucide-react";

const DJANGO_BASE = process.env.NEXT_PUBLIC_DJANGO_BASE ?? "http://127.0.0.1:2200";

export const dynamic = "force-dynamic";

export default async function ReportViewer({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);
  // Reports are served from Django at /reports/<name> per nginx config
  const src = `${DJANGO_BASE}/reports/${encodeURIComponent(decoded)}`;

  return (
    <div className="flex flex-col h-[calc(100dvh-57px-32px)] page-enter">
      <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/reports"
            className="text-gray-500 hover:text-amber-400 transition flex items-center gap-1 text-[11px]"
          >
            <ArrowLeft size={12} /> back
          </Link>
          <div className="text-amber-400/30">|</div>
          <FileText size={14} className="text-amber-400 flex-shrink-0" />
          <div className="font-mono text-[11px] text-gray-300 truncate">{decoded}</div>
        </div>
        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] text-amber-400 hover:underline"
        >
          Open original <ExternalLink size={11} />
        </a>
      </div>
      <iframe
        src={src}
        title={decoded}
        className="flex-1 w-full bg-[#0a0a0a]"
        sandbox="allow-same-origin allow-popups"
      />
    </div>
  );
}
