"""Structural checks for the ReadQuarry HTML shell (static/index.html)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "static" / "index.html"


@pytest.fixture(scope="module")
def index_html() -> str:
    return INDEX.read_text(encoding="utf-8")


def test_index_html_exists() -> None:
    assert INDEX.is_file(), "static/index.html must exist"


def test_index_html_has_doctype_and_lang(index_html: str) -> None:
    assert index_html.lstrip().upper().startswith("<!DOCTYPE HTML")
    assert '<html lang="en"' in index_html


def test_index_html_has_meta_viewport_and_title(index_html: str) -> None:
    assert 'charset="utf-8"' in index_html or "charset=utf-8" in index_html
    assert "viewport" in index_html
    assert "<title>" in index_html and "ReadQuarry" in index_html


def test_index_html_links_stylesheet(index_html: str) -> None:
    assert 'href="css/style.css"' in index_html


def test_index_html_semantic_regions(index_html: str) -> None:
    assert "<header" in index_html
    assert "<main" in index_html
    assert "<footer" in index_html or '<footer ' in index_html


def test_index_html_header_controls(index_html: str) -> None:
    assert "book-select" in index_html or 'id="book-select"' in index_html
    assert "search" in index_html.lower()
    assert "settings" in index_html.lower()


def test_index_html_main_view_nav_discussion_search(index_html: str) -> None:
    """B09: Symmetric Discussion / Search controls at top of main; no header search link or back button."""
    assert "main-nav-discussion" in index_html
    assert "main-nav-search" in index_html
    assert "Discussion" in index_html
    assert 'id="search-open"' not in index_html
    assert "search-back" not in index_html


def test_index_html_logs_view_panel(index_html: str) -> None:
    """B10: Third main nav Logs and scrollable log viewer panel."""
    assert "main-nav-logs" in index_html
    assert "view-logs" in index_html
    assert "log-viewer-output" in index_html


def test_index_html_main_views_use_view_hidden_not_broken_hidden_attr(index_html: str) -> None:
    """B17: Search/Logs panels use .view--hidden (not HTML hidden) so CSS display:flex cannot override."""
    assert 'class="panel panel--search view--hidden"' in index_html
    assert 'class="panel panel--logs view--hidden"' in index_html
    for vid in ("view-search", "view-logs"):
        m = re.search(rf"<section[\s\S]*?id=\"{vid}\"[\s\S]*?>", index_html)
        assert m is not None, vid
        tag_open = m.group(0)
        assert "view--hidden" in tag_open
        assert "hidden" not in tag_open.replace("view--hidden", "")


def test_index_html_split_panels(index_html: str) -> None:
    assert "chat-panel" in index_html
    assert "references-panel" in index_html


def test_index_html_chat_composer_and_messages(index_html: str) -> None:
    assert "chat-messages" in index_html
    assert "message-input" in index_html or 'id="message-input"' in index_html
    assert "send" in index_html.lower()


def test_index_html_references_clear(index_html: str) -> None:
    assert "references-list" in index_html
    assert "clear-references" in index_html or 'id="clear-references"' in index_html


def test_index_html_status_bar(index_html: str) -> None:
    assert "status-bar" in index_html


def test_index_html_upload_dialog_sections(index_html: str) -> None:
    assert "upload-dialog" in index_html
    assert "upload-dropzone" in index_html
    assert "chunking-strategy" in index_html
    assert "upload-progress" in index_html


def test_index_html_upload_feedback_for_errors(index_html: str) -> None:
    """B13: inline upload error area inside the dialog (not only status bar)."""
    assert 'id="upload-feedback"' in index_html
    assert "upload-feedback" in index_html


def test_index_html_settings_dialog(index_html: str) -> None:
    assert "settings-dialog" in index_html
    assert "settings-form" in index_html
    assert "settings-feedback" in index_html
    assert "settings-llm_mode" in index_html


def test_index_html_settings_clear_all_data_button(index_html: str) -> None:
    """B16: Settings includes a destructive clear-all control."""
    assert 'id="settings-clear-all"' in index_html
    assert "btn-danger" in index_html


def test_index_html_settings_clear_models_cache_button(index_html: str) -> None:
    """B08: Embeddings tab exposes clear-models-cache control."""
    assert 'id="settings-clear-models-cache"' in index_html
    assert "Clear Models Cache (Downloads)" in index_html
    assert "data/models" in index_html


def test_index_html_settings_tabs_llm_and_embeddings(index_html: str) -> None:
    """B07: Settings dialog uses LLM vs Embeddings & Search tab panels."""
    assert "settings-tab-llm" in index_html
    assert "settings-tab-embeddings" in index_html
    assert "settings-panel-llm" in index_html
    assert "settings-panel-embeddings" in index_html
    assert "role=\"tablist\"" in index_html
    assert "role=\"tab\"" in index_html
    assert "role=\"tabpanel\"" in index_html


def test_index_html_settings_cloud_storage_warning(index_html: str) -> None:
    """B08: Cloud LLM group includes local settings file security notice."""
    assert "settings-cloud-security-warning" in index_html
    assert "settings-warning" in index_html
    assert "data/settings.json" in index_html
    assert "All settings, including API keys" in index_html
    assert "Keep this file secure" in index_html


def test_index_html_settings_llm_ollama_cloud_groups(index_html: str) -> None:
    """B06: LLM fields split into Ollama vs Cloud containers toggled by mode."""
    assert "settings-llm-group-ollama" in index_html
    assert "settings-llm-group-cloud" in index_html
    assert "settings-ollama_base_url" in index_html
    assert "settings-ollama_model_id" in index_html
    assert "settings-api_key" in index_html
    assert "settings-api_base_url" in index_html
    assert "settings-model_id" in index_html


def test_index_html_search_view_and_app_module(index_html: str) -> None:
    assert "view-search" in index_html
    assert "search-query" in index_html
    assert "search-results" in index_html


def test_index_html_search_max_results_control(index_html: str) -> None:
    """B05: hybrid search exposes max results (1–50) in the search panel."""
    assert 'id="search-max-results"' in index_html
    assert 'max="50"' in index_html
    assert 'value="20"' in index_html
    assert 'src="js/app.js"' in index_html
    assert 'type="module"' in index_html
