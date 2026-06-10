import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { listWealthFolder } from "@/lib/wealth";
import { MarkdownRender } from "@/components/MarkdownRender";
import { notFound } from "next/navigation";

export async function generateStaticParams() {
  const layers = await listWealthFolder("01_Layers");
  return layers.map((l) => ({ slug: l.slug }));
}

export default async function LayerDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const layers = await listWealthFolder("01_Layers");
  const doc = layers.find((l) => l.slug === slug);
  if (!doc) return notFound();

  return (
    <div className="max-w-4xl">
      <Link
        href="/wealth/layers"
        className="inline-flex items-center gap-2 text-sm text-[var(--color-muted)] hover:text-[var(--color-gold-500)] mb-4 transition"
      >
        <ArrowLeft size={14} /> All layers
      </Link>
      <MarkdownRender content={doc.content} />
    </div>
  );
}
