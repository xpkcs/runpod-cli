"""RunPod REST API client (https://rest.runpod.io/v1)."""

from typing import Any

import httpx

from runpod_cli.models.pod import PodConfig
from runpod_cli.models.template import TemplateConfig

_BASE_URL = "https://rest.runpod.io/v1"


class RunPodClient:
    """Thin httpx wrapper around the RunPod REST API."""

    def __init__(self, api_key: str, base_url: str = _BASE_URL) -> None:
        """Initialise the client with the given API key."""

        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    def _raise(self, response: httpx.Response) -> httpx.Response:
        """Raise a descriptive ``RuntimeError`` on non-2xx responses."""

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"RunPod API error {exc.response.status_code}: {exc.response.text}") from exc

        return response

    # ── Pods ───────────────────────────────────────────────────────────────────

    def create_pod(self, cfg: PodConfig) -> dict[str, Any]:
        """Create a pod and return the API response."""

        return self._raise(self._client.post("/pods", json=cfg.model_dump(exclude_none=True))).json()

    def list_pods(self) -> list[dict[str, Any]]:
        """Return all pods for the authenticated account."""

        return self._raise(self._client.get("/pods")).json()

    def get_pod(self, pod_id: str) -> dict[str, Any]:
        """Return details for a single pod."""

        return self._raise(self._client.get(f"/pods/{pod_id}")).json()

    def stop_pod(self, pod_id: str) -> dict[str, Any]:
        """Stop a running pod (sets desiredStatus to EXITED)."""

        return self._raise(self._client.post(f"/pods/{pod_id}/stop")).json()

    def start_pod(self, pod_id: str) -> dict[str, Any]:
        """Start a stopped pod."""

        return self._raise(self._client.post(f"/pods/{pod_id}/start")).json()

    def restart_pod(self, pod_id: str) -> dict[str, Any]:
        """Restart a pod."""

        return self._raise(self._client.post(f"/pods/{pod_id}/restart")).json()

    def delete_pod(self, pod_id: str) -> None:
        """Delete a pod (sets desiredStatus to TERMINATED). Returns nothing (204)."""

        self._raise(self._client.delete(f"/pods/{pod_id}"))

    # ── Templates ──────────────────────────────────────────────────────────────

    def get_template(self, template_id: str) -> dict[str, Any]:
        """Return details for a single template."""

        return self._raise(self._client.get(f"/templates/{template_id}")).json()

    def list_templates(self) -> list[dict[str, Any]]:
        """Return all templates for the authenticated account."""

        return self._raise(self._client.get("/templates")).json()

    def create_template(self, cfg: TemplateConfig) -> dict[str, Any]:
        """Create a new template and return the API response."""

        return self._raise(self._client.post("/templates", json=cfg.model_dump(exclude_none=True))).json()

    def update_template(self, template_id: str, cfg: TemplateConfig) -> dict[str, Any]:
        """Update an existing template and return the API response."""

        payload = cfg.model_dump(exclude_none=True)

        return self._raise(self._client.patch(f"/templates/{template_id}", json=payload)).json()

    def delete_template(self, template_id: str) -> None:
        """Delete a template by ID. Returns nothing (204)."""

        self._raise(self._client.delete(f"/templates/{template_id}"))

    # ── Network Volumes ────────────────────────────────────────────────────────

    def list_network_volumes(self) -> list[dict[str, Any]]:
        """Return all network volumes for the authenticated account."""

        return self._raise(self._client.get("/networkvolumes")).json()

    def get_network_volume(self, volume_id: str) -> dict[str, Any]:
        """Return details for a single network volume."""

        return self._raise(self._client.get(f"/networkvolumes/{volume_id}")).json()

    # ── Context manager ────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    def __enter__(self) -> "RunPodClient":
        """Enter the context manager."""

        return self

    def __exit__(self, *_: object) -> None:
        """Exit the context manager, closing the HTTP client."""

        self.close()
