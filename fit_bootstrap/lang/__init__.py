import json
import locale
import os
import subprocess
import sys
from pathlib import Path

LANG_DIR = Path(__file__).parent
DEFAULT_LANG = "en"


def _normalize_lang(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = cleaned.split(".")[0].replace("-", "_")
    return cleaned.split("_")[0].lower() if cleaned else None


def get_system_lang():
    try:
        if sys.platform == "darwin":
            try:
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleLanguages"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        line = line.strip().strip('",')
                        if line and line not in ("(", ")"):
                            normalized = _normalize_lang(line)
                            if normalized:
                                return normalized
            except Exception:
                pass
            try:
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleLocale"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    normalized = _normalize_lang(result.stdout.strip())
                    if normalized:
                        return normalized
            except Exception:
                pass
        elif sys.platform == "win32":
            try:
                import ctypes

                lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                win_locale = locale.windows_locale.get(lang_id)
                normalized = _normalize_lang(win_locale)
                if normalized:
                    return normalized
            except Exception:
                pass
        else:
            for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
                normalized = _normalize_lang(os.environ.get(key))
                if normalized:
                    return normalized
        locale.setlocale(locale.LC_ALL, "")
        lang = locale.getlocale()[0]
        normalized = _normalize_lang(lang)
        return normalized or DEFAULT_LANG
    except Exception:
        return DEFAULT_LANG


def load_translations(lang=None):
    lang = lang or get_system_lang()
    filename = f"{lang}.json"
    path = LANG_DIR / filename

    if not path.exists():
        path = LANG_DIR / f"{DEFAULT_LANG}.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
