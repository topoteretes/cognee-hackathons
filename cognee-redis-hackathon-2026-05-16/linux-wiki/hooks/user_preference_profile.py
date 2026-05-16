#!/usr/bin/env python3
"""Build a Linux preference profile from user or community messages."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

DEFAULT_PROFILE_NAMESPACE = "profile"
DEFAULT_UPSTASH_REST_TOKEN_ENV = "UPSTASH_REDIS_REST_TOKEN"
DEFAULT_UPSTASH_REST_URL_ENV = "UPSTASH_REDIS_REST_URL"
DEFAULT_USER_ID = "default"
ENCODING = "utf-8"
ENV_FILES = (Path(".env"), Path("hooks/.env"))
SUMMARY_DIR = Path("wiki/profile")
PROFILE_ACTIVE_SUFFIX = "active"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SIGNAL_PATTERNS: dict[str, dict[str, list[str]]] = {
    "technical_level": {
        "beginner": [r"\bbeginner\b", r"\bnew to linux\b", r"\bnever used linux\b", r"\bnon[- ]technical\b"],
        "intermediate": [r"\bcomfortable\b", r"\bsome experience\b", r"\bused linux before\b"],
        "advanced": [r"\badvanced\b", r"\bpower user\b", r"\bsysadmin\b", r"\bdevops\b"],
        "developer": [r"\bdeveloper\b", r"\bprogrammer\b", r"\bsoftware engineer\b", r"\bcode\b", r"\bcoding\b"],
    },
    "workloads": {
        "programming": [r"\bprogramming\b", r"\bdevelopment\b", r"\bdeveloper\b", r"\bcoding\b", r"\bide\b"],
        "web_development": [r"\bweb dev\b", r"\bfrontend\b", r"\bbackend\b", r"\bfull[- ]stack\b"],
        "data_science": [r"\bdata science\b", r"\bmachine learning\b", r"\bpython\b", r"\bnotebook\b"],
        "video_editing": [r"\bvideo edit", r"\bresolve\b", r"\bdavinci\b", r"\bkdenlive\b", r"\bpremiere\b"],
        "design": [r"\bdesigner\b", r"\bfigma\b", r"\bgraphics\b", r"\billustration\b"],
        "music_audio": [r"\bmusic production\b", r"\baudio production\b", r"\bdaw\b", r"\bpipewire\b"],
        "gaming": [r"\bgaming\b", r"\bsteam\b", r"\bproton\b"],
        "school": [r"\bschool\b", r"\bstudent\b", r"\bcollege\b", r"\bclass\b"],
        "office": [r"\boffice\b", r"\bspreadsheets?\b", r"\bdocuments?\b", r"\blibreoffice\b"],
    },
    "interests": {
        "theming": [r"\btheming\b", r"\bthemes?\b", r"\brice\b", r"\bwallpapers?\b", r"\bicons?\b"],
        "window_managers": [r"\bwindow manager\b", r"\btiling\b", r"\bhyprland\b", r"\bi3\b", r"\bsway\b"],
        "desktop_polish": [r"\bpolished\b", r"\bpretty\b", r"\bbeautiful\b", r"\bmodern desktop\b"],
        "automation": [r"\bautomation\b", r"\bscripts?\b", r"\bshell scripts?\b"],
        "privacy": [r"\bprivacy\b", r"\bprivate\b", r"\btelemetry\b"],
        "open_source": [r"\bopen source\b", r"\bfoss\b", r"\bfree software\b"],
        "hardware_support": [r"\bhardware support\b", r"\bdrivers?\b", r"\bperipherals?\b"],
    },
    "priorities": {
        "stability": [r"\bstable\b", r"\breliable\b", r"\bdoesn't break\b", r"\blts\b"],
        "low_maintenance": [r"\blow maintenance\b", r"\bjust works\b", r"\bstay out of the way\b"],
        "learning": [r"\blearn\b", r"\bunderstand\b", r"\btinker\b"],
        "aesthetics": [r"\bpolished\b", r"\bpretty\b", r"\brice\b", r"\bcustomi[sz]e\b", r"\btheming\b"],
        "speed": [r"\bfast\b", r"\blightweight\b", r"\bsnappy\b"],
        "control": [r"\bcontrol\b", r"\bconfigure\b", r"\bmanual\b"],
    },
    "hardware": {
        "nvidia": [r"\bnvidia\b", r"\brtx\b", r"\bgtx\b"],
        "amd_gpu": [r"\bamd gpu\b", r"\bradeon\b"],
        "intel_gpu": [r"\bintel graphics\b", r"\bintel gpu\b"],
        "laptop": [r"\blaptop\b", r"\bnotebook\b"],
        "hidpi": [r"\bhidpi\b", r"\bfractional scaling\b", r"\b4k\b"],
    },
    "comfort": {
        "terminal_ok": [r"\bterminal\b", r"\bcli\b", r"\bcommand line\b"],
        "terminal_avoid": [r"\bavoid terminal\b", r"\bdon't want.*terminal\b", r"\bgui only\b"],
        "debugging_ok": [r"\bdebug\b", r"\bfix things\b", r"\btroubleshoot\b"],
        "debugging_avoid": [r"\bdon't want.*debug\b", r"\bavoid debugging\b", r"\bno breakage\b"],
        "tinkering_ok": [r"\btinker\b", r"\bconfigure\b", r"\bmanual setup\b", r"\bbuild.*my setup\b"],
        "tinkering_avoid": [r"\bdon't want.*tinker\b", r"\bno tinkering\b", r"\bjust works\b"],
    },
    "preferences": {
        "wayland": [r"\bwayland\b"],
        "x11": [r"\bx11\b", r"\bxorg\b"],
        "kde": [r"\bkde\b", r"\bplasma\b"],
        "gnome": [r"\bgnome\b"],
        "cosmic": [r"\bcosmic\b"],
        "hyprland": [r"\bhyprland\b"],
        "arch": [r"\barch\b"],
        "fedora": [r"\bfedora\b"],
        "debian": [r"\bdebian\b"],
        "ubuntu": [r"\bubuntu\b"],
        "nixos": [r"\bnixos\b", r"\bnix\b"],
        "pop_os": [r"\bpop![_ ]?os\b", r"\bpop os\b"],
    },
}


@dataclass(frozen=True)
class Message:
    text: str
    source: str | None = None
    created_at: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


def load_env_files() -> None:
    for env_file in ENV_FILES:
        if not env_file.exists():
            continue

        load_dotenv(env_file)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def score_signals(messages: list[Message]) -> dict[str, dict[str, int]]:
    scores: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for message in messages:
        text = normalize_text(message.text)
        for group, signals in SIGNAL_PATTERNS.items():
            for signal, patterns in signals.items():
                if any(re.search(pattern, text) for pattern in patterns):
                    scores[group][signal] += 1

    return {group: dict(group_scores) for group, group_scores in scores.items()}


def build_profile(user_id: str, messages: list[Message]) -> dict[str, Any]:
    profile = {
        "user_id": user_id,
        "updated_at": utc_now(),
        "message_count": len(messages),
        "signals": score_signals(messages),
        "evidence": [
            {
                "text": message.text,
                "source": message.source,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }
    return profile


def safe_profile_id(user_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", user_id.strip()).strip("-").lower()
    return safe_id or DEFAULT_USER_ID


def title_text(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def signal_summary(signals: dict[str, dict[str, int]], group: str) -> str:
    group_signals = signals.get(group, {})
    if not group_signals:
        return "Not recorded"

    ranked = sorted(group_signals.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(title_text(signal) for signal, _score in ranked)


def profile_summary_markdown(profile: dict[str, Any]) -> str:
    user_id = str(profile["user_id"])
    safe_id = safe_profile_id(user_id)
    updated_at = str(profile["updated_at"])
    last_checked = updated_at.split("T", maxsplit=1)[0]
    signals = profile.get("signals", {})

    lines = [
        "---",
        f"title: Profile: {user_id}",
        "type: profile",
        "status: seed",
        f"last_checked: {last_checked}",
        "sources: []",
        "tags: [profile]",
        "---",
        "",
        f"# Profile: {user_id}",
        "",
        "Brief summary of the Redis-backed user preference profile.",
        "",
        "## Summary",
        "",
        f"- Technical level: {signal_summary(signals, 'technical_level')}",
        f"- Workloads: {signal_summary(signals, 'workloads')}",
        f"- Interests: {signal_summary(signals, 'interests')}",
        f"- Hardware: {signal_summary(signals, 'hardware')}",
        f"- Comfort: {signal_summary(signals, 'comfort')}",
        f"- Priorities: {signal_summary(signals, 'priorities')}",
        f"- Linux preferences: {signal_summary(signals, 'preferences')}",
        "",
        "## Metadata",
        "",
        f"- Profile id: `{safe_id}`",
        f"- Message count: {profile.get('message_count', 0)}",
        f"- Updated: {updated_at}",
        "",
    ]
    return "\n".join(lines)


def save_profile_summary(profile: dict[str, Any]) -> Path:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = SUMMARY_DIR / f"{safe_profile_id(str(profile['user_id']))}.md"
    summary_path.write_text(profile_summary_markdown(profile), encoding=ENCODING)
    return summary_path


def delete_profile_summary(user_id: str) -> bool:
    summary_path = SUMMARY_DIR / f"{safe_profile_id(user_id)}.md"
    if not summary_path.exists():
        return False

    summary_path.unlink()
    return True


def read_messages(stream: Any) -> list[Message]:
    messages: list[Message] = []

    for line in stream:
        raw_line = line.strip()
        if not raw_line:
            continue

        payload = json.loads(raw_line)
        text = str(payload.get("text", "")).strip()
        if text:
            messages.append(
                Message(
                    text=text,
                    source=payload.get("source"),
                    created_at=payload.get("created_at"),
                )
            )

    return messages


def profile_key(namespace: str, user_id: str) -> str:
    return f"{namespace}:{user_id}"


def active_profile_key(namespace: str) -> str:
    return profile_key(namespace, PROFILE_ACTIVE_SUFFIX)


def upstash_command(rest_url: str, rest_token: str, command: list[Any]) -> Any:
    body = json.dumps(command).encode(ENCODING)
    request = Request(
        rest_url.rstrip("/"),
        data=body,
        headers={
            "Authorization": f"Bearer {rest_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode(ENCODING))
    except HTTPError as error:
        detail = error.read().decode(ENCODING)
        raise RuntimeError(f"Upstash request failed with HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Upstash: {error.reason}") from error

    if payload.get("error"):
        raise RuntimeError(f"Upstash command failed: {payload['error']}")

    return payload.get("result")


def require_upstash(args: argparse.Namespace) -> tuple[str, str]:
    if args.upstash_rest_url and args.upstash_rest_token:
        return args.upstash_rest_url, args.upstash_rest_token

    raise RuntimeError(
        "Upstash credentials are required. Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN."
    )


def save_profile_upstash(profile: dict[str, Any], rest_url: str, rest_token: str, namespace: str) -> None:
    key = profile_key(namespace, profile["user_id"])
    upstash_command(rest_url, rest_token, ["SET", key, json.dumps(profile, ensure_ascii=False)])


def get_profile_upstash(user_id: str, rest_url: str, rest_token: str, namespace: str) -> dict[str, Any] | None:
    value = upstash_command(rest_url, rest_token, ["GET", profile_key(namespace, user_id)])
    if value is None:
        return None

    return json.loads(value)


def get_active_profile_id(rest_url: str, rest_token: str, namespace: str) -> str | None:
    value = upstash_command(rest_url, rest_token, ["GET", active_profile_key(namespace)])
    return str(value) if value else None


def select_profile_upstash(user_id: str, rest_url: str, rest_token: str, namespace: str) -> dict[str, Any]:
    profile = get_profile_upstash(user_id, rest_url, rest_token, namespace)
    if profile is None:
        raise RuntimeError(f"Profile does not exist: {user_id}")

    upstash_command(rest_url, rest_token, ["SET", active_profile_key(namespace), user_id])
    return {"selected_profile": user_id, "profile": profile}


def delete_profile_upstash(user_id: str, rest_url: str, rest_token: str, namespace: str) -> dict[str, Any]:
    active_user_id = get_active_profile_id(rest_url, rest_token, namespace)
    deleted = upstash_command(rest_url, rest_token, ["DEL", profile_key(namespace, user_id)])

    if active_user_id == user_id:
        upstash_command(rest_url, rest_token, ["DEL", active_profile_key(namespace)])

    return {"deleted_profile": user_id, "deleted_count": deleted, "was_active": active_user_id == user_id}


def list_profiles_upstash(rest_url: str, rest_token: str, namespace: str) -> dict[str, Any]:
    keys = upstash_command(rest_url, rest_token, ["KEYS", profile_key(namespace, "*")]) or []
    active_user_id = get_active_profile_id(rest_url, rest_token, namespace)
    profile_ids = sorted(
        key.removeprefix(f"{namespace}:")
        for key in keys
        if key != active_profile_key(namespace)
    )
    return {"active_profile": active_user_id, "profiles": profile_ids}


def handle_create(args: argparse.Namespace) -> dict[str, Any]:
    messages = read_messages(sys.stdin)
    profile = build_profile(args.user_id, messages)
    summary_path = save_profile_summary(profile)

    if args.upstash_rest_url and args.upstash_rest_token:
        save_profile_upstash(profile, args.upstash_rest_url, args.upstash_rest_token, args.namespace)

    profile["summary_path"] = str(summary_path)
    return profile


def handle_select(args: argparse.Namespace) -> dict[str, Any]:
    rest_url, rest_token = require_upstash(args)
    result = select_profile_upstash(args.user_id, rest_url, rest_token, args.namespace)
    result["summary_path"] = str(save_profile_summary(result["profile"]))
    return result


def handle_delete(args: argparse.Namespace) -> dict[str, Any]:
    rest_url, rest_token = require_upstash(args)
    result = delete_profile_upstash(args.user_id, rest_url, rest_token, args.namespace)
    result["summary_deleted"] = delete_profile_summary(args.user_id)
    return result


def handle_get(args: argparse.Namespace) -> dict[str, Any]:
    rest_url, rest_token = require_upstash(args)
    user_id = args.user_id or get_active_profile_id(rest_url, rest_token, args.namespace)
    if not user_id:
        raise RuntimeError("No profile selected. Pass --user-id or run the select command first.")

    profile = get_profile_upstash(user_id, rest_url, rest_token, args.namespace)
    if profile is None:
        raise RuntimeError(f"Profile does not exist: {user_id}")

    profile["summary_path"] = str(save_profile_summary(profile))
    return profile


def handle_list(args: argparse.Namespace) -> dict[str, Any]:
    rest_url, rest_token = require_upstash(args)
    return list_profiles_upstash(rest_url, rest_token, args.namespace)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Linux user preference profiles.")
    parser.add_argument("--namespace", default=DEFAULT_PROFILE_NAMESPACE)
    parser.add_argument("--upstash-rest-url", default=os.getenv(DEFAULT_UPSTASH_REST_URL_ENV))
    parser.add_argument("--upstash-rest-token", default=os.getenv(DEFAULT_UPSTASH_REST_TOKEN_ENV))
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create or overwrite a profile from JSON lines.")
    create_parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    create_parser.set_defaults(handler=handle_create)

    select_parser = subparsers.add_parser("select", help="Select an existing profile.")
    select_parser.add_argument("user_id")
    select_parser.set_defaults(handler=handle_select)

    delete_parser = subparsers.add_parser("delete", help="Delete an existing profile.")
    delete_parser.add_argument("user_id")
    delete_parser.set_defaults(handler=handle_delete)

    get_parser = subparsers.add_parser("get", help="Get a profile by id, or the selected profile.")
    get_parser.add_argument("--user-id")
    get_parser.set_defaults(handler=handle_get)

    list_parser = subparsers.add_parser("list", help="List stored profiles.")
    list_parser.set_defaults(handler=handle_list)

    parser.set_defaults(command="create", handler=handle_create, user_id=DEFAULT_USER_ID)
    return parser.parse_args()


def main() -> int:
    load_env_files()
    args = parse_args()

    try:
        result = args.handler(args)
    except RuntimeError as error:
        sys.stderr.write(json.dumps({"error": str(error)}, indent=2))
        sys.stderr.write("\n")
        return 1

    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
