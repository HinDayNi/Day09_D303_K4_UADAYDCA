from pydantic import BaseModel, Field
from typing import Optional

class CustomerRequest(BaseModel):
    language: str = "vi"
    message: Optional[str] = ""
    claimed_order_id: str

class InvestigationScope(BaseModel):
    include_customer_history: bool = True
    include_product_context: bool = True

class InputCase(BaseModel):
    case_id: str
    customer_request: CustomerRequest
    investigation_scope: InvestigationScope
    policy_version: str = "EC_POLICY_V2"

    @property
    def claimed_order_id(self) -> str:
        return self.customer_request.claimed_order_id
