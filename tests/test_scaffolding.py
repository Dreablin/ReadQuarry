from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_root_files_exist() -> None:
    required_files = [
        "requirements.txt",
        "main.py",
        "config.py",
        ".gitignore",
        "start.bat",
        "start.sh",
    ]
    for file_name in required_files:
        assert (ROOT / file_name).is_file(), f"Missing file: {file_name}"


def test_prompt_documents_ralph_loop_finite_max_iterations_safety() -> None:
    """B12: prompt.md must tell operators to use a finite max_iterations cap (not unlimited)."""
    text = (ROOT / "prompt.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "max_iterations" in lower or "max-iterations" in lower
    assert "safety" in lower or "backup" in lower or "finite" in lower
    assert "do not" in lower or "don't" in lower or "never" in lower
    assert "`0`" in text or " 0 " in text


def test_required_directories_exist() -> None:
    required_dirs = [
        "src",
        "src/api",
        "src/core",
        "src/parsers",
        "src/models",
        "src/db",
        "static",
        "static/css",
        "static/js",
        "static/js/components",
        "tests",
        "tests/test_parsers",
        "tests/test_core",
        "tests/test_api",
        "tests/test_e2e",
        "tests/test_models",
        "data",
        "data/chroma",
        "data/tantivy_index",
    ]
    for dir_name in required_dirs:
        assert (ROOT / dir_name).is_dir(), f"Missing directory: {dir_name}"
