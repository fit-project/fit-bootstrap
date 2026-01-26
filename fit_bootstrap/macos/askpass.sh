#!/bin/sh

pw=$(
  /usr/bin/osascript <<'APPLESCRIPT'
tell application "System Events"
    activate
    try
        display dialog "FIT Bootstrap needs administrator privileges." default answer "" with hidden answer buttons {"Cancel", "OK"} default button "OK"
        text returned of result
    on error number -128
        return ""
    end try
end tell
APPLESCRIPT
)

if [ -z "$pw" ]; then
  exit 1
fi

printf "%s\n" "$pw"
