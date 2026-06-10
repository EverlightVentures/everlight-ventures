import Link from "next/link";
import { FileSignature, AlertTriangle } from "lucide-react";
import { getContracts } from "@/lib/api/wholesale";

export const dynamic = "force-dynamic";

export default async function ContractsPage() {
  const contracts = await getContracts();

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
          <FileSignature size={20} /> CONTRACTS
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          State contract matrix, assignment templates, deal packages · {contracts.length} docs
        </p>
      </div>

      <div className="card border-amber-400/30 bg-amber-400/5">
        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-300">
            <span className="text-amber-400 font-semibold">Disclaimer:</span>{" "}
            All templates are for internal operational use. A licensed attorney in the applicable state must review and approve any document used in an actual transaction.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {contracts.map((c) => (
          <Link
            key={c.slug}
            href={`/contracts/${c.slug}`}
            className="card group block"
          >
            <div className="flex items-start gap-2 mb-2">
              <FileSignature size={16} className="text-amber-400/60 flex-shrink-0 mt-1" />
              <div className="flex-1 min-w-0">
                <div className="font-display text-sm font-semibold leading-tight">{c.title}</div>
                <div className="text-[10px] text-gray-600 font-mono mt-1">{c.slug}</div>
              </div>
            </div>
            <div className="flex items-center justify-between text-[10px] text-gray-600 mt-3 pt-3 border-t border-white/[0.04]">
              <span>{(c.size / 1024).toFixed(1)} KB</span>
              <span className="group-hover:text-amber-400 transition">view →</span>
            </div>
          </Link>
        ))}
        {contracts.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500 text-sm">
            No contracts found. Check WHOLESALE paths in lib/api/wholesale.ts.
          </div>
        )}
      </div>
    </div>
  );
}
