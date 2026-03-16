"""Shared CLI utilities for the runpod-cli CLI."""

import functools
import inspect
import json
import os
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from dotenv import dotenv_values
from rich.console import Console
from rich.syntax import Syntax

from runpod_cli.auth import get_api_key
from runpod_cli.clients.runpod import RunPodClient
from runpod_cli.models.base import RunPodCLISettings

console = Console()


def with_yaml_config(model_cls: type[RunPodCLISettings]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Replace a ``cfg: ModelCls`` parameter with a ``yaml_file`` typer Argument in the same position.

    Typer sees a ``Path`` argument; the decorated function receives a loaded model instance.
    The ``cfg`` parameter is located by type annotation, so its position in the signature is flexible.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())

        cfg_idx = next((i for i, p in enumerate(params) if p.annotation is model_cls), None)

        if cfg_idx is None:
            raise TypeError(f"{getattr(fn, '__name__', repr(fn))} has no parameter annotated with {model_cls.__name__}")

        cfg_name = params[cfg_idx].name
        yaml_param = inspect.Parameter(
            "yaml_file",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Annotated[Path, typer.Argument(help="Path to YAML config file")],
        )
        new_sig = sig.replace(parameters=[*params[:cfg_idx], yaml_param, *params[cfg_idx + 1 :]])

        @functools.wraps(fn)
        def wrapper(**kwargs: Any) -> Any:
            yaml_path = Path(kwargs.pop("yaml_file"))

            if not yaml_path.is_absolute():
                config_dir = os.environ.get("CONFIG_DIR") or dotenv_values(".env").get("CONFIG_DIR")
                if config_dir:
                    yaml_path = Path(config_dir) / yaml_path

            with open(yaml_path) as fh:
                data: dict[str, Any] = yaml.safe_load(fh) or {}

            if "templateName" in data:
                template_name = data.pop("templateName")

                with client() as c:
                    templates = c.list_templates()

                match = next((t for t in templates if t.get("name") == template_name), None)

                if match is None:
                    raise typer.BadParameter(f"Template {template_name!r} not found in RunPod account")

                data["templateId"] = match["id"]

            cfg = model_cls(**data)

            return fn(**{cfg_name: cfg, **kwargs})

        wrapper.__signature__ = new_sig  # type: ignore[attr-defined]

        return wrapper

    return decorator


class OutputFormat(StrEnum):
    """Supported output formats for API responses."""

    json = "json"
    yaml = "yaml"


OUTPUT_FORMAT: OutputFormat = OutputFormat.yaml


def set_output_format(fmt: OutputFormat) -> None:
    """Set the module-level output format used by :class:`Printer`."""

    global OUTPUT_FORMAT
    OUTPUT_FORMAT = fmt


def client() -> RunPodClient:
    """Return an authenticated ``RunPodClient``."""

    return RunPodClient(get_api_key())


class Printer:
    """Namespace for format-aware output helpers."""

    @classmethod
    def print(cls, data: Any) -> None:
        """Print *data* in the currently configured output format."""

        getattr(cls, f"_print_{OUTPUT_FORMAT}")(data)

    @classmethod
    def _print_json(cls, data: Any) -> None:
        """Pretty-print *data* as syntax-highlighted JSON."""

        console.print_json(json.dumps(data))

    @classmethod
    def _print_yaml(cls, data: Any) -> None:
        """Pretty-print *data* as syntax-highlighted YAML."""

        text = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        console.print(Syntax(text.rstrip(), "yaml", theme="ansi_dark"))
