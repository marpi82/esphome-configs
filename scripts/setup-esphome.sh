#!/usr/bin/env bash
# Idempotent development-environment bootstrap for the esphome-configs repo.
# Installs the pinned ESPHome toolchain and prepares a local secrets file so
# that `esphome config devices/*.yaml` can validate the configurations.
set -euo pipefail

ESPHOME_VERSION="2024.12.4"
VENV_DIR="${HOME}/.esphome-venv"

# python venv support is not part of the base image on some distros.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq "python3-venv" || \
    sudo apt-get install -y -qq "python3.12-venv"
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet "esphome==${ESPHOME_VERSION}"

# Expose `esphome` on PATH for interactive use.
sudo ln -sf "${VENV_DIR}/bin/esphome" /usr/local/bin/esphome

# ESPHome resolves `!secret` relative to each config file's directory, so the
# secrets file lives next to the device configs. It is gitignored; real
# deployments must replace the placeholder values with strong credentials.
if [ ! -f devices/secrets.yaml ]; then
  cp secrets.yaml.example devices/secrets.yaml
fi

echo "ESPHome $("${VENV_DIR}/bin/esphome" version | awk '{print $2}') ready."
