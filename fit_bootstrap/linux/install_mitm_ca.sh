#!/bin/sh

set -eu

target=/usr/local/share/ca-certificates/fit-mitmproxy-ca.crt
install_bin=/usr/bin/install
update_ca_bin=/usr/sbin/update-ca-certificates

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "usage: install_mitm_ca.sh /absolute/path/to/mitmproxy-ca-cert.pem" >&2
  exit 2
fi

case "$1" in
  /*) source=$1 ;;
  *)
    echo "certificate path must be absolute" >&2
    exit 2
    ;;
esac

if [ ! -x "$install_bin" ] || [ ! -x "$update_ca_bin" ]; then
  echo "required Debian certificate tools are unavailable" >&2
  exit 3
fi

"$install_bin" -o root -g root -m 0644 -- "$source" "$target"
"$update_ca_bin"
