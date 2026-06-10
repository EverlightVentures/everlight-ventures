import { notFound } from 'next/navigation';
import { requireAuth, getProjectBySlug } from '@/lib/session';
import Link from 'next/link';
import { Button } from '@everlight/ui';

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { slug: string };
}) {
  const user = await requireAuth();
  const project = await getProjectBySlug(params.slug, user.id);

  if (!project) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/dashboard" className="text-xl font-bold text-blue-600">
                Everlight
              </Link>
              <span className="text-gray-400">→</span>
              <h2 className="text-lg font-semibold">{project.name}</h2>
            </div>
            <div className="flex items-center gap-4">
              <Link href={`/projects/${params.slug}`}>
                <Button variant="ghost">Dashboard</Button>
              </Link>
              <Link href={`/projects/${params.slug}/contacts`}>
                <Button variant="ghost">Contacts</Button>
              </Link>
              <Link href={`/projects/${params.slug}/campaigns`}>
                <Button variant="ghost">Campaigns</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>
      {children}
    </div>
  );
}
