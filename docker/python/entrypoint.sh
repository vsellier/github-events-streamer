#!/usr/bin/env bash
set -eu
load_requirements() {
  echo "Loading requirements in $(pwd)..."
  if [ -e "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    echo "No requirements file found"
  fi

}
source "${HOME}/python/bin/activate"

BASE_DIR="$(pwd)"

cd "${SCRIPT_DIRECTORY}"

# load_requirements
load_requirements

python "${SCRIPT_NAME}" "${BASE_DIR}/${GLOBAL_CONFIG_FILE}" ${PARAMS:-}
