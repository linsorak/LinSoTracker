#!/usr/bin/env bash
set -Eeuo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.14.5}"
VENV_DIR="${VENV_DIR:-.venv-linux-${PYTHON_VERSION}}"
BUILD_DIR="${BUILD_DIR:-build/nuitka-linux}"
DIST_DIR="${DIST_DIR:-dist}"
APP_NAME="${APP_NAME:-LinSoTracker}"

cd "$(dirname "$0")"

log() {
    printf '[build-linux] %s\n' "$*" >&2
}

fail() {
    printf '[build-linux] ERROR: %s\n' "$*" >&2
    exit 1
}

resolve_python() {
    if [[ -n "${PYTHON_BIN:-}" ]]; then
        printf '%s\n' "$PYTHON_BIN"
        return
    fi

    if command -v pyenv >/dev/null 2>&1; then
        log "Using pyenv to prepare Python ${PYTHON_VERSION}"
        pyenv install -s "$PYTHON_VERSION" >&2
        printf '%s\n' "$(pyenv root)/versions/${PYTHON_VERSION}/bin/python"
        return
    fi

    if command -v python3.14 >/dev/null 2>&1; then
        command -v python3.14
        return
    fi

    fail "Python ${PYTHON_VERSION} not found. Install it, install pyenv, or run with PYTHON_BIN=/path/to/python."
}

PYTHON="$(resolve_python)"

ACTUAL_VERSION="$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
[[ "$ACTUAL_VERSION" == "$PYTHON_VERSION" ]] || fail "Expected Python ${PYTHON_VERSION}, got ${ACTUAL_VERSION} from ${PYTHON}"

log "Creating venv: ${VENV_DIR}"
"$PYTHON" -m venv "$VENV_DIR"
source "${VENV_DIR}/bin/activate"

log "Installing Python dependencies"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install --no-deps pygame-menu==4.5.2

DATA_ARGS=()
[[ -d templates ]] && DATA_ARGS+=(--include-data-dir=templates=templates)
[[ -d ressources ]] && DATA_ARGS+=(--include-data-dir=ressources=ressources)
[[ -d default_saves ]] && DATA_ARGS+=(--include-data-dir=default_saves=default_saves)
[[ -f tracker.data ]] && DATA_ARGS+=(--include-data-file=tracker.data=tracker.data)
[[ -f .dev ]] && DATA_ARGS+=(--include-data-file=.dev=.dev)

ICON_ARGS=()
[[ -f icon.png ]] && ICON_ARGS+=(--linux-icon=icon.png)

log "Building standalone app with Nuitka"
rm -rf "$BUILD_DIR"
python -m nuitka \
    --standalone \
    --assume-yes-for-downloads \
    --remove-output \
    --enable-plugin=tk-inter \
    --include-package-data=pygame_menu \
    --include-package-data=pygame_gui \
    --output-dir="$BUILD_DIR" \
    --product-name="$APP_NAME" \
    "${ICON_ARGS[@]}" \
    "${DATA_ARGS[@]}" \
    LinSoTracker.py

ARCH="$(uname -m)"
PACKAGE_NAME="${APP_NAME}-linux-${ARCH}"
OUTPUT_PATH="${DIST_DIR}/${PACKAGE_NAME}"

log "Packaging ${PACKAGE_NAME}"
rm -rf "$OUTPUT_PATH"
mkdir -p "$DIST_DIR"
cp -R "${BUILD_DIR}/LinSoTracker.dist" "$OUTPUT_PATH"

if command -v zip >/dev/null 2>&1; then
    (cd "$DIST_DIR" && rm -f "${PACKAGE_NAME}.zip" && zip -qr "${PACKAGE_NAME}.zip" "$PACKAGE_NAME")
    log "Done: ${DIST_DIR}/${PACKAGE_NAME}.zip"
else
    (cd "$DIST_DIR" && rm -f "${PACKAGE_NAME}.tar.gz" && tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME")
    log "Done: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
fi
