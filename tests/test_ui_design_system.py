"""Design system contract verification tests (docs/12 §1 - §2)."""
import re
from pathlib import Path


def test_design_system_tokens_contract():
    css_file = Path(__file__).resolve().parent.parent / "src" / "ui" / "static" / "style.css"
    assert css_file.exists(), "style.css must exist in static assets"

    css_text = css_file.read_text(encoding="utf-8")

    # 1. Surface and background tokens
    assert "--bg-base:" in css_text
    assert "--bg-surface:" in css_text
    assert "--bg-raised:" in css_text
    assert "--bg-inset:" in css_text

    # 2. Text tokens
    assert "--text-primary:" in css_text
    assert "--text-secondary:" in css_text
    assert "--text-tertiary:" in css_text

    # 3. Brand accent (Electric Indigo)
    assert "--accent-brand:" in css_text
    assert "252" in css_text  # Hue 252 for Electric Indigo

    # 4. Status color tokens
    assert "--status-success:" in css_text
    assert "--status-warning:" in css_text
    assert "--status-danger:" in css_text
    assert "--status-gated:" in css_text
    assert "--status-running:" in css_text

    # 5. Typography tokens (Geist and Geist Mono)
    assert "Geist" in css_text
    assert "Geist Mono" in css_text
    assert "tabular-nums" in css_text

    # 6. Light and Dark Theme definitions
    assert '[data-theme="light"]' in css_text


def test_strict_forbidden_patterns_not_present():
    html_file = Path(__file__).resolve().parent.parent / "src" / "ui" / "static" / "index.html"
    css_file = Path(__file__).resolve().parent.parent / "src" / "ui" / "static" / "style.css"
    js_file = Path(__file__).resolve().parent.parent / "src" / "ui" / "static" / "app.js"

    html_content = html_file.read_text(encoding="utf-8")
    css_content = css_file.read_text(encoding="utf-8")
    js_content = js_file.read_text(encoding="utf-8")

    # Forbidden 1: Gradient text
    assert "-webkit-background-clip: text" not in css_content
    assert "background-clip: text" not in css_content

    # Forbidden 2: Kicker / Eyebrow class
    assert "kicker" not in html_content.lower()
    assert "eyebrow" not in html_content.lower()

    # Forbidden 3: No emoji as icons (HTML should use inline SVGs)
    emoji_regex = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    assert not emoji_regex.search(html_content), "Raw emoji icons forbidden; SVG icons required (docs/12 §1.7)"

    # Signature Tag: decided_by=default is prominently rendered
    assert "decided_by=default" in js_content
