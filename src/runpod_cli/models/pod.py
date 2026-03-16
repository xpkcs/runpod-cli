"""Pydantic model for pod YAML definitions."""

from pydantic import Field

from runpod_cli.models.base import RunPodCLISettings


# None fields are not sent to RunPod. Setting things like `volumeInGb` to None by default
# here means that while callers can override the field, by default no value will be sent
# to the RunPod create pod API endpoint. Assuming we pass in a `templateId`, this means
# the template's default values will be used.
class PodConfig(RunPodCLISettings):
    """RunPod pod definition loaded from YAML.

    Field names are camelCase to match the RunPod REST API directly.
    Pass ``model_dump(exclude_none=True)`` as the JSON payload for ``POST /pods``.
    """

    # Identity / compute
    name: str
    computeType: str | None = None
    cloudType: str | None = None

    # GPU
    gpuTypeIds: list[str]
    gpuCount: int = 1

    # Image
    imageName: str | None = None

    # Storage
    containerDiskInGb: int | None = None
    volumeInGb: int | None = None
    volumeMountPath: str | None = None
    networkVolumeId: str | None = None

    # Networking
    ports: list[str] | None = None

    # Environment
    env: dict[str, str] | None = Field(default=None, validation_alias="env")
    dockerEntrypoint: list[str] | None = None
    dockerStartCmd: list[str] | None = None

    # Placement
    dataCenterIds: list[str] | None = None
    interruptible: bool | None = None

    # Template
    templateId: str | None = None
    containerRegistryAuthId: str | None = None
