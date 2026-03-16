#!/usr/bin/env bash
# Apply secrets from a secrets.env file to persistent locations.
# Usage: apply-secrets.sh [secrets-file]
set -euo pipefail
SECRETS_FILE="${1:-secrets.env}"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "ERROR: $SECRETS_FILE not found" >&2
    exit 1
fi

set -a
# shellcheck source=/dev/null
source "$SECRETS_FILE"
set +a

if [ -n "${HF_TOKEN:-}" ]; then
    mkdir -p "${HF_HOME:-/workspace/hf_cache}" ~/.cache/huggingface
    echo "$HF_TOKEN" > ~/.cache/huggingface/token
    echo "HF token written."
fi

if [ -n "${WANDB_API_KEY:-}" ]; then
    wandb login "$WANDB_API_KEY" --relogin
    echo "W&B login complete."
fi

rm -f "$SECRETS_FILE"
echo "Secrets applied and temp file removed."
