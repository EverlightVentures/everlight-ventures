"use client";
import { useEffect, useState } from "react";
import { timeAgo } from "@/lib/api/client";
import { Newspaper, ExternalLink } from "lucide-react";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

type Note = {
  id: string;
  content: string;
  tags?: string;
  created_at: string;
};

function parseTitle(content: string): string {
  const h = content.match(/^#\s+(.+)$/m);
  if (h) return h[1].trim().slice(0, 120);
  const firstLine = content.split("\n").find((l) => l.trim() && !l.startsWith("#"));
  return (firstLine ?? "untitled").slice(0, 120);
}

function parseTags(tagStr?: string): string[] {
  if (!tagStr) return [];
  return tagStr.split(/\s+/).filter(Boolean).slice(0, 4);
}

function summary(content: string): string {
  return content
    .replace(/^#.*$/gm, "")
    .replace(/^#?\w[\w/-]*/g, "") // strip tag tokens like #hive/foo
    .replace(/\n+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
}

export function NewsFeed({ limit = 12, query = "market" }: { limit?: number; query?: string }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const r = await fetch(`${BASE_PATH}/api/blinko/proxy/api/v1/note/list`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ searchText: query }),
          cache: "no-store",
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        if (cancelled) return;
        setNotes((j.items as Note[]) ?? []);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "fetch failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const id = setInterval(load, 60_000);
    return () => { cancelled = true; clearInterval(id); };
  }, [query]);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Newspaper size={16} className="text-amber-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">News &amp; Intel</h2>
        </div>
        <span className="text-[10px] text-gray-600 font-mono">Blinko · query: {query}</span>
      </div>

      {loading && notes.length === 0 ? (
        <div className="text-sm text-gray-500 italic py-4">loading...</div>
      ) : error ? (
        <div className="text-sm text-red-400 py-4">{error}</div>
      ) : (
        <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
          {notes.slice(0, limit).map((n) => {
            const title = parseTitle(n.content);
            const tags = parseTags(n.tags);
            const sum = summary(n.content);
            return (
              <div key={n.id} className="border-l-2 border-amber-400/30 pl-3 py-1 hover:border-amber-400 transition">
                <div className="flex items-baseline justify-between gap-2 flex-wrap">
                  <h3 className="text-sm font-medium text-gray-200 leading-tight flex-1">{title}</h3>
                  <span className="text-[9px] text-gray-600 font-mono flex-shrink-0">{timeAgo(n.created_at)}</span>
                </div>
                <div className="flex items-center gap-1 flex-wrap mt-1">
                  {tags.map((t) => (
                    <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-amber-400/5 text-amber-400/70 font-mono">{t}</span>
                  ))}
                </div>
                {sum && <p className="text-[11px] text-gray-500 mt-1 leading-relaxed line-clamp-3">{sum}</p>}
              </div>
            );
          })}
          {notes.length === 0 && (
            <div className="text-sm text-gray-500 italic py-4">No notes matched "{query}".</div>
          )}
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-white/[0.04] flex items-center justify-between text-[10px]">
        <span className="text-gray-600">refresh every 60s</span>
        <a href="http://163.192.19.196:1111" target="_blank" rel="noopener noreferrer" className="text-amber-400/70 hover:text-amber-400 inline-flex items-center gap-1">
          full Blinko <ExternalLink size={9} />
        </a>
      </div>
    </div>
  );
}
