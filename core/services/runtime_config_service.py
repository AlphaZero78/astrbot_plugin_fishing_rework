from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from ..config import build_game_config


class RuntimeConfigService:
    """Persist plugin config and refresh the shared runtime configuration."""

    RESTART_REQUIRED_PREFIXES = ("storage.",)

    def __init__(
        self,
        raw_config: Mapping[str, Any],
        game_config: dict[str, Any],
        schema_path: str | Path,
        on_apply: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.raw_config = raw_config
        self.game_config = game_config
        self.schema_path = Path(schema_path)
        self.on_apply = on_apply

    def _load_schema(self) -> dict[str, Any]:
        with self.schema_path.open(encoding="utf-8") as handle:
            schema = json.load(handle)
        schema.pop("webui", None)
        return schema

    @staticmethod
    def _get_nested(mapping: Mapping[str, Any], path: str, default: Any) -> Any:
        current: Any = mapping
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return default
            current = current[part]
        return current

    @staticmethod
    def _set_nested(mapping: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split(".")
        current = mapping
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        current[parts[-1]] = value

    @staticmethod
    def _convert_value(raw_value: Any, field: Mapping[str, Any]) -> Any:
        field_type = field["type"]
        if field_type == "string":
            return str(raw_value)
        if field_type == "int":
            value = int(raw_value)
        elif field_type == "float":
            value = float(raw_value)
        elif field_type == "bool":
            if isinstance(raw_value, bool):
                return raw_value
            normalized = str(raw_value).strip().lower()
            if normalized not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError("布尔值必须为 true 或 false")
            return normalized in {"true", "1", "yes"}
        else:
            raise ValueError(f"不支持的配置类型: {field_type}")

        if field.get("min") is not None and value < field["min"]:
            raise ValueError(f"不能小于 {field['min']}")
        if field.get("max") is not None and value > field["max"]:
            raise ValueError(f"不能大于 {field['max']}")
        return value

    def _flatten_fields(
        self,
        schema: Mapping[str, Any],
        prefix: str = "",
    ) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for key, field in schema.items():
            path = f"{prefix}.{key}" if prefix else key
            if field["type"] == "object":
                fields.extend(self._flatten_fields(field["items"], path))
                continue
            default = field.get("default")
            fields.append(
                {
                    "path": path,
                    "section": path.split(".", 1)[0],
                    "label": field.get("description", key),
                    "hint": field.get("hint", ""),
                    "type": field["type"],
                    "min": field.get("min"),
                    "max": field.get("max"),
                    "value": self._get_nested(self.raw_config, path, default),
                }
            )
        return fields

    def get_sections(self) -> list[dict[str, Any]]:
        schema = self._load_schema()
        fields = self._flatten_fields(schema)
        sections = []
        for section_key, section_schema in schema.items():
            sections.append(
                {
                    "key": section_key,
                    "label": section_schema.get("description", section_key),
                    "fields": [
                        field for field in fields if field["section"] == section_key
                    ],
                }
            )
        return sections

    def update(self, submitted: Mapping[str, Any]) -> dict[str, Any]:
        schema = self._load_schema()
        fields = {field["path"]: field for field in self._flatten_fields(schema)}
        unknown = sorted(set(submitted) - set(fields))
        if unknown:
            raise ValueError(f"包含未知配置项: {', '.join(unknown)}")

        old_raw = deepcopy(dict(self.raw_config))
        old_game = deepcopy(self.game_config)
        changed: list[str] = []
        try:
            for path, raw_value in submitted.items():
                converted = self._convert_value(raw_value, fields[path])
                if self._get_nested(self.raw_config, path, None) != converted:
                    changed.append(path)
                    self._set_nested(self.raw_config, path, converted)

            refreshed = build_game_config(self.raw_config)
            self.game_config.clear()
            self.game_config.update(refreshed)
            if self.on_apply:
                self.on_apply(self.game_config)

            save_config = getattr(self.raw_config, "save_config", None)
            if callable(save_config):
                save_config()
        except Exception:
            self.raw_config.clear()
            self.raw_config.update(old_raw)
            self.game_config.clear()
            self.game_config.update(old_game)
            if self.on_apply:
                self.on_apply(self.game_config)
            raise

        restart_required = any(
            path.startswith(self.RESTART_REQUIRED_PREFIXES) for path in changed
        )
        return {
            "changed": changed,
            "restart_required": restart_required,
        }
