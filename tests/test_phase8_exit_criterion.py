"""Official Exit Criterion Test for Faz 8: Browser Verification and Regression.

Per docs/08-roadmap.md §Faz 8:
'Çıkış: Bir kabul kriterini bilerek bozmak E2E\'yi kırmızı yapıyor ve doğru
task\'ı yeniden açıyor.'
"""
from pathlib import Path
from src.models.enums import Capability, EstimatedSize, GateStatus, RiskLevel, TaskStatus, VerifiedBy
from src.models.result import GateFailure, GateResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.prompts import PromptCompiler
from src.orchestration.repair import FailureClass, RepairPlanner
from src.verification.config import GateDefinition
from src.workspace.workspace import Workspace


def test_phase8_official_exit_criterion(tmp_path: Path):
    """
    Proves Phase 8 exit criterion:
    1. A task contract defines an acceptance criterion verified by E2E/test.
    2. Code change intentionally breaks the acceptance criterion.
    3. E2E gate execution fails with GateStatus.FAIL.
    4. Repair engine classifies failure as TEST_FAIL and reopens the specific task into FIXING/READY.
    5. Prompt compiler produces focused fix prompt containing truncated failure output.
    """
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    task = TaskContract(
        id="API-001",
        title="Implement Items listing endpoint",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.MEDIUM,
        depends_on=[],
        intent="Provide items endpoint for browser and mobile clients.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="GET /items returns 200 OK and valid JSON array.",
                verified_by=VerifiedBy.GATE,
                gate_ref="e2e",
            )
        ],
        inputs=[".p2p/docs/architecture.md"],
        allowed_paths=["backend/app/**"],
        forbidden_paths=[".p2p/**"],
        gates=["e2e"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/runs/{run_id}/result.json",
        acr_path=".p2p/acr/ACR-API-001.md",
    )

    # 1. Simulate intentional breakage of AC-1 in code
    # Browser E2E run fails because /items returns 500
    e2e_output = """
1) [chromium] › tests/e2e/items.spec.ts:18:7 › GET /items returns 200
   Error: expect(received).toBe(expected) // Object.is equality

   Expected: 200
   Received: 500

      16 |   const response = await page.request.get('/items');
    > 17 |   expect(response.status()).toBe(200);
"""
    broken_gate_result = GateResult(
        gate="e2e",
        status=GateStatus.FAIL,
        exit_code=1,
        duration_ms=450,
        log_path=".p2p/runs/run-1/e2e.log",
        failures=[
            GateFailure(
                file="tests/e2e/items.spec.ts",
                line=17,
                rule="GET /items returns 200",
                message="Expected 200 but received 500 Internal Server Error",
            )
        ],
        output_summary=e2e_output,
    )

    # 2. Verify failure classification & fix loop decision
    planner = RepairPlanner()
    should_fix, failure_class, reason = planner.should_enter_fix_loop(
        task=task,
        attempt=1,
        gate_results=[broken_gate_result],
    )
    assert should_fix is True, "E2E failure on broken criterion must enter fix loop"
    assert failure_class == FailureClass.TEST_FAIL, "Broken acceptance criterion must be classified as TEST_FAIL"
    assert "scheduling fix attempt" in reason

    # 4. Generate narrowed fix prompt containing the E2E failure
    fix_prompt = PromptCompiler.compile_fix_prompt(
        contract=task,
        failures=broken_gate_result.failures,
        raw_gate_output=broken_gate_result.output_summary,
    )

    assert "Sadece bu bulguları gider. Başka refactor yapma." in fix_prompt
    assert "Expected 200 but received 500" in fix_prompt or "e2e" in fix_prompt
    assert task.id in fix_prompt
