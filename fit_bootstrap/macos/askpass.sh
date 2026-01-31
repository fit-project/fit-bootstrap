#!/bin/sh

pw=""
script_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
if [ -n "$FIT_ASKPASS_LOG" ]; then
  log="$FIT_ASKPASS_LOG"
else
  log="/tmp/fit-askpass.log"
fi
log_enabled=0
if [ "$FIT_ASKPASS_DEBUG" = "1" ]; then
  log_enabled=1
fi

if [ "$FIT_ASKPASS_MODE" = "pyside" ] && [ -n "$FIT_ASKPASS_PYTHON" ]; then
  if [ "$log_enabled" -eq 1 ]; then
    echo "askpass: trying pyside" >> "$log"
    echo "askpass: python=$FIT_ASKPASS_PYTHON" >> "$log"
  fi
  case "$FIT_ASKPASS_PYTHON" in
    *".app/Contents/MacOS/"*)
      pw=$(FIT_ASKPASS_DIALOG=1 "$FIT_ASKPASS_PYTHON" 2>>"$log")
      ;;
    *)
      pw=$(PYTHONPATH="$repo_root" "$FIT_ASKPASS_PYTHON" -m fit_bootstrap.macos.askpass_dialog 2>>"$log")
      ;;
  esac
  if [ "$log_enabled" -eq 1 ]; then
    echo "askpass: pyside rc=$?" >> "$log"
  fi
  if [ -z "$pw" ]; then
    if [ "$log_enabled" -eq 1 ]; then
      echo "askpass: pyside produced no password" >> "$log"
    fi
  fi
fi

if [ -z "$pw" ] && [ "$FIT_ASKPASS_MODE" = "applescript" ]; then
  if [ "$log_enabled" -eq 1 ]; then
    echo "askpass: trying applescript" >> "$log"
  fi
  askpass_python="${FIT_ASKPASS_PYTHON:-/usr/bin/python3}"
  pw=$(
    FIT_ASKPASS_SCRIPT_DIR="$script_dir" \
    PYTHONPATH="$repo_root" \
    "$askpass_python" - <<'PY' 2>>"$log"
import html
import os
import re
import subprocess
import sys

from fit_bootstrap.lang import load_translations

t = load_translations()
msg = t.get("ASKPASS_DIALOG_MESSAGE", "")
msg = msg.replace("<br/>", "\n").replace("<br />", "\n")
msg = re.sub(r"</p>\s*<p[^>]*>", "\n\n", msg)
msg = re.sub(r"<[^>]+>", "", msg)
msg = html.unescape(msg)
title = t.get("ASKPASS_DIALOG_TITLE", "Installazione certificato mitmproxy")
cancel = t.get("CANCEL_BUTTON", "Annulla")
ok = t.get("OK_BUTTON", "Ok")

script_dir = os.environ.get("FIT_ASKPASS_SCRIPT_DIR", ".")
script_path = os.path.join(script_dir, "askpass.applescript")
result = subprocess.run(
    ["osascript", script_path, msg, title, cancel, ok],
    stdout=subprocess.PIPE,
    stderr=sys.stderr,
    text=True,
)
sys.stdout.write(result.stdout)
sys.exit(result.returncode)
PY
  )
  if [ "$?" -ne 0 ]; then
    if [ "$log_enabled" -eq 1 ]; then
      echo "askpass: applescript python helper failed, falling back to plain osascript" >> "$log"
    fi
    pw=$(osascript "$script_dir/askpass.applescript" 2>>"$log")
  fi
  if [ "$log_enabled" -eq 1 ]; then
    echo "askpass: applescript rc=$?" >> "$log"
  fi
fi

if [ -z "$pw" ]; then
  exit 1
fi

printf "%s\n" "$pw"
