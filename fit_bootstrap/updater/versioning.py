from __future__ import annotations

import re

from packaging.version import InvalidVersion, Version


def extract_version_from_tag(tag_name: str) -> str:
    normalized = tag_name.strip().lower()
    if normalized.startswith("v."):
        normalized = normalized[2:]
    elif normalized.startswith("v"):
        normalized = normalized[1:]
    return normalized.split("+", 1)[0]


def normalize_version_for_compare(value: str) -> str:
    raw = extract_version_from_tag(value)
    if not raw:
        return ""

    try:
        return str(Version(raw))
    except InvalidVersion:
        pass

    match = re.fullmatch(r"(?P<core>\d+\.\d+\.\d+)-(?P<pre>[0-9a-z.-]+)", raw)
    if match is None:
        return ""

    core = match.group("core")
    prerelease = match.group("pre")
    prerelease_match = re.fullmatch(
        r"(?P<label>alpha|a|beta|b|rc|pre|preview)[.-]?(?P<num>\d+)?",
        prerelease,
    )
    if prerelease_match is None:
        return ""

    label = prerelease_match.group("label")
    number = prerelease_match.group("num") or "0"
    mapped = {
        "alpha": "a",
        "a": "a",
        "beta": "b",
        "b": "b",
        "rc": "rc",
        "pre": "rc",
        "preview": "rc",
    }[label]
    candidate = f"{core}{mapped}{number}"
    try:
        return str(Version(candidate))
    except InvalidVersion:
        return ""


def is_newer_than_local(
    remote_version: str,
    *,
    get_local_version_fn,
    normalize_version_for_compare_fn,
) -> bool:
    local_version = normalize_version_for_compare_fn(get_local_version_fn())
    normalized_remote = normalize_version_for_compare_fn(remote_version)
    if not local_version or not normalized_remote:
        return False
    try:
        return Version(normalized_remote) > Version(local_version)
    except InvalidVersion:
        return False


def normalized_arch(machine: str) -> str:
    normalized = machine.strip().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "aarch64": "arm64",
    }
    return aliases.get(normalized, normalized)


def expected_suffix(current_platform: str) -> str | None:
    if current_platform == "macos":
        return ".dmg"
    if current_platform == "win":
        return ".exe"
    if current_platform == "lin":
        return ".appimage"
    return None
