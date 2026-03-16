"""API key resolution for RunPod."""

import os

import typer
from dotenv import dotenv_values


def get_api_key() -> str:
    """Return the RunPod API key.

    Resolution order:
    1. ``RUNPOD_API_KEY`` environment variable
    2. ``.env`` file in the ``infra/`` directory (loaded via python-dotenv)

    Raises ``SystemExit`` with a helpful message if the key is not found.
    """

    if key := os.getenv("RUNPOD_API_KEY"):
        return key

    if key := dotenv_values(".env").get("RUNPOD_API_KEY"):
        return key

    typer.echo(
        "ERROR: RUNPOD_API_KEY is not set.\n  Set it as an environment variable or add it to .env",
        err=True,
    )
    raise typer.Exit(1)
