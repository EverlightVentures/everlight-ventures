import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@everlight/db';
import { logActivity } from '@/lib/activity-logger';

/**
 * One-Click Unsubscribe Endpoint
 *
 * Unsubscribes a contact from future emails.
 * This endpoint is public (no auth) for GDPR/CAN-SPAM compliance.
 *
 * GET /api/unsubscribe/[recipientId]?reason=optional
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { recipientId: string } }
) {
  const { recipientId } = params;
  const { searchParams } = new URL(request.url);
  const reason = searchParams.get('reason');

  try {
    // Get recipient details
    const recipient = await prisma.campaignRecipient.findUnique({
      where: { id: recipientId },
      select: {
        id: true,
        contactId: true,
        campaignId: true,
        campaign: {
          select: {
            name: true,
            projectId: true,
          },
        },
        contact: {
          select: {
            id: true,
            email: true,
            subscribed: true,
          },
        },
      },
    });

    if (!recipient) {
      return new NextResponse(
        `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsubscribe - Not Found</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
    h1 { color: #dc2626; }
  </style>
</head>
<body>
  <h1>Link Not Found</h1>
  <p>This unsubscribe link is invalid or has expired.</p>
</body>
</html>`,
        {
          status: 404,
          headers: { 'Content-Type': 'text/html' },
        }
      );
    }

    // Check if already unsubscribed
    if (!recipient.contact.subscribed) {
      return new NextResponse(
        `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Already Unsubscribed</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
    h1 { color: #059669; }
  </style>
</head>
<body>
  <h1>Already Unsubscribed</h1>
  <p>You have already unsubscribed from ${recipient.contact.email}</p>
  <p>You will not receive any future emails from us.</p>
</body>
</html>`,
        {
          status: 200,
          headers: { 'Content-Type': 'text/html' },
        }
      );
    }

    // Unsubscribe the contact
    await prisma.$transaction(async (tx) => {
      // Update contact subscription status
      await tx.contact.update({
        where: { id: recipient.contactId },
        data: { subscribed: false },
      });

      // Create unsubscribe record
      await tx.unsubscribe.create({
        data: {
          contactId: recipient.contactId,
          campaignId: recipient.campaignId,
          projectId: recipient.campaign.projectId,
          reason: reason || null,
        },
      });
    });

    // Log activity (async, don't wait)
    logActivity({
      type: 'SUBSCRIBER_UNSUBSCRIBED',
      projectId: recipient.campaign.projectId,
      userId: null,
      metadata: {
        campaignName: recipient.campaign.name,
        contactEmail: recipient.contact.email,
        reason: reason || null,
      },
    }).catch(console.error);

    console.log('[Unsubscribe] Success:', {
      email: recipient.contact.email,
      campaign: recipient.campaign.name,
      reason,
    });

    // Return success page
    return new NextResponse(
      `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsubscribed Successfully</title>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 600px;
      margin: 50px auto;
      padding: 20px;
      text-align: center;
      line-height: 1.6;
    }
    h1 { color: #059669; }
    .email { color: #6b7280; font-size: 0.9em; margin: 20px 0; }
    .message { color: #374151; margin: 20px 0; }
  </style>
</head>
<body>
  <h1>✓ Successfully Unsubscribed</h1>
  <div class="email">${recipient.contact.email}</div>
  <div class="message">
    <p>You have been unsubscribed and will no longer receive emails from us.</p>
    <p>If this was a mistake, please contact us to re-subscribe.</p>
  </div>
</body>
</html>`,
      {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      }
    );
  } catch (error) {
    console.error('[Unsubscribe] Error:', error);

    return new NextResponse(
      `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsubscribe Error</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
    h1 { color: #dc2626; }
  </style>
</head>
<body>
  <h1>Error</h1>
  <p>Sorry, we encountered an error processing your unsubscribe request.</p>
  <p>Please try again later or contact us for assistance.</p>
</body>
</html>`,
      {
        status: 500,
        headers: { 'Content-Type': 'text/html' },
      }
    );
  }
}
