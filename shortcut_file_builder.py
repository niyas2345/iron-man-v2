"""
Converts a `ShortcutBuildResponse` (our internal mapped-action plan) into
an actual Apple Shortcuts file: a property list with the exact top-level
keys and per-action `WFWorkflowActionIdentifier` / `WFWorkflowActionParameters`
structure the Shortcuts app expects on import.

IMPORTANT CONTEXT FOR MAINTAINERS
----------------------------------
Apple has never published this format. Everything here matches the
schema independently verified by the shortcuts developer community
(the same schema every third-party "shortcut gallery" site relies on to
generate importable .shortcut files) -- but it is not an official,
versioned contract, and Apple can shift details between iOS releases.

To keep every file we hand out *actually importable*, we only emit real
parameters for actions we're confident about (`EXPORT_BUILDERS` below).
Anything else (branching/loops, which need paired grouping UUIDs, and a
couple of actions whose exact keys are unverified) is swapped for a
"Comment" action explaining what to add manually. That trade-off is
deliberate: a shortcut that imports cleanly and is 90% built beats one
that fails to import at all.
"""
from __future__ import annotations

import io
import plistlib
import re
import uuid
from typing import Any, Callable, Dict, List, Tuple

from app.models.schemas import MappedAction, ShortcutBuildResponse

# --------------------------------------------------------------------------
# Per-action parameter builders.
#
# Each builder takes the MappedAction (so it can pull the human-readable
# step description / any inferred parameter values) and returns the
# WFWorkflowActionParameters dict for that action.
#
# Design choice: steps chain via Shortcuts' *implicit* behavior -- most
# actions that don't have an explicit input parameter set automatically
# operate on the previous action's result. That avoids the far more
# fragile "magic variable" UUID-linking mechanism, at the cost of not
# being able to reference an output from more than one step back. Good
# enough for the linear happy-path flows this engine generates.
# --------------------------------------------------------------------------

def _text_params(step: MappedAction) -> Dict[str, Any]:
    return {"WFTextActionText": step.parameters.get("WFTextActionText") or step.step_description}


def _ask_params(step: MappedAction) -> Dict[str, Any]:
    return {
        "WFAskActionPrompt": step.parameters.get("WFAskActionPrompt") or step.step_description,
        "WFInputType": "Text",
    }


def _set_variable_params(step: MappedAction) -> Dict[str, Any]:
    name = re.sub(r"[^A-Za-z0-9]+", " ", step.step_description).strip().title().replace(" ", "")[:40] or "Result"
    return {"WFVariableName": name}


def _get_variable_params(step: MappedAction) -> Dict[str, Any]:
    name = re.sub(r"[^A-Za-z0-9]+", " ", step.step_description).strip().title().replace(" ", "")[:40] or "Result"
    return {"WFVariableName": name}


def _download_url_params(step: MappedAction) -> Dict[str, Any]:
    return {
        "WFURL": step.parameters.get("WFURL") or "https://example.com/api?q=REPLACE_ME",
        "WFHTTPMethod": "GET",
    }


def _show_result_params(step: MappedAction) -> Dict[str, Any]:
    # Left blank on purpose: Show Result displays the previous action's
    # output by default when Text is empty.
    return {"Text": ""}


def _speak_text_params(step: MappedAction) -> Dict[str, Any]:
    return {"WFText": "", "WFSpeakTextLanguage": "en-US"}


def _notification_params(step: MappedAction) -> Dict[str, Any]:
    return {
        "WFNotificationActionTitle": step.parameters.get("WFNotificationActionTitle") or "Shortcut Result",
        "WFNotificationActionBody": "",
    }


def _replace_text_params(step: MappedAction) -> Dict[str, Any]:
    return {
        "WFReplaceTextFind": step.parameters.get("WFReplaceTextFind") or "",
        "WFReplaceTextReplace": step.parameters.get("WFReplaceTextReplace") or "",
    }


def _empty_params(step: MappedAction) -> Dict[str, Any]:
    return {}


def _comment_params(step: MappedAction, text: str) -> Dict[str, Any]:
    return {"WFCommentActionText": text}


EXPORT_BUILDERS: Dict[str, Callable[[MappedAction], Dict[str, Any]]] = {
    "is.workflow.actions.gettext": _text_params,
    "is.workflow.actions.ask": _ask_params,
    "is.workflow.actions.setvariable": _set_variable_params,
    "is.workflow.actions.getvariable": _get_variable_params,
    "is.workflow.actions.downloadurl": _download_url_params,
    "is.workflow.actions.detect.text": _empty_params,
    "is.workflow.actions.showresult": _show_result_params,
    "is.workflow.actions.speaktext": _speak_text_params,
    "is.workflow.actions.notification": _notification_params,
    "is.workflow.actions.exit": _empty_params,
    "is.workflow.actions.replacetext": _replace_text_params,
    "is.workflow.actions.copytopasteboard": _empty_params,
    "is.workflow.actions.comment": _empty_params,
}


# --------------------------------------------------------------------------
# Plist assembly
# --------------------------------------------------------------------------

DEFAULT_ICON = {
    "WFWorkflowIconStartColor": 431817727,  # standard blue, matches Apple's gallery default
    "WFWorkflowIconGlyphNumber": 61440,
}


class ShortcutFileBuilder:
    def build(self, response: ShortcutBuildResponse) -> Tuple[bytes, List[str]]:
        """Returns (plist_bytes, export_notes). export_notes lists any
        steps that were swapped for a manual-setup Comment action."""
        actions: List[Dict[str, Any]] = []
        export_notes: List[str] = []

        for step in response.steps:
            builder = EXPORT_BUILDERS.get(step.shortcut_action_identifier)

            if builder is None:
                note = (
                    f"Step {step.step_id} ('{step.step_description}') uses "
                    f"'{step.action_name}', which isn't auto-exportable yet "
                    "(needs manual setup in the Shortcuts app). Inserted as "
                    "a placeholder comment so the file still imports cleanly."
                )
                export_notes.append(note)
                actions.append(
                    {
                        "WFWorkflowActionIdentifier": "is.workflow.actions.comment",
                        "WFWorkflowActionParameters": _comment_params(
                            step,
                            f"TODO: Add '{step.action_name}' here manually -- {step.step_description}",
                        ),
                    }
                )
                continue

            actions.append(
                {
                    "WFWorkflowActionIdentifier": step.shortcut_action_identifier,
                    "WFWorkflowActionParameters": builder(step),
                }
            )

        workflow: Dict[str, Any] = {
            "WFWorkflowActions": actions,
            "WFWorkflowClientVersion": "1129.7",
            "WFWorkflowMinimumClientVersion": 900,
            "WFWorkflowMinimumClientVersionString": "900",
            "WFWorkflowIcon": DEFAULT_ICON,
            "WFWorkflowImportQuestions": [],
            "WFWorkflowTypes": [],
            "WFWorkflowHasShortcutInputVariables": False,
            "WFWorkflowInputContentItemClasses": [],
        }

        buffer = io.BytesIO()
        plistlib.dump(workflow, buffer, fmt=plistlib.FMT_BINARY)
        return buffer.getvalue(), export_notes

    @staticmethod
    def safe_filename(title: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", title).strip() or "Shortcut"
        return f"{cleaned.replace(' ', '_')}.shortcut"


shortcut_file_builder = ShortcutFileBuilder()
