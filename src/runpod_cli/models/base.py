"""Shared pydantic-settings base for RunPod config models."""

import re
from pathlib import Path
from typing import Any, ClassVar, Self

import yaml
from pydantic import AliasGenerator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def _to_upper_snake(name: str) -> str:
    """Convert camelCase → SCREAMING_SNAKE_CASE for dotenv key matching."""

    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).upper()


class RunPodCLISettings(BaseSettings):
    """
    Base settings for RunPod infrastructure models.

    Priority (highest → lowest): .env file > constructor kwargs (YAML).
    Extras in .env (RUNPOD_API_KEY, GIT_BRANCH, etc.) are silently ignored.
    model_dump() returns camelCase field names (RunPod API format).
    """

    model_config = SettingsConfigDict(
        alias_generator=AliasGenerator(validation_alias=_to_upper_snake),
        populate_by_name=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    _field_defaults: ClassVar[dict[str, Any]] = {}

    @model_validator(mode="before")
    @classmethod
    def _merge_defaults(cls, data: Any) -> Any:
        """Merge user-supplied container fields with class-defined defaults."""

        if not isinstance(data, dict):
            return data

        for field_name, default in cls._field_defaults.items():
            user_val = data.get(field_name)

            match default:
                case dict():
                    data[field_name] = {**default, **(user_val or {})}
                case list():
                    data[field_name] = list(set(default) | set(user_val or ()))

        return data

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Priority: .env > YAML (init). Shell env_settings dropped to avoid ENV/env field conflict."""

        return (dotenv_settings, init_settings)

    @classmethod
    def from_yaml(cls, path: Path | str) -> Self:
        """Load config from a YAML file, with .env field overrides applied."""

        with open(path) as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}

        return cls(**data)
