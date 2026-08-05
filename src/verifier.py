import json
from typing import Any, Dict, List

from .schemas import validate_output_schema


def validate_output(output: Any) -> List[str]:
    """Validate a parsed output JSON object and return a list of errors."""
    return validate_output_schema(output)


def load_output_from_path(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
