"""
LLMService is responsible for exactly one thing: turning a free-text
shortcut description into a structured, validated `Workflow` object.

It never knows about Apple Shortcuts action identifiers -- that mapping
is the ActionMapper's job (separation of concerns). This keeps the LLM
prompt focused on *planning intent*, and keeps the Shortcuts-specific
knowledge in one place (the action catalog).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from app.config import settings
from app.models.schemas import ShortcutRequest, Workflow

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a workflow-planning engine for an AI Shortcut Assistant.

Given a natural language description of something a user wants an Apple \
Shortcut to do, decompose it into a clear, ordered, platform-agnostic \
workflow of atomic steps.

Rules:
- Break the goal into the smallest sensible atomic steps (get input, call \
an API/service, extract/transform data, branch on a condition, display or \
speak output, handle the "not found" case, etc).
- Each step must have a short snake_case `intent` (e.g. "ask_user_input", \
"call_web_api", "extract_field", "check_condition", "display_result").
- Do NOT reference Apple Shortcuts action names or identifiers. Describe \
*what* needs to happen, not the specific native action.
- Always include error/empty-result handling as its own step when the \
happy path could plausibly fail (e.g. network calls, lookups).
- Respond with ONLY valid JSON matching this exact schema, no prose, no \
markdown fences:

{
  "title": "string, short title for the shortcut",
  "summary": "string, one sentence summary of what it does",
  "steps": [
    {
      "step_id": 1,
      "intent": "snake_case_intent",
      "description": "human readable description of this step",
      "inputs": {"key": "value"},
      "outputs": {"key": "value"},
      "requires_user_input": false
    }
  ]
}
"""


class LLMServiceError(RuntimeError):
    """Raised when the LLM backend fails or returns an unparsable plan."""


class LLMService:
    def __init__(self) -> None:
        self._client = None
        if not settings.use_mock_llm:
            # Imported lazily so the package is only a hard dependency
            # when a real API key is actually configured.
            import anthropic

            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_workflow(self, request: ShortcutRequest) -> Workflow:
        if settings.use_mock_llm:
            logger.info("ANTHROPIC_API_KEY not set - using mock planner.")
            raw = self._mock_plan(request.description)
        else:
            raw = self._call_claude(request)

        return Workflow.model_validate(raw)

    # ------------------------------------------------------------------
    # Real LLM path
    # ------------------------------------------------------------------
    def _call_claude(self, request: ShortcutRequest) -> Dict[str, Any]:
        user_prompt = (
            f"User's shortcut description: \"{request.description}\"\n"
            f"Desired granularity: {request.complexity.value}\n\n"
            "Produce the JSON workflow now."
        )
        try:
            response = self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:  # network / auth / rate-limit errors
            raise LLMServiceError(f"Anthropic API call failed: {exc}") from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return self._extract_json(text)

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Strip markdown fences / stray prose and parse the JSON payload."""
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Last resort: grab the outermost {...} block.
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise LLMServiceError(f"Could not parse LLM output as JSON: {exc}") from exc

    # ------------------------------------------------------------------
    # Mock / offline planner
    # ------------------------------------------------------------------
    # A small deterministic rule-based planner so the API works out of the
    # box for demos/tests without a network call or API key. It recognizes
    # a few common intent families and otherwise falls back to a generic
    # fetch -> process -> display skeleton.
    def _mock_plan(self, description: str) -> Dict[str, Any]:
        desc_lower = description.lower()
        steps: List[Dict[str, Any]] = []
        step_id = 1

        def add(intent: str, desc: str, inputs=None, outputs=None, needs_input=False):
            nonlocal step_id
            steps.append(
                {
                    "step_id": step_id,
                    "intent": intent,
                    "description": desc,
                    "inputs": inputs or {},
                    "outputs": outputs or {},
                    "requires_user_input": needs_input,
                }
            )
            step_id += 1

        wants_lyrics = "lyric" in desc_lower
        wants_song = "song" in desc_lower or wants_lyrics
        wants_speak = "speak" in desc_lower or "read aloud" in desc_lower or "read it" in desc_lower
        wants_save = "save" in desc_lower or "export" in desc_lower
        wants_notify = "notif" in desc_lower or "alert" in desc_lower

        if wants_song:
            add(
                "get_current_song",
                "Get the currently playing song (or ask the user for a song name).",
                outputs={"song_title": "string", "artist": "string"},
            )
            add(
                "ask_user_input",
                "If no song is playing, ask the user to type a song name.",
                needs_input=True,
                outputs={"song_query": "string"},
            )
            add(
                "call_web_api",
                "Call a lyrics lookup API/service with the song title and artist.",
                inputs={"query": "song_title + artist"},
                outputs={"api_response": "json"},
            )
            add(
                "extract_field",
                "Extract the lyrics text field from the API response.",
                inputs={"api_response": "json"},
                outputs={"lyrics_text": "string"},
            )
            add(
                "check_condition",
                "Check whether lyrics were found; if not, show an error message and stop.",
                inputs={"lyrics_text": "string"},
            )
            add(
                "display_result",
                "Display the lyrics text to the user.",
                inputs={"lyrics_text": "string"},
            )
        else:
            add(
                "ask_user_input",
                "Ask the user for the input needed to fulfill the request.",
                needs_input=True,
                outputs={"user_query": "string"},
            )
            add(
                "call_web_api",
                "Fetch or compute the requested data based on the user's input.",
                inputs={"user_query": "string"},
                outputs={"result": "any"},
            )
            add(
                "check_condition",
                "Check whether a valid result was returned; handle the empty case.",
                inputs={"result": "any"},
            )
            add(
                "display_result",
                "Display the result to the user.",
                inputs={"result": "any"},
            )

        if wants_speak:
            add(
                "speak_result",
                "Speak the result text aloud using text-to-speech.",
                inputs={"result_text": "string"},
            )
        if wants_save:
            add(
                "save_file",
                "Save the result to a file for later reference.",
                inputs={"result_text": "string"},
            )
        if wants_notify:
            add(
                "send_notification",
                "Send a notification summarizing the result.",
                inputs={"result_text": "string"},
            )

        title = "Get Song Lyrics" if wants_lyrics else "Custom Shortcut"
        summary = description.strip().rstrip(".") + "."

        return {"title": title, "summary": summary, "steps": steps}
