# IronMan Recovery V1 audit

Audit baseline: `niyas2345/iron-man-v2`, GitHub `main`, commit `e1e6eb73a709ed000a6f6c505c2cba72657f93e3`.

## What the audit found

- The committed FastAPI application assembles several routers, models, and services through a Docker-only file-copy layout.
- The committed voice implementation exposes only `/api/voice/stream` over WebSockets and depends on Google Speech credentials.
- The existing orchestrator also owns task planning, approvals, specialists, execution backends, verification, and cloud migration concerns.
- The task-oriented JSON memory schema is not suitable for short user/assistant conversation history.
- Existing local modifications outside this directory were present before recovery work started and were left untouched.

## Reuse decisions

| Existing source | V1 decision |
| --- | --- |
| `config.py` | Reuse the environment-variable and lazy-provider pattern in a smaller recovery config. |
| `llm_service.py` | Reuse its provider boundary and Anthropic configuration conventions; omit workflow-generation concerns. |
| `iron_man_orchestrator.py` | Preserve Iron Man identity and concise executive behavior; do not import its cloud/task dependency graph. |
| `memory_store.py` | Preserve the explicit memory abstraction; use bounded per-session conversation turns instead of task records. |
| `voice.py` | Replace the WebSocket flow only inside the parallel project with one HTTP transcript endpoint. |

## V1 boundary

Included: one FastAPI app, `POST /command`, one orchestrator, one config module, one bounded memory layer, optional Bearer authentication, optional Anthropic responses, and a deterministic no-key fallback. Deployment packaging and keyless GitHub-to-Cloud-Run automation live outside the runtime modules.

Excluded from the application runtime: WebSockets, audio streaming, Google Speech-to-Text, Pushcut, shortcut signing, Docker remapping, task approvals, specialist agents, and cloud-provider SDKs.
