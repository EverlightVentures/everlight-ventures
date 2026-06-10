import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getComplianceDoc } from "@/lib/api/wholesale";
import { MarkdownRender } from "@/components/MarkdownRender";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function PolicyDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const doc = await getComplianceDoc(slug);
  if (!doc) return notFound();

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto page-enter">
      <Link href="/compliance" className="inline-flex items-center gap-2 text-xs text-gray-500 hover:text-amber-400 mb-4 transition">
        <ArrowLeft size={12} /> Back to compliance
      </Link>
      <div className="card">
        <MarkdownRender content={doc.content} />
      </div>
    </div>
  );
}
