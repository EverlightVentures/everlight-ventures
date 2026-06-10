import { requireAuth, getProjectBySlug } from '@/lib/session';
import { notFound } from 'next/navigation';
import { prisma } from '@everlight/db';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@everlight/ui';
import Link from 'next/link';

async function getCampaigns(projectId: string) {
  return prisma.campaign.findMany({
    where: { projectId },
    include: {
      _count: {
        select: { recipients: true },
      },
    },
    orderBy: { createdAt: 'desc' },
  });
}

export default async function CampaignsPage({
  params,
}: {
  params: { slug: string };
}) {
  const user = await requireAuth();
  const project = await getProjectBySlug(params.slug, user.id);

  if (!project) {
    notFound();
  }

  const campaigns = await getCampaigns(project.id);

  const statusColors: Record<string, any> = {
    DRAFT: 'secondary',
    SCHEDULED: 'warning',
    SENDING: 'default',
    SENT: 'success',
    FAILED: 'destructive',
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl font-bold">Campaigns</h1>
        <Link href={`/projects/${params.slug}/campaigns/new`}>
          <Button>Create Campaign</Button>
        </Link>
      </div>

      {campaigns.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            <p>No campaigns yet. Create your first campaign to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <Card key={campaign.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle>{campaign.name}</CardTitle>
                    <p className="mt-1 text-sm text-gray-600">{campaign.subject}</p>
                  </div>
                  <Badge variant={statusColors[campaign.status]}>
                    {campaign.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    <span>{campaign._count.recipients} recipients</span>
                    {campaign.sentAt && (
                      <span className="ml-4">
                        Sent {new Date(campaign.sentAt).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/projects/${params.slug}/campaigns/${campaign.id}`}>
                      <Button variant="outline" size="sm">
                        View
                      </Button>
                    </Link>
                    {campaign.status === 'DRAFT' && (
                      <Link href={`/projects/${params.slug}/campaigns/${campaign.id}/send`}>
                        <Button size="sm">Send</Button>
                      </Link>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
