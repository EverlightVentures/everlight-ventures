import { requireAuth, getProjectBySlug } from '@/lib/session';
import { notFound } from 'next/navigation';
import { prisma } from '@everlight/db';
import { ContactsTable } from '@/components/contacts-table';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@everlight/ui';
import Link from 'next/link';

async function getContacts(projectId: string) {
  return prisma.contact.findMany({
    where: { projectId },
    orderBy: { createdAt: 'desc' },
  });
}

export default async function ContactsPage({
  params,
}: {
  params: { slug: string };
}) {
  const user = await requireAuth();
  const project = await getProjectBySlug(params.slug, user.id);

  if (!project) {
    notFound();
  }

  const contacts = await getContacts(project.id);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl font-bold">Contacts</h1>
        <div className="flex gap-2">
          <Link href={`/projects/${params.slug}/contacts/import`}>
            <Button variant="outline">Import CSV</Button>
          </Link>
          <Link href={`/projects/${params.slug}/contacts/new`}>
            <Button>Add Contact</Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Contacts ({contacts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <ContactsTable contacts={contacts} projectSlug={params.slug} />
        </CardContent>
      </Card>
    </div>
  );
}
