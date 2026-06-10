import { redirect } from 'next/navigation';
import { requireAuth, getUserProjects } from '@/lib/session';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@everlight/ui';
import Link from 'next/link';

export default async function DashboardPage() {
  const user = await requireAuth();
  const projects = await getUserProjects(user.id);

  if (projects.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Welcome to Everlight Ventures</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">
              You don't have any projects yet. Create your first project to get started.
            </p>
            <Link href="/projects/new">
              <Button className="w-full">Create Project</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (projects.length === 1) {
    redirect(`/projects/${projects[0].slug}`);
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold">Your Projects</h1>
          <Link href="/projects/new">
            <Button>New Project</Button>
          </Link>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.slug}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <CardTitle>{project.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  {project.description && (
                    <p className="text-sm text-gray-600 mb-4">{project.description}</p>
                  )}
                  <div className="flex gap-4 text-sm text-gray-500">
                    <span>{project._count.contacts} contacts</span>
                    <span>{project._count.campaigns} campaigns</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-400">
                    Role: {project.members[0].role.toLowerCase()}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
