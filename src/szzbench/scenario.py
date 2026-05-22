from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .findings import ValidationResult

class UniqueKeyLoader(yaml.SafeLoader):
    pass

def _construct_mapping(loader: UniqueKeyLoader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key}",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping

UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)

def load_yaml(path: Path) -> tuple[dict[str, Any] | None, ValidationResult]:
    result = ValidationResult()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.load(fh, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        result.error("E001", f"YAML parse error: {exc}", str(path))
        return None, result
    except OSError as exc:
        result.error("E000", f"Cannot read scenario file: {exc}", str(path))
        return None, result
    if not isinstance(data, dict):
        result.error("E002", "The root of scenario.yml must be a mapping/object.", str(path))
        return None, result
    return data, result
