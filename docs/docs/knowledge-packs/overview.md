---
sidebar_position: 1
---

# Knowledge Packs

Knowledge packs are bundled document collections that users can browse and install from the UI. They provide pre-curated content with metadata and suggested starter queries.

## What's in a Pack?

A knowledge pack is a directory containing:

```
packs/my-pack/
├── manifest.json           # Pack metadata
├── suggested_queries.json  # Starter questions
└── documents/              # Document files (PDF, DOCX, MD, TXT)
    ├── intro.md
    ├── guide.pdf
    └── reference.md
```

## Using Packs

### From the UI

1. Navigate to the **Packs** tab
2. Browse available packs with descriptions
3. Click **Install** on a pack
4. Documents are automatically ingested
5. Suggested queries appear in the Chat page

### From the API

```bash
# List available packs
curl http://localhost:8000/api/packs

# Install a pack
curl -X POST http://localhost:8000/api/packs/install \
  -H "Content-Type: application/json" \
  -d '{"packId": "python-basics"}'
```

## Built-in Packs

doc-qna ships with sample packs:

| Pack | Description |
|------|-------------|
| **python-basics** | Python language fundamentals |
| **ml-basics** | Machine learning concepts |

## Pack Registry

Packs are discovered from the directory specified by `PACKS_DIR` (default: `../packs`). A `registry.json` tracks installed packs.

The registry supports both **local** and **remote** pack sources, enabling community-contributed packs.
