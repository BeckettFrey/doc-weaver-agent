"""Command-line interface for Doc Weaver template management and document generation."""

import asyncio
import json
import shutil
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from doc_weaver.hydrate_queue import hydrate, PLACEHOLDER_PATTERN
from doc_weaver.parser import load_markdown, ValidationError

CONFIG_DIR = Path.home() / ".doc_weaver"
ENV_FILE = CONFIG_DIR / ".env"
TEMPLATES_DIR = CONFIG_DIR / "templates"
CONTEXTS_DIR = CONFIG_DIR / "contexts"

console = Console()


def _ensure_templates_dir():
    """Ensure the templates directory exists."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _template_path(name: str) -> Path:
    """Return the file path for a template by name."""
    return TEMPLATES_DIR / f"{name}.md"


def _ensure_contexts_dir():
    """Ensure the contexts directory exists."""
    CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)


def _context_path(name: str) -> Path:
    """Return the file path for a context by name."""
    return CONTEXTS_DIR / f"{name}.txt"


@click.group()
def cli():
    """Doc Weaver — fill markdown templates with LLM-generated content."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=False)


@cli.group()
def config():
    """Manage Doc Weaver configuration."""


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Store a KEY=VALUE pair in ~/.doc_weaver/.env."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing entries, update or append
    entries: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                entries[k.strip()] = v.strip()

    entries[key] = value
    ENV_FILE.write_text(
        "\n".join(f"{k}={v}" for k, v in entries.items()) + "\n"
    )
    ENV_FILE.chmod(0o600)
    console.print(f"[green]✓[/green] Saved {key} to {ENV_FILE}")


@config.command("show")
def config_show():
    """Print stored config keys with masked values."""
    if not ENV_FILE.exists():
        console.print("[dim]No config file found.[/dim]")
        return

    table = Table(title="Config", show_header=True, border_style="dim")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            masked = v.strip()[:4] + "****" if len(v.strip()) > 4 else "****"
            table.add_row(k.strip(), masked)

    console.print(table)


@cli.group()
def template():
    """Manage markdown templates."""


@template.command("list")
def list_templates():
    """List all saved templates."""
    _ensure_templates_dir()
    templates = sorted(p.stem for p in TEMPLATES_DIR.glob("*.md"))
    if not templates:
        console.print("[dim]No templates found.[/dim]")
        return
    table = Table(title="Templates", show_header=False, border_style="dim")
    table.add_column("Name", style="cyan")
    for name in templates:
        table.add_row(name)
    console.print(table)


@template.command("add")
@click.argument("name")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def add(name, file):
    """Copy a markdown file into the templates directory under NAME."""
    markdown = Path(file).read_text()
    errors = validate_template(markdown)
    if errors:
        console.print(f"[red]Found {len(errors)} error(s) in {file}:[/red]\n")
        for i, error in enumerate(errors, 1):
            console.print(f"  [red]{i}.[/red] {error}")
        raise SystemExit(1)

    _ensure_templates_dir()
    dest = _template_path(name)
    if dest.exists():
        console.print(f"[yellow]Template '{name}' already exists. Overwriting.[/yellow]")
    shutil.copy2(file, dest)
    console.print(f"[green]✓[/green] Template '{name}' added.")


@template.command("show")
@click.argument("name")
def show(name):
    """Print a template's contents to stdout."""
    _ensure_templates_dir()
    path = _template_path(name)
    if not path.exists():
        raise click.ClickException(f"Template '{name}' not found.")
    console.print(Panel(path.read_text(), title=name, border_style="dim"))


@template.command("remove")
@click.argument("name")
def remove(name):
    """Delete a template."""
    _ensure_templates_dir()
    path = _template_path(name)
    if not path.exists():
        raise click.ClickException(f"Template '{name}' not found.")
    path.unlink()
    console.print(f"[green]✓[/green] Template '{name}' removed.")


@cli.group()
def context():
    """Manage per-task context strings."""


@context.command("add")
@click.argument("name")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def context_add(name, file):
    """Store a context text file under NAME."""
    if not name.isidentifier():
        console.print(
            f"[red]✗[/red] Invalid context name '{name}'. "
            "Names must contain only letters, digits, and underscores, "
            "and cannot start with a digit."
        )
        raise SystemExit(1)
    _ensure_contexts_dir()
    dest = _context_path(name)
    if dest.exists():
        console.print(f"[yellow]Context '{name}' already exists. Overwriting.[/yellow]")
    shutil.copy2(file, dest)
    console.print(f"[green]✓[/green] Context '{name}' added.")


@context.command("list")
def context_list():
    """List all saved contexts."""
    _ensure_contexts_dir()
    contexts = sorted(p.stem for p in CONTEXTS_DIR.glob("*.txt"))
    if not contexts:
        console.print("[dim]No contexts found.[/dim]")
        return
    table = Table(title="Contexts", show_header=False, border_style="dim")
    table.add_column("Name", style="cyan")
    for name in contexts:
        table.add_row(name)
    console.print(table)


@context.command("show")
@click.argument("name")
def context_show(name):
    """Print a context's contents to stdout."""
    _ensure_contexts_dir()
    path = _context_path(name)
    if not path.exists():
        raise click.ClickException(f"Context '{name}' not found.")
    console.print(Panel(path.read_text(), title=name, border_style="dim"))


@context.command("remove")
@click.argument("name")
def context_remove(name):
    """Delete a context."""
    _ensure_contexts_dir()
    path = _context_path(name)
    if not path.exists():
        raise click.ClickException(f"Context '{name}' not found.")
    path.unlink()
    console.print(f"[green]✓[/green] Context '{name}' removed.")


def validate_template(markdown: str) -> list[str]:
    """Validate that a markdown string is a well-formed Doc Weaver template.

    Returns a list of error messages. An empty list means the template is valid.
    """
    errors = []

    # 1. Find placeholders
    matches = list(PLACEHOLDER_PATTERN.finditer(markdown))
    if not matches:
        errors.append("No placeholders found. Expected at least one <batch, min_chars, max_chars> placeholder.")
        # Still check structure below, but swap nothing for <TODO>

    # 2. Validate each placeholder's values and line placement
    for match in matches:
        raw = match.group(0)
        batch = int(match.group(1))
        min_chars = int(match.group(2))
        max_chars = int(match.group(3))
        context_id = match.group(4)  # None if not present

        if context_id is not None and not context_id.isidentifier():
            errors.append(f"{raw}: context_id '{context_id}' is not a valid identifier.")

        if batch < 1:
            errors.append(f"{raw}: batch number must be >= 1, got {batch}.")
        if min_chars < 0:
            errors.append(f"{raw}: min_chars must be >= 0, got {min_chars}.")
        if max_chars < 1:
            errors.append(f"{raw}: max_chars must be >= 1, got {max_chars}.")
        if min_chars >= max_chars:
            errors.append(f"{raw}: min_chars ({min_chars}) must be less than max_chars ({max_chars}).")

        # Find the line containing this placeholder and check it's alone
        line_start = markdown.rfind('\n', 0, match.start()) + 1
        line_end = markdown.find('\n', match.end())
        if line_end == -1:
            line_end = len(markdown)
        line = markdown[line_start:line_end]
        stripped = line.lstrip('#').lstrip('>').lstrip('-').strip()
        if stripped != raw:
            errors.append(f"{raw}: placeholder must be the only content on its line, found: '{line.strip()}'.")

    # 3. Validate markdown structure by replacing placeholders and parsing
    #    Replace all placeholders with dummy text, then swap one for <TODO>
    #    so load_markdown's structure + TODO checks pass.
    if matches:
        test_md = markdown
        for i, match in enumerate(reversed(matches)):
            start, end = match.start(), match.end()
            replacement = "<TODO>" if i == 0 else "placeholder text"
            test_md = test_md[:start] + replacement + test_md[end:]
    else:
        test_md = markdown

    try:
        load_markdown(test_md, check_todo=True)
    except ValidationError as e:
        errors.append(f"Structure error: {e}")

    return errors


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def validate(file):
    """Validate that a markdown file is template compatible."""
    markdown = Path(file).read_text()
    errors = validate_template(markdown)

    if errors:
        error_lines = "\n".join(f"  {i}. {e}" for i, e in enumerate(errors, 1))
        console.print(Panel(
            error_lines,
            title=f"[red]✗ {len(errors)} error(s) in {file}[/red]",
            border_style="red",
        ))
        raise SystemExit(1)
    else:
        console.print(f"[green]✓[/green] {file} is a valid Doc Weaver template.")
        placeholders = list(PLACEHOLDER_PATTERN.finditer(markdown))
        batches = sorted(set(int(m.group(1)) for m in placeholders))
        console.print(f"  Placeholders: [cyan]{len(placeholders)}[/cyan]")
        console.print(f"  Batches: [cyan]{', '.join(str(b) for b in batches)}[/cyan]")


@cli.command()
@click.argument("template_name")
@click.option("--output-dir", required=True, type=click.Path(file_okay=False), help="Directory to save output files.")
@click.option("--prompt", default=None, help="Context/prompt text for hydration.")
@click.option("--prompt-file", default=None, type=click.Path(exists=True, dir_okay=False), help="File containing the prompt text.")
@click.option("--model", default="gpt-4o", show_default=True, help="LLM model to use.")
@click.option("--timeout", default=30, show_default=True, type=int, help="Timeout in seconds per batch.")
def generate(template_name, output_dir, prompt, prompt_file, model, timeout):
    """Generate a hydrated document from a template."""
    if prompt and prompt_file:
        raise click.ClickException("Provide --prompt or --prompt-file, not both.")

    _ensure_templates_dir()
    path = _template_path(template_name)
    if not path.exists():
        raise click.ClickException(f"Template '{template_name}' not found.")

    markdown = path.read_text()

    context = ""
    if prompt:
        context = prompt
    elif prompt_file:
        context = Path(prompt_file).read_text()

    # Load all stored contexts
    _ensure_contexts_dir()
    contexts = {}
    for ctx_file in CONTEXTS_DIR.glob("*.txt"):
        contexts[ctx_file.stem] = ctx_file.read_text()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        with console.status(f"Hydrating template '{template_name}'...", spinner="dots"):
            result_md, metadata = asyncio.run(hydrate(markdown, context=context, model=model, timeout=timeout, contexts=contexts))
    except ValueError as e:
        raise click.ClickException(str(e))

    (output_path / "output.md").write_text(result_md)
    (output_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

    table = Table(title="Hydration Summary", border_style="dim")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Template", template_name)
    table.add_row("Model", metadata.get("model", model))
    table.add_row("Tasks", str(len(metadata.get("tasks", []))))
    table.add_row("Total time", f"{metadata.get('total_elapsed_ms', '?')}ms")
    console.print(table)

    console.print(f"\n[green]✓[/green] Output saved to [bold]{output_path}/[/bold]")
