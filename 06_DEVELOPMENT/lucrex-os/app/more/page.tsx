import Link from "next/link";
import { DOMAINS, DOMAIN_ORDER } from "@/lib/theme";

export default function MorePage() {
  return (
    <div className="px-4 py-6 max-w-md mx-auto">
      <h1 className="font-display text-3xl font-semibold mb-1">More</h1>
      <p className="text-sm text-[var(--color-muted)] mb-6">All domains, fast jumper for mobile.</p>
      <div className="space-y-2">
        {DOMAIN_ORDER.map((key) => {
          const d = DOMAINS[key];
          return (
            <Link
              key={key}
              href={d.href}
              className="block rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 hover:border-[var(--color-gold-700)] hover:bg-[var(--color-elevated)] transition"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-display text-base font-semibold">{d.label}</div>
                  <div className="text-xs text-[var(--color-muted)] mt-0.5">{d.tagline}</div>
                </div>
                <div className="h-2 w-2 rounded-full" style={{ background: d.accent }} />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
