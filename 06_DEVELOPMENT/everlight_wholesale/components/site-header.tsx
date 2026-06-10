import Link from "next/link";
import { Crown, Building2, Home, Users, Layers, Activity, HandshakeIcon, Search } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur-lg bg-obsidian/85 border-b border-ash">
      <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between gap-4">
        <Link href="/" className="group flex items-center gap-3 flex-none">
          <div className="w-9 h-9 rounded bg-gold-gradient flex items-center justify-center shadow-gold-glow">
            <Crown className="w-5 h-5 text-obsidian" strokeWidth={2.5} />
          </div>
          <div className="hidden md:block">
            <div className="text-[10px] tracking-[0.35em] text-gold/80">EVERLIGHT VENTURES</div>
            <div className="font-display text-lg text-ivory leading-none mt-0.5">
              Wholesale Command
            </div>
          </div>
        </Link>

        <form method="get" action="/search" className="flex-1 max-w-md mx-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-smoke" />
            <input
              name="q"
              placeholder="Search anything..."
              className="w-full pl-9 pr-3 py-2 bg-charcoal border border-ash rounded-lg text-sm text-ivory placeholder:text-smoke focus:border-gold/60 focus:outline-none"
            />
          </div>
        </form>

        <nav className="flex items-center gap-0.5 text-sm overflow-x-auto">
          <NavLink href="/" icon={<Home className="w-4 h-4" />} label="Dashboard" />
          <NavLink href="/pipeline" icon={<Layers className="w-4 h-4" />} label="Pipeline" />
          <NavLink href="/deals" icon={<HandshakeIcon className="w-4 h-4" />} label="Deals" />
          <NavLink href="/activity" icon={<Activity className="w-4 h-4" />} label="Activity" />
          <NavLink href="/buyers" icon={<Users className="w-4 h-4" />} label="Buyers" />
          <NavLink href="/title-companies" icon={<Building2 className="w-4 h-4" />} label="Titles" />
        </nav>
      </div>
      <div className="divider-gold" />
    </header>
  );
}

function NavLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-1.5 px-3 py-2 rounded text-fog hover:text-gold hover:bg-ash/40 transition-colors whitespace-nowrap"
    >
      {icon}
      <span className="hidden lg:inline">{label}</span>
    </Link>
  );
}
