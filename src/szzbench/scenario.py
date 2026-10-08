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
        # A file that is not UTF-8 raised UnicodeDecodeError from inside PyYAML, which
        # nothing caught: every command that reads scenarios or an index ended in a
        # traceback (issue #149).  Decoding the bytes first also gives the offset in
        # the file, not in PyYAML's read buffer.
        path.read_bytes().decode("utf-8")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.load(fh, Loader=UniqueKeyLoader)
    except UnicodeDecodeError as exc:
        result.error("E000", f"Cannot read {path.name}: it is not UTF-8 (byte 0x{exc.object[exc.start]:02x} at "
                     f"position {exc.start}); save it as UTF-8.", str(path))
        return None, result
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
