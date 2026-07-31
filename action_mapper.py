"""
ActionMapper takes a platform-agnostic `Workflow` (list of abstract steps)
and maps each step onto a concrete Apple Shortcuts action from the
catalog in app/data/actions_catalog.json.

Matching strategy:
  1. Build a "search text" per step = intent + description.
  2. Score every catalog action by keyword overlap + fuzzy string
     similarity (difflib) against that search text.
  3. Take the best-scoring action above a confidence threshold.
  4. If nothing clears the threshold, fall back to a generic
     "Get Contents of URL" / "Text" placeholder action and raise a
     warning so the caller (and the end user) knows this step needs
     manual configuration in the Shortcuts app.

This keeps the LLM out of the business of knowing exact Apple action
identifiers (which change across iOS versions) -- that knowledge lives
entirely in the catalog, making it easy to update/extend independently.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.config import settings
from app.models.schemas import MappedAction, Workflow

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "actions_catalog.json"

# Fallback action used when no catalog entry meets the confidence threshold.
FALLBACK_ACTION = {
    "identifier": "is.workflow.actions.downloadurl",
    "name": "Get Contents of URL (manual setup needed)",
    "category": "Web",
    "keywords": [],
    "default_parameters": {"WFURL": "", "WFHTTPMethod": "GET"},
}


class ActionMapper:
    def __init__(self, catalog_path: Path = CATALOG_PATH) -> None:
        with open(catalog_path, "r", encoding="utf-8") as fh:
            self.catalog: List[Dict[str, Any]] = json.load(fh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def map_workflow(self, workflow: Workflow) -> Tuple[List[MappedAction], List[str]]:
        mapped_steps: List[MappedAction] = []
        warnings: List[str] = []

        for step in workflow.steps:
            action, confidence = self._best_match(step.intent, step.description)

            note = None
            if confidence < settings.action_match_threshold:
                warning = (
                    f"Step {step.step_id} ('{step.description}') had no confident "
                    f"catalog match (confidence={confidence:.2f}). Using a generic "
                    "placeholder action -- please configure it manually in the "
                    "Shortcuts app."
                )
                warnings.append(warning)
                note = "Low-confidence match: manual configuration recommended."
                action = FALLBACK_ACTION

            mapped_steps.append(
                MappedAction(
                    step_id=step.step_id,
                    step_description=step.description,
                    shortcut_action_identifier=action["identifier"],
                    action_name=action["name"],
                    parameters=self._build_parameters(action, step),
                    match_confidence=round(confidence, 2),
                    notes=note,
                )
            )

        return mapped_steps, warnings

    # ------------------------------------------------------------------
    # Matching internals
    # ------------------------------------------------------------------
    def _best_match(self, intent: str, description: str) -> Tuple[Dict[str, Any], float]:
        search_text = f"{intent.replace('_', ' ')} {description}".lower()

        best_action = FALLBACK_ACTION
        best_score = 0.0

        for action in self.catalog:
            score = self._score(search_text, action)
            if score > best_score:
                best_score = score
                best_action = action

        return best_action, best_score

    @staticmethod
    def _score(search_text: str, action: Dict[str, Any]) -> float:
        keywords = action.get("keywords", [])
        if not keywords:
            return 0.0

        search_words = set(search_text.split())

        # A keyword phrase "hits" if either (a) it appears verbatim as a
        # substring of the search text, or (b) every individual word in
        # the phrase appears somewhere among the search text's tokens.
        # (b) is what lets "call api" match "...call a lyrics lookup api..."
        # without requiring the words to be adjacent.
        hits = 0
        best_token_overlap = 0.0
        for kw in keywords:
            kw_words = set(kw.split())
            if kw in search_text or kw_words.issubset(search_words):
                hits += 1

            overlap = len(kw_words & search_words) / len(kw_words)
            best_token_overlap = max(best_token_overlap, overlap)

        keyword_score = hits / len(keywords)

        # Fuzzy fallback for near-synonyms that share no exact tokens,
        # scored keyword-by-keyword (not against the whole sentence) so
        # long descriptions don't get unfairly penalized.
        fuzzy_score = max(
            (difflib.SequenceMatcher(None, kw, search_text).ratio() for kw in keywords),
            default=0.0,
        )

        return (0.55 * keyword_score) + (0.30 * best_token_overlap) + (0.15 * fuzzy_score)

    @staticmethod
    def _build_parameters(action: Dict[str, Any], step) -> Dict[str, Any]:
        """Seed the action's default parameters with anything we can infer
        from the step's declared inputs, so the output is closer to a
        ready-to-import shortcut rather than a bare template."""
        params = dict(action.get("default_parameters", {}))

        # Best-effort heuristic prefill: drop the step description into
        # the most relevant text-like parameter, if the action has one.
        for key in ("WFTextActionText", "WFAskActionPrompt", "Text", "WFText"):
            if key in params:
                params[key] = step.description
                break

        return params


# Module-level singleton so the catalog is parsed once per process.
action_mapper = ActionMapper()
