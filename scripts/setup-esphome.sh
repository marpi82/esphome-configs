#!/usr/bin/env bash
# Idempotent development-environment bootstrap for the esphome-configs repo.
# Installs the pinned ESPHome toolchain and prepares a local secrets file so
# that `esphome config devices/*.yaml` can validate the configurations.
set -euo pipefail

# Keep in sync with .github/workflows/validate.yml; Renovate updates both.
# renovate: datasource=pypi depName=esphome versioning=pep440
ESPHOME_VERSION="2026.8.2"
VENV_DIR="${HOME}/.esphome-venv"

# ESPHome 2026.x supports Python >=3.12,<3.15. Pick the newest already-installed
# interpreter in that range, preferring an explicitly versioned executable.
find_python() {
  local candidate
  for candidate in python3.14 python3.13 python3.12 python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 12) <= sys.version_info[:2] < (3, 15) else 1)
PY
    then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [ -z "${PYTHON}" ]; then
  echo "ERROR: ESPHome ${ESPHOME_VERSION} needs Python >=3.12,<3.15, but no matching" >&2
  echo "       interpreter was found on PATH. Install Python 3.12-3.14 and retry." >&2
  exit 1
fi
echo "Using $("${PYTHON}" --version) at ${PYTHON}"

# Create the virtualenv, installing distro venv/ensurepip support only if the
# first attempt fails (common on Debian/Ubuntu, where it ships separately).
create_venv() { "${PYTHON}" -m venv "${VENV_DIR}" >/dev/null 2>&1; }

if [ ! -x "${VENV_DIR}/bin/python" ] && ! create_venv; then
  if command -v sudo >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1; then
    pyver="$("${PYTHON}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "python${pyver}-venv" || sudo apt-get install -y -qq python3-venv
    rm -rf "${VENV_DIR}"
    create_venv || true
  fi
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  echo "ERROR: could not create a virtualenv at ${VENV_DIR}. Ensure the 'venv' and" >&2
  echo "       'ensurepip' modules are available for ${PYTHON} (e.g. the python*-venv" >&2
  echo "       package on Debian/Ubuntu)." >&2
  exit 1
fi

"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet "esphome==${ESPHOME_VERSION}"

# Expose `esphome` on PATH for interactive use (best-effort).
if command -v sudo >/dev/null 2>&1; then
  sudo ln -sf "${VENV_DIR}/bin/esphome" /usr/local/bin/esphome
else
  ln -sf "${VENV_DIR}/bin/esphome" /usr/local/bin/esphome 2>/dev/null || true
fi

# ESPHome resolves `!secret` relative to each config file's directory, so the
# secrets file lives next to the device configs. It is gitignored (the bare
# `secrets.yaml` pattern in .gitignore matches at any depth); real deployments
# must replace the placeholder values with strong credentials.
if [ ! -f devices/secrets.yaml ]; then
  cp secrets.yaml.example devices/secrets.yaml
fi

echo "ESPHome $("${VENV_DIR}/bin/esphome" version | awk '{print $2}') ready."
