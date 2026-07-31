from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import JellycutsBuildRequest, JellycutsBuildResponse


def _clean_base_url(url: str) -> str:
    return url.rstrip("/")


def _jelly_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _shortcut_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", name).strip()
    return cleaned or "Ask Iron Man"


@dataclass(frozen=True)
class JellycutsBuilder:
    """Build Jellycuts source for Iron Man iPhone voice-command shortcuts."""

    def build_voice_task_shortcut(
        self,
        request: JellycutsBuildRequest,
        base_url: str,
    ) -> JellycutsBuildResponse:
        name = _shortcut_name(request.name)
        endpoint = f"{_clean_base_url(request.service_url or base_url)}/api/iron-man/tasks"
        prompt = _jelly_string(request.command_prompt)
        confirmation = _jelly_string(request.confirmation_text)

        jellycuts = f'''import Shortcuts
#Color: red, #Icon: shortcuts

// {name}
// Dictate a command, submit it to Iron Man V2, then speak confirmation.

var command = dictateText(prompt: "{prompt}", language: "en-US", stopListening: afterPause)

var ironManResponse = downloadURL(
  url: "{endpoint}",
  method: post,
  headers: {{"Content-Type": "application/json"}},
  requestBody: json({{
    "request": "${{command}}",
    "priority": "{request.priority}"
  }})
)

speakText(
  "{confirmation}",
  waitUntilFinished: true,
  language: "en-US"
)
'''

        return JellycutsBuildResponse(
            name=name,
            endpoint=endpoint,
            jellycuts=jellycuts,
            install_steps=[
                "Open Jellycuts on the iPhone.",
                "Create or replace a shortcut with this source.",
                "Compile it into Apple Shortcuts and run it once to grant microphone/network permission.",
            ],
        )


jellycuts_builder = JellycutsBuilder()
