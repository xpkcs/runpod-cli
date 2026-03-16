#!/usr/bin/env bash
# Boot script for RunPod pods. Idempotent — safe to re-run.
#
# Environment variables (set via pod env, .env, or passed by the Taskfile):
#   GIT_REPO           — SSH URL of the repository
#   GIT_BRANCH         — branch to check out (default: main)
#   UV_EXTRAS          — comma-separated uv extras to install (e.g. "prune,wandb")
#   SETUP_SCRIPT_PATH  — (optional) path to a user setup script sourced at the end
#   EXPORTS_PATH       — (optional) path to extra shell exports appended to /workspace/.exports
set -euo pipefail

# ── Source Docker env vars ───────────────────────────────────────────────────
# sshd does not reliably expose Docker env vars to SSH sessions;
# dockerStartCmd writes them to /etc/rp-environment at startup.
set -a
# shellcheck source=/dev/null
source /etc/rp-environment 2>/dev/null || source /etc/environment 2>/dev/null || true
set +a

# ── Platform detection ───────────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Linux)  ;;
    Darwin) ;;
    *)
        echo "Unsupported platform: $OS" >&2
        exit 1
        ;;
esac

# ── Paths: prefer /workspace (RunPod network volume) over $HOME ─────────────
if [ -d "/workspace" ]; then
    TOOLS_DIR="/workspace/tools"
else
    TOOLS_DIR="$HOME/.local"
fi
BIN_DIR="$TOOLS_DIR/bin"
NVM_DIR="$TOOLS_DIR/nvm"
NODE_GLOBAL_DIR="$TOOLS_DIR/node_global"
export NVM_DIR
mkdir -p "$BIN_DIR" "$NODE_GLOBAL_DIR/bin"

export PATH="$BIN_DIR:$NODE_GLOBAL_DIR/bin:$PATH"

# Load nvm if already installed
# shellcheck source=/dev/null
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

# ── uv ───────────────────────────────────────────────────────────────────────
if [ ! -x "$BIN_DIR/uv" ]; then
    echo "Installing uv to persistent storage..."
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$BIN_DIR" sh
fi
if [ -d "/workspace" ]; then
    export UV_CACHE_DIR="/workspace/.uv-cache"
    export UV_LINK_MODE=copy
fi

# ── yq ───────────────────────────────────────────────────────────────────────
if ! command -v yq &>/dev/null; then
    echo "Installing yq..."
    case "$OS" in
        Darwin)
            brew install yq
            ;;
        Linux)
            wget --quiet --show-progress \
                "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64" \
                -O "$BIN_DIR/yq" \
                && chmod +x "$BIN_DIR/yq"
            ;;
    esac
fi

# ── Node.js / npm ────────────────────────────────────────────────────────────
if ! command -v npm &>/dev/null; then
    echo "Installing Node.js (via nvm)..."
    export npm_config_tar="tar --no-same-owner"
    NVM_VERSION=$(curl -fsSL https://api.github.com/repos/nvm-sh/nvm/releases/latest \
        | grep '"tag_name"' | cut -d'"' -f4)
    curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" \
        | PROFILE=/dev/null bash
    # shellcheck source=/dev/null
    [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
    nvm install --lts
    npm install -g --prefix "$NODE_GLOBAL_DIR" npm@latest
fi

# ── Claude Code ──────────────────────────────────────────────────────────────
if ! command -v claude &>/dev/null; then
    echo "Installing Claude Code..."
    npm install -g --prefix "$NODE_GLOBAL_DIR" @anthropic-ai/claude-code
fi

# ── Shell profile: persistent exports ────────────────────────────────────────
SHELL_PROFILE="${HOME}/.bashrc"
[ -n "${ZSH_VERSION:-}" ] && SHELL_PROFILE="${HOME}/.zshrc"

if [ -d "/workspace" ]; then
    cat > /workspace/.exports <<'EXPORTS'
export PATH="/workspace/tools/node_global/bin:/workspace/tools/bin:$PATH"
export NVM_DIR="/workspace/tools/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
EXPORTS

    if [ -n "${EXPORTS_PATH:-}" ] && [ -f "$EXPORTS_PATH" ]; then
        echo "" >> /workspace/.exports
        cat "$EXPORTS_PATH" >> /workspace/.exports
    fi

    if ! grep -qF '/workspace/.exports' "$SHELL_PROFILE" 2>/dev/null; then
        echo '[ -f /workspace/.exports ] && . /workspace/.exports' >> "$SHELL_PROFILE"
    fi

    if [ -f "$HOME/.profile" ]; then
        if ! grep -qF '/workspace/.exports' "$HOME/.profile" 2>/dev/null; then
            echo '[ -f /workspace/.exports ] && . /workspace/.exports' >> "$HOME/.profile"
        fi
    fi
else
    add_line() {
        local marker="$1" line="$2"
        grep -qF "$marker" "$SHELL_PROFILE" 2>/dev/null || echo "$line" >> "$SHELL_PROFILE"
    }
    add_line "$BIN_DIR"         "export PATH=\"$BIN_DIR:\$PATH\""
    add_line "$NODE_GLOBAL_DIR" "export PATH=\"$NODE_GLOBAL_DIR/bin:\$PATH\""
    add_line "NVM_DIR"          "export NVM_DIR=\"$NVM_DIR\""
    add_line "nvm.sh"           "[ -s \"\$NVM_DIR/nvm.sh\" ] && source \"\$NVM_DIR/nvm.sh\""

    if [ -n "${EXPORTS_PATH:-}" ] && [ -f "$EXPORTS_PATH" ]; then
        while IFS= read -r line; do
            grep -qF "$line" "$SHELL_PROFILE" 2>/dev/null || echo "$line" >> "$SHELL_PROFILE"
        done < "$EXPORTS_PATH"
    fi
fi

# ── Clone repo (skip if already present) ─────────────────────────────────────
GIT_BRANCH="${GIT_BRANCH:-main}"
UV_EXTRAS="${UV_EXTRAS:-}"
REPO_DIR="/workspace/$(basename "${GIT_REPO:?GIT_REPO must be set}" .git)"

echo "=== RunPod boot ==="
echo "Repo:    $GIT_REPO"
echo "Branch:  $GIT_BRANCH"

if [ -d "$REPO_DIR/.git" ]; then
    echo "Repo already present at $REPO_DIR, skipping clone."
else
    echo "Cloning repo..."
    git clone --branch "$GIT_BRANCH" "$GIT_REPO" "$REPO_DIR"
fi

cd "$REPO_DIR"

# ── Install project deps / extras ────────────────────────────────────────────
if [ -n "$UV_EXTRAS" ]; then
    echo "Installing extras: $UV_EXTRAS"
    if [ "$UV_EXTRAS" = "--all-extras" ]; then
        uv sync --all-extras
    else
        EXTRA_FLAGS=""
        IFS=',' read -ra EXTRAS <<< "$UV_EXTRAS"
        for extra in "${EXTRAS[@]}"; do
            EXTRA_FLAGS="$EXTRA_FLAGS --extra ${extra// /}"
        done
        # shellcheck disable=SC2086
        uv sync $EXTRA_FLAGS
    fi
fi

# ── User setup script ────────────────────────────────────────────────────────
if [ -n "${SETUP_SCRIPT_PATH:-}" ] && [ -f "$SETUP_SCRIPT_PATH" ]; then
    echo "Running user setup script: $SETUP_SCRIPT_PATH"
    # shellcheck source=/dev/null
    source "$SETUP_SCRIPT_PATH"
fi

# ── GPU info ─────────────────────────────────────────────────────────────────
echo ""
echo "=== GPU info ==="
nvidia-smi 2>/dev/null || echo "(no GPU detected)"

echo ""
echo "=== Boot complete ==="
