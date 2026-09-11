"""Phase 4 exit criterion test per docs/08-roadmap.md:

"Çıkış: Bilerek bozulmuş örnek projede her kapı doğru sınıfla düşüyor;
Failure[] yapılandırılmış üretiliyor; iki paralel task'ın smoke kapısı
birbirini bozmuyor."
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import time

from src.models.enums import GateStatus
from src.verification.config import GateDefinition, GatesConfig
from src.verification.runner import GateRunner
from src.workspace.workspace import Workspace


def test_phase4_exit_criterion(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    # 1. Bilerek bozulmuş projede kapı tanımları:
    # - unit: Kod hatasıyla patlar -> FAIL verir, Failure[] üretir
    # - typecheck: Tip hatasıyla patlar -> FAIL verir, Failure[] üretir
    # - broken_infra: Olmayan binary çağırır -> ERROR verir (altyapı sorunu)
    # - smoke: isolation="serialized" olan kapı

    synthetic_pytest = (
        "import sys\n"
        "sys.stdout.write('FAILED tests/api/test_users.py::test_create_user:25 - AssertionError: Expected 201\\n')\n"
        "sys.exit(1)\n"
    )

    synthetic_tsc = (
        "import sys\n"
        "sys.stdout.write('src/models/user.ts:18:5 - error TS2322: Type number is not assignable to string.\\n')\n"
        "sys.exit(1)\n"
    )

    # Smoke test simulates container startup taking 0.2 seconds and asserting lock exclusivity
    synthetic_smoke = (
        "import time, sys\n"
        "time.sleep(0.15)\n"
        "sys.stdout.write('Container health check PASS\\n')\n"
        "sys.exit(0)\n"
    )

    config = GatesConfig(
        gates={
            "unit": GateDefinition(
                cmd=[sys.executable, "-c", synthetic_pytest],
                cwd=".",
                timeout_s=30,
                parse="pytest",
            ),
            "typecheck": GateDefinition(
                cmd=[sys.executable, "-c", synthetic_tsc],
                cwd=".",
                timeout_s=30,
                parse="tsc",
            ),
            "broken_infra": GateDefinition(
                cmd=["non_existent_docker_cli_tool_xyz"],
                cwd=".",
                timeout_s=30,
                on_missing_tool=GateStatus.ERROR,
                parse="none",
            ),
            "smoke": GateDefinition(
                cmd=[sys.executable, "-c", synthetic_smoke],
                cwd=".",
                timeout_s=30,
                isolation="serialized",
                parse="none",
            ),
        }
    )

    runner = GateRunner(ws, config)

    # Doğrulama 1 & 2: Her kapı doğru sınıfla düşüyor ve Failure[] yapılandırılmış üretiliyor
    unit_res = runner.run_gate("unit", run_id="run-broken")
    assert unit_res.status == GateStatus.FAIL
    assert len(unit_res.failures) == 1
    assert unit_res.failures[0].file == "tests/api/test_users.py"
    assert unit_res.failures[0].line == 25
    assert unit_res.failures[0].rule == "test_create_user"
    assert "Expected 201" in unit_res.failures[0].message

    typecheck_res = runner.run_gate("typecheck", run_id="run-broken")
    assert typecheck_res.status == GateStatus.FAIL
    assert len(typecheck_res.failures) == 1
    assert typecheck_res.failures[0].file == "src/models/user.ts"
    assert typecheck_res.failures[0].line == 18
    assert typecheck_res.failures[0].rule == "TS2322"

    infra_res = runner.run_gate("broken_infra", run_id="run-broken")
    assert infra_res.status == GateStatus.ERROR
    assert any("not found" in f.message for f in infra_res.failures)

    # Doğrulama 3: İki paralel task'ın smoke kapısı birbirini bozmuyor (serialized isolation)
    # İki thread aynı anda smoke kapısını çağırır
    smoke_results = []
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(runner.run_gate, "smoke", None, "run-task1")
        f2 = executor.submit(runner.run_gate, "smoke", None, "run-task2")
        smoke_results = [f1.result(), f2.result()]

    total_time = time.perf_counter() - start_time

    # İkisi de başarılı bitmeli
    for sr in smoke_results:
        assert sr.status == GateStatus.PASS
        assert sr.exit_code == 0

    # Her smoke 0.15s sürdüğü için, serialized çalıştıklarında toplam süre >= 0.25s olmalıdır
    assert total_time >= 0.25, f"Expected serialized execution taking >= 0.25s, but took {total_time:.3f}s"
