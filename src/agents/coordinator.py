import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.schemas.task import InputCase
from src.schemas.handoff import HandoffEnvelope, FactBundle, ValidationReport
from src.trace import TraceSink
from src.assembler import ResultAssembler

from src.agents.customer_product_agent import CustomerProductAgent as CustomerAgent
from src.agents.order_product import OrderProductAgent
from src.agents.delivery import DeliveryAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.verifier import VerifierAgent
from src.llm_client import LLMClient



# =====================================================================
# 1. SYSTEM PROMPT DÀNH CHO AGENT ĐIỀU PHỐI (COORDINATOR PROMPT)
# =====================================================================
COORDINATOR_SYSTEM_PROMPT = """
[BẢN HƯỚNG DẪN AGENT ĐIỀU PHỐI - COORDINATOR AGENT]

Bạn là Agent Điều Phối Trung Tâm (Coordinator Agent). Nhiệm vụ của bạn là nhận các yêu cầu điều tra khiếu nại thương mại điện tử, lập kế hoạch thực hiện (State Plan), lưu trữ bộ nhớ ngắn hạn (Memory Store) và động năng quyết định gọi các Agent chuyên biệt.

DANG SÁCH AGENTS THUỘC QUYỀN ĐIỀU PHỐI (TOOL REGISTRY):
1. `customer_agent`: Tra cứu thông tin khách hàng, `customer_unique_id` và lịch sử đơn hàng.
2. `order_product_agent`: Tra cứu đơn hàng, các mặt hàng (items), thông tin sellers, sản phẩm và danh mục (categories).
3. `delivery_agent`: Phân tích thời gian giao hàng, tính `delivery_variance_hours` và `handoff_variance_hours`.
4. `payment_agent`: Tra cứu các khoản thanh toán (`order_payments`) và thực hiện đối soát tài chính (`reconciliation`).
5. `policy_agent`: Đưa ra quyết định cuối cùng dựa trên quy tắc `EC_POLICY_V2` (Primary issue, Secondary issues, Refund, Actions).
6. `verifier_agent`: Kiểm tra độc lập tính hợp lệ của Candidate Output JSON trước khi xuất file.

QUY TRÌNH RA QUYẾT ĐỊNH (REASONING & EXECUTION LOOP):
- BƯỚC 1 (Lên Plan): Đọc scope điều tra và tạo `StatePlan` chứa chuỗi công việc cần làm.
- BƯỚC 2 (Theo dõi Plan & Bộ nhớ Memory): Lần lượt kiểm tra bước tiếp theo trong `StatePlan`. Tra cứu bộ nhớ ngắn hạn `CoordinatorMemory` để lấy dữ liệu cần thiết cho Agent được chọn.
- BƯỚC 3 (Động năng gọi Agent): Gọi Agent thông qua Registry dựa theo quyết định trong Plan thay vì chạy cố định luồng tĩnh.
- BƯỚC 4 (Cập nhật State & Tổng hợp): Cập nhật kết quả vào `CoordinatorMemory`, đánh dấu bước hoàn thành trong `StatePlan` và tiến hành đóng gói Candidate Output.
"""


# =====================================================================
# 2. STATE PLAN (BỘ QUẢN LÝ KẾ HOẠCH & TIẾN ĐỘ)
# =====================================================================
class PlanStep(BaseModel):
    step_id: int
    agent_name: str
    goal: str
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    result_summary: Optional[Dict[str, Any]] = None

class StatePlan(BaseModel):
    case_id: str
    steps: List[PlanStep] = Field(default_factory=list)
    current_step_index: int = 0
    is_completed: bool = False

    def get_next_step(self) -> Optional[PlanStep]:
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def mark_step_completed(self, summary: Optional[Dict[str, Any]] = None):
        if self.current_step_index < len(self.steps):
            self.steps[self.current_step_index].status = "completed"
            self.steps[self.current_step_index].result_summary = summary
            self.current_step_index += 1
            if self.current_step_index >= len(self.steps):
                self.is_completed = True

    def mark_step_failed(self, error_msg: str):
        if self.current_step_index < len(self.steps):
            self.steps[self.current_step_index].status = "failed"


# =====================================================================
# 3. COORDINATOR MEMORY (BỘ NHỚ NGẮN HẠN PHỤC VỤ THỰC THI)
# =====================================================================
class CoordinatorMemory:
    def __init__(self):
        self.short_term_store: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []

    def set_fact(self, key: str, value: Any):
        self.short_term_store[key] = value

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.short_term_store.get(key, default)

    def log_action(self, agent_name: str, status: str, summary: Dict[str, Any]):
        self.execution_history.append({
            "timestamp": time.time(),
            "agent": agent_name,
            "status": status,
            "summary": summary
        })


# =====================================================================
# 4. COORDINATOR AGENT (AGENT ĐIỀU PHỐI ĐỘNG)
# =====================================================================
class CoordinatorAgent:
    """
    Coordinator Agent - Trưởng nhóm / Điều phối hệ thống (Người 1).
    - Có Prompt hướng dẫn quy trình (`COORDINATOR_SYSTEM_PROMPT`).
    - Lên Kế hoạch trước khi làm (`StatePlan`).
    - Quản lý bộ nhớ thực thi ngắn hạn (`CoordinatorMemory`).
    - Động năng chọn và gọi Agent dựa theo Registry chứ không hardcode luồng tĩnh trong code.
    """
    def __init__(
        self,
        repo=None,
        trace_sink: Optional[TraceSink] = None,
        customer_agent: Optional[CustomerAgent] = None,
        order_product_agent: Optional[OrderProductAgent] = None,
        delivery_agent: Optional[DeliveryAgent] = None,
        payment_agent: Optional[PaymentAgent] = None,
        policy_agent: Optional[PolicyAgent] = None,
        verifier_agent: Optional[VerifierAgent] = None
    ):
        if repo is None:
            from pathlib import Path
            from src.data_store import DataStore
            data_dir = Path("data")
            if data_dir.exists():
                try:
                    self.repo = DataStore(data_dir)
                except Exception:
                    self.repo = None
            else:
                self.repo = None
        else:
            self.repo = repo

        self.trace_sink = trace_sink or TraceSink()
        self.assembler = ResultAssembler()
        self.prompt = COORDINATOR_SYSTEM_PROMPT

        # Khởi tạo các Agent chuyên biệt an toàn
        def _init_agent(agent_obj, agent_cls):
            if agent_obj is not None:
                return agent_obj
            try:
                return agent_cls(repo=self.repo)
            except TypeError:
                try:
                    return agent_cls(data_store=self.repo)
                except TypeError:
                    return agent_cls()

        self.customer_agent = _init_agent(customer_agent, CustomerAgent)
        self.order_product_agent = _init_agent(order_product_agent, OrderProductAgent)
        self.delivery_agent = _init_agent(delivery_agent, DeliveryAgent)
        self.payment_agent = _init_agent(payment_agent, PaymentAgent)
        self.policy_agent = _init_agent(policy_agent, PolicyAgent)
        self.verifier_agent = _init_agent(verifier_agent, VerifierAgent)



        # Agent Registry (Danh mục các Agent sẵn sàng được chọn gọi động)
        self.agent_registry = {
            "customer_agent": self.customer_agent,
            "order_product_agent": self.order_product_agent,
            "delivery_agent": self.delivery_agent,
            "payment_agent": self.payment_agent,
            "policy_agent": self.policy_agent,
            "verifier_agent": self.verifier_agent,
        }
        self.llm_client = LLMClient()


    def _build_initial_plan(self, input_case: InputCase) -> StatePlan:
        """
        Dựa vào Prompt và Yêu cầu điều tra của InputCase để LÊN PLAN trước khi làm.
        """
        steps = [
            PlanStep(step_id=1, agent_name="customer_agent", goal="Xác định danh tính khách hàng và lịch sử đơn mua cũ"),
            PlanStep(step_id=2, agent_name="order_product_agent", goal="Thu thập đơn hàng, items, sellers, sản phẩm và danh mục"),
            PlanStep(step_id=3, agent_name="delivery_agent", goal="Phân tích chênh lệch giao hàng và thời hạn bàn giao của seller"),
            PlanStep(step_id=4, agent_name="payment_agent", goal="Tổng hợp các khoản payment và đối soát tài chính"),
            PlanStep(step_id=5, agent_name="policy_agent", goal="Áp dụng quy tắc EC_POLICY_V2 xác định trách nhiệm và hoàn tiền"),
            PlanStep(step_id=6, agent_name="verifier_agent", goal="Kiểm tra độc lập Schema, Evidence ID và các hạn chế")
        ]
        return StatePlan(case_id=input_case.case_id, steps=steps)

    def process_case(self, input_case: InputCase) -> Dict[str, Any]:
        case_id = input_case.case_id
        claimed_order_id = input_case.claimed_order_id

        # 1. Khởi tạo Kế hoạch (State Plan) & Bộ nhớ (Memory Store)
        plan = self._build_initial_plan(input_case)
        memory = CoordinatorMemory()
        memory.set_fact("case_id", case_id)
        memory.set_fact("claimed_order_id", claimed_order_id)
        memory.set_fact("input_case", input_case)

        self.trace_sink.log_event(
            case_id=case_id,
            agent="coordinator_agent",
            event="agent_started",
            status="success",
            summary={
                "claimed_order_id": claimed_order_id,
                "plan_steps_count": len(plan.steps)
            }
        )

        retry_count = 0
        max_repairs = 1

        while retry_count <= max_repairs:
            # Vòng lặp thực thi động dựa theo State Plan và Registry
            while not plan.is_completed:
                current_step = plan.get_next_step()
                if not current_step:
                    break

                agent_name = current_step.agent_name
                t0 = time.time()

                # Động năng gọi Agent từ Registry dựa theo quyết định trong Plan & Memory
                if agent_name == "customer_agent":
                    agent = self.agent_registry["customer_agent"]
                    env = agent.run(case_id, claimed_order_id)
                    memory.set_fact("customer_result", env.data)
                    plan.mark_step_completed(summary={"status": env.status})

                elif agent_name == "order_product_agent":
                    agent = self.agent_registry["order_product_agent"]
                    # Kiểm tra xem có method run hay process/analyze
                    if hasattr(agent, "run"):
                        env = agent.run(case_id, claimed_order_id)
                        data = env.data if hasattr(env, "data") else env
                    else:
                        data = agent.process_case(claimed_order_id) if hasattr(agent, "process_case") else {}
                    memory.set_fact("order_product_result", data)
                    plan.mark_step_completed(summary={"items_count": len(data.get("items", [])) if isinstance(data, dict) else 0})

                elif agent_name == "delivery_agent":
                    agent = self.agent_registry["delivery_agent"]
                    order_product_data = memory.get_fact("order_product_result", {})
                    if hasattr(agent, "run"):
                        env = agent.run(case_id, order_product_data)
                        data = env.data if hasattr(env, "data") else env
                    else:
                        data = order_product_data
                    memory.set_fact("delivery_result", data)
                    plan.mark_step_completed(summary={"delivery_variance": data.get("delivery_variance_hours") if isinstance(data, dict) else None})

                elif agent_name == "payment_agent":
                    agent = self.agent_registry["payment_agent"]
                    order_product_data = memory.get_fact("order_product_result", {})
                    if hasattr(agent, "run"):
                        env = agent.run(case_id, claimed_order_id, order_product_data)
                        data = env.data if hasattr(env, "data") else env
                    else:
                        data = order_product_data
                    memory.set_fact("payment_result", data)
                    plan.mark_step_completed(summary={"reconciled": data.get("reconciled") if isinstance(data, dict) else None})

                elif agent_name == "policy_agent":
                    agent = self.agent_registry["policy_agent"]
                    fact_bundle = FactBundle(
                        case_id=case_id,
                        customer_result=memory.get_fact("customer_result", {}),
                        order_product_result=memory.get_fact("order_product_result", {}),
                        payment_result=memory.get_fact("payment_result", {}),
                        delivery_result=memory.get_fact("delivery_result", {})
                    )
                    memory.set_fact("fact_bundle", fact_bundle)
                    if hasattr(agent, "run"):
                        env = agent.run(case_id, fact_bundle)
                        policy_data = env.data if hasattr(env, "data") else env
                    else:
                        policy_data = {}
                    memory.set_fact("policy_result", policy_data)
                    plan.mark_step_completed(summary={"primary_issue": policy_data.get("primary_issue") if isinstance(policy_data, dict) else None})

                elif agent_name == "verifier_agent":
                    agent = self.agent_registry["verifier_agent"]
                    policy_data = memory.get_fact("policy_result", {})
                    fact_bundle = memory.get_fact("fact_bundle")
                    fact_bundle_dict = fact_bundle.model_dump() if hasattr(fact_bundle, "model_dump") else {}

                    # Dựng Candidate bằng Assembler
                    candidate = self.assembler.assemble(
                        case_id=case_id,
                        fact_bundle=fact_bundle_dict,
                        policy_data=policy_data
                    )
                    memory.set_fact("candidate_output", candidate)

                    report: ValidationReport = agent.verify(case_id, candidate)
                    memory.set_fact("validation_report", report)

                    if report.status == "passed":
                        plan.mark_step_completed(summary={"verification": "passed"})
                        self.trace_sink.log_event(
                            case_id=case_id,
                            agent="coordinator_agent",
                            event="agent_completed",
                            status="success"
                        )
                        return candidate
                    else:
                        plan.mark_step_failed("Verification failed")
                        break

                # Ghi nhận log trace cho từng bước thực thi trong Plan
                self.trace_sink.log_event(
                    case_id=case_id,
                    agent=agent_name,
                    event="handoff_completed",
                    status="success",
                    input_from="coordinator_agent",
                    output_to="coordinator_agent",
                    duration_ms=int((time.time() - t0) * 1000),
                    retry=retry_count
                )

            # Nếu Verification không pass -> Tái lập Plan để Repair
            retry_count += 1
            if retry_count <= max_repairs:
                # Reset plan để chạy lại repair
                plan = self._build_initial_plan(input_case)
            else:
                candidate = memory.get_fact("candidate_output", {})
                self.trace_sink.log_event(
                    case_id=case_id,
                    agent="coordinator_agent",
                    event="agent_failed",
                    status="failed",
                    summary={"error": "Verification failed after retry limit"}
                )
                return candidate

        return memory.get_fact("candidate_output", {})
