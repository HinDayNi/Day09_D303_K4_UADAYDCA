import json
import os
import time
import uuid
from typing import Any, Dict, Optional

class TraceSink:
    def __init__(self, trace_path: str = "trace.jsonl"):
        self.trace_path = trace_path
        self.run_id = str(uuid.uuid4())[:8]

    def log_event(
        self,
        case_id: str,
        agent: str,
        event: str,
        status: str = "success",
        input_from: Optional[str] = None,
        output_to: Optional[str] = None,
        duration_ms: int = 0,
        retry: int = 0,
        summary: Optional[Dict[str, Any]] = None
    ):
        record = {
            "run_id": self.run_id,
            "case_id": case_id,
            "agent": agent,
            "event": event,
            "status": status,
            "input_from": input_from or "",
            "output_to": output_to or "",
            "duration_ms": duration_ms,
            "retry": retry,
            "summary": summary or {}
        }
        with open(self.trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def reset_trace(self):
        if os.path.exists(self.trace_path):
            os.remove(self.trace_path)
