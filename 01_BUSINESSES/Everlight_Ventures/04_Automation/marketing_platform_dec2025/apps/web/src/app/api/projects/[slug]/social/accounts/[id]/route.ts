/**
 * Social Media Account Management API
 * Delete a connected social media account
 */

import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import { logActivity } from '@/lib/activity-logger';
import prisma from '@/lib/prisma';

/**
 * DELETE /api/projects/[slug]/social/accounts/[id]
 * Disconnect a social media account
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { slug: string; id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { slug, id } = params;

    const project = await getProjectBySlug(slug, session.user.id);
    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 });
    }

    if (project.role === 'VIEWER') {
      return NextResponse.json({ error: 'Insufficient permissions' }, { status: 403 });
    }

    // Get account to verify it belongs to this project
    const account = await prisma.socialMediaAccount.findUnique({
      where: { id },
    });

    if (!account || account.projectId !== project.id) {
      return NextResponse.json({ error: 'Account not found' }, { status: 404 });
    }

    // Delete the account
    await prisma.socialMediaAccount.delete({
      where: { id },
    });

    // Log activity
    await logActivity({
      type: 'SOCIAL_ACCOUNT_DISCONNECTED',
      projectId: project.id,
      metadata: {
        platform: account.platform,
        accountName: account.platformUsername || account.displayName,
      },
    });

    return NextResponse.json({
      success: true,
      message: 'Social media account disconnected successfully',
    });
  } catch (error) {
    console.error('[Social Account Delete] Error:', error);
    return NextResponse.json(
      {
        error: 'Failed to disconnect social media account',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
