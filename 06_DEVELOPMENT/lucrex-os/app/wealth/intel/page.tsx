import { getDispatchLog } from "@/lib/wealth";
import { StatusBadge } from "@/components/StatusBadge";
import { Calendar, FileText, Scale, ScrollText } from "lucide-react";

const SOURCE_ICONS = {
  IRS: Scale,
  JCT: ScrollText,
  Default: FileText,
};

export default async function IntelPage() {
  const drops = await getDispatchLog();

  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
          Quarterly Intel Engine
        </div>
        <h2 className="font-display text-2xl md:text-3xl font-semibold">Intel feed</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
          Monthly law-change scan from IRS, JCT, Tax Notes, and state legislatures. Posts to
          {" "}<span className="text-[var(--color-gold-400)]">#ceo-brief</span>{" "}
          on the 1st. Recent drops below.
        </p>
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Calendar size={16} className="text-[var(--color-gold-500)]" />
            <div>
              <div className="font-medium">Next scheduled scan</div>
              <div className="text-xs text-[var(--color-muted)]">May 1, 5:00 AM PT</div>
            </div>
          </div>
          <StatusBadge variant="active">Engine armed</StatusBadge>
        </div>
      </div>

      {drops.length === 0 ? (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
          <FileText className="mx-auto mb-3 text-[var(--color-faint)]" size={28} />
          <div className="text-sm text-[var(--color-muted)] mb-1">No dispatch drops yet.</div>
          <div className="text-xs text-[var(--color-faint)]">
            First scan posts to <code className="text-[var(--color-gold-400)]">04_Dispatch_Log/</code> on May 1.
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {drops.map((d) => {
            const date = (d.frontmatter.date as string) ?? d.slug.match(/(\d{4}-\d{2}-\d{2})/)?.[1] ?? "";
            const severity = ((d.frontmatter.severity as string) ?? "info") as "info" | "warn" | "alert";
            const source = (d.frontmatter.source as string) ?? "Hive";
            const SourceIcon = SOURCE_ICONS[source as keyof typeof SOURCE_ICONS] ?? SOURCE_ICONS.Default;
            const summary = d.content.split("\n").find((l) => l.trim() && !l.startsWith("#"))?.slice(0, 240) ?? "";

            return (
              <div key={d.slug} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 hover:border-[var(--color-gold-700)] transition">
                <div className="flex items-center gap-3 text-xs text-[var(--color-muted)] mb-2">
                  {date && <span className="font-mono">{date}</span>}
                  <span className="flex items-center gap-1">
                    <SourceIcon size={11} /> {source}
                  </span>
                  <StatusBadge variant={severity === "alert" ? "alert" : severity === "warn" ? "warn" : "info"}>
                    {severity}
                  </StatusBadge>
                </div>
                <h3 className="font-display text-lg font-semibold mb-1">{d.title}</h3>
                <p className="text-sm text-[var(--color-muted)]">{summary}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
