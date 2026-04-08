"""Structural checks for the settings modal (static/js/components/settings.js)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_JS = ROOT / "static" / "js" / "components" / "settings.js"


@pytest.fixture(scope="module")
def settings_js() -> str:
    return SETTINGS_JS.read_text(encoding="utf-8")


def test_settings_js_exists() -> None:
    assert SETTINGS_JS.is_file(), "static/js/components/settings.js must exist"


def test_settings_js_imports_api(settings_js: str) -> None:
    assert "export " in settings_js
    assert 'from "../api.js"' in settings_js or "from '../api.js'" in settings_js
    assert "getSettings" in settings_js
    assert "updateSettings" in settings_js
    assert "resetSettings" in settings_js
    assert "testLlm" in settings_js


def test_settings_js_exports_init(settings_js: str) -> None:
    assert "initSettings" in settings_js


def test_settings_js_dialog_and_form_ids(settings_js: str) -> None:
    assert "settings-dialog" in settings_js
    assert "settings-form" in settings_js


def test_settings_js_llm_fields(settings_js: str) -> None:
    assert "llm_mode" in settings_js


def test_settings_js_llm_group_visibility_toggle(settings_js: str) -> None:
    """B06: Mode select shows one LLM group and hides the other (display via CSS class)."""
    assert "settings-llm-group-ollama" in settings_js
    assert "settings-llm-group-cloud" in settings_js
    assert "applyLlmModeVisibility" in settings_js
    assert "change" in settings_js


def test_settings_js_tab_panel_activation(settings_js: str) -> None:
    """B07: Tab buttons switch settings panels; LLM tab default on open."""
    assert "settings-panel-llm" in settings_js
    assert "settings-panel-embeddings" in settings_js
    assert "activateSettingsTab" in settings_js


def test_settings_js_cloud_security_warning_id(settings_js: str) -> None:
    """B08: LLM visibility sync updates the cloud storage warning element."""
    assert "settings-cloud-security-warning" in settings_js


def test_settings_js_save_flow(settings_js: str) -> None:
    lower = settings_js.lower()
    assert "submit" in lower or "save" in lower


def test_settings_js_feedback_or_status(settings_js: str) -> None:
    assert "settings-feedback" in settings_js or "feedback" in settings_js.lower()
