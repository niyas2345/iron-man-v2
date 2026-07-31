# Iron Man V2 Clean Build

This folder is the clean deployable Iron Man V2 source tree.

Included:

- `app/` - FastAPI application, orchestration layer, capability registry, Antigravity backend, memory store, and voice pipeline.
- `data/` - action catalog data used by the app.
- `deploy/` - Google Cloud Run service template.
- `docs/` - V2 audit and migration notes.
- `Dockerfile` - Cloud Run container build entry point.
- `requirements.txt` - Python dependencies.
- `README.md` - setup and deployment notes.
- `test_iron_man_orchestrator.py` - core orchestration verification tests.

Excluded:

- Legacy root-level duplicate Python modules.
- macOS metadata.
- Python cache files.
- Old shortcut archives and historical backup folders.
- Previous AWS/local experiment files not needed for Cloud Run deployment.

Upload the contents of this folder to the GitHub repository root.
