"""Build the fixed Add New Task shortcut from its approved specification."""
from __future__ import annotations

import io
import plistlib
from typing import Any, Dict, Iterable, List, Tuple


def _action(identifier: str, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "WFWorkflowActionIdentifier": identifier,
        "WFWorkflowActionParameters": parameters or {},
    }


def _text_attachment(variable_name: str) -> Dict[str, Any]:
    return {
        "WFSerializationType": "WFTextTokenAttachment",
        "Value": {"Type": "Variable", "VariableName": variable_name},
    }


def _text_token(template: str, bindings: Iterable[Tuple[str, str]]) -> Dict[str, Any]:
    attachments: Dict[str, Any] = {}
    result = template
    start = 0
    for marker, variable_name in bindings:
        index = result.index(marker, start)
        result = result[:index] + "\ufffc" + result[index + len(marker):]
        attachments[f"{{{index}, 1}}"] = _text_attachment(variable_name)
        start = index + 1
    return {
        "WFSerializationType": "WFTextTokenString",
        "Value": {"string": result, "attachmentsByRange": attachments},
    }


def _set_text_variable(value: str, variable_name: str) -> List[Dict[str, Any]]:
    return [
        _action("is.workflow.actions.gettext", {"WFTextActionText": value}),
        _action("is.workflow.actions.setvariable", {"WFVariableName": variable_name}),
    ]


def _menu_item(title: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"WFMenuItemTitle": title, "WFWorkflowActions": actions}


def build_add_new_task() -> bytes:
    """Return the binary property-list body for Add New Task.

    It deliberately keeps the list names from the approved specification:
    Work, Personal, and Inbox. The user can rename them in Shortcuts after
    import if their Reminders lists use different names.
    """
    priority_menu = _action(
        "is.workflow.actions.choosefrommenu",
        {
            "WFMenuPrompt": "Choose priority",
            "WFMenuItems": [
                _menu_item("High", _set_text_variable("High", "Task Priority")),
                _menu_item("Medium", _set_text_variable("Medium", "Task Priority")),
                _menu_item("Low", _set_text_variable("Low", "Task Priority")),
                _menu_item("None", _set_text_variable("None", "Task Priority")),
            ],
        },
    )
    list_menu = _action(
        "is.workflow.actions.choosefrommenu",
        {
            "WFMenuPrompt": "Which list?",
            "WFMenuItems": [
                _menu_item("Work", _set_text_variable("Work", "Target List")),
                _menu_item("Personal", _set_text_variable("Personal", "Target List")),
                _menu_item("Inbox", _set_text_variable("Inbox", "Target List")),
            ],
        },
    )
    workflow = {
        "WFWorkflowActions": [
            _action(
                "is.workflow.actions.dictatetext",
                {
                    "WFDictateTextActionPrompt": "What task would you like to add?",
                    "WFDictateTextActionStopListening": "After Pause",
                },
            ),
            _action("is.workflow.actions.setvariable", {"WFVariableName": "Task Title"}),
            priority_menu,
            list_menu,
            _action(
                "is.workflow.actions.reminder.add",
                {
                    "WFReminderTitle": _text_attachment("Task Title"),
                    "WFReminderList": _text_attachment("Target List"),
                    "WFReminderPriority": _text_attachment("Task Priority"),
                },
            ),
            _action(
                "is.workflow.actions.gettext",
                {
                    "WFTextActionText": _text_token(
                        "Added [Task Title] to [Target List] with [Task Priority] priority.",
                        [
                            ("[Task Title]", "Task Title"),
                            ("[Target List]", "Target List"),
                            ("[Task Priority]", "Task Priority"),
                        ],
                    )
                },
            ),
            _action("is.workflow.actions.speaktext"),
        ],
        "WFWorkflowClientVersion": "1129.7",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 431817727,
            "WFWorkflowIconGlyphNumber": 61440,
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasShortcutInputVariables": False,
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowName": "Add New Task",
    }
    buffer = io.BytesIO()
    plistlib.dump(workflow, buffer, fmt=plistlib.FMT_BINARY, sort_keys=False)
    return buffer.getvalue()
