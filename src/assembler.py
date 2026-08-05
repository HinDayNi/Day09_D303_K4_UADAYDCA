from typing import Any, Dict, List

class ResultAssembler:
    """
    Tích hợp kết quả từ các Specialist Agent và Policy Agent thành 1 candidate JSON hoàn chỉnh
    đúng chuẩn Output Schema của EC_POLICY_V2.
    """
    def assemble(self, case_id: str, fact_bundle: dict, policy_data: dict) -> Dict[str, Any]:
        cust = fact_bundle.get("customer_result", {})
        ord_prod = fact_bundle.get("order_product_result", {})
        pay = fact_bundle.get("payment_result", {})
        deliv = fact_bundle.get("delivery_result", {})

        claimed_order_id = ord_prod.get("order_id", "")

        # Extract policy_data fields whether nested or flat
        case_assess = policy_data.get("case_assessment", {}) if isinstance(policy_data.get("case_assessment"), dict) else {}
        root_cause = policy_data.get("root_cause_analysis", {}) if isinstance(policy_data.get("root_cause_analysis"), dict) else {}
        fin_res = policy_data.get("financial_resolution", {}) if isinstance(policy_data.get("financial_resolution"), dict) else {}

        primary_issue = case_assess.get("primary_issue") or policy_data.get("primary_issue")
        secondary_issues = case_assess.get("secondary_issues") if "secondary_issues" in case_assess else policy_data.get("secondary_issues", [])
        case_status = case_assess.get("case_status") or policy_data.get("case_status")
        confidence = case_assess.get("confidence") or policy_data.get("confidence", 0.95)

        ranked_causes = root_cause.get("ranked_causes") if "ranked_causes" in root_cause else policy_data.get("ranked_causes", [])
        responsible_parties = root_cause.get("responsible_parties") if "responsible_parties" in root_cause else policy_data.get("responsible_parties", [])

        recommended_refund = fin_res.get("recommended_refund_brl") if "recommended_refund_brl" in fin_res else policy_data.get("recommended_refund_brl", 0.0)
        resolution_actions = policy_data.get("resolution_actions", [])

        # 1. Affected entities
        # 1. Affected entities
        items_raw = ord_prod.get("items", [])
        item_ids = [f"{claimed_order_id}:{it.get('order_item_id')}" for it in items_raw][:5]
        order_ids = [claimed_order_id][:5] if claimed_order_id else []
        seller_ids = ord_prod.get("sellers", [])[:3] if item_ids else []
        payment_ids = pay.get("affected_payment_ids") or pay.get("payment_ids", [])[:5]

        # 2. Customer context
        cust_ctx = cust.get("customer_context", {}) if isinstance(cust.get("customer_context"), dict) else cust
        customer_unique_id = cust_ctx.get("customer_unique_id", "") or cust.get("customer_unique_id", "")
        related_order_ids = (cust_ctx.get("related_order_ids") if "related_order_ids" in cust_ctx else cust.get("related_order_ids", []))[:5]

        # 3. Product context
        prod_ctx = cust.get("product_context", {}) if isinstance(cust.get("product_context"), dict) else {}
        if item_ids:
            product_ids = (prod_ctx.get("product_ids") or ord_prod.get("products", []))[:5]
            category_names = (prod_ctx.get("category_names") or ord_prod.get("categories", []))[:5]
        else:
            product_ids = []
            category_names = []

        # 4. Delivery analysis
        seller_handoff_analysis = deliv.get("seller_handoff_analysis", []) if item_ids else []
        late_handoff_seller_ids = deliv.get("late_handoff_seller_ids", []) if item_ids else []
        delivery_analysis = {
            "delivered_at": deliv.get("delivered_at"),
            "estimated_delivery_at": deliv.get("estimated_delivery_at"),
            "carrier_handoff_at": deliv.get("carrier_handoff_at"),
            "delivery_variance_hours": deliv.get("delivery_variance_hours"),
            "seller_handoff_analysis": seller_handoff_analysis,
            "late_handoff_seller_ids": late_handoff_seller_ids
        }

        # 5. Payment reconciliation
        pay_recon = pay.get("payment_reconciliation", {}) if isinstance(pay.get("payment_reconciliation"), dict) else pay
        payment_reconciliation = {
            "currency": pay_recon.get("currency", "BRL"),
            "item_total_brl": pay_recon.get("item_total_brl"),
            "freight_total_brl": pay_recon.get("freight_total_brl"),
            "expected_total_brl": pay_recon.get("expected_total_brl"),
            "payment_total_brl": pay_recon.get("payment_total_brl"),
            "difference_brl": pay_recon.get("difference_brl"),
            "reconciled": pay_recon.get("reconciled"),
            "payment_types": pay_recon.get("payment_types", [])
        }

        # 6. Evidence IDs generation
        evidence_ids = []
        if claimed_order_id:
            evidence_ids.append(f"order:{claimed_order_id}")
        for it_id in item_ids:
            evidence_ids.append(f"item:{it_id}")
        for p_id in payment_ids:
            evidence_ids.append(f"payment:{p_id}")
        
        # Add responsible seller evidence
        for party in responsible_parties:
            if party.get("party_type") == "seller":
                s_id = party.get("party_id")
                if s_id and s_id not in ["OLIST_PLATFORM", "LOGISTICS_PROVIDER"]:
                    evidence_ids.append(f"seller:{s_id}")

        # Add policy root cause evidence
        if ranked_causes:
            top_cause = ranked_causes[0].get("cause_code")
            if top_cause:
                evidence_ids.append(f"policy:{top_cause}")

        # Deduplicate and cap at 20
        unique_evidences = []
        for ev in evidence_ids:
            if ev not in unique_evidences:
                unique_evidences.append(ev)
        evidence_ids = unique_evidences[:20]

        candidate = {
            "case_id": case_id,
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": case_status,
                "confidence": confidence
            },
            "affected_entities": {
                "order_ids": order_ids,
                "item_ids": item_ids,
                "seller_ids": seller_ids,
                "payment_ids": payment_ids
            },
            "customer_context": {
                "customer_unique_id": customer_unique_id,
                "related_order_ids": related_order_ids
            },
            "product_context": {
                "product_ids": product_ids,
                "category_names": category_names
            },
            "delivery_analysis": delivery_analysis,
            "payment_reconciliation": payment_reconciliation,
            "root_cause_analysis": {
                "ranked_causes": ranked_causes[:3],
                "responsible_parties": responsible_parties[:3]
            },
            "evidence_ids": evidence_ids,
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": recommended_refund
            },
            "resolution_actions": resolution_actions[:5]
        }
        return candidate
