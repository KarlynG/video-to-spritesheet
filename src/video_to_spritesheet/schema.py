"""Conversion schema exposed to agents and usable in editors."""

from dataclasses import asdict

from .core import Options, FORMATS


def options_schema() -> dict:
    defaults = asdict(Options())
    positive_int = {"frame_count", "frame_width", "frame_height", "columns", "rows", "max_sheet_size", "max_frames", "max_pixels"}
    integers = positive_int | {"padding", "spacing"}
    nullable = {"fps", "frame_count", "end", "frame_width", "frame_height", "columns", "rows", "key_color", "despill"}
    strings = {"fit", "resample", "key_color", "despill", "format"}
    properties = {}
    for name, default in defaults.items():
        kind = "boolean" if type(default) is bool else "integer" if name in integers else "string" if name in strings else "number"
        prop = {"type": [kind, "null"] if name in nullable else kind, "default": default}
        if name in positive_int:
            prop["minimum"] = 1
        elif name in ("padding", "spacing", "start", "blend", "pivot_x", "pivot_y"):
            prop["minimum"] = 0
        elif name in ("fps", "timeout", "pixels_per_unit"):
            prop["exclusiveMinimum"] = 0
        if name == "similarity":
            prop.update(minimum=0.01, maximum=1)
        if name in ("blend", "pivot_x", "pivot_y"):
            prop["maximum"] = 1
        properties[name] = prop
    for name, values in {"fit": ["contain", "cover", "stretch"], "resample": ["nearest", "lanczos"],
                         "format": list(FORMATS), "despill": ["green", "blue", None]}.items():
        properties[name]["enum"] = values
    properties["frame_count"]["description"] = "Exact frame count sampled uniformly across the selected time range; mutually exclusive with fps."
    properties["fps"]["description"] = "Uniform sample rate, default 12 when frame_count is omitted."
    properties["key_color"]["description"] = "Six-digit RGB hex, optionally prefixed with # or 0x; null preserves existing alpha/background."
    properties["trim"]["description"] = "Crop all frames to one shared alpha bounding box, preserving alignment."
    properties["pixels_per_unit"]["description"] = "Unity sprite world scale; also recorded as a suggested Paper2D import setting."
    properties["pivot_y"]["description"] = "Normalized pivot measured from the bottom. Converted to Paper2D's top-origin pivot on export."
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Sprite sheet conversion options",
            "type": "object", "additionalProperties": False, "properties": properties}
