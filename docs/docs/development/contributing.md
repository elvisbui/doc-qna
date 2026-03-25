---
sidebar_position: 4
---

# Contributing

Contributions to doc-qna are welcome. Here's how to get started.

## Development Setup

1. Fork and clone the repository
2. Follow the [Installation guide](/docs/getting-started/installation) for local setup
3. Create a feature branch: `git checkout -b feature/my-feature`

## Code Style

### Python
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Linting**: `ruff` — run `make lint`
- **Type checking**: `pyright` — run `make typecheck`
- **Async**: use `async`/`await` throughout (FastAPI is async-first)

### TypeScript
- **Naming**: `camelCase` for functions/variables, `PascalCase` for components/types
- **Linting**: ESLint — run `cd frontend && npx eslint .`
- **Type checking**: `tsc` — run `cd frontend && npx tsc --noEmit`
- **Components**: functional React components with hooks
- **Exports**: use named exports

## Architecture Rules

- **Routers** handle only validation and response formatting — business logic goes in `services/`
- **Services** are pure Python — import from `core/`, `providers/`, `parsers/` only
- **Providers** implement Protocol classes from `providers/base.py`
- All API routes use the `/api/` prefix
- Environment config uses Pydantic `BaseSettings`

## Testing

- Write tests for new features in `backend/tests/` or colocated `__tests__/` directories
- Backend tests use pytest with async support
- Frontend tests use Vitest with React Testing Library
- Run `make test` before submitting a PR

## Pull Request Process

1. Ensure all tests pass: `make test`
2. Ensure linting passes: `make lint`
3. Ensure type checks pass: `make typecheck`
4. Write a clear PR description explaining the change
5. Reference any related issues

## Project Structure

See [Project Structure](/docs/getting-started/project-structure) for the full directory layout and design principles.
