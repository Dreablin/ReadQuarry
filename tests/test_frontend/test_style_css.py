"""Checks that the ReadQuarry design system CSS exists and meets PRD F-UI-02 hooks."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STYLE = ROOT / "static" / "css" / "style.css"


@pytest.fixture(scope="module")
def style_css() -> str:
    return STYLE.read_text(encoding="utf-8")


def test_style_css_exists() -> None:
    assert STYLE.is_file(), "static/css/style.css must exist"


def test_style_css_uses_custom_properties(style_css: str) -> None:
    assert ":root" in style_css
    assert "--color-bg" in style_css or "--rq-" in style_css
    assert "--" in style_css


def test_style_css_dark_theme_base(style_css: str) -> None:
    lower = style_css.lower()
    assert "background" in lower and ("#0" in style_css or "rgb" in lower or "hsl" in lower)


def test_style_css_glassmorphism(style_css: str) -> None:
    lower = style_css.lower()
    assert "backdrop-filter" in lower or "-webkit-backdrop-filter" in lower
    assert "rgba(" in style_css or "rgb(" in style_css


def test_style_css_gradient_accents(style_css: str) -> None:
    assert "linear-gradient" in style_css.lower() or "radial-gradient" in style_css.lower()


def test_style_css_google_font(style_css: str) -> None:
    assert "fonts.googleapis.com" in style_css or "font-family" in style_css.lower()


def test_style_css_animations(style_css: str) -> None:
    assert "@keyframes" in style_css.lower()


def test_style_css_no_idle_header_shimmer_gpu_loop(style_css: str) -> None:
    """B04: infinite filter-based header animation forces continuous GPU work when idle."""
    assert "header-shimmer" not in style_css


def test_style_css_responsive_stack(style_css: str) -> None:
    assert "@media" in style_css.lower()
    assert "max-width" in style_css.lower()


def test_style_css_settings_llm_group_hidden(style_css: str) -> None:
    """B06: Hidden LLM group uses display:none (CSS class, not DOM removal)."""
    assert "settings-llm-group--hidden" in style_css


def test_style_css_settings_tab_panels(style_css: str) -> None:
    """B07: Inactive settings tab panel is hidden via CSS."""
    assert "settings-tab-panel--hidden" in style_css
    assert "settings-tabs" in style_css


def test_style_css_covers_shell_layout_classes(style_css: str) -> None:
    for cls in (
        ".app-header",
        ".app-main",
        ".panel",
        ".chat-messages",
        ".chat-form",
        ".status-bar",
        ".dialog",
        ".upload-dropzone",
        ".sr-only",
    ):
        assert cls in style_css, f"Expected {cls} in style.css"


def test_style_css_button_and_panel_hover_or_transitions(style_css: str) -> None:
    lower = style_css.lower()
    assert "transition" in lower or "animation" in lower
