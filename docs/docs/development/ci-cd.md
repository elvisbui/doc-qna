---
sidebar_position: 3
---

# CI/CD

doc-qna uses GitHub Actions for continuous integration with five parallel jobs.

## Pipeline Overview

The CI workflow (`.github/workflows/ci.yml`) runs on every push and pull request:

| Job | What It Does |
|-----|-------------|
| **lint** | Python (ruff) + TypeScript (eslint) linting |
| **typecheck** | Python (pyright) + TypeScript (tsc) type checking |
| **backend-test** | `python3 -m pytest` |
| **frontend-test** | `npx vitest run` |
| **docker-build** | Verifies the Docker image builds successfully |

All five jobs run in parallel for fast feedback.

## Running Locally

Use the Makefile to run the same checks locally:

```bash
make lint       # Lint Python + TypeScript
make typecheck  # Type-check Python + TypeScript
make test       # Run all tests
make build      # Build frontend + Docker image
```

## Workflow Configuration

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: pip install ruff
      - run: ruff check backend/
      - run: cd frontend && npm ci && npx eslint .

  # ... typecheck, backend-test, frontend-test, docker-build
```

## Status Badges

CI status badges are displayed in the project's README:

```markdown
![CI](https://github.com/elvisbui/doc-qna/actions/workflows/ci.yml/badge.svg)
```
