import os
import glob
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

from src.schemas.task import InputCase
from src.agents.coordinator import CoordinatorAgent
from src.writer import OutputWriter
from src.trace import TraceSink
from src.data_store import DataStore

def process_file(filepath: str, repo: DataStore, trace_sink: TraceSink, writer: OutputWriter) -> Tuple[bool, str]:
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        input_case = InputCase(**data)
        # Khởi tạo CoordinatorAgent mới cho mỗi file -> Ngữ cảnh & Bộ nhớ hoàn toàn độc lập
        coordinator = CoordinatorAgent(repo=repo, trace_sink=trace_sink)
        candidate_output = coordinator.process_case(input_case)
        written_path = writer.write_output(input_case.case_id, candidate_output)
        return True, f"▶ Processed {input_case.case_id} (Order: {input_case.claimed_order_id}) -> ✅ Saved {written_path}"
    except Exception as e:
        return False, f"❌ Error processing {filename}: {str(e)}"

def main():
    print("=" * 60)
    print("K4 Day 09 - Multi-Agent E-commerce Dispute Resolution")
    print("Coordinator & Batch Execution Pipeline (Parallel Multi-Thread)")
    print("=" * 60)

    input_dir = "input"
    output_dir = "output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    trace_sink = TraceSink(trace_path="trace.jsonl")
    writer = OutputWriter(output_dir=output_dir)
    
    # Pre-load shared read-only DataStore once to avoid reloading CSVs multiple times
    repo = None
    data_dir = Path("data")
    if data_dir.exists():
        repo = DataStore(data_dir)

    input_files = sorted(glob.glob(os.path.join(input_dir, "EC_*.json")))

    if not input_files:
        print(f"⚠️  Không tìm thấy file JSON nào trong thư mục '{input_dir}/'.")
        sys.exit(0)

    print(f"🚀 Tìm thấy {len(input_files)} cases trong '{input_dir}/'. Bắt đầu xử lý song song (Parallel 5 workers)...\n")

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_file, fp, repo, trace_sink, writer) for fp in input_files]
        for future in as_completed(futures):
            success, msg = future.result()
            print(msg)
            if success:
                success_count += 1
            else:
                fail_count += 1

    from src.verifier import write_metadata
    write_metadata(model_name="qwen2.5-7b-instruct", param_size="7B", framework="Custom Multi-Agent", log_dir=".")
    write_metadata(model_name="qwen2.5-7b-instruct", param_size="7B", framework="Custom Multi-Agent", log_dir="logging")

    print("\n" + "=" * 60)
    print(f"🏁 Hoàn thành Batch Run: {success_count} thành công, {fail_count} thất bại.")
    print(f"📄 Trace log đã lưu tại: trace.jsonl")
    print(f"📄 Metadata đã lưu tại: metadata.json")
    print(f"📁 Output files tại: {output_dir}/")
    print("=" * 60)

if __name__ == "__main__":
    main()
