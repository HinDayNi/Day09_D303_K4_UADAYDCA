from typing import Any, Dict
from src.schemas.handoff import ValidationReport
from src.verifier import validate_output

class VerifierAgent:
    """
    Agent 5: Verifier Agent kiểm tra schema, evidence ID, số tiền, null, array limits.
    Phụ trách bởi: Người 5 (Verifier, Testing & Submission - Trần Thị Hường)
    """
    def __init__(self, repo=None, check_csv: bool = False):
        self.repo = repo
        self.check_csv = check_csv

    def verify(self, case_id: str, candidate_output: Dict[str, Any]) -> ValidationReport:
        errors = validate_output(candidate_output, check_csv=self.check_csv)
        formatted_errors = [{"message": err} for err in errors]
        status = "passed" if len(errors) == 0 else "failed"
        return ValidationReport(
            case_id=case_id,
            status=status,
            errors=formatted_errors,
            warnings=[]
        )
