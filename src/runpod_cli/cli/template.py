"""Template subgroup — CRUD for RunPod container templates via REST API."""

from typing import Annotated

import typer
from rich.table import Table

from runpod_cli.cli._helpers import Printer, client, console, with_yaml_config
from runpod_cli.models.template import TemplateConfig

app = typer.Typer(name="template", help="Manage RunPod templates.")


@app.command("get")
def template_get(
    template_id: Annotated[str, typer.Argument(help="Template ID to retrieve")],
) -> None:
    """Get a single template by ID."""

    with client() as c:
        Printer.print(c.get_template(template_id))


@app.command("list")
def template_list() -> None:
    """List all templates."""

    with client() as c:
        templates = c.list_templates()

    table = Table("ID", "Name", "Image", "Disk (GB)", "Volume (GB)", "Runtime (min)")

    for t in templates:
        table.add_row(
            t.get("id", ""),
            t.get("name", ""),
            t.get("imageName", ""),
            str(t.get("containerDiskInGb", "-")),
            str(t.get("volumeInGb", "-")),
            str(t.get("runtimeInMin", "-")),
            # str(t.get("env", "-")),
            # str(t.get("ports", "-")),
        )

    console.print(table)


@app.command("create")
@with_yaml_config(TemplateConfig)
def template_create(
    cfg: TemplateConfig,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print API payload without calling")] = False,
) -> None:
    """Create a template from a YAML definition."""

    if dry_run:
        Printer.print(cfg.model_dump(exclude_none=True))
        return

    with client() as c:
        Printer.print(c.create_template(cfg))


@app.command("update")
@with_yaml_config(TemplateConfig)
def template_update(
    template_id: Annotated[str, typer.Argument(help="Template ID to update")],
    cfg: TemplateConfig,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print API payload without calling")] = False,
) -> None:
    """Update an existing template."""

    if dry_run:
        Printer.print(cfg.model_dump(exclude_none=True))
        return

    with client() as c:
        Printer.print(c.update_template(template_id, cfg))


@app.command("delete")
def template_delete(
    template_id: Annotated[str, typer.Argument(help="Template ID to delete")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Delete a template by ID."""

    if not yes:
        typer.confirm(f"Delete template {template_id}?", abort=True)

    with client() as c:
        c.delete_template(template_id)

    typer.echo(f"Deleted template {template_id}.")


@app.command("apply")
@with_yaml_config(TemplateConfig)
def template_apply(
    cfg: TemplateConfig,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print API payload without calling")] = False,
) -> None:
    """Idempotent create-or-update by template name."""

    if dry_run:
        Printer.print(cfg.model_dump(exclude_none=True))
        return

    with client() as c:
        templates = c.list_templates()
        existing = next((t for t in templates if t.get("name") == cfg.name), None)

        if existing:
            tid = existing["id"]
            typer.echo(f"Updating existing template {tid} ({cfg.name})")
            Printer.print(c.update_template(tid, cfg))
        else:
            typer.echo(f"Creating new template ({cfg.name})")
            Printer.print(c.create_template(cfg))
