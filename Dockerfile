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
    if [ -d /src/app ]; then cp -R /src/app/. app/; else \
      cp /src/config.py app/config.py; \
      cp /src/main.py app/main.py; \
      cp /src/schemas.py app/models/schemas.py; \
      cp /src/boq.py app/business/boq.py; \
      cp /src/crm.py app/business/crm.py; \
      cp /src/finance.py app/business/finance.py; \
      cp /src/actions_catalog.json app/data/actions_catalog.json; \
      for f in action_mapper.py add_new_task_builder.py agent_interface.py apple_notes.py approval_engine.py approval_notifications.py capabilities.py communication_adapter.py conversation.py execution_engine.py file_store.py firebase.py flashbots.py forms.py github_actions.py google_drive.py google_sheets.py gpt_wrapper.py helpers.py import_handler.py installer.py jira.py klaxon.py ldap_helpers.py local_file_store.py logging_utils.py mailgun.py meetings.py meta_task.py msteams.py musicbrainz.py notion.py organizer.py persister.py plugins.py pull_request.py quickstart.py redis_adapters.py redis_helpers.py research.py rmq.py router.py schema_helpers.py search.py security.py sendgrid.py sina.py slack.py slack_app.py slack_bots.py s3_adapters.py settings.py slack_notifications.py souremap.py speech_utils.py sql_helpers.py storage.py sw.py systemd.py telemetry.py test_runner.py time_helpers.py utils.py websocket_server.py; do [ -f /src/$f ] && cp /src/$f app/routers/$f || true; done; \
      for f in iron_man.py shortcuts.py system.py voice.py; do [ -f /src/$f ] && cp /src/$f app/routers/$f || printf 'from fastapi import APIRouter\nrouter = APIRouter()\n' > app/routers/$f; done; \
    fi; \
    [ -d /src/data ] && cp -R /src/data/. data/ || true

EXPOSE 8080
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
