"""Unit tests for A11yScanner and A11yParser quality gate."""
from pathlib import Path
from src.verification.a11y import A11yParser, A11yScanner


def test_a11y_scanner_catches_violations():
    scanner = A11yScanner()

    bad_html = """<!DOCTYPE html>
<html>
<body>
    <h1>Title 1</h1>
    <h1>Title 2</h1>
    <img src="avatar.png">
    <button></button>
    <a href="/home"></a>
    <input type="text">
</body>
</html>"""

    failures = scanner.scan_content(bad_html)
    assert len(failures) >= 5

    rules = [f.rule for f in failures]
    assert "A11Y_IMG_NO_ALT" in rules
    assert "A11Y_BUTTON_NO_LABEL" in rules
    assert "A11Y_INPUT_NO_LABEL" in rules
    assert "A11Y_EMPTY_LINK" in rules
    assert "A11Y_MULTIPLE_H1" in rules


def test_a11y_scanner_clean_html():
    scanner = A11yScanner()

    clean_html = """<!DOCTYPE html>
<html>
<body>
    <h1>Single Accessible Title</h1>
    <img src="avatar.png" alt="User profile avatar">
    <button aria-label="Submit form">Submit</button>
    <a href="/home" aria-label="Home page">Home</a>
    <input type="text" id="username" aria-label="Username">
</body>
</html>"""

    failures = scanner.scan_content(clean_html)
    assert len(failures) == 0


def test_a11y_parser_output():
    parser = A11yParser()

    cli_output = """Error: [WCAG2AA.Principle1.Guideline1_1.1_1_1.H37] Img element missing an alt attribute. at src/index.html:15
Violation: Button lacks accessible name at src/nav.html:22
"""

    parsed = parser.parse(cli_output, "", exit_code=1)
    assert len(parsed) == 2
    assert parsed[0].file == "src/index.html"
    assert parsed[0].line == 15
    assert "alt" in parsed[0].message
