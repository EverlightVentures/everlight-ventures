import Link from "next/link";
import { Crown } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-14 h-14 rounded-full bg-gold/10 border border-gold/30 flex items-center justify-center">
        <Crown className="w-7 h-7 text-gold" />
      </div>
      <h1 className="font-display text-5xl text-ivory mt-6 tracking-tight">Not here</h1>
      <p className="text-fog text-sm mt-3 max-w-md">
        That lead, buyer, or page is not in the book. Might have been recycled, or the link is stale.
      </p>
      <div className="mt-8 flex gap-3">
        <Link href="/" className="px-5 py-2.5 bg-gold text-obsidian font-medium rounded-lg hover:brightness-110 transition">
          Back to dashboard
        </Link>
        <Link href="/search" className="px-5 py-2.5 border border-ash text-ivory rounded-lg hover:border-gold/50 transition">
          Search the book
        </Link>
      </div>
    </div>
  );
}
