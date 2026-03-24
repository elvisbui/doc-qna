.PHONY: setup setup-docker dev test test-backend test-frontend build typecheck lint lint-backend lint-frontend format up down clean

# One-command local setup
setup:
	./setup.sh

# One-command Docker setup
setup-docker:
	./setup.sh docker

# Start backend (run frontend in a separate terminal: cd frontend && npm run dev)
dev:
	cd backend && uvicorn app.main:app --reload

# Run all tests
test: test-backend test-frontend

test-backend:
	cd backend && python3 -m pytest tests/ -v

test-frontend:
	cd frontend && npx vitest run

# Build production frontend + Docker image
build:
	cd frontend && npm run build
	docker build .

# TypeScript check
typecheck:
	cd frontend && npx tsc --noEmit

# Lint
lint: lint-backend lint-frontend

lint-backend:
	ruff check backend/

lint-frontend:
	cd frontend && npx tsc --noEmit && npx eslint src

# Format
format:
	ruff format backend/

# Docker
up:
	docker compose up --build -d

down:
	docker compose down

# Clean generated files
clean:
	rm -rf backend/.venv backend/__pycache__ backend/chroma_data backend/uploads
	rm -rf frontend/node_modules frontend/dist
