# Contributing to Everlight Ventures

Thank you for your interest in contributing to Everlight Ventures! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/everlight-ventures.git
   cd everlight-ventures
   ```
3. **Set up the development environment**:
   ```bash
   make setup
   # or
   bash scripts/setup.sh
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests

### 2. Make Your Changes

- Write clean, readable code
- Follow the existing code style
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run the development server
make dev

# Test manually in browser
# Check health endpoint
make health

# Run tests (when available)
make test

# Lint your code
make lint
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: add user profile page"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style Guidelines

### TypeScript

- Use TypeScript strict mode
- Define types for all function parameters and return values
- Avoid `any` type when possible
- Use interfaces for object shapes
- Use enums for fixed sets of values

Example:
```typescript
interface User {
  id: string;
  email: string;
  name?: string;
}

async function getUser(id: string): Promise<User> {
  // Implementation
}
```

### React Components

- Use functional components
- Use TypeScript for props
- Prefer server components when possible
- Use `'use client'` only when needed

Example:
```typescript
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}

export function Button({ label, onClick, variant = 'primary' }: ButtonProps) {
  return (
    <button onClick={onClick} className={variant}>
      {label}
    </button>
  );
}
```

### API Routes

- Validate input with Zod
- Handle errors properly
- Return consistent error format
- Check authentication and authorization

Example:
```typescript
import { z } from 'zod';

const schema = z.object({
  email: z.string().email(),
  name: z.string().min(1),
});

export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await req.json();
    const data = schema.parse(body);

    // Process data...

    return NextResponse.json({ success: true });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid input', details: error.errors },
        { status: 400 }
      );
    }
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

### Database

- Always scope queries to projectId for multi-tenancy
- Use transactions for related operations
- Add indexes for frequently queried fields
- Use Prisma's type-safe queries

Example:
```typescript
// ✅ Good - scoped to project
const contacts = await prisma.contact.findMany({
  where: { projectId: authorizedProjectId },
});

// ❌ Bad - not scoped to project
const contacts = await prisma.contact.findMany();
```

## Project Structure

When adding new features, follow these conventions:

### Adding a New Page

1. Create page in `apps/web/src/app/`
2. Use server components by default
3. Fetch data in the component
4. Handle loading and error states

### Adding a New API Route

1. Create route in `apps/web/src/app/api/`
2. Export GET, POST, etc. as needed
3. Add Zod validation schema
4. Check authentication and authorization
5. Return consistent error format

### Adding a New Component

1. Small, reusable components → `packages/ui/`
2. App-specific components → `apps/web/src/components/`
3. Export from index file
4. Add TypeScript types

### Adding a Database Model

1. Add to `packages/db/schema.prisma`
2. Run `npm run db:generate`
3. Create migration: `npm run db:migrate`
4. Update seed script if needed

## Testing

When tests are set up:

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

## Documentation

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for technical changes
- Add JSDoc comments for complex functions
- Update API documentation

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Linting passes
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] Changes are focused (one feature/fix per PR)

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe how you tested your changes

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests
- [ ] All tests pass
```

## Common Tasks

### Adding a New Database Field

```bash
# 1. Edit packages/db/schema.prisma
# Add your field to the model

# 2. Generate Prisma client
npm run db:generate

# 3. Create migration
npm run db:migrate

# 4. Update seed script if needed
# Edit packages/db/seed.ts
```

### Adding a New UI Component

```bash
# 1. Create component file
# packages/ui/your-component.tsx

# 2. Export from index
# Add to packages/ui/index.tsx

# 3. Use in your app
# import { YourComponent } from '@everlight/ui'
```

### Debugging

```bash
# View database in Prisma Studio
make db-studio

# Check health endpoint
make health

# View Docker logs
make docker-logs

# Reset database (WARNING: destroys data)
make db-reset
```

## Questions?

- Check existing issues and discussions
- Read the documentation (README, ARCHITECTURE)
- Ask in discussions or create an issue

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Give and receive constructive feedback
- Focus on what's best for the project

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

---

Thank you for contributing! 🎉
