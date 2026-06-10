import { Sparkles } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

type Props = {
  title: string;
  domain: string;
  accent: string;
  themeClass: string;
  blurb: string;
  willInclude: string[];
};

export function ComingSoon({ title, domain, accent, themeClass, blurb, willInclude }: Props) {
  return (
    <div className={themeClass}>
      <div className="px-4 md:px-8 lg:px-12 py-12 md:py-20 max-w-3xl mx-auto">
        <div className="flex items-center gap-2 mb-2 text-[10px] uppercase tracking-[0.3em]" style={{ color: accent }}>
          <span>Domain</span>
          <span className="h-px w-6" style={{ background: accent, opacity: 0.4 }} />
          <span>{domain}</span>
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-semibold leading-tight mb-3">{title}</h1>
        <p className="text-base text-[var(--color-muted)] mb-6">{blurb}</p>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} style={{ color: accent }} />
            <span className="font-display text-lg font-semibold">Phase 2 scope</span>
            <StatusBadge variant="warn">scaffolded</StatusBadge>
          </div>
          <ul className="space-y-2">
            {willInclude.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm">
                <span
                  className="mt-2 h-1.5 w-1.5 rounded-full flex-shrink-0"
                  style={{ background: accent }}
                />
                <span className="text-[var(--color-fg)]">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
