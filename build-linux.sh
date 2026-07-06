#!/usr/bin/env bash
set -Eeuo pipefail

ARCH="$(uname -m)"
PYTHON_VERSION="${PYTHON_VERSION:-3.14.5}"

VENV_DIR="${VENV_DIR:-.venv-linux-${ARCH}-${PYTHON_VERSION}}"

BUILD_BASE_DIR="${BUILD_BASE_DIR:-build}"
BUILD_DIR="${BUILD_DIR:-${BUILD_BASE_DIR}/nuitka-linux-${ARCH}-$(date +%Y%m%d-%H%M%S)}"

OUT_DIR="${OUT_DIR:-dist-nuitka-onefile}"
DIST_DIR="${DIST_DIR:-dist}"
APP_NAME="${APP_NAME:-LinSoTracker}"
APP_VERSION=""
SYSTEM_VERSION=""
PACKAGE_VERSION=""

cd "$(dirname "$0")"

log() {
    printf '[build-linux] %s\n' "$*" >&2
}

fail() {
    printf '[build-linux] ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

install_linux_package() {
    local package="$1"

    if command -v apt-get >/dev/null 2>&1; then
        log "Installing ${package} with apt-get"
        sudo apt-get update
        sudo apt-get install -y "$package"
        return
    fi

    if command -v dnf >/dev/null 2>&1; then
        log "Installing ${package} with dnf"
        sudo dnf install -y "$package"
        return
    fi

    if command -v yum >/dev/null 2>&1; then
        log "Installing ${package} with yum"
        sudo yum install -y "$package"
        return
    fi

    if command -v pacman >/dev/null 2>&1; then
        log "Installing ${package} with pacman"
        sudo pacman -Sy --noconfirm "$package"
        return
    fi

    if command -v zypper >/dev/null 2>&1; then
        log "Installing ${package} with zypper"
        sudo zypper --non-interactive install "$package"
        return
    fi

    fail "Missing ${package}. Install it manually, e.g. sudo apt install ${package}."
}

ensure_command() {
    local command_name="$1"
    local package_name="${2:-$1}"

    if command -v "$command_name" >/dev/null 2>&1; then
        return
    fi

    install_linux_package "$package_name"
    command -v "$command_name" >/dev/null 2>&1 || fail "${command_name} is still missing after installing ${package_name}."
}

copy_dir_to_dist() {
    local source_dir="$1"
    local dist_path="$2"

    if [[ -d "$source_dir" ]]; then
        log "Copying directory into dist: ${source_dir}"
        rm -rf "${dist_path}/${source_dir}"
        mkdir -p "${dist_path}"
        cp -R "${source_dir}" "${dist_path}/"
    fi
}

copy_file_to_dist() {
    local source_file="$1"
    local dist_path="$2"

    if [[ -f "$source_file" ]]; then
        log "Copying file into dist: ${source_file}"
        mkdir -p "${dist_path}"
        cp -f "${source_file}" "${dist_path}/"
    fi
}

clean_old_builds_safe() {
    mkdir -p "$BUILD_BASE_DIR"

    log "Keeping previous build folders. Current build dir: ${BUILD_DIR}"

    find "$BUILD_BASE_DIR" \
        -maxdepth 1 \
        -type d \
        -name "nuitka-linux-*" \
        -mtime +7 \
        -exec rm -rf {} + 2>/dev/null || true
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

[[ "$(uname -s)" == "Linux" ]] || fail "This script must run on Linux."
ensure_command patchelf patchelf

PYTHON="$(resolve_python)"

ACTUAL_VERSION="$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
[[ "$ACTUAL_VERSION" == "$PYTHON_VERSION" ]] || fail "Expected Python ${PYTHON_VERSION}, got ${ACTUAL_VERSION} from ${PYTHON}"

"$PYTHON" -c 'import ssl; print(ssl.OPENSSL_VERSION)' >/dev/null 2>&1 || fail "Python SSL module is missing from ${PYTHON}"
"$PYTHON" -c 'import tkinter' >/dev/null 2>&1 || fail "Python tkinter module is missing from ${PYTHON}"

log "Using Python: ${PYTHON}"

log "Creating venv: ${VENV_DIR}"
rm -rf "$VENV_DIR"
"$PYTHON" -m venv "$VENV_DIR"

source "${VENV_DIR}/bin/activate"

APP_VERSION="$(python Tools/sync_version.py --print-version)"
SYSTEM_VERSION="$(python Tools/sync_version.py --print-system-version)"
PACKAGE_VERSION="$(printf '%s' "$APP_VERSION" | tr -c 'A-Za-z0-9._-' '-')"
log "App version: ${APP_VERSION} (system metadata: ${SYSTEM_VERSION})"

log "Installing Python dependencies"
python -m pip install --upgrade pip setuptools wheel

if [[ -f requirements.txt ]]; then
    python -m pip install -r requirements.txt
else
    log "requirements.txt not found, skipping"
fi

log "Installing Nuitka from develop branch (same as Windows build)"
python -m pip install --upgrade --force-reinstall "https://github.com/Nuitka/Nuitka/archive/develop.zip"

DATA_ARGS=()
[[ -d templates ]] && DATA_ARGS+=(--include-data-dir=templates=templates)
[[ -d ressources ]] && DATA_ARGS+=(--include-data-dir=ressources=ressources)
[[ -d resources ]] && DATA_ARGS+=(--include-data-dir=resources=resources)
[[ -d default_saves ]] && DATA_ARGS+=(--include-data-dir=default_saves=default_saves)
[[ -d extensions ]] && DATA_ARGS+=(--include-data-dir=extensions=extensions)
[[ -d plugins ]] && DATA_ARGS+=(--include-data-dir=plugins=plugins)
[[ -d seeds ]] && DATA_ARGS+=(--include-data-dir=seeds=seeds)

[[ -f tracker.data ]] && DATA_ARGS+=(--include-data-file=tracker.data=tracker.data)
[[ -f .dev ]] && DATA_ARGS+=(--include-data-file=.dev=.dev)
[[ -f config.ini ]] && DATA_ARGS+=(--include-data-file=config.ini=config.ini)
[[ -f settings.ini ]] && DATA_ARGS+=(--include-data-file=settings.ini=settings.ini)
[[ -f settings.json ]] && DATA_ARGS+=(--include-data-file=settings.json=settings.json)

ICON_ARGS=()
[[ -f icon.png ]] && ICON_ARGS+=(--linux-icon=icon.png)

log "Building onefile Linux executable with Nuitka"

clean_old_builds_safe
mkdir -p "$BUILD_DIR"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

python -m nuitka \
    --mode=onefile \
    --assume-yes-for-downloads \
    --remove-output \
    --enable-plugin=tk-inter \
    --include-package-data=pygame_gui \
    --output-dir="$OUT_DIR" \
    --output-filename="$APP_NAME" \
    --product-name="$APP_NAME" \
    --product-version="$SYSTEM_VERSION" \
    --file-version="$SYSTEM_VERSION" \
    "${ICON_ARGS[@]}" \
    "${DATA_ARGS[@]}" \
    LinSoTracker.py

BIN_PATH="${OUT_DIR}/${APP_NAME}.bin"
[[ -f "$BIN_PATH" ]] || BIN_PATH="${OUT_DIR}/${APP_NAME}"
[[ -f "$BIN_PATH" ]] || fail "Could not find ${APP_NAME} executable in ${OUT_DIR}"
if [[ "$BIN_PATH" != "${OUT_DIR}/${APP_NAME}" ]]; then
    mv -f "$BIN_PATH" "${OUT_DIR}/${APP_NAME}"
fi
chmod +x "${OUT_DIR}/${APP_NAME}"

log "Copying external runtime files next to the executable"
copy_dir_to_dist "templates" "$OUT_DIR"
copy_dir_to_dist "default_saves" "$OUT_DIR"
copy_dir_to_dist "devtemplates" "$OUT_DIR"

copy_file_to_dist "tracker.data" "$OUT_DIR"
copy_file_to_dist ".dev" "$OUT_DIR"

PACKAGE_NAME="${APP_NAME}-${PACKAGE_VERSION}-linux-${ARCH}"
OUTPUT_PATH="${DIST_DIR}/${PACKAGE_NAME}"

log "Packaging ${PACKAGE_NAME}"

rm -rf "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH"

cp -R "$OUT_DIR"/. "$OUTPUT_PATH/"

log "Package content:"
find "$OUTPUT_PATH" -maxdepth 2 -print >&2 || true

(
    cd "$DIST_DIR"
    if command -v zip >/dev/null 2>&1; then
        rm -f "${PACKAGE_NAME}.zip"
        zip -qr "${PACKAGE_NAME}.zip" "$PACKAGE_NAME"
        log "Done: ${DIST_DIR}/${PACKAGE_NAME}.zip"
    else
        rm -f "${PACKAGE_NAME}.tar.gz"
        tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
        log "Done: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz"
    fi
)

log "App: ${OUT_DIR}/${APP_NAME}"
