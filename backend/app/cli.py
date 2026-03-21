"""CLI entrypoint for doc-qna — built with Typer + Rich.

Run via:
    cd backend && python -m app
    # or, after `pip install -e .`:
    doc-qna --help
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="doc-qna",
    help="RAG document Q&A system — upload documents, ask questions, get cited answers.",
    no_args_is_help=True,
)

console = Console()


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------
@app.command()
def ingest(
    path: Annotated[
        Path,
        typer.Argument(help="File or directory to ingest."),
    ],
    chunk_size: Annotated[
        int | None,
        typer.Option("--chunk-size", help="Maximum characters per chunk."),
    ] = None,
    chunk_overlap: Annotated[
        int | None,
        typer.Option("--chunk-overlap", help="Overlap characters between chunks."),
    ] = None,
) -> None:
    """Ingest documents into the vector store."""
    from app.config import get_settings
    from app.core.constants import CHUNK_OVERLAP, CHUNK_SIZE
    from app.core.exceptions import DocumentProcessingError, UnsupportedFileTypeError
    from app.core.models import Document
    from app.parsers import SUPPORTED_FILE_TYPES
    from app.services.ingestion import ingest_document

    resolved = path.resolve()

    # Collect files to ingest
    if resolved.is_dir():
        files = [f for f in sorted(resolved.iterdir()) if f.is_file() and f.suffix.lower() in SUPPORTED_FILE_TYPES]
        if not files:
            console.print(
                f"[bold red]Error:[/bold red] No supported files found in {resolved}\n"
                f"Supported types: {', '.join(sorted(SUPPORTED_FILE_TYPES))}"
            )
            raise typer.Exit(code=1)
    elif resolved.is_file():
        if resolved.suffix.lower() not in SUPPORTED_FILE_TYPES:
            console.print(
                f"[bold red]Error:[/bold red] Unsupported file type '{resolved.suffix}'\n"
                f"Supported types: {', '.join(sorted(SUPPORTED_FILE_TYPES))}"
            )
            raise typer.Exit(code=1)
        files = [resolved]
    else:
        console.print(f"[bold red]Error:[/bold red] Path not found: {resolved}")
        raise typer.Exit(code=1)

    settings = get_settings()

    # Apply chunk size/overlap overrides
    effective_chunk_size = chunk_size if chunk_size is not None else CHUNK_SIZE
    effective_chunk_overlap = chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP

    if effective_chunk_overlap >= effective_chunk_size:
        console.print("[bold red]Error:[/bold red] chunk-overlap must be less than chunk-size.")
        raise typer.Exit(code=1)

    total_chunks = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for file_path in files:
            task = progress.add_task(f"Ingesting {file_path.name}...", total=None)
            doc = Document(
                filename=file_path.name,
                file_type=file_path.suffix.lower(),
                file_size=file_path.stat().st_size,
            )
            try:
                chunks = asyncio.run(
                    ingest_document(
                        file_path,
                        doc,
                        settings,
                        chunk_size=effective_chunk_size if chunk_size is not None else None,
                        chunk_overlap=effective_chunk_overlap if chunk_overlap is not None else None,
                    )
                )
                n = len(chunks)
                total_chunks += n
                progress.update(task, description=f"[green]Done:[/green] {file_path.name} — {n} chunks")
                progress.stop_task(task)
            except (DocumentProcessingError, UnsupportedFileTypeError) as exc:
                progress.update(task, description=f"[red]Failed:[/red] {file_path.name}")
                progress.stop_task(task)
                console.print(f"  [red]{exc}[/red]")
            except Exception as exc:  # noqa: BLE001
                progress.update(task, description=f"[red]Failed:[/red] {file_path.name}")
                progress.stop_task(task)
                console.print(f"  [red]Unexpected error: {exc}[/red]")

    console.print(
        f"\n[bold]Ingestion complete.[/bold] {len(files)} file(s) processed, {total_chunks} total chunks created."
    )


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------
@app.command()
def query(
    question: Annotated[str, typer.Argument(help="The question to ask")],
) -> None:
    """Ask a question and get a cited answer."""
    from rich.panel import Panel
    from rich.table import Table

    if not question.strip():
        console.print("[bold red]Error:[/bold red] Question cannot be empty.")
        raise typer.Exit(code=1)

    async def _run() -> None:
        from app.config import get_settings
        from app.services.confidence import calculate_confidence, should_abstain
        from app.services.generation import ABSTAIN_MESSAGE, build_context, get_llm_provider
        from app.services.retrieval import retrieve_relevant_chunks

        settings = get_settings()

        # 1. Retrieve relevant chunks
        with console.status("[bold cyan]Searching documents..."):
            citations = await retrieve_relevant_chunks(question, settings)

        # 2. Calculate confidence
        confidence = calculate_confidence(citations)

        # 3. Check abstention
        if should_abstain(confidence):
            console.print(
                Panel(
                    ABSTAIN_MESSAGE,
                    title="Answer",
                    border_style="yellow",
                )
            )
            console.print(f"\n[dim]Confidence: {confidence:.2f}[/dim]")
            return

        # 4. Build context and generate answer
        context = build_context(citations)
        provider = get_llm_provider(settings)

        from app.services.generation import build_generation_kwargs

        gen_kwargs = build_generation_kwargs(settings)

        answer_tokens: list[str] = []
        with console.status("[bold cyan]Generating answer..."):
            async for token in provider.generate_stream(question, context, **gen_kwargs):
                answer_tokens.append(token)
        answer = "".join(answer_tokens)

        # 5. Print answer
        console.print(
            Panel(
                answer,
                title="Answer",
                border_style="green",
            )
        )

        # 6. Print citations table
        if citations:
            table = Table(title="Citations")
            table.add_column("Document", style="cyan")
            table.add_column("Chunk Index", justify="right", style="magenta")
            table.add_column("Relevance Score", justify="right", style="green")

            for c in citations:
                table.add_row(
                    c.document_name,
                    str(c.chunk_index),
                    f"{c.relevance_score:.4f}",
                )
            console.print(table)

        # 7. Print confidence
        console.print(f"\n[dim]Confidence: {confidence:.2f}[/dim]")

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


# ---------------------------------------------------------------------------
# status (stub)
# ---------------------------------------------------------------------------
@app.command()
def status() -> None:
    """Show loaded documents, provider config, and ChromaDB stats."""
    from rich.table import Table

    from app.config import get_settings

    settings = get_settings()

    # --- Provider Config ---
    provider_table = Table(title="Provider Config", show_header=False, box=None, padding=(0, 1))
    provider_table.add_column(style="bold cyan")
    provider_table.add_column()
    provider_table.add_row("LLM Provider", settings.LLM_PROVIDER)
    provider_table.add_row("Ollama Model", settings.OLLAMA_MODEL)
    provider_table.add_row("Embedding Provider", settings.EMBEDDING_PROVIDER)
    provider_table.add_row("Embedding Model", settings.EMBEDDING_MODEL)
    console.print(provider_table)

    # --- ChromaDB Stats ---
    try:
        from app.services.vectorstore import get_chroma_client

        client = get_chroma_client(settings)
        from app.core.constants import COLLECTION_NAME

        collection = client.get_or_create_collection(COLLECTION_NAME)
        chunk_count = collection.count()

        chroma_table = Table(title="ChromaDB Stats", show_header=False, box=None, padding=(0, 1))
        chroma_table.add_column(style="bold cyan")
        chroma_table.add_column()
        chroma_table.add_row("Total Chunks", str(chunk_count))
        console.print(chroma_table)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] Could not connect to ChromaDB: {exc}")

    # --- Upload Directory ---
    upload_path = Path(settings.UPLOAD_DIR).resolve()
    upload_table = Table(title="Upload Directory", show_header=False, box=None, padding=(0, 1))
    upload_table.add_column(style="bold cyan")
    upload_table.add_column()
    upload_table.add_row("Path", str(upload_path))
    upload_table.add_row("Exists", str(upload_path.exists()))
    console.print(upload_table)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
config_app = typer.Typer(
    name="config",
    help="Get or set provider, model, and API key configuration.",
    invoke_without_command=True,
)
app.add_typer(config_app)

# Keys that contain secrets and should be masked in display.
_SECRET_KEYS = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "API_KEYS"}


def _mask_value(key: str, value: str | None) -> str:
    """Mask secret values, showing only the last 4 characters."""
    if key not in _SECRET_KEYS or not value:
        return str(value) if value is not None else ""
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def _settings_fields() -> list[str]:
    """Return the list of valid Settings field names."""
    from app.config import Settings

    return list(Settings.model_fields.keys())


def _config_overlay_path() -> Path:
    """Return the path to the settings overlay JSON file."""
    from app.core.overlay import overlay_path

    return overlay_path()


def _load_config_overlay() -> dict[str, Any]:
    """Load the overlay file, returning an empty dict if it doesn't exist."""
    from app.core.overlay import load_overlay

    return load_overlay()


def _save_config_overlay(data: dict[str, Any]) -> None:
    """Persist the overlay dict to disk."""
    from app.core.overlay import save_overlay

    save_overlay(data)


@config_app.callback()
def config_callback(ctx: typer.Context) -> None:
    """Show all current configuration when no subcommand is given."""
    if ctx.invoked_subcommand is not None:
        return

    from rich.table import Table

    from app.config import get_settings

    settings = get_settings()
    overlay = _load_config_overlay()

    table = Table(title="doc-qna Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="magenta")

    for field_name in _settings_fields():
        value = getattr(settings, field_name)
        source = "overlay" if field_name.lower() in overlay else "default/env"
        display_value = _mask_value(field_name, str(value) if value is not None else None)
        table.add_row(field_name, display_value, source)

    console.print(table)


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Setting key to retrieve")],
) -> None:
    """Get the value of a specific configuration setting."""
    from app.config import get_settings

    valid_keys = _settings_fields()
    matched = None
    for k in valid_keys:
        if k.upper() == key.upper():
            matched = k
            break

    if matched is None:
        console.print(f"[bold red]Error:[/bold red] Unknown key [yellow]{key}[/yellow]")
        console.print(f"[dim]Available keys:[/dim] {', '.join(valid_keys)}")
        raise typer.Exit(code=1)

    settings = get_settings()
    value = getattr(settings, matched)
    display = _mask_value(matched, str(value) if value is not None else None)
    console.print(f"{matched} = {display}")


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Setting key to update")],
    value: Annotated[str, typer.Argument(help="New value")],
) -> None:
    """Set a configuration setting value (persists to overlay file)."""
    valid_keys = _settings_fields()
    matched = None
    for k in valid_keys:
        if k.upper() == key.upper():
            matched = k
            break

    if matched is None:
        console.print(f"[bold red]Error:[/bold red] Unknown key [yellow]{key}[/yellow]")
        console.print(f"[dim]Available keys:[/dim] {', '.join(valid_keys)}")
        raise typer.Exit(code=1)

    # Coerce the string value to the correct type based on Settings field annotations.
    from app.config import Settings

    field_info = Settings.model_fields.get(matched)
    if field_info and field_info.annotation is not None:
        import typing

        ann = field_info.annotation
        # Unwrap Optional / Union with None
        origin = typing.get_origin(ann)
        if origin is type(int | str) or origin is typing.Union:  # types.UnionType (Python 3.10+)
            args = typing.get_args(ann)
            ann = next((a for a in args if a is not type(None)), ann)

        if ann is int:
            value = int(value)  # type: ignore[assignment]
        elif ann is float:
            value = float(value)  # type: ignore[assignment]
        elif ann is bool:
            value = value.lower() in ("1", "true", "yes")  # type: ignore[assignment]

    overlay = _load_config_overlay()
    # Normalize to lowercase to match the settings router convention.
    overlay_key = matched.lower()
    overlay[overlay_key] = value
    _save_config_overlay(overlay)
    display = _mask_value(matched, str(value))
    console.print(f"[green]Set[/green] {matched} = {display}")


# ---------------------------------------------------------------------------
# serve (implemented)
# ---------------------------------------------------------------------------
@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Bind address")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Port number")] = 8000,
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload for development")] = False,
    workers: Annotated[int, typer.Option(help="Number of uvicorn workers")] = 1,
    log_level: Annotated[str, typer.Option(help="Log level (default from settings)")] = "",
) -> None:
    """Start the FastAPI server via uvicorn."""
    import uvicorn
    from rich.panel import Panel
    from rich.table import Table

    from app.config import get_settings

    settings = get_settings()

    # Resolve log level: CLI flag overrides settings default.
    resolved_log_level = log_level if log_level else settings.LOG_LEVEL
    resolved_log_level = resolved_log_level.lower()

    # Rich startup banner
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Host", host)
    table.add_row("Port", str(port))
    table.add_row("Workers", str(workers))
    table.add_row("Reload", str(reload))
    table.add_row("Log level", resolved_log_level)
    table.add_row("LLM provider", settings.LLM_PROVIDER)

    console.print(Panel(table, title="[bold green]Doc Q&A Server[/bold green]", expand=False))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=resolved_log_level,
    )


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------
@app.command(name="eval")
def eval_cmd(
    test_set_path: Annotated[str, typer.Argument(help="Path to a JSON test set file")],
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Save results as JSON to this file"),
    ] = None,
) -> None:
    """Run RAG evaluation metrics against a test set."""
    from dataclasses import asdict

    from rich.table import Table

    test_file = Path(test_set_path)
    if not test_file.exists():
        console.print(f"[bold red]Error:[/bold red] Test set file not found: {test_set_path}")
        raise typer.Exit(code=1)

    try:
        test_cases = json.loads(test_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[bold red]Error:[/bold red] Failed to read test set: {exc}")
        raise typer.Exit(code=1) from None

    if not isinstance(test_cases, list) or not test_cases:
        console.print("[bold red]Error:[/bold red] Test set must be a non-empty JSON array.")
        raise typer.Exit(code=1)

    async def _run() -> list:
        from app.config import get_settings
        from app.services.confidence import calculate_confidence
        from app.services.evaluation import EvalResult, evaluate_single, summarize_results
        from app.services.generation import build_context, build_generation_kwargs, get_llm_provider
        from app.services.retrieval import retrieve_relevant_chunks

        settings = get_settings()
        provider = get_llm_provider(settings)
        gen_kwargs = build_generation_kwargs(settings)
        results: list[EvalResult] = []

        for i, case in enumerate(test_cases, start=1):
            query_text = case.get("query", "")
            console.print(f"[dim]({i}/{len(test_cases)})[/dim] Evaluating: {query_text[:80]}")

            # 1. Retrieve citations
            citations = await retrieve_relevant_chunks(query_text, settings)

            # 2. Generate answer
            context = build_context(citations)
            answer_tokens: list[str] = []
            async for token in provider.generate_stream(query_text, context, **gen_kwargs):
                answer_tokens.append(token)
            answer = "".join(answer_tokens)

            # 3. Compute confidence and evaluate
            confidence = calculate_confidence(citations)
            result = evaluate_single(
                query=query_text,
                answer=answer,
                citations=citations,
                confidence=confidence,
            )
            results.append(result)

        # --- Results table ---
        table = Table(title="Evaluation Results")
        table.add_column("Query", style="cyan", max_width=40)
        table.add_column("Relevance", justify="right", style="green")
        table.add_column("Coverage", justify="right", style="green")
        table.add_column("Groundedness", justify="right", style="green")
        table.add_column("Confidence", justify="right", style="green")

        for r in results:
            table.add_row(
                r.query[:40],
                f"{r.retrieval_relevance:.3f}",
                f"{r.context_coverage:.3f}",
                f"{r.groundedness:.3f}",
                f"{r.confidence:.3f}",
            )
        console.print(table)

        # --- Summary statistics ---
        summary = summarize_results(results)
        console.print("\n[bold]Summary[/bold]")
        console.print(f"  Total test cases : {summary['count']}")
        console.print(f"  Abstained        : {summary['abstained_count']}")
        for metric in (
            "retrieval_relevance",
            "context_coverage",
            "groundedness",
            "confidence",
        ):
            s = summary[metric]
            console.print(f"  {metric:22s}: mean={s['mean']:.3f}  min={s['min']:.3f}  max={s['max']:.3f}")

        # --- Optional JSON output ---
        if output:
            output_data = {
                "results": [asdict(r) for r in results],
                "summary": summary,
            }
            Path(output).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
            console.print(f"\n[green]Results saved to {output}[/green]")

        return results

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------
pack_app = typer.Typer(
    name="pack",
    help="Manage knowledge packs — list, install, and remove.",
    no_args_is_help=True,
)
app.add_typer(pack_app)


@pack_app.command("list")
def pack_list() -> None:
    """Show available and installed knowledge packs."""
    from rich.table import Table

    from app.config import get_settings
    from app.packs.registry import PackRegistry

    settings = get_settings()
    registry = PackRegistry(settings.PACKS_DIR)
    registry.scan_local()
    index = registry.get_index()

    if not index:
        console.print("[yellow]No packs found.[/yellow]")
        return

    table = Table(title="Knowledge Packs")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Description")
    table.add_column("Docs", justify="right", style="green")
    table.add_column("Installed", justify="center")

    for entry in index:
        installed_mark = "[green]yes[/green]" if entry["installed"] else "[dim]no[/dim]"
        table.add_row(
            entry["name"],
            entry["version"],
            entry["description"],
            str(entry["doc_count"]),
            installed_mark,
        )

    console.print(table)


@pack_app.command("install")
def pack_install_cmd(
    pack_path: Annotated[
        str,
        typer.Argument(help="Path to the pack archive (.tar.gz) to install."),
    ],
) -> None:
    """Install a knowledge pack from a .tar.gz archive."""
    from app.config import get_settings
    from app.packs.installer import install_pack

    resolved = Path(pack_path).resolve()
    if not resolved.is_file():
        console.print(f"[bold red]Error:[/bold red] Pack file not found: {resolved}")
        raise typer.Exit(code=1)

    settings = get_settings()

    try:
        manifest = asyncio.run(install_pack(resolved, settings))
        console.print(f"[green]Installed[/green] pack [bold]{manifest.name}[/bold] v{manifest.version}")
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


@pack_app.command("remove")
def pack_remove_cmd(
    pack_name: Annotated[
        str,
        typer.Argument(help="Name of the pack to remove."),
    ],
) -> None:
    """Uninstall a knowledge pack and remove its data."""
    from app.config import get_settings
    from app.packs.installer import uninstall_pack

    settings = get_settings()

    try:
        asyncio.run(uninstall_pack(pack_name, settings))
        console.print(f"[green]Removed[/green] pack [bold]{pack_name}[/bold]")
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None
