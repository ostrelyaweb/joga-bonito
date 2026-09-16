"""Read-only Windows data providers used by external overlay windows."""

from __future__ import annotations

import ctypes
import os
import subprocess
from ctypes import wintypes


CREATE_NO_WINDOW = 0x08000000


def rocket_league_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq RocketLeague.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
        return "RocketLeague.exe" in result.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def keyboard_mouse_snapshot() -> str:
    if os.name != "nt":
        return "Input unavailable"
    user32 = ctypes.windll.user32
    keys = ((0x57, "W"), (0x41, "A"), (0x53, "S"), (0x44, "D"), (0x20, "SPACE"))
    active = [label for code, label in keys if user32.GetAsyncKeyState(code) & 0x8000]
    if user32.GetAsyncKeyState(0x01) & 0x8000:
        active.append("M1")
    if user32.GetAsyncKeyState(0x02) & 0x8000:
        active.append("M2")
    return "INPUT  " + ("  ".join(active) if active else "—")


class _XInputGamepad(ctypes.Structure):
    _fields_ = [
        ("buttons", wintypes.WORD),
        ("left_trigger", ctypes.c_ubyte),
        ("right_trigger", ctypes.c_ubyte),
        ("thumb_lx", ctypes.c_short),
        ("thumb_ly", ctypes.c_short),
        ("thumb_rx", ctypes.c_short),
        ("thumb_ry", ctypes.c_short),
    ]


class _XInputState(ctypes.Structure):
    _fields_ = [("packet", wintypes.DWORD), ("gamepad", _XInputGamepad)]


_BUTTONS = (
    (0x1000, "A"),
    (0x2000, "B"),
    (0x4000, "X"),
    (0x8000, "Y"),
    (0x0100, "LB"),
    (0x0200, "RB"),
)


def _xinput():
    if os.name != "nt":
        return None
    for library in ("xinput1_4.dll", "xinput9_1_0.dll", "xinput1_3.dll"):
        try:
            return ctypes.WinDLL(library)
        except OSError:
            continue
    return None


_XINPUT = _xinput()


def controller_snapshot() -> str:
    if _XINPUT is None:
        return "CONTROLLER  unavailable"
    state = _XInputState()
    if _XINPUT.XInputGetState(0, ctypes.byref(state)) != 0:
        return "CONTROLLER  disconnected"
    pad = state.gamepad
    buttons = [label for mask, label in _BUTTONS if pad.buttons & mask]
    lx = int(pad.thumb_lx * 100 / 32767) if pad.thumb_lx >= 0 else int(pad.thumb_lx * 100 / 32768)
    ly = int(pad.thumb_ly * 100 / 32767) if pad.thumb_ly >= 0 else int(pad.thumb_ly * 100 / 32768)
    pressed = " ".join(buttons) if buttons else "—"
    return f"PAD  {pressed}\nL {lx:+d},{ly:+d}   LT {pad.left_trigger:03d}  RT {pad.right_trigger:03d}"
