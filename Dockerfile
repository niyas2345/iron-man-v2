FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

COPY . /src

RUN set -eux; \
    mkdir -p app/business app/models app/routers app/services app/data data; \
    touch app/__init__.py app/business/__init__.py app/models/__init__.py app/routers/__init__.py app/services/__init__.py; \
    cp /src/config.py app/config.py; \
    cp /src/main.py app/main.py; \
    cp /src/schemas.py app/models/schemas.py; \
    cp /src/boq.py app/business/boq.py; \
    cp /src/crm.py app/business/crm.py; \
    cp /src/finance.py app/business/finance.py; \
    cp /src/actions_catalog.json app/data/actions_catalog.json; \
    for f in action_mapper.py add_new_task_builder.py agent_interface.py apple_notes.py approval_engine.py approval_notifications.py capabilities.py communication_adapter.py conversation.py execution_backends.py executive_engine.py fallback_engine.py iron_man_orchestrator.py llm_service.py memory_store.py phone_push.py planner.py quality_gate.py shortcut_file_builder.py signing_client.py verifier.py voice_interface.py voice_pipeline.py workflow_engine.py; do cp /src/$f app/services/$f; done; \
    for f in iron_man.py shortcuts.py system.py voice.py; do [ -f /src/$f ] && cp /src/$f app/routers/$f || printf 'from fastapi import APIRouter\nrouter = APIRouter()\n' > app/routers/$f; done; \
    [ -d /src/data ] && cp -R /src/data/. data/ || true

EXPOSE 8080
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
