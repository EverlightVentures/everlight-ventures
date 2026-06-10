import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import { prisma } from '@everlight/db';

export async function GET(
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

    const subscribedCount = await prisma.contact.count({
      where: {
        projectId: project.id,
        subscribed: true,
      },
    });

    return NextResponse.json({ subscribedCount });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch preview data' },
      { status: 500 }
    );
  }
}
