import { PrismaClient } from '@prisma/client';
import { hash } from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding database...');

  // Create a demo user
  const passwordHash = await hash('demo123', 10);
  const user = await prisma.user.upsert({
    where: { email: 'demo@everlight.dev' },
    update: {},
    create: {
      email: 'demo@everlight.dev',
      name: 'Demo User',
      passwordHash,
      emailVerified: true,
    },
  });

  console.log('✅ Created user:', user.email);

  // Create a demo project
  const project = await prisma.project.upsert({
    where: { slug: 'demo-project' },
    update: {},
    create: {
      name: 'Demo Project',
      slug: 'demo-project',
      description: 'A demo project for testing',
    },
  });

  console.log('✅ Created project:', project.name);

  // Add user as owner of the project
  await prisma.projectMember.upsert({
    where: {
      projectId_userId: {
        projectId: project.id,
        userId: user.id,
      },
    },
    update: {},
    create: {
      projectId: project.id,
      userId: user.id,
      role: 'OWNER',
    },
  });

  console.log('✅ Added user as project owner');

  // Create some demo contacts
  const contacts = [
    {
      email: 'alice@example.com',
      firstName: 'Alice',
      lastName: 'Anderson',
      company: 'Acme Corp',
      tags: ['vip', 'customer'],
    },
    {
      email: 'bob@example.com',
      firstName: 'Bob',
      lastName: 'Builder',
      company: 'BuildCo',
      tags: ['prospect'],
    },
    {
      email: 'carol@example.com',
      firstName: 'Carol',
      lastName: 'Chen',
      company: 'TechStart',
      tags: ['customer'],
    },
  ];

  for (const contact of contacts) {
    await prisma.contact.upsert({
      where: {
        projectId_email: {
          projectId: project.id,
          email: contact.email,
        },
      },
      update: {},
      create: {
        ...contact,
        projectId: project.id,
      },
    });
  }

  console.log(`✅ Created ${contacts.length} contacts`);

  // Create a demo campaign
  const campaign = await prisma.campaign.create({
    data: {
      name: 'Welcome Campaign',
      subject: 'Welcome to Everlight Ventures!',
      htmlContent: '<h1>Welcome!</h1><p>Thanks for joining us.</p>',
      textContent: 'Welcome! Thanks for joining us.',
      status: 'DRAFT',
      projectId: project.id,
    },
  });

  console.log('✅ Created campaign:', campaign.name);

  // Log activity
  await prisma.activity.create({
    data: {
      type: 'PROJECT_CREATED',
      projectId: project.id,
      userId: user.id,
      metadata: { name: project.name },
    },
  });

  console.log('✅ Seeding completed!');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
