import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import { prisma } from '@everlight/db';
import { Resend } from 'resend';
import { processEmailForSending, stripHTMLTags } from '@/lib/email-tracking';
import { publishCampaignToSocialMedia } from '@/lib/social-media/publisher';

export async function POST(
  req: Request,
  { params }: { params: { slug: string; id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const project = await getProjectBySlug(params.slug, session.user.id);
    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 });
    }

    if (project.role === 'VIEWER') {
      return NextResponse.json({ error: 'Insufficient permissions' }, { status: 403 });
    }

    const campaign = await prisma.campaign.findFirst({
      where: {
        id: params.id,
        projectId: project.id,
      },
    });

    if (!campaign) {
      return NextResponse.json({ error: 'Campaign not found' }, { status: 404 });
    }

    if (campaign.status !== 'DRAFT') {
      return NextResponse.json(
        { error: 'Campaign has already been sent' },
        { status: 400 }
      );
    }

    const contacts = await prisma.contact.findMany({
      where: {
        projectId: project.id,
        subscribed: true,
      },
    });

    if (contacts.length === 0) {
      return NextResponse.json(
        { error: 'No subscribed contacts to send to' },
        { status: 400 }
      );
    }

    // Get base URL for tracking links
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';

    // Create recipient records individually (we need their IDs for tracking)
    const recipients = await Promise.all(
      contacts.map((contact) =>
        prisma.campaignRecipient.create({
          data: {
            campaignId: campaign.id,
            contactId: contact.id,
            status: 'PENDING',
          },
        })
      )
    );

    // Create a map of contact ID to recipient ID
    const contactToRecipient = new Map(
      recipients.map((r) => [r.contactId, r.id])
    );

    // Update campaign status to SENDING
    await prisma.campaign.update({
      where: { id: campaign.id },
      data: {
        status: 'SENDING',
      },
    });

    // Send emails via Resend
    const resend = new Resend(process.env.RESEND_API_KEY);
    const fromEmail = process.env.EMAIL_FROM || 'noreply@everlight.dev';

    console.log(`Sending campaign "${campaign.name}" to ${contacts.length} recipients...`);

    // Prepare UTM parameters
    const utmParams = {
      utmSource: campaign.utmSource,
      utmMedium: campaign.utmMedium,
      utmCampaign: campaign.utmCampaign,
      utmContent: campaign.utmContent,
    };

    // Send emails to all contacts
    const sendResults = await Promise.allSettled(
      contacts.map(async (contact) => {
        const recipientId = contactToRecipient.get(contact.id);
        if (!recipientId) {
          throw new Error('Recipient ID not found');
        }

        try {
          // Process HTML with tracking (pixel, link rewriting, UTM params)
          const processedHtml = processEmailForSending(
            campaign.htmlContent,
            recipientId,
            baseUrl,
            utmParams
          );

          // Generate plain text
          const plainText = campaign.textContent || stripHTMLTags(campaign.htmlContent);

          // In dev mode, just log instead of sending
          if (process.env.NODE_ENV === 'development') {
            console.log(`📧 [DEV] Would send to: ${contact.email} - ${campaign.subject}`);
            console.log(`📧 [DEV] Tracking enabled: recipientId=${recipientId}`);

            await prisma.campaignRecipient.update({
              where: { id: recipientId },
              data: {
                status: 'SENT',
                sentAt: new Date(),
              },
            });

            return { success: true, email: contact.email };
          }

          // Production: Send via Resend with tracking
          const result = await resend.emails.send({
            from: fromEmail,
            to: contact.email,
            subject: campaign.subject,
            html: processedHtml,
            text: plainText,
          });

          // Update recipient status to SENT
          await prisma.campaignRecipient.update({
            where: { id: recipientId },
            data: {
              status: 'SENT',
              sentAt: new Date(),
            },
          });

          console.log(`✅ Sent to ${contact.email} (tracking: ${recipientId})`);
          return { success: true, email: contact.email, id: result.id };
        } catch (error: any) {
          console.error(`❌ Failed to send to ${contact.email}:`, error.message);

          // Update recipient status to FAILED
          await prisma.campaignRecipient.update({
            where: { id: recipientId },
            data: {
              status: 'FAILED',
              failedAt: new Date(),
              errorMsg: error.message,
            },
          });

          return { success: false, email: contact.email, error: error.message };
        }
      })
    );

    // Count successes and failures
    const successCount = sendResults.filter(
      (result) => result.status === 'fulfilled' && result.value.success
    ).length;
    const failureCount = sendResults.length - successCount;

    // Update campaign as sent
    await prisma.campaign.update({
      where: { id: campaign.id },
      data: {
        status: 'SENT',
        sentAt: new Date(),
      },
    });

    await prisma.activity.create({
      data: {
        type: 'CAMPAIGN_SENT',
        projectId: project.id,
        userId: session.user.id,
        metadata: {
          campaignName: campaign.name,
          recipientCount: contacts.length,
        },
      },
    });

    // Post to social media if enabled (non-blocking)
    if (campaign.enableSocialPosting) {
      console.log('📱 Publishing campaign to social media...');
      publishCampaignToSocialMedia({
        ...campaign,
        project: { id: project.id, slug: params.slug },
      }).catch((error) => {
        console.error('❌ Social media publishing failed (non-blocking):', error);
        // Don't fail the request - social media errors are logged separately
      });
    }

    return NextResponse.json({
      success: true,
      recipientCount: contacts.length,
      successCount,
      failureCount,
      message:
        process.env.NODE_ENV === 'development'
          ? 'Campaign sent successfully (logged to console in dev mode)'
          : `Campaign sent: ${successCount} successful, ${failureCount} failed`,
    });
  } catch (error) {
    console.error('Failed to send campaign:', error);
    return NextResponse.json(
      { error: 'Failed to send campaign' },
      { status: 500 }
    );
  }
}
