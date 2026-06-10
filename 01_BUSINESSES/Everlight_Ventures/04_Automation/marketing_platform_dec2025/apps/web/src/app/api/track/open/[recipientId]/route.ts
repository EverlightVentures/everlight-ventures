import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@everlight/db';
import { logActivity } from '@/lib/activity-logger';

// 1x1 transparent GIF in base64
const TRACKING_PIXEL = Buffer.from(
  'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
  'base64'
);

/**
 * Email Open Tracking Endpoint
 *
 * Returns a 1x1 transparent GIF and records the email open event.
 * This endpoint is public (no auth) as it's called by email clients.
 *
 * GET /api/track/open/[recipientId]
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { recipientId: string } }
) {
  const { recipientId } = params;

  // Always return tracking pixel, even if recording fails
  const headers = new Headers({
    'Content-Type': 'image/gif',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  });

  try {
    // Verify recipient exists
    const recipient = await prisma.campaignRecipient.findUnique({
      where: { id: recipientId },
      select: {
        id: true,
        campaignId: true,
        contactId: true,
        campaign: {
          select: {
            name: true,
            projectId: true,
          },
        },
        contact: {
          select: {
            email: true,
          },
        },
      },
    });

    if (!recipient) {
      console.error('[Track Open] Recipient not found:', recipientId);
      return new NextResponse(TRACKING_PIXEL, { headers });
    }

    // Get IP address and user agent for tracking
    const ipAddress =
      request.headers.get('x-forwarded-for')?.split(',')[0].trim() ||
      request.headers.get('x-real-ip') ||
      'unknown';
    const userAgent = request.headers.get('user-agent') || 'unknown';

    // Record email open event
    await prisma.$transaction(async (tx) => {
      // Create EmailOpen record
      await tx.emailOpen.create({
        data: {
          recipientId: recipient.id,
          ipAddress,
          userAgent,
        },
      });

      // Update CampaignRecipient with open count and timestamp
      await tx.campaignRecipient.update({
        where: { id: recipient.id },
        data: {
          openCount: { increment: 1 },
          lastOpenedAt: new Date(),
        },
      });
    });

    // Log activity (async, don't wait)
    logActivity({
      type: 'EMAIL_OPENED',
      projectId: recipient.campaign.projectId,
      userId: null,
      metadata: {
        campaignName: recipient.campaign.name,
        contactEmail: recipient.contact.email,
        recipientId,
      },
    }).catch(console.error);

    console.log('[Track Open] Recorded:', {
      recipientId,
      campaign: recipient.campaign.name,
      email: recipient.contact.email,
      ipAddress,
    });
  } catch (error) {
    console.error('[Track Open] Error recording open:', error);
    // Don't throw - always return tracking pixel
  }

  return new NextResponse(TRACKING_PIXEL, { headers });
}
