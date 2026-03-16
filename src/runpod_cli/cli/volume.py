"""Volume subgroup — read-only access to RunPod network volumes."""

from typing import Annotated

import typer
from rich.table import Table

from runpod_cli.cli._helpers import Printer, client, console

app = typer.Typer(name="volume", help="Manage RunPod network volumes.")


@app.command("get")
def volume_get(
    volume_id: Annotated[str, typer.Argument(help="Volume ID")],
) -> None:
    """Get details for a network volume."""

    with client() as c:
        Printer.print(c.get_network_volume(volume_id))


@app.command("list")
def volume_list() -> None:
    """List all network volumes."""

    with client() as c:
        volumes = c.list_network_volumes()

    table = Table("ID", "Name", "Datacenter", "Size (GB)")

    for v in volumes:
        table.add_row(
            v.get("id", ""),
            v.get("name", ""),
            v.get("dataCenterId", ""),
            str(v.get("size", "")),
        )

    console.print(table)
