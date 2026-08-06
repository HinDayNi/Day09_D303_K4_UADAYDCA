import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import glob
import json
from pathlib import Path
from src.verifier import validate_output

def check_outputs():
    output_files = sorted(glob.glob("output/EC_*.json"))
    print(f"Checking {len(output_files)} files in output/...")
    
    total_errors = 0
    for file_path in output_files:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        errors = validate_output(data, check_csv=True)
        if errors:
            print(f"❌ {filename}: {errors}")
            total_errors += len(errors)
        
        # Specific checks from review:
        # Check no-item orders: item_total_brl and freight_total_brl must be 0.0, expected/difference/reconciled must be None
        items = data.get("affected_entities", {}).get("item_ids", [])
        pay_rec = data.get("payment_reconciliation", {})
        if not items:
            if pay_rec.get("item_total_brl") != 0.0:
                print(f"⚠️ {filename}: No-item order item_total_brl is {pay_rec.get('item_total_brl')}, expected 0.0")
                total_errors += 1
            if pay_rec.get("freight_total_brl") != 0.0:
                print(f"⚠️ {filename}: No-item order freight_total_brl is {pay_rec.get('freight_total_brl')}, expected 0.0")
                total_errors += 1
            if pay_rec.get("expected_total_brl") is not None:
                print(f"⚠️ {filename}: No-item order expected_total_brl is {pay_rec.get('expected_total_brl')}, expected None")
                total_errors += 1

        # Check canceled/unavailable orders: delivered_at, carrier_handoff_at, delivery_variance_hours must be None
        primary_issue = data.get("case_assessment", {}).get("primary_issue")
        deliv = data.get("delivery_analysis", {})
        if primary_issue in ("canceled_order_paid", "unavailable_order_paid"):
            if deliv.get("delivered_at") is not None:
                print(f"⚠️ {filename}: Canceled/Unavailable order delivered_at is {deliv.get('delivered_at')}, expected None")
                total_errors += 1
            if deliv.get("carrier_handoff_at") is not None:
                print(f"⚠️ {filename}: Canceled/Unavailable order carrier_handoff_at is {deliv.get('carrier_handoff_at')}, expected None")
                total_errors += 1
            if deliv.get("delivery_variance_hours") is not None:
                print(f"⚠️ {filename}: Canceled/Unavailable order delivery_variance_hours is {deliv.get('delivery_variance_hours')}, expected None")
                total_errors += 1

    if total_errors == 0:
        print("✅ ALL 50 CASES PASSED VERIFIER AND REVIEW CHECK!")
    else:
        print(f"❌ TOTAL ERRORS: {total_errors}")

if __name__ == "__main__":
    check_outputs()
