"""Free install, update, and uninstall counts for Alveos Beacon.

Consent 1 stays on this machine. The POST carries the public app id and no
Bearer token. The only host is Alveos Beacon.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import click

APP_ID = "alv_prd_mgpy_public"
LIFE_URL = "https://login.alveos.eu/api/v1/track"
SKIP_ENV = "MGPY_SKIP_BEACON"
ACCEPT_ENV = "MGPY_BEACON_ACCEPT"
HOME_ENV = "MGPY_BEACON_HOME"
URL_ENV = "ALVEOS_BEACON_URL"
QUEUE_CAP = 50
_NOTICE = (
    "ManifestGuard Free can send an anonymous install, update, or uninstall count to Alveos.\n"
    "The count is an instance id, the event, and the version. No name, email, or activation key.\n"
    "You can refuse. The check still runs.\n"
)


Poster = Callable[[str, dict[str, Any], float], int]


def _truthy(env: dict[str, str], key: str) -> bool:
    return str(env.get(key) or "").strip().lower() in {"1", "true", "yes"}


def state_dir(env: dict[str, str] | None = None) -> Path:
    values = env if env is not None else os.environ
    override = str(values.get(HOME_ENV) or "").strip()
    if override:
        return Path(override)
    if os.name == "nt":
        appdata = values.get("APPDATA")
        if appdata:
            return Path(appdata) / "ManifestGuard"
    return Path.home() / ".manifestguard"


def _state_path(folder: Path) -> Path:
    return folder / "free-beacon.json"


def _queue_path(folder: Path) -> Path:
    return folder / "free-beacon.queue.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _load_state(folder: Path) -> dict[str, Any]:
    return _read_json(_state_path(folder))


def _save_state(folder: Path, state: dict[str, Any]) -> None:
    _write_json(_state_path(folder), state)


def _platform() -> str:
    name = sys.platform.lower().replace(" ", "")
    if not name or not name[0].isalnum():
        return "python"
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return f"{cleaned}_python"[:48]


def _http_post(url: str, body: dict[str, Any], timeout: float) -> int:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "manifestguard-free-beacon",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except URLError:
        return 0


def _load_queue(folder: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(_queue_path(folder).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return []
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, dict)]


def _enqueue(folder: Path, body: dict[str, Any]) -> None:
    row = dict(body)
    row.setdefault("timestamp", int(time.time()))
    rows = _load_queue(folder)
    rows.append(row)
    stored = rows[-QUEUE_CAP:]
    try:
        _queue_path(folder).parent.mkdir(parents=True, exist_ok=True)
        _queue_path(folder).write_text(json.dumps(stored), encoding="utf-8")
    except OSError:
        return


def _post(url: str, body: dict[str, Any], timeout: float, poster: Poster) -> int:
    try:
        return int(poster(url, body, timeout))
    except Exception:
        return 0


def _flush(folder: Path, url: str, timeout: float, poster: Poster) -> None:
    rows = _load_queue(folder)
    if not rows:
        return
    kept: list[dict[str, Any]] = []
    for row in rows:
        status = _post(url, row, timeout, poster)
        if not 200 <= status < 300:
            kept.append(row)
    try:
        _queue_path(folder).write_text(json.dumps(kept[-QUEUE_CAP:]), encoding="utf-8")
    except OSError:
        return


def choose_event(state: dict[str, Any], version: str, explicit: str | None = None) -> str:
    if explicit == "uninstall":
        if state.get("uninstall_reported") is True:
            return ""
        return "uninstall"
    if state.get("install_reported") is not True:
        return "install"
    last = str(state.get("last_version") or "")
    if last and last != version:
        return "update"
    return ""


def _ensure_consent(
    folder: Path,
    state: dict[str, Any],
    env: dict[str, str],
    *,
    stdin_is_tty: bool,
) -> dict[str, Any]:
    if state.get("consented") is True or state.get("consented") is False:
        return state
    if _truthy(env, ACCEPT_ENV):
        state["consented"] = True
        _save_state(folder, state)
        return state
    if not stdin_is_tty:
        return state
    click.echo(_NOTICE, nl=False)
    agreed = click.confirm("Count this install?", default=False)
    state["consented"] = bool(agreed)
    _save_state(folder, state)
    return state


def note_free_run(
    version: str,
    *,
    event: str | None = None,
    env: dict[str, str] | None = None,
    stdin_is_tty: bool | None = None,
    poster: Poster | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Record Consent 1, then POST install, update, or uninstall. Fail-open."""
    try:
        return _note(
            version,
            event=event,
            env=os.environ if env is None else env,
            stdin_is_tty=sys.stdin.isatty() if stdin_is_tty is None else stdin_is_tty,
            poster=poster or _http_post,
            timeout=timeout,
        )
    except Exception:
        return {"ok": True, "skipped": True, "reason": "fail_open"}


def _note(
    version: str,
    *,
    event: str | None,
    env: dict[str, str],
    stdin_is_tty: bool,
    poster: Poster,
    timeout: float,
) -> dict[str, Any]:
    if _truthy(env, SKIP_ENV):
        return {"ok": True, "skipped": True, "reason": "skip"}
    if env.get("PYTEST_CURRENT_TEST") and not str(env.get(HOME_ENV) or "").strip():
        return {"ok": True, "skipped": True, "reason": "test"}
    current = str(version or "").strip()
    if current == "":
        return {"ok": True, "skipped": True, "reason": "no_version"}
    folder = state_dir(env)
    state = _load_state(folder)
    state = _ensure_consent(folder, state, env, stdin_is_tty=stdin_is_tty)
    if state.get("consented") is not True:
        reason = "refused" if state.get("consented") is False else "no_consent"
        return {"ok": True, "skipped": True, "reason": reason}
    chosen = choose_event(state, current, event)
    if chosen == "":
        return {"ok": True, "skipped": True, "reason": "already_reported", "version": current}
    instance = str(state.get("instance_id") or "").strip()
    if instance == "":
        instance = str(uuid.uuid4())
        state["instance_id"] = instance
        _save_state(folder, state)
    url = str(env.get(URL_ENV) or LIFE_URL).strip() or LIFE_URL
    body = {
        "app_id": APP_ID,
        "instance_id": instance,
        "event": chosen,
        "version": current,
        "platform": _platform(),
        "client_type": "pip",
    }
    status = _post(url, body, timeout, poster)
    if 200 <= status < 300:
        _flush(folder, url, timeout, poster)
        state["last_version"] = current
        if chosen == "uninstall":
            state["uninstall_reported"] = True
        else:
            state["install_reported"] = True
        _save_state(folder, state)
        return {"ok": True, "skipped": False, "event": chosen, "status": status}
    if status in (0, 429):
        _enqueue(folder, body)
    return {"ok": False, "skipped": False, "event": chosen, "status": status}
