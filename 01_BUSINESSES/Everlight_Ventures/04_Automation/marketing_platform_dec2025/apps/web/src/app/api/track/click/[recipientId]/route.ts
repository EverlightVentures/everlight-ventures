import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@everlight/db';
import { logActivity } from '@/lib/activity-logger';

/**
 * Email Click Tracking Endpoint
 *
 * Records click event and redirects to the original URL.
 * This endpoint is public (no auth) as it's called from emails.
 *
 * GET /api/track/click/[recipientId]?url=https://example.com
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { recipientId: string } }
) {
  const { recipientId } = params;
  const { searchParams } = new URL(request.url);
  const targetUrl = searchParams.get('url');

  // Validate URL parameter
  if (!targetUrl) {
    return NextResponse.json(
      { error: 'Missing url parameter' },
      { status: 400 }
    );
  }

  // Validate URL is HTTP/HTTPS for security
  try {
    const url = new URL(targetUrl);
    if (!['http:', 'https:'].includes(url.protocol)) {
      throw new Error('Invalid URL protocol');
    }
  } catch (error) {
    console.error('[Track Click] Invalid URL:', targetUrl, error);
    return NextResponse.json(
      { error: 'Invalid url parameter' },
      { status: 400 }
    );
  }

  // Record click event (async, don't wait for it)
  recordClickEvent(recipientId, targetUrl, request).catch((error) => {
    console.error('[Track Click] Error recording click:', error);
  });

  // Redirect immediately to target URL
  return NextResponse.redirect(targetUrl, 302);
}

/**
 * Records the click event in the database
 */
async function recordClickEvent(
  recipientId: string,
  targetUrl: string,
  request: NextRequest
) {
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
      console.error('[Track Click] Recipient not found:', recipientId);
      return;
    }

    // Get IP address and user agent
    const ipAddress =
      request.headers.get('x-forwarded-for')?.split(',')[0].trim() ||
      request.headers.get('x-real-ip') ||
      'unknown';
    const userAgent = request.headers.get('user-agent') || 'unknown';

    // Record click event
    await prisma.$transaction(async (tx) => {
      // Create EmailClick record
      await tx.emailClick.create({
        data: {
          recipientId: recipient.id,
          url: targetUrl,
          ipAddress,
          userAgent,
        },
      });

      // Update CampaignRecipient with click count and timestamp
      await tx.campaignRecipient.update({
        where: { id: recipient.id },
        data: {
          clickCount: { increment: 1 },
          lastClickedAt: new Date(),
        },
      });
    });

    // Log activity (async, don't wait)
    logActivity({
      type: 'EMAIL_CLICKED',
      projectId: recipient.campaign.projectId,
      userId: null,
      metadata: {
        campaignName: recipient.campaign.name,
        contactEmail: recipient.contact.email,
        url: targetUrl,
        recipientId,
      },
    }).catch(console.error);

    console.log('[Track Click] Recorded:', {
      recipientId,
      campaign: recipient.campaign.name,
      email: recipient.contact.email,
      url: targetUrl,
      ipAddress,
    });
  } catch (error) {
    console.error('[Track Click] Database error:', error);
    throw error;
  }
}
