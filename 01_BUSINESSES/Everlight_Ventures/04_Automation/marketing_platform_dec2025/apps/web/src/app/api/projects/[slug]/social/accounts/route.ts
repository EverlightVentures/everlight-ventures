/**
 * Social Media Accounts API
 * Get connected social media accounts for a project
 */

import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import prisma from '@/lib/prisma';

/**
 * GET /api/projects/[slug]/social/accounts
 * Get all connected social media accounts
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { slug } = params;

    const project = await getProjectBySlug(slug, session.user.id);
    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 });
    }

    // Fetch all social media accounts for this project
    const accounts = await prisma.socialMediaAccount.findMany({
      where: {
        projectId: project.id,
      },
      select: {
        id: true,
        platform: true,
        platformUsername: true,
        displayName: true,
        profileImageUrl: true,
        status: true,
        lastSyncedAt: true,
        createdAt: true,
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    return NextResponse.json({
      success: true,
      accounts,
    });
  } catch (error) {
    console.error('[Social Accounts] Error:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch social media accounts',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
