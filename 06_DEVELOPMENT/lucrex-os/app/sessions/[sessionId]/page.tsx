import Link from "next/link";
import { ArrowLeft, ExternalLink, Network } from "lucide-react";

const DJANGO_BASE = process.env.NEXT_PUBLIC_DJANGO_BASE ?? "http://127.0.0.1:2200";

export const dynamic = "force-dynamic";

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const djangoUrl = `${DJANGO_BASE}/hive/sessions/${encodeURIComponent(sessionId)}/`;

  return (
    <div className="flex flex-col h-[calc(100dvh-57px-32px)] page-enter">
      <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/sessions"
            className="text-gray-500 hover:text-amber-400 transition flex items-center gap-1 text-[11px]"
          >
            <ArrowLeft size={12} /> back
          </Link>
          <div className="text-amber-400/30">|</div>
          <Network size={14} className="text-amber-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-widest text-gray-500">Session</div>
            <div className="font-mono text-[12px] text-gray-200 truncate">{sessionId}</div>
          </div>
        </div>
        <a
          href={djangoUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] text-amber-400 hover:underline"
        >
          Open original <ExternalLink size={11} />
        </a>
      </div>
      <iframe
        src={djangoUrl}
        title={`Session ${sessionId}`}
        className="flex-1 w-full bg-[#0a0a0a]"
        sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
      />
    </div>
  );
}
