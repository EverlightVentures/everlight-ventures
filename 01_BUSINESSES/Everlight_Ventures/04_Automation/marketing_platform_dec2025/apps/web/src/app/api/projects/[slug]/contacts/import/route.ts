import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import { prisma } from '@everlight/db';
import { z } from 'zod';

const importContactSchema = z.object({
  contacts: z.array(
    z.object({
      email: z.string().email(),
      firstName: z.string().optional(),
      lastName: z.string().optional(),
      company: z.string().optional(),
      phone: z.string().optional(),
      tags: z.union([z.array(z.string()), z.string()]).optional(),
    })
  ),
});

export async function POST(
  req: Request,
  { params }: { params: { slug: string } }
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

    const body = await req.json();
    const { contacts } = importContactSchema.parse(body);

    const results = await Promise.allSettled(
      contacts.map(async (contactData) => {
        const tags = Array.isArray(contactData.tags)
          ? contactData.tags
          : typeof contactData.tags === 'string'
          ? contactData.tags.split(',').map((t) => t.trim()).filter(Boolean)
          : [];

        return prisma.contact.upsert({
          where: {
            projectId_email: {
              projectId: project.id,
              email: contactData.email,
            },
          },
          update: {
            firstName: contactData.firstName,
            lastName: contactData.lastName,
            company: contactData.company,
            phone: contactData.phone,
            tags,
          },
          create: {
            email: contactData.email,
            firstName: contactData.firstName,
            lastName: contactData.lastName,
            company: contactData.company,
            phone: contactData.phone,
            tags,
            projectId: project.id,
          },
        });
      })
    );

    const successful = results.filter((r) => r.status === 'fulfilled').length;
    const failed = results.filter((r) => r.status === 'rejected').length;

    await prisma.activity.create({
      data: {
        type: 'CONTACT_IMPORTED',
        projectId: project.id,
        userId: session.user.id,
        metadata: { count: successful, failed },
      },
    });

    return NextResponse.json({
      count: successful,
      failed,
      message: `Imported ${successful} contacts${failed > 0 ? `, ${failed} failed` : ''}`,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to import contacts' },
      { status: 500 }
    );
  }
}
