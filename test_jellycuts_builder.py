from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent


def _prepare_app_package(folder: Path) -> None:
    app = folder / "app"
    (app / "models").mkdir(parents=True)
    (app / "services").mkdir(parents=True)
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "models" / "__init__.py").write_text("", encoding="utf-8")
    (app / "services" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(PROJECT_ROOT / "schemas.py", app / "models" / "schemas.py")
    shutil.copy2(PROJECT_ROOT / "jellycuts_builder.py", app / "services" / "jellycuts_builder.py")


def test_jellycuts_builder_creates_ask_iron_man_voice_shortcut():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        _prepare_app_package(root)
        sys.path.insert(0, str(root))
        try:
            from app.models.schemas import JellycutsBuildRequest
            from app.services.jellycuts_builder import jellycuts_builder

            build = jellycuts_builder.build_voice_task_shortcut(
                JellycutsBuildRequest(service_url="https://iron-man.example.run.app"),
                "https://ignored.example",
            )
        finally:
            sys.path.remove(str(root))

    assert build.endpoint == "https://iron-man.example.run.app/api/voice/command"
    assert "var command = dictateText" in build.jellycuts
    assert "var ironManResponse = downloadURL" in build.jellycuts
    assert "method: post" in build.jellycuts
    assert "requestBody: json" in build.jellycuts
    assert '"command": "${command}"' in build.jellycuts
    assert '"priority": "normal"' in build.jellycuts
    assert '"X-API-Key": "REPLACE_WITH_IRON_MAN_API_KEY"' in build.jellycuts
    assert 'key: "response"' in build.jellycuts
