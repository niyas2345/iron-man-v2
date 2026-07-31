"""Private Apple Notes bridge for Iron Man."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

NOTE_NAME = "Iron Man - Executive Memory"
FOLDER_NAME = "Iron Man"


@dataclass(frozen=True)
class NotesResult:
    status: str
    note_name: str
    detail: str


class AppleNotesBridge:
    def append_confirmed(self, text: str, *, execute: bool = True) -> NotesResult:
        if not text.strip():
            return NotesResult("invalid", NOTE_NAME, "Nothing was supplied to save.")
        if not execute:
            return NotesResult("ready", NOTE_NAME, "Ready to request macOS Notes permission.")
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        script = f'''tell application "Notes"
    if not (exists folder "{FOLDER_NAME}") then make new folder with properties {{name:"{FOLDER_NAME}"}}
    set targetFolder to folder "{FOLDER_NAME}"
    if exists note "{NOTE_NAME}" of targetFolder then
        set body of note "{NOTE_NAME}" of targetFolder to (body of note "{NOTE_NAME}" of targetFolder) & "<br><br>{escaped}"
    else
        make new note at targetFolder with properties {{name:"{NOTE_NAME}", body:"{escaped}"}}
    end if
end tell'''
        try:
            output = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True, timeout=20)
            return NotesResult("saved", NOTE_NAME, output.stdout.strip() or "Saved in Apple Notes.")
        except FileNotFoundError:
            return NotesResult("unavailable", NOTE_NAME, "Apple Notes is available only on macOS.")
        except subprocess.TimeoutExpired:
            return NotesResult("needs_user_action", NOTE_NAME, "Notes permission did not finish in time.")
        except subprocess.CalledProcessError as error:
            return NotesResult("needs_user_action", NOTE_NAME, (error.stderr or "Approve the macOS Notes permission, then try again.").strip())


apple_notes = AppleNotesBridge()
