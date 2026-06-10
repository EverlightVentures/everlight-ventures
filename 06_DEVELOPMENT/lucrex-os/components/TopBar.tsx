"use client";
import { Menu, Search, Bell } from "lucide-react";
import Link from "next/link";
import { CountdownClock } from "./CountdownClock";

type Props = { onMenuClick: () => void };

export function TopBar({ onMenuClick }: Props) {
  return (
    <header className="sticky top-0 z-30 h-[57px] border-b border-[var(--color-border)] bg-[var(--color-bg)]/85 backdrop-blur-md">
      <div className="h-full flex items-center px-4 gap-4">
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 text-[var(--color-muted)] hover:text-[var(--color-gold-500)]"
          aria-label="Open menu"
        >
          <Menu size={22} />
        </button>

        <Link href="/" className="flex items-center gap-2 group">
          <div
            className="h-7 w-7 rounded-md flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, #F1E4B6 0%, #D4A843 50%, #8E6E20 100%)",
            }}
          >
            <span className="font-display font-bold text-sm text-black">L</span>
          </div>
          <div className="leading-tight">
            <div className="font-display text-base text-gold-gradient font-semibold">
              LUCREX OS
            </div>
            <div className="text-[9px] uppercase tracking-[0.2em] text-[var(--color-muted)] -mt-0.5">
              Everlight Ventures
            </div>
          </div>
        </Link>

        <div className="hidden md:flex items-center gap-3 ml-6 text-xs text-[var(--color-muted)]">
          <span className="px-2 py-0.5 rounded border border-[var(--color-gold-800)] text-[var(--color-gold-400)]">
            T0 · Foundation
          </span>
          <CountdownClock />
        </div>

        <div className="flex-1" />

        <button
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-fg)] hover:border-[var(--color-gold-700)] transition"
          aria-label="Search"
        >
          <Search size={14} />
          <span>Search</span>
          <kbd className="ml-2 text-[10px] px-1 py-0.5 rounded bg-[var(--color-elevated)] border border-[var(--color-border)]">
            ⌘K
          </kbd>
        </button>

        <button
          className="relative p-2 text-[var(--color-muted)] hover:text-[var(--color-gold-500)] transition"
          aria-label="Notifications"
        >
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[var(--color-alert)] animate-pulse-gold" />
        </button>
      </div>
    </header>
  );
}
