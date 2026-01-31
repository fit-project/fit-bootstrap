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

if [ -n "$FIT_ASKPASS_PYTHON" ]; then
  if [ "$log_enabled" -eq 1 ]; then
    echo "askpass: trying pyside" >> "$log"
    echo "askpass: python=$FIT_ASKPASS_PYTHON" >> "$log"
    echo "askpass: form_type_arg=$FIT_ASKPASS_FORM_TYPE_ARGUMENT" >> "$log"
  fi
  case "$FIT_ASKPASS_PYTHON" in
    *".app/Contents/MacOS/"*)
      pw=$(FIT_ASKPASS_DIALOG=1 "$FIT_ASKPASS_PYTHON" "$FIT_ASKPASS_FORM_TYPE_ARGUMENT" 2>>"$log")
      ;;
    *)
      pw=$(PYTHONPATH="$repo_root" "$FIT_ASKPASS_PYTHON" -m fit_bootstrap.macos.askpass_dialog "$FIT_ASKPASS_FORM_TYPE_ARGUMENT" 2>>"$log")
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

if [ -z "$pw" ]; then
  exit 1
fi

printf "%s\n" "$pw"
