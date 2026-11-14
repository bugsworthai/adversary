#!/usr/bin/env python3
"""Anonymous, opt-in usage counts for the AdversaryPR skill. See telemetry_constants.py.

Standard library only, Python 3.8+. The payload is built only from the allowlisted
fields in telemetry_constants.PAYLOAD_KEYS. Sending never raises and never prints.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import telemetry_constants as C
except ImportError:  # run from another folder by path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import telemetry_constants as C


def state_file() -> Path:
    return Path.home() / C.STATE_DIR_NAME / C.STATE_FILE_NAME


def env_forces_off() -> bool:
    if os.environ.get(C.ENV_TELEMETRY, "").strip().lower() in C.ENV_TELEMETRY_OFF_VALUES:
        return True
    return os.environ.get(C.ENV_DO_NOT_TRACK, "").strip().lower() in C.ENV_DO_NOT_TRACK_ON_VALUES


def read_consent() -> str:
    """ask, on, or off. An environment switch means off and never ask."""
    if env_forces_off():
        return C.OFF
    try:
        data = json.loads(state_file().read_text(encoding=C.ENCODING))
        value = data.get(C.CONSENT_KEY)
    except (OSError, ValueError, AttributeError):
        return C.ASK
    return value if value in (C.ON, C.OFF) else C.ASK


def write_consent(value: str) -> None:
    path = state_file()
    path.parent.mkdir(mode=C.STATE_DIR_MODE, parents=True, exist_ok=True)
    os.chmod(str(path.parent), C.STATE_DIR_MODE)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, C.STATE_FILE_MODE)
    with os.fdopen(fd, "w", encoding=C.ENCODING) as f:
        json.dump({C.CONSENT_KEY: value}, f)
    os.chmod(str(path), C.STATE_FILE_MODE)


def build_payload(version: str, dry_run: bool = False, html: bool = False,
                  model: str = C.MODEL_DEFAULT, pinned: bool = False) -> dict:
    if not isinstance(version, str) or not re.fullmatch(C.VERSION_PATTERN, version, re.ASCII):
        raise ValueError(C.ERR_BAD_VERSION)
    if model not in C.MODELS:
        raise ValueError(C.ERR_BAD_MODEL)
    payload = {
        C.KEY_SCHEMA: C.SCHEMA_VERSION,
        C.KEY_EVENT: C.EVENT_RUN,
        C.KEY_VERSION: version,
        C.KEY_DRY_RUN: bool(dry_run),
        C.KEY_HTML: bool(html),
        C.KEY_MODEL: model,
        C.KEY_VERSION_PINNED: bool(pinned),
    }
    assert tuple(payload) == C.PAYLOAD_KEYS
    return payload


def counter_id(payload: dict, now=None) -> str:
    """The id of the one counter this run adds to: day, version, model, and three 0/1 option flags."""
    now = now or datetime.now(timezone.utc)
    flags = "".join("1" if payload[k] else "0" for k in (C.KEY_DRY_RUN, C.KEY_HTML, C.KEY_VERSION_PINNED))
    version = payload[C.KEY_VERSION].replace(C.DOT, C.DOT_REPLACEMENT)
    return C.ID_JOINER.join((now.strftime(C.DAY_FORMAT), version, payload[C.KEY_MODEL], flags))


def build_request(payload: dict, now=None) -> dict:
    """The Firestore commit body: raise one counter by one. Nothing from the payload except its id."""
    name = C.FIRESTORE_DOC_PATH % (C.FIRESTORE_PROJECT, C.FIRESTORE_COLLECTION, counter_id(payload, now))
    return {
        "writes": [{
            "update": {"name": name},
            "updateMask": {"fieldPaths": []},
            "updateTransforms": [{"fieldPath": C.FIRESTORE_FIELD, "increment": {"integerValue": "1"}}],
        }]
    }


def send(payload: dict) -> bool:
    """Raise the counter by one. Returns True on success. Swallows every error."""
    try:
        body = json.dumps(build_request(payload)).encode(C.ENCODING)
        req = urllib.request.Request(C.ENDPOINT_URL, data=body, method=C.HTTP_METHOD)
        req.add_header(C.CONTENT_TYPE_HEADER, C.CONTENT_TYPE_JSON)
        with urllib.request.urlopen(req, timeout=C.TIMEOUT_SECONDS) as resp:
            resp.read()
        return True
    except BaseException:  # noqa: B902 - nothing here may break a review
        return False


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=C.PROG, description=C.DESCRIPTION)
    sub = p.add_subparsers(dest=C.DEST_COMMAND)
    sub.add_parser(C.CMD_STATUS, help=C.HELP_STATUS)
    s = sub.add_parser(C.CMD_SET, help=C.HELP_SET)
    s.add_argument(C.DEST_VALUE, choices=(C.ON, C.OFF), help=C.HELP_SET_VALUE)
    for name, helptext in ((C.CMD_PREVIEW, C.HELP_PREVIEW), (C.CMD_SEND, C.HELP_SEND)):
        c = sub.add_parser(name, help=helptext)
        c.add_argument(C.FLAG_VERSION, dest=C.DEST_VERSION, required=True, help=C.HELP_VERSION)
        c.add_argument(C.FLAG_DRY_RUN, dest=C.DEST_DRY_RUN, action="store_true", help=C.HELP_DRY_RUN)
        c.add_argument(C.FLAG_HTML, dest=C.DEST_HTML, action="store_true", help=C.HELP_HTML)
        c.add_argument(C.FLAG_MODEL, dest=C.DEST_MODEL, default=C.MODEL_DEFAULT, help=C.HELP_MODEL)
        c.add_argument(C.FLAG_PINNED, dest=C.DEST_PINNED, action="store_true", help=C.HELP_PINNED)
    return p


def run_send(argv) -> int:
    try:
        args = make_parser().parse_args(argv)
        if read_consent() != C.ON:
            return C.EXIT_OK
        payload = build_payload(args.version, args.dry_run, args.html, args.model, args.pinned)
        send(payload)
    except BaseException:  # noqa: B902 - includes argparse's SystemExit
        pass
    return C.EXIT_OK


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == C.CMD_SEND:
        return run_send(argv)
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.command == C.CMD_STATUS:
        print(read_consent())
    elif args.command == C.CMD_SET:
        try:
            write_consent(args.value)
        except OSError:
            print(C.ERR_STATE_WRITE, file=sys.stderr)
            return C.EXIT_USAGE
        print(C.MSG_SET_ON if args.value == C.ON else C.MSG_SET_OFF)
        if env_forces_off():
            print(C.MSG_ENV_OFF)
    elif args.command == C.CMD_PREVIEW:
        try:
            payload = build_payload(args.version, args.dry_run, args.html, args.model, args.pinned)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return C.EXIT_USAGE
        print(json.dumps(build_request(payload), indent=C.JSON_INDENT))
    else:
        parser.print_help()
        return C.EXIT_USAGE
    return C.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
