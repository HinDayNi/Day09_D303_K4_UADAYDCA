import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class CaseAssessmentSchema:
    primary_issue: str
    secondary_issues: List[str]
    case_status: str
    confidence: float

@dataclass
class AffectedEntitiesSchema:
    order_ids: List[str]
    item_ids: List[str]
    seller_ids: List[str]
    payment_ids: List[str]

@dataclass
class CustomerContextSchema:
    customer_unique_id: Optional[str]
    related_order_ids: List[str]

@dataclass
class ProductContextSchema:
    product_ids: List[str]
    category_names: List[str]

@dataclass
class SellerHandoffAnalysisSchema:
    seller_id: str
    shipping_limit_at: Optional[str]
    handoff_variance_hours: Optional[float]
    late_handoff: bool

@dataclass
class DeliveryAnalysisSchema:
    delivered_at: Optional[str]
    estimated_delivery_at: Optional[str]
    carrier_handoff_at: Optional[str]
    delivery_variance_hours: Optional[float]
    seller_handoff_analysis: List[SellerHandoffAnalysisSchema]
    late_handoff_seller_ids: List[str]

@dataclass
class PaymentReconciliationSchema:
    currency: str
    item_total_brl: Optional[float]
    freight_total_brl: Optional[float]
    expected_total_brl: Optional[float]
    payment_total_brl: Optional[float]
    difference_brl: Optional[float]
    reconciled: Optional[bool]
    payment_types: List[str]

@dataclass
class CauseRankSchema:
    cause_code: str
    rank: int

@dataclass
class ResponsiblePartySchema:
    party_type: str
    party_id: str

@dataclass
class RootCauseAnalysisSchema:
    ranked_causes: List[CauseRankSchema]
    responsible_parties: List[ResponsiblePartySchema]

@dataclass
class FinancialResolutionSchema:
    currency: str
    recommended_refund_brl: Optional[float]

@dataclass
class OutputSchema:
    case_id: str
    case_assessment: CaseAssessmentSchema
    affected_entities: AffectedEntitiesSchema
    customer_context: CustomerContextSchema
    product_context: ProductContextSchema
    delivery_analysis: DeliveryAnalysisSchema
    payment_reconciliation: PaymentReconciliationSchema
    root_cause_analysis: RootCauseAnalysisSchema
    evidence_ids: List[str]
    financial_resolution: FinancialResolutionSchema
    resolution_actions: List[str]


def is_valid_evidence_id(eid: str) -> bool:
    if not isinstance(eid, str):
        return False
    patterns = [
        r"^order:[^:]+$",
        r"^item:[^:]+:[^:]+$",
        r"^payment:[^:]+:[^:]+$",
        r"^seller:[^:]+$",
        r"^policy:[^:]+$"
    ]
    return any(re.match(p, eid) for p in patterns)


def is_valid_iso_datetime(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        import datetime
        datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def is_valid_case_status(value: str) -> bool:
    return value in {"action_required", "no_action"}


def round2(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    # Làm tròn chuẩn 2 chữ số thập phân và kiểm tra chênh lệch vi mô
    rounded = round(float(value), 2)
    return abs(float(value) - rounded) < 1e-6


def validate_output_schema(output: Dict[str, Any]) -> List[str]:
    errors = []

    if not isinstance(output, dict):
        return ["Output must be a JSON object."]

    required_root = [
        "case_id",
        "case_assessment",
        "affected_entities",
        "customer_context",
        "product_context",
        "delivery_analysis",
        "payment_reconciliation",
        "root_cause_analysis",
        "evidence_ids",
        "financial_resolution",
        "resolution_actions",
    ]

    for key in required_root:
        if key not in output:
            errors.append(f"Missing root field: {key}")

    # 1. case_assessment
    if "case_assessment" in output:
        ca = output["case_assessment"]
        if not isinstance(ca, dict):
            errors.append("case_assessment must be an object.")
        else:
            if not isinstance(ca.get("primary_issue"), str):
                errors.append("case_assessment.primary_issue must be a string.")
            if not isinstance(ca.get("secondary_issues"), list):
                errors.append("case_assessment.secondary_issues must be an array.")
            if not is_valid_case_status(ca.get("case_status", "")):
                errors.append("case_assessment.case_status must be 'action_required' or 'no_action'.")
            confidence = ca.get("confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
                errors.append("case_assessment.confidence must be a number between 0 and 1.")

    # 2. affected_entities & No-item Order Check
    is_no_item_order = False
    if "affected_entities" in output:
        ae = output["affected_entities"]
        if not isinstance(ae, dict):
            errors.append("affected_entities must be an object.")
        else:
            for field in ["order_ids", "item_ids", "seller_ids", "payment_ids"]:
                value = ae.get(field)
                if not isinstance(value, list):
                    errors.append(f"affected_entities.{field} must be an array.")
                else:
                    max_len = 3 if field == "seller_ids" else 5
                    if len(value) > max_len:
                        errors.append(f"affected_entities.{field} may contain at most {max_len} elements.")
                    for item in value:
                        if not isinstance(item, str):
                            errors.append(f"affected_entities.{field} values must be strings.")

            if isinstance(ae.get("item_ids"), list) and len(ae.get("item_ids")) == 0:
                is_no_item_order = True
                if len(ae.get("seller_ids", [])) > 0:
                    errors.append("No-item order must have empty seller_ids [].")

    # 3. customer_context
    if "customer_context" in output:
        cc = output["customer_context"]
        if not isinstance(cc, dict):
            errors.append("customer_context must be an object.")
        else:
            if cc.get("customer_unique_id") is not None and not isinstance(cc.get("customer_unique_id"), str):
                errors.append("customer_context.customer_unique_id must be a string or null.")
            if not isinstance(cc.get("related_order_ids"), list):
                errors.append("customer_context.related_order_ids must be an array.")
            elif len(cc.get("related_order_ids")) > 5:
                errors.append("customer_context.related_order_ids may contain at most 5 elements.")

    # 4. product_context
    if "product_context" in output:
        pc = output["product_context"]
        if not isinstance(pc, dict):
            errors.append("product_context must be an object.")
        else:
            for field in ["product_ids", "category_names"]:
                value = pc.get(field)
                if not isinstance(value, list):
                    errors.append(f"product_context.{field} must be an array.")
                elif len(value) > 5:
                    errors.append(f"product_context.{field} may contain at most 5 elements.")
                else:
                    for item in value:
                        if not isinstance(item, str):
                            errors.append(f"product_context.{field} values must be strings.")

            if is_no_item_order:
                if len(pc.get("product_ids", [])) > 0 or len(pc.get("category_names", [])) > 0:
                    errors.append("No-item order must have empty product_ids [] and category_names [].")

    # 5. delivery_analysis
    if "delivery_analysis" in output:
        da = output["delivery_analysis"]
        if not isinstance(da, dict):
            errors.append("delivery_analysis must be an object.")
        else:
            for field in ["delivered_at", "estimated_delivery_at", "carrier_handoff_at"]:
                if field not in da:
                    errors.append(f"delivery_analysis.{field} is required.")
                elif not is_valid_iso_datetime(da.get(field)):
                    errors.append(f"delivery_analysis.{field} must be null or 'YYYY-MM-DD HH:MM:SS'.")
            dv = da.get("delivery_variance_hours")
            if dv is not None and not round2(dv):
                errors.append("delivery_analysis.delivery_variance_hours must be rounded to 2 decimals.")
            if not isinstance(da.get("seller_handoff_analysis"), list):
                errors.append("delivery_analysis.seller_handoff_analysis must be an array.")
            else:
                for entry in da.get("seller_handoff_analysis"):
                    if not isinstance(entry, dict):
                        errors.append("delivery_analysis.seller_handoff_analysis entries must be objects.")
                        continue
                    if not isinstance(entry.get("seller_id"), str):
                        errors.append("delivery_analysis.seller_handoff_analysis.seller_id must be a string.")
                    if not is_valid_iso_datetime(entry.get("shipping_limit_at")):
                        errors.append("delivery_analysis.seller_handoff_analysis.shipping_limit_at must be null or timestamp.")
                    if entry.get("handoff_variance_hours") is not None and not round2(entry.get("handoff_variance_hours")):
                        errors.append("delivery_analysis.seller_handoff_analysis.handoff_variance_hours must be rounded to 2 decimals.")
                    if not isinstance(entry.get("late_handoff"), bool):
                        errors.append("delivery_analysis.seller_handoff_analysis.late_handoff must be a boolean.")
            if not isinstance(da.get("late_handoff_seller_ids"), list):
                errors.append("delivery_analysis.late_handoff_seller_ids must be an array.")
            elif len(da.get("late_handoff_seller_ids")) > 3:
                errors.append("delivery_analysis.late_handoff_seller_ids may contain at most 3 elements.")

    # 6. payment_reconciliation
    if "payment_reconciliation" in output:
        pr = output["payment_reconciliation"]
        if not isinstance(pr, dict):
            errors.append("payment_reconciliation must be an object.")
        else:
            if pr.get("currency") != "BRL":
                errors.append("payment_reconciliation.currency must be 'BRL'.")
            for field in ["item_total_brl", "freight_total_brl", "expected_total_brl", "payment_total_brl", "difference_brl"]:
                value = pr.get(field)
                if value is not None and not round2(value):
                    errors.append(f"payment_reconciliation.{field} must be rounded to 2 decimals or null.")
            if pr.get("reconciled") is not None and not isinstance(pr.get("reconciled"), bool):
                errors.append("payment_reconciliation.reconciled must be a boolean or null.")
            if not isinstance(pr.get("payment_types"), list):
                errors.append("payment_reconciliation.payment_types must be an array.")

            if is_no_item_order:
                if pr.get("expected_total_brl") is not None or pr.get("difference_brl") is not None or pr.get("reconciled") is not None:
                    errors.append("No-item order must have null for expected_total_brl, difference_brl, and reconciled.")

    # 7. root_cause_analysis
    if "root_cause_analysis" in output:
        rc = output["root_cause_analysis"]
        if not isinstance(rc, dict):
            errors.append("root_cause_analysis must be an object.")
        else:
            if not isinstance(rc.get("ranked_causes"), list):
                errors.append("root_cause_analysis.ranked_causes must be an array.")
            elif len(rc.get("ranked_causes")) > 3:
                errors.append("root_cause_analysis.ranked_causes may contain at most 3 elements.")
            if not isinstance(rc.get("responsible_parties"), list):
                errors.append("root_cause_analysis.responsible_parties must be an array.")
            elif len(rc.get("responsible_parties")) > 3:
                errors.append("root_cause_analysis.responsible_parties may contain at most 3 elements.")

    # 8. evidence_ids
    if "evidence_ids" in output:
        evs = output["evidence_ids"]
        if not isinstance(evs, list):
            errors.append("evidence_ids must be an array.")
        elif len(evs) > 20:
            errors.append("evidence_ids may contain at most 20 elements.")
        else:
            for eid in evs:
                if not is_valid_evidence_id(eid):
                    errors.append(f"Invalid evidence_id format: {eid}")

    # 9. financial_resolution
    if "financial_resolution" in output:
        fr = output["financial_resolution"]
        if not isinstance(fr, dict):
            errors.append("financial_resolution must be an object.")
        else:
            if fr.get("currency") != "BRL":
                errors.append("financial_resolution.currency must be 'BRL'.")
            if fr.get("recommended_refund_brl") is not None and not round2(fr.get("recommended_refund_brl")):
                errors.append("financial_resolution.recommended_refund_brl must be rounded to 2 decimals or null.")

    # 10. resolution_actions
    if "resolution_actions" in output:
        res_actions = output["resolution_actions"]
        if not isinstance(res_actions, list):
            errors.append("resolution_actions must be an array.")
        elif len(res_actions) > 5:
            errors.append("resolution_actions may contain at most 5 elements.")

    return errors