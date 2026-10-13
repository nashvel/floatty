#!/usr/bin/env sh
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$app_dir/src/island.py" "$@"
