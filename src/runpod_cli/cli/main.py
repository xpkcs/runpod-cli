"""Top-level ``runpod-cli`` CLI."""

from typing import Annotated

import typer

from runpod_cli.cli._helpers import OutputFormat, set_output_format
from runpod_cli.cli.pod import app as pod_app
from runpod_cli.cli.template import app as template_app
from runpod_cli.cli.volume import app as volume_app

app = typer.Typer(
    name="runpod-cli",
    help="RunPod infrastructure CLI — pod and template management via the RunPod REST API.",
    no_args_is_help=True,
)


@app.callback()
def _global_options(
    output: Annotated[
        OutputFormat | None,
        typer.Option("--output", "-o", help="Output format for API responses (json or yaml)."),
    ] = None,
) -> None:
    """Configure global options (output format) before any subcommand runs."""

    if output is not None:
        set_output_format(output)


app.add_typer(pod_app)
app.add_typer(template_app)
app.add_typer(volume_app)


def main() -> None:
    """Entrypoint for the ``runpod-cli`` CLI."""

    app()


if __name__ == "__main__":
    main()
