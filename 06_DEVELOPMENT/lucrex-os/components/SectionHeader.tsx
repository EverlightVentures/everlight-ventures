import { cn } from "@/lib/utils";

type Props = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  accent?: string;
  className?: string;
  children?: React.ReactNode;
};

export function SectionHeader({ eyebrow, title, subtitle, accent, className, children }: Props) {
  return (
    <div className={cn("flex items-end justify-between gap-4 mb-6", className)}>
      <div>
        {eyebrow && (
          <div
            className="text-[10px] uppercase tracking-[0.25em] mb-1"
            style={{ color: accent ?? "var(--color-gold-500)" }}
          >
            {eyebrow}
          </div>
        )}
        <h1 className="font-display text-3xl md:text-4xl font-semibold leading-tight">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-[var(--color-muted)] mt-1.5 max-w-2xl">
            {subtitle}
          </p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
