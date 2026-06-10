import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import Link from 'next/link';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import { prisma } from '@everlight/db';
import { Card, CardContent, CardHeader, CardTitle } from '@everlight/ui/card';
import { Badge } from '@everlight/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@everlight/ui/table';
import { formatDistance } from 'date-fns';

interface CampaignPageProps {
  params: {
    slug: string;
    id: string;
  };
}

export default async function CampaignPage({ params }: CampaignPageProps) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    redirect('/auth/signin');
  }

  const project = await getProjectBySlug(params.slug, session.user.id);
  if (!project) {
    redirect('/dashboard');
  }

  // Fetch campaign with all analytics data
  const campaign = await prisma.campaign.findFirst({
    where: {
      id: params.id,
      projectId: project.id,
    },
    include: {
      recipients: {
        include: {
          contact: true,
          opens: {
            orderBy: { openedAt: 'desc' },
            take: 1,
          },
          clicks: {
            orderBy: { clickedAt: 'desc' },
          },
        },
      },
      _count: {
        select: {
          recipients: true,
          unsubscribes: true,
        },
      },
    },
  });

  if (!campaign) {
    redirect(`/projects/${params.slug}/campaigns`);
  }

  // Calculate analytics
  const totalRecipients = campaign.recipients.length;
  const uniqueOpens = campaign.recipients.filter((r) => r.openCount > 0).length;
  const uniqueClicks = campaign.recipients.filter((r) => r.clickCount > 0).length;
  const openRate = totalRecipients > 0 ? (uniqueOpens / totalRecipients) * 100 : 0;
  const clickRate = totalRecipients > 0 ? (uniqueClicks / totalRecipients) * 100 : 0;
  const unsubscribeCount = campaign._count.unsubscribes;
  const unsubscribeRate =
    totalRecipients > 0 ? (unsubscribeCount / totalRecipients) * 100 : 0;

  // Get top clicked links
  const allClicks = campaign.recipients.flatMap((r) => r.clicks);
  const linkClickCounts = new Map<string, number>();
  allClicks.forEach((click) => {
    linkClickCounts.set(click.url, (linkClickCounts.get(click.url) || 0) + 1);
  });
  const topLinks = Array.from(linkClickCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  // Status badge variant
  const statusVariant =
    campaign.status === 'SENT'
      ? 'default'
      : campaign.status === 'DRAFT'
      ? 'secondary'
      : campaign.status === 'FAILED'
      ? 'destructive'
      : 'default';

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{campaign.name}</h1>
            <Badge variant={statusVariant}>{campaign.status}</Badge>
          </div>
          <p className="text-lg text-muted-foreground">{campaign.subject}</p>
          {campaign.sentAt && (
            <p className="text-sm text-muted-foreground">
              Sent {formatDistance(campaign.sentAt, new Date(), { addSuffix: true })}
            </p>
          )}
        </div>
        <Link
          href={`/projects/${params.slug}/campaigns`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to campaigns
        </Link>
      </div>

      {/* Analytics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Recipients</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRecipients}</div>
            <p className="text-xs text-muted-foreground">
              Sent to {totalRecipients} contact{totalRecipients !== 1 ? 's' : ''}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{openRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {uniqueOpens} of {totalRecipients} opened
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Click Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{clickRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {uniqueClicks} of {totalRecipients} clicked
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unsubscribe Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{unsubscribeRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {unsubscribeCount} unsubscribe{unsubscribeCount !== 1 ? 's' : ''}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Top Clicked Links */}
      {topLinks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Top Clicked Links</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>URL</TableHead>
                  <TableHead className="text-right">Clicks</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topLinks.map(([url, count]) => (
                  <TableRow key={url}>
                    <TableCell className="font-mono text-sm">
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline truncate block max-w-md"
                      >
                        {url}
                      </a>
                    </TableCell>
                    <TableCell className="text-right font-semibold">{count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Recipients Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recipients ({totalRecipients})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Opens</TableHead>
                <TableHead className="text-right">Clicks</TableHead>
                <TableHead>Last Opened</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaign.recipients.map((recipient) => (
                <TableRow key={recipient.id}>
                  <TableCell className="font-medium">
                    {recipient.contact.email}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        recipient.status === 'SENT'
                          ? 'default'
                          : recipient.status === 'FAILED'
                          ? 'destructive'
                          : 'secondary'
                      }
                    >
                      {recipient.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {recipient.openCount > 0 ? (
                      <span className="font-semibold text-green-600">
                        {recipient.openCount}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">0</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {recipient.clickCount > 0 ? (
                      <span className="font-semibold text-blue-600">
                        {recipient.clickCount}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">0</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {recipient.lastOpenedAt
                      ? formatDistance(recipient.lastOpenedAt, new Date(), {
                          addSuffix: true,
                        })
                      : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* UTM Parameters Info */}
      {(campaign.utmSource || campaign.utmMedium || campaign.utmCampaign || campaign.utmContent) && (
        <Card>
          <CardHeader>
            <CardTitle>UTM Tracking Parameters</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {campaign.utmSource && (
                <>
                  <dt className="font-medium text-muted-foreground">Source:</dt>
                  <dd className="font-mono">{campaign.utmSource}</dd>
                </>
              )}
              {campaign.utmMedium && (
                <>
                  <dt className="font-medium text-muted-foreground">Medium:</dt>
                  <dd className="font-mono">{campaign.utmMedium}</dd>
                </>
              )}
              {campaign.utmCampaign && (
                <>
                  <dt className="font-medium text-muted-foreground">Campaign:</dt>
                  <dd className="font-mono">{campaign.utmCampaign}</dd>
                </>
              )}
              {campaign.utmContent && (
                <>
                  <dt className="font-medium text-muted-foreground">Content:</dt>
                  <dd className="font-mono">{campaign.utmContent}</dd>
                </>
              )}
            </dl>
            <p className="mt-4 text-xs text-muted-foreground">
              These UTM parameters are automatically added to all links in your emails for
              Google Analytics tracking.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
