# {{PROJECT_NAME}} Style Guide

## Overview

This document defines the coding standards and conventions for {{PROJECT_NAME}}. All AI assistants (Claude, Gemini, Continue.dev) should adhere to these guidelines when generating or reviewing code.

---

## TypeScript Conventions

### General Rules

- Use TypeScript strict mode (`"strict": true` in tsconfig.json)
- Prefer `const` over `let`; never use `var`
- Use explicit type annotations for function parameters and return types
- Avoid `any`; use `unknown` when type is truly unknown

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Variables | camelCase | `userName`, `isActive` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_RETRIES`, `API_BASE_URL` |
| Functions | camelCase | `getUserById()`, `calculateTotal()` |
| Classes | PascalCase | `UserService`, `DataProcessor` |
| Interfaces | PascalCase (no "I" prefix) | `User`, `ApiResponse` |
| Types | PascalCase | `UserId`, `RequestConfig` |
| Enums | PascalCase | `Status`, `ErrorCode` |
| Files | kebab-case | `user-service.ts`, `api-client.ts` |

### Function Guidelines

```typescript
// ✅ Good: Explicit types, descriptive name, JSDoc
/**
 * Retrieves a user by their unique identifier.
 * @param userId - The user's unique ID
 * @returns The user object or null if not found
 * @throws {ValidationError} If userId is invalid
 */
async function getUserById(userId: string): Promise<User | null> {
  // Implementation
}

// ❌ Bad: Missing types, unclear name
async function get(id) {
  // Implementation
}
```

### Error Handling

```typescript
// ✅ Use custom error classes
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

// ✅ Use Result types for recoverable errors
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };
```

---

## Code Organization

### File Structure

```
src/
├── domain/           # Business logic, entities, value objects
│   ├── entities/
│   ├── services/
│   └── repositories/
├── application/      # Use cases, DTOs, mappers
│   ├── use-cases/
│   ├── dtos/
│   └── mappers/
├── infrastructure/   # External services, database, APIs
│   ├── database/
│   ├── http/
│   └── external/
├── shared/           # Shared utilities, types, constants
│   ├── utils/
│   ├── types/
│   └── constants/
└── tests/            # Test files mirroring src structure
    ├── unit/
    ├── integration/
    └── e2e/
```

### Import Order

```typescript
// 1. Node built-ins
import { readFile } from 'node:fs/promises';

// 2. External packages
import { z } from 'zod';
import express from 'express';

// 3. Internal absolute imports
import { UserService } from '@/domain/services';
import { validateRequest } from '@/shared/utils';

// 4. Relative imports
import { UserDto } from './dtos';
import type { CreateUserInput } from './types';
```

---

## Documentation

### JSDoc Requirements

All exported functions, classes, and types must have JSDoc documentation:

```typescript
/**
 * Service for managing user operations.
 *
 * @example
 * ```typescript
 * const userService = new UserService(repository);
 * const user = await userService.create({ name: 'John' });
 * ```
 */
export class UserService {
  /**
   * Creates a new user in the system.
   *
   * @param input - The user creation input
   * @returns The created user with generated ID
   * @throws {ValidationError} If input fails validation
   * @throws {DuplicateError} If email already exists
   */
  async create(input: CreateUserInput): Promise<User> {
    // Implementation
  }
}
```

---

## Testing Standards

### Test File Naming

- Unit tests: `*.test.ts` (co-located) or `tests/unit/*.test.ts`
- Integration tests: `tests/integration/*.integration.test.ts`
- E2E tests: `tests/e2e/*.e2e.test.ts`

### Test Structure

```typescript
describe('UserService', () => {
  describe('create', () => {
    it('should create a user with valid input', async () => {
      // Arrange
      const input = { name: 'John', email: 'john@example.com' };

      // Act
      const result = await userService.create(input);

      // Assert
      expect(result).toMatchObject({
        name: 'John',
        email: 'john@example.com',
      });
      expect(result.id).toBeDefined();
    });

    it('should throw ValidationError for invalid email', async () => {
      // Arrange
      const input = { name: 'John', email: 'invalid' };

      // Act & Assert
      await expect(userService.create(input))
        .rejects
        .toThrow(ValidationError);
    });
  });
});
```

---

## Git Conventions

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`

Examples:
```
feat(auth): add OAuth2 login support
fix(api): handle null response from external service
docs(readme): update installation instructions
refactor(user-service): extract validation logic
```

### Branch Naming

Format: `<user>/<linear-id>-<description>`

Examples:
```
clduab11/PAR-123-add-user-auth
clduab11/PAR-456-fix-api-timeout
```

---

## Performance Guidelines

- Prefer `Map` and `Set` over plain objects for dynamic collections
- Use `Promise.all()` for parallel async operations
- Implement pagination for list endpoints (default: 20, max: 100)
- Cache expensive computations and external API calls
- Use database indexes for frequently queried fields

---

## Security Checklist

- [ ] Validate and sanitize all user input
- [ ] Use parameterized queries (no string concatenation)
- [ ] Implement rate limiting on public endpoints
- [ ] Never log sensitive data (passwords, tokens, PII)
- [ ] Use environment variables for secrets
- [ ] Enable CORS with specific origins only
- [ ] Implement proper authentication and authorization
