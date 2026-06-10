import { getServerSession } from 'next-auth';
import { authOptions } from './auth';
import { prisma } from '@everlight/db';
import { redirect } from 'next/navigation';

export async function getCurrentUser() {
  const session = await getServerSession(authOptions);
  return session?.user;
}

export async function requireAuth() {
  const user = await getCurrentUser();
  if (!user?.id) {
    redirect('/auth/signin');
  }
  return user;
}

export async function getUserProjects(userId: string) {
  return prisma.project.findMany({
    where: {
      members: {
        some: {
          userId,
        },
      },
    },
    include: {
      members: {
        where: { userId },
        select: { role: true },
      },
      _count: {
        select: {
          contacts: true,
          campaigns: true,
        },
      },
    },
    orderBy: {
      updatedAt: 'desc',
    },
  });
}

export async function getProjectBySlug(slug: string, userId: string) {
  const project = await prisma.project.findUnique({
    where: { slug },
    include: {
      members: {
        where: { userId },
        select: { role: true },
      },
    },
  });

  if (!project || project.members.length === 0) {
    return null;
  }

  return {
    ...project,
    role: project.members[0].role,
  };
}
