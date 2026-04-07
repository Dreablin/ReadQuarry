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
