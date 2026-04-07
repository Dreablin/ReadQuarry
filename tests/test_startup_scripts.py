"""Structural checks for PRD §4.1 startup scripts (start.bat / start.sh)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
START_BAT = ROOT / "start.bat"
START_SH = ROOT / "start.sh"


@pytest.fixture(scope="module")
def start_bat_text() -> str:
    return START_BAT.read_text(encoding="utf-8", errors="replace")


@pytest.fixture(scope="module")
def start_sh_text() -> str:
    return START_SH.read_text(encoding="utf-8", errors="replace")


def test_start_bat_exists() -> None:
    assert START_BAT.is_file(), "start.bat must exist at repo root"


def test_start_sh_exists() -> None:
    assert START_SH.is_file(), "start.sh must exist at repo root"


def test_start_bat_checks_python_version(start_bat_text: str) -> None:
    lower = start_bat_text.lower()
    assert "sys.version_info" in start_bat_text or "3.10" in start_bat_text
    assert "python" in lower


def test_start_bat_uses_venv_and_requirements(start_bat_text: str) -> None:
    assert ".venv" in start_bat_text
    assert "requirements.txt" in start_bat_text
    assert "pip" in start_bat_text.lower()


def test_start_bat_runs_app_and_opens_browser(start_bat_text: str) -> None:
    assert "main.py" in start_bat_text
    assert "8000" in start_bat_text
    assert "start " in start_bat_text.lower() or "http://" in start_bat_text.lower()


def test_start_sh_checks_python_version(start_sh_text: str) -> None:
    assert "sys.version_info" in start_sh_text or "3.10" in start_sh_text
    assert "python3" in start_sh_text


def test_start_sh_uses_venv_and_requirements(start_sh_text: str) -> None:
    assert ".venv" in start_sh_text
    assert "requirements.txt" in start_sh_text
    assert "pip" in start_sh_text.lower()


def test_start_sh_runs_app_and_opens_browser(start_sh_text: str) -> None:
    assert "main.py" in start_sh_text
    assert "8000" in start_sh_text
    assert "xdg-open" in start_sh_text or "open " in start_sh_text
