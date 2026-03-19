#!/usr/bin/env bash
# doc-qna setup script
# Usage:
#   ./setup.sh          — local development setup
#   ./setup.sh docker   — Docker setup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; }

# ── Docker path ──────────────────────────────────────────────────────────────
if [ "${1:-}" = "docker" ]; then
    info "Starting doc-qna with Docker Compose..."

    if ! command -v docker &>/dev/null; then
        error "Docker is not installed. Get it at https://docs.docker.com/get-docker/"
        exit 1
    fi

    if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
        cp "$SCRIPT_DIR/backend/.env.example" "$SCRIPT_DIR/backend/.env"
        info "Created backend/.env from .env.example (defaults to Ollama — no API keys needed)"
    fi

    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up --build -d
    info "Pulling Ollama models (first run only, may take a few minutes)..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" exec ollama ollama pull llama3.2 || warn "Could not pull llama3.2 — pull it manually later"
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" exec ollama ollama pull nomic-embed-text || warn "Could not pull nomic-embed-text"

    echo ""
    info "doc-qna is running at http://localhost:8000"
    info "Stop with: docker compose down"
    exit 0
fi

# ── Local development path ───────────────────────────────────────────────────
echo ""
echo "  doc-qna — local development setup"
echo "  ================================="
echo ""

# Check prerequisites
MISSING=()

if ! command -v python3 &>/dev/null; then
    MISSING+=("python3 (3.13+)")
else
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 13 ]; }; then
        error "Python $PY_VERSION found, but 3.13+ is required"
        exit 1
    fi
    info "Python $PY_VERSION detected"
fi

if ! command -v node &>/dev/null; then
    MISSING+=("node (20+)")
else
    NODE_MAJOR=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 20 ]; then
        error "Node $(node -v) found, but v20+ is required"
        exit 1
    fi
    info "Node $(node -v) detected"
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    error "Missing prerequisites: ${MISSING[*]}"
    echo "  Install them and re-run this script."
    exit 1
fi

# 1. Backend setup
info "Setting up backend..."

(
    cd "$SCRIPT_DIR/backend"

    if [ ! -d .venv ]; then
        python3 -m venv .venv
        info "Created Python virtual environment"
    fi

    .venv/bin/pip install -q -e ".[dev]"
    info "Installed Python dependencies (editable mode)"

    if [ ! -f .env ]; then
        cp .env.example .env
        info "Created .env from .env.example (defaults to Ollama — no API keys needed)"
    fi
)

# 2. Frontend setup
info "Setting up frontend..."

(
    cd "$SCRIPT_DIR/frontend"
    npm install --silent
    info "Installed Node dependencies"
)

# 3. Check Ollama
echo ""
if command -v ollama &>/dev/null; then
    info "Ollama detected. Pulling models..."
    ollama pull llama3.2 2>/dev/null || warn "Could not pull llama3.2 — run: ollama pull llama3.2"
    ollama pull nomic-embed-text 2>/dev/null || warn "Could not pull nomic-embed-text — run: ollama pull nomic-embed-text"
else
    warn "Ollama not found. Install it from https://ollama.com to use local LLMs (free)."
    warn "Or set OPENAI_API_KEY or ANTHROPIC_API_KEY in backend/.env to use cloud providers."
fi

# 4. Done
echo ""
info "Setup complete! Start the app:"
echo ""
echo "  Terminal 1 (backend):"
echo "    cd backend && source .venv/bin/activate"
echo "    uvicorn app.main:app --reload"
echo ""
echo "  Terminal 2 (frontend dev server):"
echo "    cd frontend && npm run dev"
echo ""
echo "  Then open http://localhost:5173"
echo ""
echo "  Or use the CLI (installed as 'doc-qna' command):"
echo "    cd backend && source .venv/bin/activate"
echo "    doc-qna serve"
echo ""
