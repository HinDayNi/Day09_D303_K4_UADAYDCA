import time
from typing import Any, Dict, Optional

from src.schemas.task import InputCase
from src.schemas.handoff import HandoffEnvelope, FactBundle, ValidationReport
from src.trace import TraceSink
from src.assembler import ResultAssembler

from src.agents.customer import CustomerAgent
from src.agents.order_product import OrderProductAgent
from src.agents.delivery import DeliveryAgent
from src.agents.payment import PaymentAgent
from src.agents.policy import PolicyAgent
from src.agents.verifier import VerifierAgent

class CoordinatorAgent:
    """
    Coordinator Agent - Trưởng nhóm / Điều phối hệ thống (Người 1).
    Chịu trách nhiệm quản lý luồng handoff, chạy theo graph DAG, xử lý lỗi/retry và thu thập trace.
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
        self.repo = repo
        self.trace_sink = trace_sink or TraceSink()
        self.assembler = ResultAssembler()

        # Khởi tạo các Agent chuyên biệt (sẽ dùng stub nếu chưa được tiêm dependency)
        self.customer_agent = customer_agent or CustomerAgent(repo=self.repo)
        self.order_product_agent = order_product_agent or OrderProductAgent(repo=self.repo)
        self.delivery_agent = delivery_agent or DeliveryAgent(repo=self.repo)
        self.payment_agent = payment_agent or PaymentAgent(repo=self.repo)
        self.policy_agent = policy_agent or PolicyAgent(repo=self.repo)
        self.verifier_agent = verifier_agent or VerifierAgent(repo=self.repo)

    def process_case(self, input_case: InputCase) -> Dict[str, Any]:
        case_id = input_case.case_id
        claimed_order_id = input_case.claimed_order_id
        
        self.trace_sink.log_event(
            case_id=case_id,
            agent="coordinator_agent",
            event="agent_started",
            status="success",
            summary={"claimed_order_id": claimed_order_id}
        )

        retry_count = 0
        max_repairs = 1

        while retry_count <= max_repairs:
            # 1. Phase 1: Customer Agent + Order & Product Agent
            t0 = time.time()
            customer_env = self.customer_agent.run(case_id, claimed_order_id)
            self.trace_sink.log_event(
                case_id=case_id,
                agent="customer_agent",
                event="handoff_completed",
                status=customer_env.status,
                input_from="coordinator_agent",
                output_to="coordinator_agent",
                duration_ms=int((time.time() - t0) * 1000),
                retry=retry_count
            )

            t0 = time.time()
            order_product_env = self.order_product_agent.run(case_id, claimed_order_id)
            self.trace_sink.log_event(
                case_id=case_id,
                agent="order_product_agent",
                event="handoff_completed",
                status=order_product_env.status,
                input_from="coordinator_agent",
                output_to="coordinator_agent",
                duration_ms=int((time.time() - t0) * 1000),
                retry=retry_count
            )

            # 2. Phase 2: Delivery Agent + Payment Agent
            t0 = time.time()
            delivery_env = self.delivery_agent.run(case_id, order_product_env.data)
            self.trace_sink.log_event(
                case_id=case_id,
                agent="delivery_agent",
                event="handoff_completed",
                status=delivery_env.status,
                input_from="order_product_agent",
                output_to="coordinator_agent",
                duration_ms=int((time.time() - t0) * 1000),
                retry=retry_count
            )

            t0 = time.time()
            payment_env = self.payment_agent.run(case_id, claimed_order_id, order_product_env.data)
            self.trace_sink.log_event(
                case_id=case_id,
                agent="payment_agent",
                event="handoff_completed",
                status=payment_env.status,
                input_from="order_product_agent",
                output_to="coordinator_agent",
                duration_ms=int((time.time() - t0) * 1000),
                retry=retry_count
            )

            # 3. Phase 3: Gom FactBundle & gọi Policy Agent
            fact_bundle = FactBundle(
                case_id=case_id,
                customer_result=customer_env.data,
                order_product_result=order_product_env.data,
                payment_result=payment_env.data,
                delivery_result=delivery_env.data
            )

            t0 = time.time()
            policy_env = self.policy_agent.run(case_id, fact_bundle)
            self.trace_sink.log_event(
                case_id=case_id,
                agent="policy_agent",
                event="handoff_completed",
                status=policy_env.status,
                input_from="coordinator_agent",
                output_to="assembler",
                duration_ms=int((time.time() - t0) * 1000),
                retry=retry_count
            )

            # 4. Phase 4: Assembler & Verifier Agent
            candidate = self.assembler.assemble(
                case_id=case_id,
                fact_bundle=fact_bundle.model_dump(),
                policy_data=policy_env.data
            )

            t0 = time.time()
            report: ValidationReport = self.verifier_agent.verify(case_id, candidate)
            self.trace_sink.log_event(
                case_id=case_id,
                agent="verifier_agent",
                event="handoff_completed",
                status="success" if report.status == "passed" else "failed",
                input_from="assembler",
                output_to="coordinator_agent",
                duration_ms=int((time.time() - t0) * 1000),
                retry=retry_count,
                summary={"report_status": report.status, "errors_count": len(report.errors)}
            )

            if report.status == "passed":
                self.trace_sink.log_event(
                    case_id=case_id,
                    agent="coordinator_agent",
                    event="agent_completed",
                    status="success"
                )
                return candidate

            # Nếu verification failed và chưa vượt quá max_repairs -> Retry repair
            retry_count += 1
            if retry_count > max_repairs:
                self.trace_sink.log_event(
                    case_id=case_id,
                    agent="coordinator_agent",
                    event="agent_failed",
                    status="failed",
                    summary={"error": "Verification failed after maximum repairs"}
                )
                # Vẫn trả về candidate để tránh crash batch nhưng log error
                return candidate

        return candidate
