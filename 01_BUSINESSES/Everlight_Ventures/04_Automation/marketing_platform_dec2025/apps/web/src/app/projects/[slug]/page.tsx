import { requireAuth, getProjectBySlug } from '@/lib/session';
import { notFound } from 'next/navigation';
import { prisma } from '@everlight/db';
import { Card, CardContent, CardHeader, CardTitle } from '@everlight/ui';

async function getProjectStats(projectId: string) {
  const [
    totalContacts,
    subscribedContacts,
    totalCampaigns,
    sentCampaigns,
    recentActivities,
  ] = await Promise.all([
    prisma.contact.count({ where: { projectId } }),
    prisma.contact.count({ where: { projectId, subscribed: true } }),
    prisma.campaign.count({ where: { projectId } }),
    prisma.campaign.count({ where: { projectId, status: 'SENT' } }),
    prisma.activity.findMany({
      where: { projectId },
      orderBy: { createdAt: 'desc' },
      take: 10,
      include: {
        user: {
          select: { name: true, email: true },
        },
      },
    }),
  ]);

  return {
    totalContacts,
    subscribedContacts,
    totalCampaigns,
    sentCampaigns,
    recentActivities,
  };
}

export default async function ProjectDashboard({
  params,
}: {
  params: { slug: string };
}) {
  const user = await requireAuth();
  const project = await getProjectBySlug(params.slug, user.id);

  if (!project) {
    notFound();
  }

  const stats = await getProjectStats(project.id);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-8 text-3xl font-bold">Dashboard</h1>

      <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Total Contacts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalContacts}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Subscribed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.subscribedContacts}</div>
            <div className="text-sm text-gray-500">
              {stats.totalContacts > 0
                ? Math.round((stats.subscribedContacts / stats.totalContacts) * 100)
                : 0}
              % of total
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Total Campaigns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalCampaigns}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">
              Sent Campaigns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.sentCampaigns}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {stats.recentActivities.length === 0 ? (
            <p className="text-gray-500">No recent activity</p>
          ) : (
            <div className="space-y-4">
              {stats.recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-start gap-4 border-b pb-4 last:border-0">
                  <div className="flex-1">
                    <div className="font-medium">{activity.type.replace(/_/g, ' ')}</div>
                    <div className="text-sm text-gray-500">
                      by {activity.user?.name || activity.user?.email || 'System'}
                    </div>
                  </div>
                  <div className="text-sm text-gray-400">
                    {new Date(activity.createdAt).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
