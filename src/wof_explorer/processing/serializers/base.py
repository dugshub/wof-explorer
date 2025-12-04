"""
Base serializer infrastructure for WOF data export.
Defines SerializerBase and a simple SerializerRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, IO
from pathlib import Path

from wof_explorer.models.places import WOFPlace


class SerializerBase(ABC):
    """Abstract base class for all serializers."""

    @abstractmethod
    def serialize(self, places: List[WOFPlace], **options) -> str:
        """Serialize places to a string format."""
        raise NotImplementedError

    @abstractmethod
    def serialize_to_dict(self, places: List[WOFPlace], **options) -> Any:
        """Serialize places to a structured object (dict/list)."""
        raise NotImplementedError

    def write(self, places: List[WOFPlace], file: IO[str], **options) -> None:
        """Write serialized data to an open file-like object."""
        data = self.serialize(places, **options)
        file.write(data)

    def save(self, places: List[WOFPlace], path: Path | str, **options) -> None:
        """Save serialized output to a file path."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        text = self.serialize(places, **options)
        p.write_text(text, encoding="utf-8")

    def validate_options(self, **options) -> Dict[str, Any]:
        """Validate and normalize serializer options.

        Subclasses may override to enforce allowed options or defaults.
        """
        return options


class SerializerRegistry:
    """Registry mapping format names to serializer instances."""

    _serializers: Dict[str, SerializerBase] = {}

    @classmethod
    def register(cls, fmt: str, serializer: SerializerBase) -> None:
        key = fmt.strip().lower()
        cls._serializers[key] = serializer

    @classmethod
    def get(cls, fmt: str) -> SerializerBase:
        key = fmt.strip().lower()
        if key not in cls._serializers:
            available = ", ".join(sorted(cls._serializers.keys())) or "<none>"
            raise ValueError(f"Unknown format: {fmt}. Available: {available}")
        return cls._serializers[key]

    @classmethod
    def formats(cls) -> List[str]:
        return sorted(cls._serializers.keys())
