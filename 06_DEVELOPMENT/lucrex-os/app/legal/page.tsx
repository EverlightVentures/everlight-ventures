import Link from "next/link";
import { Scale, FileText } from "lucide-react";
import { getLegalDocs, getComplianceDocs, getContracts } from "@/lib/api/wholesale";

export const dynamic = "force-dynamic";

export default async function LegalPage() {
  const [legal, compliance, contracts] = await Promise.all([
    getLegalDocs(),
    getComplianceDocs(),
    getContracts(),
  ]);

  const allDocs = [
    ...legal.map((d) => ({ ...d, kind: "legal" as const,      href: `/legal/${d.slug}` })),
    ...compliance.map((d) => ({ ...d, kind: "compliance" as const, href: `/compliance/policy/${d.slug}` })),
    ...contracts.map((d) => ({
      slug: d.slug,
      title: d.title,
      content: d.content,
      preview: d.content.replace(/^#.*$/gm, "").replace(/\n+/g, " ").trim().slice(0, 200),
      size: d.size,
      updated: null,
      kind: "contract" as const,
      href: `/contracts/${d.slug}`,
    })),
  ];

  const KIND_BADGE = {
    legal:      "bg-purple-400/10 text-purple-400 border-purple-400/30",
    compliance: "bg-amber-400/10 text-amber-400 border-amber-400/30",
    contract:   "bg-blue-400/10 text-blue-400 border-blue-400/30",
  };

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
          <Scale size={20} /> LEGAL LIBRARY
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Everything legal, compliance, and contractual in one place · {allDocs.length} docs total
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="card text-center">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Legal Foundations</div>
          <div className="font-mono text-3xl font-bold text-purple-400 mt-1">{legal.length}</div>
        </div>
        <div className="card text-center">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Compliance Policies</div>
          <div className="font-mono text-3xl font-bold text-amber-400 mt-1">{compliance.length}</div>
        </div>
        <div className="card text-center">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Contract Templates</div>
          <div className="font-mono text-3xl font-bold text-blue-400 mt-1">{contracts.length}</div>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.04]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">All Documents</h2>
        </div>
        <div className="divide-y divide-white/[0.03]">
          {allDocs.map((d) => (
            <Link
              key={`${d.kind}-${d.slug}`}
              href={d.href}
              className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.02] transition group"
            >
              <FileText size={14} className="text-gray-500 mt-1 flex-shrink-0 group-hover:text-amber-400" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="font-medium text-sm text-gray-200">{d.title}</div>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-semibold border ${KIND_BADGE[d.kind]}`}>
                    {d.kind}
                  </span>
                </div>
                <div className="text-[11px] text-gray-500 line-clamp-1 mt-0.5">{d.preview}</div>
              </div>
              <div className="text-[9px] text-gray-600 font-mono flex-shrink-0 text-right">
                <div>{(d.size / 1024).toFixed(1)} KB</div>
                {d.updated && <div className="text-gray-700">{d.updated.slice(0, 10)}</div>}
              </div>
            </Link>
          ))}
          {allDocs.length === 0 && (
            <div className="text-center py-8 text-gray-500 text-sm">No documents found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
