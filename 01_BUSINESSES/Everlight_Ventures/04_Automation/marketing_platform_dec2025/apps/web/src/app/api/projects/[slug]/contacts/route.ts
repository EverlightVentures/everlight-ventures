import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getProjectBySlug } from '@/lib/session';
import { prisma } from '@everlight/db';
import { z } from 'zod';

const createContactSchema = z.object({
  email: z.string().email(),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  company: z.string().optional(),
  phone: z.string().optional(),
  tags: z.array(z.string()).default([]),
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
    const data = createContactSchema.parse(body);

    const existingContact = await prisma.contact.findUnique({
      where: {
        projectId_email: {
          projectId: project.id,
          email: data.email,
        },
      },
    });

    if (existingContact) {
      return NextResponse.json(
        { error: 'Contact with this email already exists' },
        { status: 400 }
      );
    }

    const contact = await prisma.contact.create({
      data: {
        ...data,
        projectId: project.id,
      },
    });

    await prisma.activity.create({
      data: {
        type: 'CONTACT_CREATED',
        projectId: project.id,
        userId: session.user.id,
        metadata: { email: contact.email },
      },
    });

    return NextResponse.json({ contact });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to create contact' },
      { status: 500 }
    );
  }
}
