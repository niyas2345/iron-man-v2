from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent


def _prepare_app_package(folder: Path) -> None:
    app = folder / "app"
    (app / "services").mkdir(parents=True)
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "services" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(PROJECT_ROOT / "legacy_blueprint.py", app / "services" / "legacy_blueprint.py")


def test_legacy_blueprint_preserves_thor_loki_rules_for_iron_man_v2():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        _prepare_app_package(root)
        sys.path.insert(0, str(root))
        try:
            from app.services.legacy_blueprint import legacy_blueprint
        finally:
            sys.path.remove(str(root))

    assert "Thor" in legacy_blueprint.source_names
    assert "Loki" in legacy_blueprint.source_names
    assert "single executive coordinator" in legacy_blueprint.orchestration_rule
    assert "adapters only" in legacy_blueprint.adapter_rule
    assert "explicit approval" in legacy_blueprint.approval_rule
    assert legacy_blueprint.specialists[0].name == "Loki"
    assert "shortcut_automation" in legacy_blueprint.specialists[0].capabilities
