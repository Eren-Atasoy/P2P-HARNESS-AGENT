You are the Planning Architect for a feasibility test. Produce an executable
specification: a task contract plus the test file that will judge it.

Goal: implement a duration string parser.

Write EXACTLY two files, nothing else:

1. `{WORKSPACE}/tests/test_duration.py`

   pytest tests for a function `parse_duration(text: str) -> int` importable as
   `from src.duration import parse_duration`. It returns the total number of
   SECONDS.

   Cover at minimum:
   - "90s" -> 90, "5m" -> 300, "2h" -> 7200, "1d" -> 86400
   - compound: "1h30m" -> 5400, "2d4h" -> 187200
   - whitespace tolerated: " 5m " -> 300
   - invalid input raises ValueError: "", "abc", "5x", "-3m", "m5", "5"
   - integer overflow is not a concern; do not test it

   Each test function name must be descriptive. No test may pass against an
   empty implementation — verify this by reading your own assertions.

2. `{WORKSPACE}/.p2p/task.json`

   ```json
   {
     "id": "DUR-001",
     "title": "...",
     "capabilities": ["backend"],
     "risk": "low",
     "intent": "2-3 sentences: what and why, no implementation detail",
     "acceptance_criteria": [
       {"id":"AC-1","statement":"observable behaviour","verified_by":"test",
        "test_ref":"tests/test_duration.py::<exact test name>"}
     ],
     "allowed_paths": ["src/**"],
     "forbidden_paths": ["tests/**", ".p2p/**"],
     "gates": ["unit"],
     "max_attempts": 3
   }
   ```

   Every acceptance criterion must reference a test function you actually
   wrote, by its exact name. A criterion without a real `test_ref` is a defect.

Do not create `src/duration.py`. The implementer writes it.
Do not write anything outside the two files above.
