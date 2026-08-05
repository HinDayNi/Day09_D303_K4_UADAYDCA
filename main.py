import os
import glob
import json
import sys
from pathlib import Path
from typing import List

from src.schemas.task import InputCase
from src.agents.coordinator import CoordinatorAgent
from src.data_store import DataStore
from src.writer import OutputWriter
from src.trace import TraceSink

def main():
    print("=" * 60)
    print("K4 Day 09 - Multi-Agent E-commerce Dispute Resolution")
    print("Coordinator & Batch Execution Pipeline (Người 1)")
    print("=" * 60)

    input_dir = "input"
    output_dir = "output"
    data_dir = Path("data")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print(f"📦 Đang nạp DataStore từ '{data_dir}/'...")
    data_store = DataStore(data_dir)
    print("✅ DataStore sẵn sàng.\n")

    trace_sink = TraceSink(trace_path="trace.jsonl")
    writer = OutputWriter(output_dir=output_dir)
    coordinator = CoordinatorAgent(repo=data_store, trace_sink=trace_sink)

    # Tìm các file input EC_*.json
    input_files = sorted(glob.glob(os.path.join(input_dir, "EC_*.json")))

    if not input_files:
        print(f"⚠️  Không tìm thấy file JSON nào trong thư mục '{input_dir}/'.")
        print("    Vui lòng đặt các file test case (EC_001.json -> EC_050.json) vào thư mục input/.")
        sys.exit(0)

    print(f"🚀 Tìm thấy {len(input_files)} cases trong '{input_dir}/'. Bắt đầu xử lý batch...\n")

    success_count = 0
    fail_count = 0

    for filepath in input_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            input_case = InputCase(**data)
            print(f"▶ Processing {input_case.case_id} (Order: {input_case.claimed_order_id})...", end=" ", flush=True)

            candidate_output = coordinator.process_case(input_case)
            written_path = writer.write_output(input_case.case_id, candidate_output)
            print(f"✅ Saved -> {written_path}")
            success_count += 1

        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"🏁 Hoàn thành Batch Run: {success_count} thành công, {fail_count} thất bại.")
    print(f"📄 Trace log đã lưu tại: trace.jsonl")
    print(f"📁 Output files tại: {output_dir}/")
    print("=" * 60)

if __name__ == "__main__":
    main()
