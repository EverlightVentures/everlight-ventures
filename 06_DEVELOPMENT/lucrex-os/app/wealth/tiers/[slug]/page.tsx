import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { listWealthFolder } from "@/lib/wealth";
import { MarkdownRender } from "@/components/MarkdownRender";
import { notFound } from "next/navigation";

export async function generateStaticParams() {
  const tiers = await listWealthFolder("02_Tiers");
  return tiers.map((t) => ({ slug: t.slug }));
}

export default async function TierDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const tiers = await listWealthFolder("02_Tiers");
  const doc = tiers.find((t) => t.slug === slug);
  if (!doc) return notFound();

  return (
    <div className="max-w-4xl">
      <Link
        href="/wealth/tiers"
        className="inline-flex items-center gap-2 text-sm text-[var(--color-muted)] hover:text-[var(--color-gold-500)] mb-4 transition"
      >
        <ArrowLeft size={14} /> All tiers
      </Link>
      <MarkdownRender content={doc.content} />
    </div>
  );
}
