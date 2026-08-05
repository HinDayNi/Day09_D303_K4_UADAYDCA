from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class HandoffEnvelope(BaseModel):
    schema_version: str = "1.0"
    case_id: str
    producer: str
    consumer: str
    status: str = "success"  # "success" or "failed"
    data: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class FactBundle(BaseModel):
    case_id: str
    customer_result: Dict[str, Any] = Field(default_factory=dict)
    order_product_result: Dict[str, Any] = Field(default_factory=dict)
    payment_result: Dict[str, Any] = Field(default_factory=dict)
    delivery_result: Dict[str, Any] = Field(default_factory=dict)

class ValidationReport(BaseModel):
    case_id: str
    status: str  # "passed" or "failed"
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
