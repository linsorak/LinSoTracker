#!/usr/bin/env bash
set -Eeuo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.14.5}"
PYTHON_MAJOR_MINOR="${PYTHON_MAJOR_MINOR:-3.14}"

VENV_DIR="${VENV_DIR:-.venv-macos-arm64-${PYTHON_VERSION}}"

BUILD_BASE_DIR="${BUILD_BASE_DIR:-build}"
BUILD_DIR="${BUILD_DIR:-${BUILD_BASE_DIR}/nuitka-macos-arm64-$(date +%Y%m%d-%H%M%S)}"

DIST_DIR="${DIST_DIR:-dist}"
APP_NAME="${APP_NAME:-LinSoTracker}"
APP_VERSION=""
SYSTEM_VERSION=""
MACOS_VERSION=""
PACKAGE_VERSION=""

PYTHON_INSTALL_ROOT="/Library/Frameworks/Python.framework/Versions/${PYTHON_MAJOR_MINOR}"
PYTHON_BIN_DEFAULT="${PYTHON_INSTALL_ROOT}/bin/python3.14"

PYTHON_PKG_URL="${PYTHON_PKG_URL:-https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macos11.pkg}"
PYTHON_PKG_DIR="${PYTHON_PKG_DIR:-.python-downloads}"
PYTHON_PKG_PATH="${PYTHON_PKG_DIR}/python-${PYTHON_VERSION}-macos11.pkg"

cd "$(dirname "$0")"

log() {
    printf '[build-macos] %s\n' "$*" >&2
}

fail() {
    printf '[build-macos] ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

download_file() {
    local url="$1"
    local output="$2"

    mkdir -p "$(dirname "$output")"

    if command -v curl >/dev/null 2>&1; then
        curl -L --fail --retry 3 -o "$output" "$url"
        return
    fi

    if command -v wget >/dev/null 2>&1; then
        wget -O "$output" "$url"
        return
    fi

    fail "Missing curl or wget to download Python."
}

install_python_pkg() {
    require_command installer

    if [[ -x "$PYTHON_BIN_DEFAULT" ]]; then
        local installed_version
        installed_version="$("$PYTHON_BIN_DEFAULT" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || true)"

        if [[ "$installed_version" == "$PYTHON_VERSION" ]]; then
            if "$PYTHON_BIN_DEFAULT" -c 'import ssl, tkinter' >/dev/null 2>&1; then
                log "Python ${PYTHON_VERSION} already installed: ${PYTHON_BIN_DEFAULT}"
                return
            fi

            log "Python exists but ssl/tkinter check failed, reinstalling official package"
        else
            log "Python found but version is ${installed_version:-unknown}; expected ${PYTHON_VERSION}"
        fi
    fi

    if [[ ! -f "$PYTHON_PKG_PATH" ]]; then
        log "Downloading Python ${PYTHON_VERSION} macOS installer"
        log "URL: ${PYTHON_PKG_URL}"
        download_file "$PYTHON_PKG_URL" "$PYTHON_PKG_PATH"
    else
        log "Using already downloaded package: ${PYTHON_PKG_PATH}"
    fi

    log "Installing Python ${PYTHON_VERSION}; macOS may ask for your password"
    sudo installer -pkg "$PYTHON_PKG_PATH" -target /

    [[ -x "$PYTHON_BIN_DEFAULT" ]] || fail "Python installer finished but executable was not found: ${PYTHON_BIN_DEFAULT}"

    local installed_version
    installed_version="$("$PYTHON_BIN_DEFAULT" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"

    [[ "$installed_version" == "$PYTHON_VERSION" ]] || fail "Expected Python ${PYTHON_VERSION}, got ${installed_version} from ${PYTHON_BIN_DEFAULT}"

    "$PYTHON_BIN_DEFAULT" -c 'import ssl; print(ssl.OPENSSL_VERSION)' >/dev/null 2>&1 || fail "Python SSL module is missing after install."
    "$PYTHON_BIN_DEFAULT" -c 'import tkinter' >/dev/null 2>&1 || fail "Python tkinter module is missing after install."

    log "Python ${PYTHON_VERSION} installed correctly"
}

resolve_python() {
    if [[ -n "${PYTHON_BIN:-}" ]]; then
        printf '%s\n' "$PYTHON_BIN"
        return
    fi

    install_python_pkg

    printf '%s\n' "$PYTHON_BIN_DEFAULT"
}

copy_dir_to_app_resources() {
    local source_dir="$1"
    local app_resources="$2"

    if [[ -d "$source_dir" ]]; then
        log "Copying directory into app resources: ${source_dir}"
        rm -rf "${app_resources}/${source_dir}"
        mkdir -p "${app_resources}"
        cp -R "${source_dir}" "${app_resources}/"
    fi
}

copy_file_to_app_resources() {
    local source_file="$1"
    local app_resources="$2"

    if [[ -f "$source_file" ]]; then
        log "Copying file into app resources: ${source_file}"
        mkdir -p "${app_resources}"
        cp -f "${source_file}" "${app_resources}/"
    fi
}

clean_old_builds_safe() {
    mkdir -p "$BUILD_BASE_DIR"

    log "Keeping previous build folders. Current build dir: ${BUILD_DIR}"

    # Optionnel : supprime les vieux builds de plus de 7 jours.
    find "$BUILD_BASE_DIR" \
        -maxdepth 1 \
        -type d \
        -name "nuitka-macos-arm64-*" \
        -mtime +7 \
        -exec rm -rf {} + 2>/dev/null || true
}

[[ "$(uname -s)" == "Darwin" ]] || fail "This script must run on macOS."
[[ "$(uname -m)" == "arm64" ]] || fail "This script builds the Apple Silicon app. Current arch: $(uname -m)."

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
MACOS_VERSION="$(python Tools/sync_version.py --print-macos-version)"
PACKAGE_VERSION="$(printf '%s' "$APP_VERSION" | tr -c 'A-Za-z0-9._-' '-')"
log "App version: ${APP_VERSION} (system metadata: ${SYSTEM_VERSION}, macOS bundle: ${MACOS_VERSION})"

log "Installing Python dependencies"
python -m pip install --upgrade pip setuptools wheel

if [[ -f requirements.txt ]]; then
    python -m pip install -r requirements.txt
else
    log "requirements.txt not found, skipping"
fi

python -m pip install --no-deps pygame-menu==4.5.2

log "Installing Nuitka from develop branch (same as Windows build)"
python -m pip install --upgrade --force-reinstall "https://github.com/Nuitka/Nuitka/archive/develop.zip"

# Required by Nuitka to convert PNG icon.png to native macOS icon format.
python -m pip install imageio pillow

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
[[ -f icon.png ]] && ICON_ARGS+=(--macos-app-icon=icon.png)

log "Building macOS Apple Silicon app bundle with Nuitka"

clean_old_builds_safe
mkdir -p "$BUILD_DIR"

python -m nuitka \
    --standalone \
    --macos-create-app-bundle \
    --assume-yes-for-downloads \
    --remove-output \
    --enable-plugin=tk-inter \
    --include-package-data=pygame_menu \
    --include-package-data=pygame_gui \
    --output-dir="$BUILD_DIR" \
    --product-name="$APP_NAME" \
    --product-version="$SYSTEM_VERSION" \
    --file-version="$SYSTEM_VERSION" \
    --macos-app-version="$MACOS_VERSION" \
    "${ICON_ARGS[@]}" \
    "${DATA_ARGS[@]}" \
    LinSoTracker.py

APP_PATH="$(find "$BUILD_DIR" -maxdepth 4 -name "${APP_NAME}.app" -type d | head -n 1)"
[[ -n "$APP_PATH" ]] || fail "Could not find ${APP_NAME}.app in ${BUILD_DIR}"

APP_MACOS_PATH="${APP_PATH}/Contents/MacOS"

log "Forcing project files into app bundle (Contents/MacOS — same dir as binary)"

copy_dir_to_app_resources "templates" "$APP_MACOS_PATH"
copy_dir_to_app_resources "ressources" "$APP_MACOS_PATH"
copy_dir_to_app_resources "resources" "$APP_MACOS_PATH"
copy_dir_to_app_resources "default_saves" "$APP_MACOS_PATH"
copy_dir_to_app_resources "extensions" "$APP_MACOS_PATH"
copy_dir_to_app_resources "plugins" "$APP_MACOS_PATH"
copy_dir_to_app_resources "seeds" "$APP_MACOS_PATH"

copy_file_to_app_resources "tracker.data" "$APP_MACOS_PATH"
copy_file_to_app_resources ".dev" "$APP_MACOS_PATH"
copy_file_to_app_resources "config.ini" "$APP_MACOS_PATH"
copy_file_to_app_resources "settings.ini" "$APP_MACOS_PATH"
copy_file_to_app_resources "settings.json" "$APP_MACOS_PATH"

log "App MacOS dir content:"
find "$APP_MACOS_PATH" -maxdepth 2 -print >&2 || true

PACKAGE_NAME="${APP_NAME}-${PACKAGE_VERSION}-macos-arm64"
OUTPUT_PATH="${DIST_DIR}/${PACKAGE_NAME}"

log "Packaging ${PACKAGE_NAME}"

rm -rf "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH"

cp -R "$APP_PATH" "$OUTPUT_PATH/"

(
    cd "$DIST_DIR"
    rm -f "${PACKAGE_NAME}.zip"
    zip -qr "${PACKAGE_NAME}.zip" "$PACKAGE_NAME"
)

log "Done: ${DIST_DIR}/${PACKAGE_NAME}.zip"
log "App: ${OUTPUT_PATH}/${APP_NAME}.app"
