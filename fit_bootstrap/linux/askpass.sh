#!/bin/sh

if [ -z "${FIT_LINUX_ASKPASS_PYTHON:-}" ]; then
  exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)

if [ "${FIT_LINUX_ASKPASS_BUNDLED:-0}" = "1" ]; then
  password=$(FIT_LINUX_ASKPASS_DIALOG=1 "$FIT_LINUX_ASKPASS_PYTHON")
else
  password=$(
    PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" \
      "$FIT_LINUX_ASKPASS_PYTHON" -m fit_bootstrap.linux.askpass_dialog
  )
fi

if [ -z "$password" ]; then
  exit 1
fi

printf '%s\n' "$password"
