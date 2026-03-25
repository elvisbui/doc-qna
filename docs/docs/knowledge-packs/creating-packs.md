---
sidebar_position: 2
---

# Creating Knowledge Packs

You can create custom knowledge packs to bundle documents for easy distribution and installation.

## Directory Structure

Create a new directory in the `packs/` folder:

```
packs/my-pack/
├── manifest.json
├── suggested_queries.json
└── documents/
    ├── doc1.md
    ├── doc2.pdf
    └── doc3.txt
```

## manifest.json

```json
{
  "id": "my-pack",
  "name": "My Knowledge Pack",
  "description": "A collection of documents about my topic",
  "version": "1.0.0",
  "author": "Your Name",
  "tags": ["topic1", "topic2"],
  "documents": [
    {
      "filename": "doc1.md",
      "title": "Introduction",
      "description": "Overview of the topic"
    },
    {
      "filename": "doc2.pdf",
      "title": "Deep Dive",
      "description": "Detailed analysis"
    }
  ]
}
```

## suggested_queries.json

Provide starter questions that work well with the pack's content:

```json
{
  "queries": [
    "What are the key concepts covered in this collection?",
    "Explain the relationship between X and Y",
    "What are the best practices for Z?",
    "Summarize the main findings"
  ]
}
```

These queries appear in the Chat page after the pack is installed, helping users get started.

## Supported Document Formats

- **Markdown** (`.md`) — best for structured text
- **PDF** (`.pdf`) — supports page-number citations
- **DOCX** (`.docx`) — Microsoft Word documents
- **Plain text** (`.txt`) — simple text files

## Distribution

Packs can be distributed as `.tar.gz` archives:

```bash
cd packs
tar -czf my-pack.tar.gz my-pack/
```

Users can extract the archive into their `packs/` directory, or the pack registry can fetch from remote URLs.

## Tips

- Keep documents focused on a specific topic for better retrieval quality
- Write suggested queries that exercise different parts of the content
- Include a mix of overview and detailed documents
- Test your pack by installing it and asking the suggested queries
