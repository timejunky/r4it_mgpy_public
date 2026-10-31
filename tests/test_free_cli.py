import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from manifestguard.cli import main

def test_version():
    assert main(["--version"]) == 0

def test_check_missing_manifest(tmp_path: Path):
    assert main(["check", str(tmp_path)]) == 1

def test_check_does_not_load_pro(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"sample\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 0
    forbidden = (
        "manifestguard.extended",
        "manifestguard.licensing",
        "manifestguard.core",
        "manifestguard.quickcheck",
    )
    assert [name for name in forbidden if name in sys.modules] == []