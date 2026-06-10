import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";

export function Breadcrumbs({
  items,
}: {
  items: { label: string; href?: string }[];
}) {
  return (
    <nav className="flex items-center gap-1.5 text-[12px] text-fog">
      <Link href="/" className="flex items-center gap-1.5 hover:text-gold transition-colors">
        <Home className="w-3.5 h-3.5" />
        <span>Dashboard</span>
      </Link>
      {items.map((it, i) => (
        <span key={i} className="flex items-center gap-1.5">
          <ChevronRight className="w-3 h-3 text-smoke" />
          {it.href ? (
            <Link href={it.href} className="hover:text-gold transition-colors">
              {it.label}
            </Link>
          ) : (
            <span className="text-ivory">{it.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
