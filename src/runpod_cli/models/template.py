"""Pydantic model for RunPod template YAML / API payloads."""

from typing import Any, ClassVar

from pydantic import Field

from runpod_cli.models.base import RunPodCLISettings


# None fields are omitted and not sent to the RunPod API
class TemplateConfig(RunPodCLISettings):
    """
    RunPod container template.

    Field names are camelCase to match the RunPod REST API directly.
    ``model_dump(exclude_none=True)`` produces a payload ready for
    ``POST /templates`` or ``PATCH /templates/{id}`` — ``None`` fields
    are omitted and not sent to RunPod.

    Container fields (``ports``, ``env``) are merged with ``_field_defaults``:
    - ``ports``: union with defaults (``["22/tcp"]``).
    - ``env``: defaults applied first, user keys override.
    """

    _field_defaults: ClassVar[dict[str, Any]] = {
        "ports": ["22/tcp"],
        "env": {
            "GIT_REPO": "git@github.com:xXCoolinXx/SPARBackdoor.git",
            "GIT_BRANCH": "main",
            "HF_HOME": "/workspace/hf_cache",
        },
    }

    # Important
    name: str = Field(description="Custom name for the template")
    imageName: str = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
    containerDiskInGb: int = 30
    volumeInGb: int = 250
    volumeMountPath: str | None = None
    ports: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

    # Optional
    category: str | None = None
    dockerEntrypoint: list[str] | None = None
    # sshd sanitizes Docker env vars; /etc/rp-environment is a dedicated file
    # for Docker env vars that pod-start.sh sources explicitly. /etc/environment
    # is also written as a fallback for PAM-based SSH sessions.
    dockerStartCmd: list[str] = Field(
        default=[
            "/bin/bash",
            "-c",
            "env > /etc/rp-environment && env >> /etc/environment && exec /start.sh",
        ],
    )
    containerRegistryAuthId: str | None = None
    isPublic: bool | None = None
    isServerless: bool | None = None
    readme: str | None = None
