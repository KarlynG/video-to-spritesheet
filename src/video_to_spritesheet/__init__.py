"""Video to Sprite Sheet: one converter shared by the CLI, Python API, and MCP."""

__version__ = "0.2.0"

from .core import ConversionError, Options, convert, probe, validate_manifest

__all__ = ["ConversionError", "Options", "convert", "probe", "validate_manifest"]
