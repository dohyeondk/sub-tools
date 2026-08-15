#!/usr/bin/env bash

set -Eeuo pipefail

if ! command -v uv >/dev/null 2>&1 && ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to install uv. Install curl and run this script again." >&2
    exit 1
fi

uv_command="$(command -v uv || true)"

if [[ -z "$uv_command" ]]; then
    echo "uv was not found; installing it with Astral's official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    uv_candidates=()
    if [[ -n "${UV_INSTALL_DIR:-}" ]]; then
        uv_candidates+=("${UV_INSTALL_DIR}/uv")
    fi
    if [[ -n "${XDG_BIN_HOME:-}" ]]; then
        uv_candidates+=("${XDG_BIN_HOME}/uv")
    fi
    uv_candidates+=("${HOME}/.local/bin/uv" "${HOME}/.cargo/bin/uv")

    for candidate in "${uv_candidates[@]}"; do
        if [[ -x "$candidate" ]]; then
            uv_command="$candidate"
            break
        fi
    done
fi

if [[ -z "$uv_command" ]]; then
    echo "uv was installed, but its executable could not be located." >&2
    echo "Add uv to PATH and run 'uv sync' manually." >&2
    exit 1
fi

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_directory"

echo "Using $uv_command"
"$uv_command" sync
