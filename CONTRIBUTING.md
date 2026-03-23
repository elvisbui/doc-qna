# Contributing Knowledge Packs

Thank you for your interest in contributing a knowledge pack to doc-qna. This guide explains how to create, validate, and submit a pack.

## What Is a Knowledge Pack?

A knowledge pack is a `.tar.gz` archive that bundles a set of documents with a `manifest.json` descriptor. Once loaded, users can ask questions against the pack's content using the doc-qna interface.

## Directory Structure

A pack archive must follow this layout:

```
<pack-name>/
  manifest.json
  doc1.pdf
  doc2.md
  ...
```

The top-level directory inside the archive **must** match the `name` field in `manifest.json`.

## Manifest Format

Every pack must include a `manifest.json` at the root of its directory. The manifest follows this schema:

```json
{
  "name": "my-pack",
  "version": "1.0.0",
  "description": "A short description of what this pack covers.",
  "author": "Your Name or Organisation",
  "license": "CC-BY-4.0",
  "documents": [
    "doc1.pdf",
    "doc2.md"
  ],
  "doc_count": 2
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Short identifier using lowercase letters, numbers, and hyphens (e.g. `python-docs`). Must be non-empty. |
| `version` | Semantic version string (e.g. `1.0.0`). Must be non-empty. |
| `documents` | List of relative paths to every document inside the pack directory. |
| `doc_count` | Integer matching the length of the `documents` list. |

### Optional Fields

| Field | Description |
|-------|-------------|
| `description` | Human-readable summary of the pack's contents. |
| `author` | Author or organisation name. |
| `license` | SPDX license identifier (see Licensing below). |
| `created_at` | ISO 8601 timestamp. Auto-generated if omitted. |

## Pack Naming Conventions

- Use **lowercase** letters, numbers, and hyphens only (e.g. `react-docs`, `aws-s3-guide`).
- Choose a descriptive, unique name that reflects the subject matter.
- Avoid generic names like `docs` or `test-pack`.
- Prefix with a topic area when appropriate (e.g. `python-stdlib`, `k8s-networking`).

## Licensing Requirements

All pack content **must be freely redistributable**. By submitting a pack you confirm that:

1. You have the right to redistribute every document in the pack.
2. The content is available under an open license. Acceptable licenses include (but are not limited to):
   - `CC-BY-4.0` / `CC-BY-SA-4.0` / `CC0-1.0`
   - `MIT` / `Apache-2.0`
   - Public domain
3. The `license` field in `manifest.json` contains a valid [SPDX identifier](https://spdx.org/licenses/).
4. No document contains proprietary, confidential, or personally identifiable information.

Packs that do not meet these requirements will not be merged.

## Quality Guidelines

- **Relevance** -- Documents should be focused on a coherent topic. Avoid mixing unrelated subjects in a single pack.
- **Accuracy** -- Content should be up-to-date and factually correct.
- **File formats** -- Supported formats are PDF, DOCX, Markdown (`.md`), and plain text (`.txt`).
- **Size** -- Keep individual documents under 50 MB and total pack size under 200 MB. If your content is larger, split it into multiple packs.
- **No duplicates** -- Check existing packs before submitting. If your content overlaps with an existing pack, consider contributing improvements to that pack instead.
- **Encoding** -- All text files must use UTF-8 encoding.

## Creating a Pack Archive

```bash
# 1. Create the pack directory
mkdir my-pack
cp doc1.pdf doc2.md my-pack/

# 2. Create manifest.json inside the directory
cat > my-pack/manifest.json <<'EOF'
{
  "name": "my-pack",
  "version": "1.0.0",
  "description": "Example knowledge pack",
  "author": "Your Name",
  "license": "CC-BY-4.0",
  "documents": ["doc1.pdf", "doc2.md"],
  "doc_count": 2
}
EOF

# 3. Create the tar.gz archive
tar -czf my-pack.tar.gz my-pack/
```

## Validating Your Pack

Before submitting, run the validation script to catch common errors:

```bash
python scripts/validate_pack.py my-pack.tar.gz
```

The script checks that:
- The archive is a valid `.tar.gz` file.
- A `manifest.json` is present and parseable.
- Required fields (`name`, `version`) are non-empty.
- All listed documents exist in the archive.
- `doc_count` matches the number of listed documents.

Fix any reported errors before opening a pull request.

## Submitting a Pack

1. **Fork** this repository.
2. **Add** your `.tar.gz` pack file to the `packs/` directory.
3. **Validate** the pack using the validation script (see above).
4. **Open a pull request** against the `main` branch with:
   - A clear title, e.g. "Add python-stdlib pack v1.0.0".
   - A short description of the pack's contents and source.
   - Confirmation that the content is freely redistributable.
5. A maintainer will review the pack and may request changes.

## Updating an Existing Pack

To update a pack you previously contributed:

1. Bump the `version` field in `manifest.json`.
2. Update the `documents` list and `doc_count` if files were added or removed.
3. Rebuild the `.tar.gz` archive.
4. Open a pull request replacing the old archive in `packs/`.
