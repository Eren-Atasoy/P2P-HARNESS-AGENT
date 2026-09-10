"""Faz 0 / Test 3 - otonom dongu fizibilite kosum takimi.

Bu P2P'nin cekirdegi DEGILDIR. Tek isi su donguyu insan mudahalesi olmadan
kapatip kapatamadigimizi olcmek:

    Claude plan -> Gemini implement -> gates -> Claude review -> Gemini fix

Olcer, varsaymaz: her adim artifact birakir ve kosu sonunda docs/11
maddelerine karsilik gelen bir rapor uretir.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE / "workspace"
RUNS = HERE / "runs"
PROMPTS = HERE / "prompts"
POLICY = HERE / "policy" / "implementer.yaml"

AGENT_TIMEOUT = 900   # 15 dk
GATE_TIMEOUT = 120
MAX_ATTEMPTS = 3


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Log:
    """Konsola ve olay gunlugune ayni anda yazar (docs/01 §5 provasi)."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.path = run_dir / "events.jsonl"
        self.seq = 0

    def __call__(self, kind: str, msg: str = "", **payload):
        self.seq += 1
        rec = {"seq": self.seq, "ts": now(), "type": kind, "payload": payload}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        icon = {"OK": "[ok]", "FAIL": "[!!]", "WARN": "[warn]", "STEP": "==>"}.get(kind, "   ")
        print(f"{icon} {msg or kind}", flush=True)


@dataclass
class Proc:
    ok: bool
    code: int
    out: str
    err: str
    secs: float
    timed_out: bool = False


def run_proc(cmd: list[str], cwd: Path, timeout: int, env: dict | None = None) -> Proc:
    """stdin kapali: onay istemi gelirse asilmaz, hemen duser (docs/04 §4)."""
    t0 = time.time()
    full_env = {**os.environ, **(env or {})}
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, stdin=subprocess.DEVNULL, env=full_env,
        )
        return Proc(p.returncode == 0, p.returncode, p.stdout or "", p.stderr or "", time.time() - t0)
    except subprocess.TimeoutExpired as e:
        return Proc(False, -1, (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
                    "TIMEOUT", time.time() - t0, timed_out=True)
    except FileNotFoundError as exc:
        return Proc(False, -2, "", f"NOT FOUND: {exc}", time.time() - t0)


@dataclass
class Findings:
    """docs/11 maddelerine karsilik gelen olcumler."""
    items: dict = field(default_factory=dict)

    def set(self, key: str, ok: bool | None, note: str = ""):
        self.items[key] = (ok, note)

    def render(self) -> str:
        order = ["V2", "V1", "ENV", "ADR-008", "PROMPT", "SCOPE", "C4", "LOOP", "V8"]
        labels = {
            "V2": "claude -p headless, yapilandirilmis cikti",
            "V1": "gemini -p worktree icinde dosya degistiriyor",
            "ADR-008": "dar kabuk politikasi uygulandi",
            "PROMPT": "onay istemi asilmadi",
            "SCOPE": "kapsam ihlali git ile yakalandi",
            "C4": "durum 3 kaynaktan turetildi",
            "LOOP": "onarim dongusu kapandi",
            "V8": "paralel oturum siniri",
            "ENV": "runtime kimlik dogrulamasi hazir",
        }
        lines = []
        for k in order:
            if k not in self.items:
                continue
            ok, note = self.items[k]
            mark = {True: "DOGRULANDI  ", False: "YANLIS CIKTI", None: "DOGRULANMADI"}[ok]
            lines.append(f"  {mark}  {k:<8} {labels.get(k,'')}" + (f"  -- {note}" if note else ""))
        return "\n".join(lines)


# --------------------------------------------------------------------------
# runtime adapterlari - docs/04 §4'un minik provasi
# --------------------------------------------------------------------------

# npm global dizini Windows'ta PATH'te olmayabilir; bilinen yerlere de bak.
EXTRA_BINS = [
    Path(os.environ.get("APPDATA", "")) / "npm",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "npm",
    Path.home() / ".local" / "bin",
    Path.home() / "AppData" / "Roaming" / "npm",
]


def resolve(name: str) -> str | None:
    hit = shutil.which(name)
    if hit:
        return hit
    for d in EXTRA_BINS:
        for ext in (".cmd", ".exe", ".bat", ""):
            c = d / (name + ext)
            if c.exists():
                return str(c)
    return None


def claude_run(prompt: str, cwd: Path, run_dir: Path, tag: str, extra: list[str] | None = None) -> Proc:
    exe = resolve("claude")
    cmd = [exe, "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits"]
    cmd += extra or []
    r = run_proc(cmd, cwd, AGENT_TIMEOUT)
    (run_dir / f"{tag}.stdout.txt").write_text(r.out, encoding="utf-8")
    (run_dir / f"{tag}.stderr.txt").write_text(r.err, encoding="utf-8")
    (run_dir / f"{tag}.prompt.txt").write_text(prompt, encoding="utf-8")
    return r


def gemini_run(prompt: str, cwd: Path, run_dir: Path, tag: str, use_policy: bool) -> tuple[Proc, bool]:
    """Once dar politikayla dener; policy reddedilirse politikasiz tekrarlar
    ve bunu raporlar (ADR-008 sessizce atlanmaz)."""
    exe = resolve("gemini")
    base = [exe, "-p", prompt, "--output-format", "json", "--approval-mode", "auto_edit"]
    policy_applied = False
    if use_policy and POLICY.exists():
        r = run_proc(base + ["--policy", str(POLICY)], cwd, AGENT_TIMEOUT)
        if r.code not in (2, -2) and "policy" not in (r.err or "").lower()[:400]:
            policy_applied = True
        else:
            (run_dir / f"{tag}.policy-rejected.txt").write_text(r.err[:4000], encoding="utf-8")
            r = run_proc(base, cwd, AGENT_TIMEOUT)
    else:
        r = run_proc(base, cwd, AGENT_TIMEOUT)
    (run_dir / f"{tag}.stdout.txt").write_text(r.out, encoding="utf-8")
    (run_dir / f"{tag}.stderr.txt").write_text(r.err, encoding="utf-8")
    (run_dir / f"{tag}.prompt.txt").write_text(prompt, encoding="utf-8")
    return r, policy_applied


APPROVAL_HINTS = ("waiting for approval", "requires approval", "confirm?", "y/n",
                  "permission denied by policy", "awaiting user")

# docs/03 §3: ENV sinifi fix dongusune GIRMEZ, dogrudan escalate olur.
ENV_HINTS = ("set an auth method", "not authenticated", "unauthenticated",
             "gemini_api_key", "please login", "credentials not found",
             "invalid api key", "command not found", "enoent")


def looks_like_env_error(r: Proc) -> bool:
    blob = (r.out + r.err).lower()
    return any(h in blob for h in ENV_HINTS)


def env_error_line(r: Proc) -> str:
    """Ham JSON/gurultu yerine gercek hata cumlesini cikar."""
    blob = (r.err or "") + chr(10) + (r.out or "")
    for raw in blob.replace(chr(92) + "n", chr(10)).splitlines():
        t = raw.strip().strip(chr(34) + chr(39) + ",")
        if t and any(h in t.lower() for h in ENV_HINTS):
            return t[:150]
    return "kimlik/ortam hatasi"


def looks_like_approval_hang(r: Proc) -> bool:
    blob = (r.out + r.err).lower()
    return r.timed_out and any(h in blob for h in APPROVAL_HINTS)


# --------------------------------------------------------------------------
# calisma alani ve kapilar
# --------------------------------------------------------------------------

def git(args: list[str], cwd: Path) -> Proc:
    return run_proc([resolve("git"), *args], cwd, 60)


def setup_workspace(log: Log) -> Path:
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    (WORKSPACE / "src").mkdir(parents=True)
    (WORKSPACE / "tests").mkdir(parents=True)
    (WORKSPACE / ".p2p").mkdir(parents=True)
    (WORKSPACE / "src" / "__init__.py").write_text("", encoding="utf-8")
    (WORKSPACE / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (WORKSPACE / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    git(["init", "-q"], WORKSPACE)
    git(["add", "-A"], WORKSPACE)
    git(["-c", "user.email=faz0@local", "-c", "user.name=faz0", "commit", "-q", "-m", "seed"], WORKSPACE)
    log("OK", f"calisma alani hazir: {WORKSPACE}")
    return WORKSPACE


def gate_unit(run_dir: Path, tag: str) -> tuple[bool, str]:
    r = run_proc([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"], WORKSPACE, GATE_TIMEOUT)
    blob = (r.out + "\n" + r.err).strip()
    (run_dir / f"{tag}.gate-unit.log").write_text(blob, encoding="utf-8")
    tail = "\n".join(blob.splitlines()[-25:])
    return r.ok, tail


def changed_files(cwd: Path) -> list[str]:
    r = git(["status", "--porcelain"], cwd)
    out = []
    for line in r.out.splitlines():
        if len(line) > 3:
            out.append(line[3:].strip().replace("\\", "/"))
    return sorted(out)


def scope_violation(changed: list[str], forbidden: list[str]) -> list[str]:
    bad = []
    for f in changed:
        for pat in forbidden:
            root = pat.replace("/**", "").replace("**", "").strip("/")
            if root and (f == root or f.startswith(root + "/")):
                bad.append(f)
                break
    return sorted(set(bad))


def load_json_file(p: Path) -> dict | None:
    if not p.exists():
        return None
    raw = p.read_text(encoding="utf-8", errors="replace").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.lower().startswith("json") else raw
    try:
        return json.loads(raw)
    except Exception:
        i, j = raw.find("{"), raw.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(raw[i:j + 1])
            except Exception:
                return None
    return None


def tmpl(name: str, **kw) -> str:
    s = (PROMPTS / name).read_text(encoding="utf-8")
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


# --------------------------------------------------------------------------
# fazlar
# --------------------------------------------------------------------------

def preflight(log: Log, f: Findings) -> bool:
    ok = True
    for tool in ("claude", "gemini", "git"):
        p = resolve(tool)
        if p:
            log("OK", f"{tool:<8} {p}")
        else:
            log("FAIL", f"{tool:<8} PATH'te bulunamadi")
            ok = False
    r = run_proc([sys.executable, "-m", "pytest", "--version"], HERE, 60)
    log("OK" if r.ok else "FAIL", f"pytest    {r.out.strip().splitlines()[0] if r.ok else 'YOK - pip install pytest'}")
    ok = ok and r.ok
    log("OK" if POLICY.exists() else "WARN", f"policy    {POLICY if POLICY.exists() else 'yok'}")

    # Kimlik dogrulamasi: en ucuz gercek cagri. Bunu burada yakalamazsak
    # hata PLAN asamasina kadar gizli kalir ve 3 deneme bosa gider.
    for tool, cmd in (("claude", [resolve("claude"), "-p", "ping", "--output-format", "json"]),
                      ("gemini", [resolve("gemini"), "-p", "ping", "--output-format", "json"])):
        if not cmd[0]:
            continue
        r = run_proc(cmd, HERE, 120)
        if looks_like_env_error(r):
            log("FAIL", f"{tool:<8} KIMLIK DOGRULAMASI YOK")
            log("WARN", f"  {env_error_line(r)}")
            if tool == "gemini":
                log("WARN", "  cozum: bir kez interaktif calistir -> `gemini` -> Login with Google")
            f.set("ENV", False, f"{tool}: kimlik dogrulamasi yok")
            ok = False
        elif r.timed_out:
            log("WARN", f"{tool:<8} yanit vermedi (120s) - kota veya ag olabilir")
        else:
            log("OK", f"{tool:<8} kimlik dogrulamasi calisiyor ({r.secs:.1f}s)")
    if ok and "ENV" not in f.items:
        f.set("ENV", True, "her iki runtime da yanit verdi")
    return ok


def phase_plan(log: Log, run_dir: Path, f: Findings) -> dict | None:
    log("STEP", "1/5  PLAN  (claude: testleri + task sozlesmesini yazar)")
    r = claude_run(tmpl("plan.md", WORKSPACE=WORKSPACE.as_posix()), WORKSPACE, run_dir, "1-plan",
                   extra=["--allowedTools", "Read", "Write", "Glob", "Grep"])
    if looks_like_approval_hang(r):
        f.set("PROMPT", False, "claude onay isteminde asildi")
    task_p = WORKSPACE / ".p2p" / "task.json"
    tests_p = WORKSPACE / "tests" / "test_duration.py"
    if not task_p.exists() or not tests_p.exists():
        log("FAIL", f"beklenen dosyalar yok (task.json={task_p.exists()} tests={tests_p.exists()})")
        f.set("V2", False, "yapilandirilmis cikti uretilmedi")
        return None
    task = load_json_file(task_p)
    if not task:
        log("FAIL", "task.json ayristirilamadi")
        f.set("V2", False, "gecersiz JSON")
        return None
    n_tests = tests_p.read_text(encoding="utf-8").count("def test_")
    log("OK", f"task={task.get('id')}  kriter={len(task.get('acceptance_criteria', []))}  test={n_tests}")
    f.set("V2", True, f"{n_tests} test + task.json")
    ok, tail = gate_unit(run_dir, "1-plan")
    if ok:
        log("FAIL", "testler bos implementasyonda GECTI - spesifikasyon degersiz")
        f.set("V2", False, "testler bos implementasyonda gecti")
        return None
    log("OK", "testler bos implementasyonda kirmizi (beklenen)")
    git(["add", "-A"], WORKSPACE)
    git(["-c", "user.email=faz0@local", "-c", "user.name=faz0", "commit", "-q", "-m", "spec"], WORKSPACE)
    return task


def phase_agent_work(log: Log, run_dir: Path, f: Findings, task: dict, prompt: str,
                     tag: str, use_policy: bool) -> tuple[bool, dict | None]:
    result_p = WORKSPACE / ".p2p" / f"{tag}-result.json"
    if result_p.exists():
        result_p.unlink()
    r, policy_applied = gemini_run(prompt, WORKSPACE, run_dir, tag, use_policy)
    if looks_like_env_error(r):
        f.set("ENV", False, env_error_line(r))
        log("FAIL", "ORTAM HATASI -> fix dongusune girmez, dogrudan escalate (docs/03 §3)")
        return False, None
    if use_policy:
        # cagri basarisizsa politikanin uygulandigini iddia edemeyiz
        f.set("ADR-008", policy_applied if r.ok else None,
              "" if (policy_applied and r.ok) else "cagri basarisiz - politika dogrulanamadi")
    if looks_like_approval_hang(r):
        f.set("PROMPT", False, "gemini onay isteminde asildi")
        log("FAIL", "onay isteminde asildi")
        return False, None
    if r.timed_out:
        log("FAIL", f"zaman asimi ({AGENT_TIMEOUT}s)")
        return False, None
    changed = changed_files(WORKSPACE)
    bad = scope_violation(changed, task.get("forbidden_paths", []))
    if bad:
        log("FAIL", f"KAPSAM IHLALI: {bad}")
        f.set("SCOPE", True, f"yakalandi: {bad}")
        git(["checkout", "--", *bad], WORKSPACE)
        return False, None
    f.set("SCOPE", True, "ihlal yok")
    res = load_json_file(result_p)
    f.set("C4", True, "result.json var" if res else "result.json yok/bozuk - git+kapidan turetildi")
    log("OK" if res else "WARN",
        f"degisen={changed}  result.json={'var' if res else 'YOK (C4: git+kapidan turetiliyor)'}")
    return True, res


def phase_review(log: Log, run_dir: Path, f: Findings, task: dict, gate_tail: str, attempt: int) -> dict | None:
    log("STEP", f"4/5  REVIEW  (claude: mimari + dogruluk incelemesi, tur {attempt})")
    result_p = WORKSPACE / ".p2p" / f"review-{attempt}.json"
    impl = (WORKSPACE / "src" / "duration.py").read_text(encoding="utf-8", errors="replace")
    tests = (WORKSPACE / "tests" / "test_duration.py").read_text(encoding="utf-8", errors="replace")
    prompt = tmpl("review.md", TASK_JSON=json.dumps(task, ensure_ascii=False, indent=2),
                  IMPL=impl, TESTS=tests, GATE="PASS\n" + gate_tail,
                  RESULT=result_p.as_posix())
    r = claude_run(prompt, WORKSPACE, run_dir, f"4-review-{attempt}",
                   extra=["--allowedTools", "Read", "Write", "Glob", "Grep"])
    if looks_like_approval_hang(r):
        f.set("PROMPT", False, "claude review onay isteminde asildi")
    rev = load_json_file(result_p)
    if not rev:
        log("WARN", "inceleme JSON'u okunamadi - APPROVED sayilmiyor")
        return None
    sev = [x.get("severity", "").upper() for x in rev.get("findings", [])]
    verdict = "REJECTED" if "CRITICAL" in sev else ("CHANGES_REQUESTED" if "HIGH" in sev else "APPROVED")
    if verdict != rev.get("verdict"):
        log("WARN", f"model verdict={rev.get('verdict')} -> orchestrator yeniden hesapladi: {verdict}")
    rev["verdict"] = verdict
    log("OK", f"verdict={verdict}  bulgu={len(sev)} {sev}")
    return rev


def inject_fault(log: Log) -> bool:
    p = WORKSPACE / "src" / "duration.py"
    src = p.read_text(encoding="utf-8")
    for a, b in (("3600", "3000"), ("86400", "8640"), ("60", "61")):
        if a in src:
            p.write_text(src.replace(a, b, 1), encoding="utf-8")
            log("WARN", f"HATA ENJEKTE EDILDI: {a} -> {b} (onarim dongusu zorlaniyor)")
            return True
    log("WARN", "enjekte edilecek sabit bulunamadi")
    return False


def probe_concurrency(log: Log, run_dir: Path, f: Findings, n: int):
    log("STEP", f"V8  {n} es zamanli gemini oturumu deneniyor")
    exe = resolve("gemini")
    procs = [subprocess.Popen([exe, "-p", f"Reply with exactly: PONG{i}", "--output-format", "json"],
                              cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
             for i in range(n)]
    ok = 0
    for i, p in enumerate(procs):
        try:
            out, err = p.communicate(timeout=180)
            (run_dir / f"v8-{i}.txt").write_text((out or "") + "\n---\n" + (err or ""), encoding="utf-8")
            if p.returncode == 0:
                ok += 1
        except subprocess.TimeoutExpired:
            p.kill()
    f.set("V8", ok == n, f"{ok}/{n} oturum basarili")
    log("OK" if ok == n else "WARN", f"{ok}/{n} es zamanli oturum basarili")


def main() -> int:
    ap = argparse.ArgumentParser(description="Faz 0 Test 3 - otonom dongu fizibilitesi")
    ap.add_argument("--preflight", action="store_true", help="model cagirmadan ortami dogrula")
    ap.add_argument("--inject-fault", action="store_true", help="ilk yesilden sonra hata enjekte et")
    ap.add_argument("--concurrency", type=int, default=0, help="V8: n es zamanli oturum dene")
    ap.add_argument("--no-policy", action="store_true", help="dar kabuk politikasini gecirme")
    a = ap.parse_args()

    RUNS.mkdir(exist_ok=True)
    run_dir = RUNS / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir()
    log, f = Log(run_dir), Findings()
    print(f"\nFAZ 0 / TEST 3 - otonom dongu\nartifact: {run_dir}\n" + "-" * 66)

    log("STEP", "0/5  PREFLIGHT")
    if not preflight(log, f):
        log("FAIL", "ortam eksik - durduruldu")
        return 2
    if a.preflight:
        print("\npreflight tamam. tam dongu icin --preflight'siz calistir.")
        return 0
    if a.concurrency:
        probe_concurrency(log, run_dir, f, a.concurrency)

    setup_workspace(log)
    task = phase_plan(log, run_dir, f)
    if not task:
        print("\n" + "=" * 66 + "\nSONUC: PLAN asamasinda kaldi\n" + f.render())
        return 1

    log("STEP", "2/5  IMPLEMENT  (gemini: src/ yazar, tests/ yasak)")
    prompt = tmpl("implement.md", TASK_JSON=json.dumps(task, ensure_ascii=False, indent=2),
                  WORKSPACE=WORKSPACE.as_posix(), ALLOWED=task.get("allowed_paths"),
                  FORBIDDEN=task.get("forbidden_paths"),
                  RESULT=(WORKSPACE / ".p2p" / "impl-result.json").as_posix())
    ok, _ = phase_agent_work(log, run_dir, f, task, prompt, "2-implement", not a.no_policy)
    if not ok:
        print("\n" + "=" * 66 + "\nSONUC: IMPLEMENT asamasinda kaldi\n" + f.render())
        return 1
    created = (WORKSPACE / "src" / "duration.py").exists()
    f.set("V1", created, "src/duration.py olusturuldu" if created else "hicbir dosya olusturulmadi")

    attempt, faulted, verdict = 1, False, None
    max_attempts = int(task.get("max_attempts", MAX_ATTEMPTS))
    while attempt <= max_attempts:
        log("STEP", f"3/5  VERIFY  (deterministik kapi, tur {attempt})")
        gate_ok, tail = gate_unit(run_dir, f"3-verify-{attempt}")
        log("OK" if gate_ok else "FAIL", f"unit kapisi: {'PASS' if gate_ok else 'FAIL'}")

        if not gate_ok:
            if attempt >= max_attempts:
                log("FAIL", "max deneme asildi -> ESCALATED")
                break
            attempt += 1
            log("STEP", f"5/5  FIX  (gemini, kapi hatasi, tur {attempt}/{max_attempts})")
            fp = tmpl("fix.md", TASK_JSON=json.dumps(task, ensure_ascii=False, indent=2),
                      FAILURES=tail, WORKSPACE=WORKSPACE.as_posix(),
                      ATTEMPT=attempt, MAX=max_attempts,
                      RESULT=(WORKSPACE / ".p2p" / f"fix-{attempt}-result.json").as_posix())
            ok, _ = phase_agent_work(log, run_dir, f, task, fp, f"5-fix-{attempt}", not a.no_policy)
            if not ok:
                break
            continue

        if a.inject_fault and not faulted:
            faulted = inject_fault(log)
            if faulted:
                attempt += 1
                continue

        rev = phase_review(log, run_dir, f, task, tail, attempt)
        verdict = rev.get("verdict") if rev else None
        if verdict == "APPROVED":
            break
        if attempt >= max_attempts or not rev:
            log("FAIL", "inceleme gecmedi / max deneme -> ESCALATED")
            break
        attempt += 1
        log("STEP", f"5/5  FIX  (gemini, inceleme bulgulari, tur {attempt})")
        fp = tmpl("fix.md", TASK_JSON=json.dumps(task, ensure_ascii=False, indent=2),
                  FAILURES=json.dumps(rev.get("findings", []), ensure_ascii=False, indent=2),
                  WORKSPACE=WORKSPACE.as_posix(), ATTEMPT=attempt, MAX=max_attempts,
                  RESULT=(WORKSPACE / ".p2p" / f"fix-{attempt}-result.json").as_posix())
        ok, _ = phase_agent_work(log, run_dir, f, task, fp, f"5-fix-{attempt}", not a.no_policy)
        if not ok:
            break

    gate_ok, _ = gate_unit(run_dir, "final")
    closed = bool(gate_ok and verdict == "APPROVED")
    f.set("LOOP", closed, f"{attempt} tur, verdict={verdict}, kapi={'PASS' if gate_ok else 'FAIL'}")
    if "PROMPT" not in f.items:
        f.set("PROMPT", True, "hicbir adimda onay istemi asilmadi")

    print("\n" + "=" * 66)
    print("SONUC: " + ("DONGU KAPANDI - Faz 0 Test 3 GECTI" if closed else "DONGU KAPANMADI"))
    print("=" * 66)
    print(f.render())
    print(f"\nartifact: {run_dir}\ncalisma alani: {WORKSPACE}")
    (run_dir / "findings.json").write_text(
        json.dumps({k: {"ok": v[0], "note": v[1]} for k, v in f.items.items()},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if closed else 1


if __name__ == "__main__":
    sys.exit(main())
