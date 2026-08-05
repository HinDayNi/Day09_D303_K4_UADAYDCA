import json
import os
from typing import Any, Dict

class OutputWriter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write_output(self, case_id: str, candidate_output: Dict[str, Any]) -> str:
        filepath = os.path.join(self.output_dir, f"{case_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(candidate_output, f, ensure_ascii=False, indent=2)
        return filepath
