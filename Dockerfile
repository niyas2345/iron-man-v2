FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Copy requirements early so Docker can cache dependency installation
COPY requirements.txt /src/requirements.txt

RUN pip install --no-cache-dir -r /src/requirements.txt

# Copy the full source after installing dependencies
COPY . /src

# Move or create the app package inside /app. This keeps the runtime layout stable
RUN python - <<'PY'
from pathlib import Path
import shutil

src = Path("/src")
dst = Path("/app")
app = dst / "app"

if (src / "app").exists():
    shutil.copytree(src / "app", app, dirs_exist_ok=True)
else:
    for folder in ["business", "models", "routers", "services", "data"]:
        (app / folder).mkdir(parents=True, exist_ok=True)
    for init in [app, app/"business", app/"models", app/"routers", app/"services"]:
        (init / "__init__.py").write_text("", encoding="utf-8")

    files = {
        "config.py": "app/config.py",
        "main.py": "app/main.py",
        "schemas.py": "app/models/schemas.py",
        "boq.py": "app/business/boq.py",
        "crm.py": "app/business/crm.py",
        "finance.py": "app/business/finance.py",
        "actions_catalog.json": "app/data/actions_catalog.json",
    }

    for name in [
        "action_mapper.py", "add_new_task_builder.py", "agent_interface.py",
        "apple_notes.py", "approval_engine.py", "approval_notifications.py",
        "capabilities.py", "communication_adapter.py", "conversation.py",
        "execution_backends.py", "executive_engine.py", "fallback_engine.py",
        "iron_man_orchestrator.py", "llm_service.py", "memory_store.py",
        "phone_push.py", "planner.py", "quality_gate.py",
        "shortcut_file_builder.py", "signing_client.py", "verifier.py",
        "voice_interface.py", "voice_pipeline.py", "workflow_engine.py",
    ]:
        files[name] = f"app/services/{name}"

    for name in ["iron_man.py", "shortcuts.py", "system.py", "voice.py"]:
        files[name] = f"app/routers/{name}"

    for source, target in files.items():
        source_path = src / source
        if source_path.exists():
            shutil.copy2(source_path, dst / target)

if (src / "data").exists():
    shutil.copytree(src / "data", dst / "data", dirs_exist_ok=True)
PY

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
