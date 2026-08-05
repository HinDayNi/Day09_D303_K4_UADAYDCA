from typing import Any, Dict
from src.schemas.handoff import ValidationReport

class VerifierAgent:
    """
    Agent 5: Verifier Agent kiểm tra schema, evidence ID, số tiền, null, array limits.
    Phụ trách bởi: Người 5 (Verifier, Testing & Submission)
    """
    def __init__(self, repo=None):
        self.repo = repo

    def verify(self, case_id: str, candidate_output: Dict[str, Any]) -> ValidationReport:
        # Stub implementation - sẽ được Người 5 bổ sung kiểm tra invariants và schema
        return ValidationReport(
            case_id=case_id,
            status="passed",
            errors=[],
            warnings=[]
        )
