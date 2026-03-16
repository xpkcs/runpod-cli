"""Pod subgroup — full pod lifecycle via the RunPod REST API."""

import os
from typing import Annotated, Any

import typer
from dotenv import dotenv_values
from rich.table import Table

from runpod_cli.cli._helpers import Printer, client, console, with_yaml_config
from runpod_cli.models.pod import PodConfig

app = typer.Typer(name="pod", help="Manage RunPod pods.")


@app.command("get")
def pod_get(
    pod_id: Annotated[str, typer.Argument(help="Pod ID")],
) -> None:
    """Get details for a pod."""

    with client() as c:
        Printer.print(c.get_pod(pod_id))


@app.command("list")
def pod_list() -> None:
    """List all pods."""

    with client() as c:
        pods = c.list_pods()

    table = Table("ID", "Name", "Image", "Status", "Cost/hr")

    for p in pods:
        table.add_row(
            p.get("id", ""),
            p.get("name", ""),
            p.get("image", ""),
            p.get("desiredStatus", ""),
            str(p.get("costPerHr", "")),
        )

    console.print(table)


@app.command("create")
@with_yaml_config(PodConfig)
def pod_create(
    cfg: PodConfig,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print API payload without calling")] = False,
) -> None:
    """Create a pod from a YAML definition."""

    if dry_run:
        Printer.print(cfg.model_dump(exclude_none=True))
        return

    with client() as c:
        Printer.print(c.create_pod(cfg))


@app.command("start")
def pod_start(pod_id: Annotated[str, typer.Argument(help="Pod ID")]) -> None:
    """Start a stopped pod."""

    with client() as c:
        Printer.print(c.start_pod(pod_id))


@app.command("stop")
def pod_stop(pod_id: Annotated[str, typer.Argument(help="Pod ID")]) -> None:
    """Stop a running pod."""

    with client() as c:
        Printer.print(c.stop_pod(pod_id))


@app.command("restart")
def pod_restart(pod_id: Annotated[str, typer.Argument(help="Pod ID")]) -> None:
    """Restart a pod."""

    with client() as c:
        Printer.print(c.restart_pod(pod_id))


@app.command("delete")
def pod_delete(
    pod_id: Annotated[str, typer.Argument(help="Pod ID")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a pod."""

    if not yes:
        typer.confirm(f"Delete pod {pod_id}?", abort=True)

    with client() as c:
        c.delete_pod(pod_id)

    typer.echo(f"Deleted pod {pod_id}.")


@app.command("id")
def pod_id(name: Annotated[str, typer.Argument(help="Pod name to resolve")]) -> None:
    """Print the ID of the first pod matching the given name.

    Exits with code 1 if no match is found. Useful in shell scripts::

        POD_ID=$(uv run rp pod id prune-7b)  # or: uv run runpod-cli pod id prune-7b
    """

    with client() as c:
        pods = c.list_pods()

    match = next((p for p in pods if p.get("name") == name), None)

    if not match:
        typer.echo(f"ERROR: No pod named '{name}' found.", err=True)
        raise typer.Exit(1)

    typer.echo(match["id"])


@app.command("ssh-cmd")
def pod_ssh_cmd(
    pod_id: Annotated[str, typer.Argument(help="Pod ID")],
    identity: Annotated[
        str | None,
        typer.Option("--identity", "-i", envvar="SSH_KEY", help="Path to SSH private key."),
    ] = dotenv_values().get("SSH_KEY"),
) -> None:
    """Print the SSH command for a pod (for use in shell pipelines).

    Example::

        $(uv run rp pod ssh-cmd <id> -i ~/.ssh/id_ed25519) "bash -s" < script.sh
    """

    if identity is None:
        typer.echo("ERROR: SSH identity file required. Pass -i <path> or set SSH_KEY.", err=True)
        raise typer.Exit(1)

    with client() as c:
        pod = c.get_pod(pod_id)

    public_ip = pod.get("publicIp")
    port_mappings: dict[str, Any] = pod.get("portMappings", {})
    ssh_port = port_mappings.get("22") or port_mappings.get("22/tcp")

    if not public_ip or not ssh_port:
        typer.echo(
            f"ERROR: Pod {pod_id} does not have SSH available.\n"
            "  Ensure port 22/tcp is listed in the pod's ports and the pod is RUNNING.",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"ssh root@{public_ip} -p {ssh_port} -i {identity}")


@app.command("ssh")
def pod_ssh(
    pod_id: Annotated[str, typer.Argument(help="Pod ID")],
    identity: Annotated[
        str | None,
        typer.Option("--identity", "-i", envvar="SSH_KEY", help="Path to SSH private key."),
    ] = dotenv_values().get("SSH_KEY"),
) -> None:
    """Open an SSH session to a pod via its public IP and port mapping."""

    if identity is None:
        typer.echo("ERROR: SSH identity file required. Pass -i <path> or set SSH_KEY.", err=True)
        raise typer.Exit(1)

    with client() as c:
        pod = c.get_pod(pod_id)

    public_ip = pod.get("publicIp")
    port_mappings: dict[str, Any] = pod.get("portMappings", {})
    # portMappings keys may be "22" or "22/tcp"
    ssh_port = port_mappings.get("22") or port_mappings.get("22/tcp")

    if not public_ip or not ssh_port:
        typer.echo(
            f"ERROR: Pod {pod_id} does not have SSH available.\n"
            "  Ensure port 22/tcp is listed in the pod's ports and the pod is RUNNING.",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"Connecting: ssh root@{public_ip} -p {ssh_port} -i {identity}")
    os.execvp("ssh", ["ssh", f"root@{public_ip}", "-p", str(ssh_port), "-i", identity])  # noqa: S606
