# runpod-cli

A command-line tool for managing RunPod infrastructure — pods, templates, and network volumes. Available as both `runpod-cli` and the shorter `rp` alias.

## Installation

```bash
uv tool install .
```

Or run directly without installing:

```bash
uv run rp --help
```

## Configuration

### API Key

Set your RunPod API key in a `.env` file or as an environment variable:

```bash
# .env
RUNPOD_API_KEY=your_api_key_here
```

```bash
export RUNPOD_API_KEY=your_api_key_here
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```
RUNPOD_API_KEY=              # Required — RunPod API key
SSH_KEY=~/.ssh/id_ed25519    # Path to SSH private key for pod access
GIT_SSH_KEY=~/.ssh/github    # Path to GitHub SSH private key
GIT_BRANCH=main              # Branch to check out on pod startup
NETWORK_VOLUME_ID=abc123     # RunPod Network Volume ID (optional)
```

Any field on a pod or template config model can also be overridden via `.env` using SCREAMING_SNAKE_CASE. For example, `CONTAINER_DISK_IN_GB=50` overrides the disk size regardless of what's in the YAML.

---

## CLI Reference

Global options apply to all commands:

```
-o, --output [json|yaml]    Output format (default: yaml)
```

---

### `rp pod`

Manage RunPod pods.

#### `rp pod list`

List all pods with their status and cost.

```bash
rp pod list
```

```
id           name            image                  status    cost/hr
─────────────────────────────────────────────────────────────────────
abc123def    bdd-dev         my-org/my-image:latest  RUNNING   $0.74
xyz789ghi    bdd-prune-7b    my-org/my-image:latest  EXITED    $0.00
```

#### `rp pod get <pod_id>`

Get full details for a specific pod.

```bash
rp pod get abc123def
rp pod get abc123def -o json
```

#### `rp pod create <yaml_file>`

Create a pod from a YAML config file.

```bash
rp pod create config/pods/dev.yaml
rp pod create config/pods/prune-7b.yaml --dry-run   # preview API payload
```

Example pod config (`config/pods/dev.yaml`):

```yaml
name: bdd-dev
templateName: bdd-dev          # resolves to templateId automatically
gpuTypeIds:
  - "NVIDIA GeForce RTX 4090"
containerDiskInGb: 20
env:
  UV_EXTRAS: "--all-extras"
```

Fields not specified inherit from the template. `templateName` is resolved to a `templateId` via the API automatically.

#### `rp pod start <pod_id>`

Start a stopped pod.

```bash
rp pod start abc123def
```

#### `rp pod stop <pod_id>`

Stop a running pod (preserves disk).

```bash
rp pod stop abc123def
```

#### `rp pod restart <pod_id>`

Restart a running pod.

```bash
rp pod restart abc123def
```

#### `rp pod delete <pod_id>`

Delete a pod permanently.

```bash
rp pod delete abc123def          # prompts for confirmation
rp pod delete abc123def --yes    # skip confirmation
```

#### `rp pod id <pod_name>`

Print the ID of the first pod matching a name. Useful in shell scripts.

```bash
rp pod id bdd-dev
# abc123def

POD_ID=$(rp pod id bdd-dev)
```

#### `rp pod ssh-cmd <pod_id>`

Print the full SSH command for a pod without executing it. Useful for shell pipelines or copying.

```bash
rp pod ssh-cmd abc123def
# ssh -p 22345 root@123.45.67.89 -i ~/.ssh/id_ed25519

rp pod ssh-cmd abc123def --identity ~/.ssh/custom_key
```

The `--identity` / `-i` flag selects the SSH key. Falls back to the `SSH_KEY` environment variable.

#### `rp pod ssh <pod_id>`

Open an interactive SSH session to a pod.

```bash
rp pod ssh abc123def
rp pod ssh abc123def -i ~/.ssh/custom_key
```

---

### `rp template`

Manage RunPod pod templates.

#### `rp template list`

List all templates.

```bash
rp template list
```

```
id           name            image                  disk(GB)  volume(GB)  runtime(min)
──────────────────────────────────────────────────────────────────────────────────────
tmpl_abc     bdd-dev         my-org/my-image:latest  20        250         0
tmpl_xyz     bdd-prune-7b    my-org/my-image:latest  30        250         0
```

#### `rp template get <template_id>`

Get full details for a specific template.

```bash
rp template get tmpl_abc
```

#### `rp template create <yaml_file>`

Create a template from a YAML config file.

```bash
rp template create config/templates/dev.yaml
rp template create config/templates/dev.yaml --dry-run
```

Example template config (`config/templates/dev.yaml`):

```yaml
name: bdd-dev
containerDiskInGb: 20
env:
  UV_EXTRAS: "--all-extras"
```

Default values (from the model) that don't need to be specified:

- `imageName`: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- `volumeInGb`: 250
- `ports`: `["22/tcp"]`
- `HF_HOME`: `/workspace/hf_cache`

#### `rp template update <template_id> <yaml_file>`

Update an existing template.

```bash
rp template update tmpl_abc config/templates/dev.yaml
```

#### `rp template apply <yaml_file>`

Idempotent create-or-update by template name. Creates if no template with that name exists; updates the existing one if it does. Safe to run repeatedly.

```bash
rp template apply config/templates/dev.yaml
rp template apply config/templates/prune-7b.yaml
```

#### `rp template delete <template_id>`

Delete a template.

```bash
rp template delete tmpl_abc
rp template delete tmpl_abc --yes
```

---

### `rp volume`

Inspect RunPod network volumes.

#### `rp volume list`

List all network volumes.

```bash
rp volume list
```

```
id          name         datacenter    size(GB)
────────────────────────────────────────────────
vol_abc123  workspace    US-TX-3       500
```

#### `rp volume get <volume_id>`

Get details for a specific network volume.

```bash
rp volume get vol_abc123
```

---

## Pod Config Reference

All fields in a pod YAML config:

```yaml
name: my-pod                      # Pod display name
computeType: GPU                  # GPU or CPU (default: GPU)
cloudType: SECURE                 # SECURE or COMMUNITY

# GPU selection
gpuTypeIds:
  - "NVIDIA GeForce RTX 4090"
  - "NVIDIA RTX A6000"            # fallback GPU types
gpuCount: 1                       # number of GPUs

# Image
imageName: my-org/my-image:latest
templateName: my-template         # resolves templateId automatically (alternative to templateId)
templateId: tmpl_abc123           # explicit template ID

# Storage
containerDiskInGb: 30
volumeInGb: 250
volumeMountPath: /workspace
networkVolumeId: vol_abc123

# Networking
ports:
  - "22/tcp"
  - "8888/http"

# Environment
env:
  MY_VAR: value
  UV_EXTRAS: "--all-extras"

dockerEntrypoint: ["/bin/bash", "-c"]
dockerStartCmd: ["/start.sh"]

# Placement
dataCenterIds:
  - "US-TX-3"
interruptible: false

# Registry auth
containerRegistryAuthId: reg_abc
```

---

## Template Config Reference

```yaml
name: my-template
imageName: runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

containerDiskInGb: 30
volumeInGb: 250

ports:
  - "22/tcp"

env:
  GIT_REPO: git@github.com:my-org/my-repo.git
  GIT_BRANCH: main
  HF_HOME: /workspace/hf_cache
  UV_EXTRAS: "--all-extras"

# Custom startup command (default writes env vars then runs /start.sh)
dockerStartCmd: "bash -c 'source /etc/rp-environment && /start.sh'"
```

---

## Tasks

The `Taskfile.yml` provides higher-level deployment automation built on top of the `rp` CLI. Tasks handle the full lifecycle of spinning up a pod: creating it, waiting for SSH, uploading secrets, and running a boot script.

### Prerequisites

Install [Task](https://taskfile.dev):

```bash
brew install go-task
# or
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
```

### Environment Setup

Tasks read from your `.env` file. Required variables:

```bash
# .env
RUNPOD_API_KEY=your_api_key
SSH_KEY=~/.ssh/id_ed25519        # SSH key for connecting to pods
GIT_SSH_KEY=~/.ssh/github        # GitHub deploy key (uploaded to pod)
```

Optional:

```bash
SECRETS_FILE=secrets.env         # defaults to "secrets.env"
```

Sensitive credentials for the pod itself go in `secrets.env` (gitignored):

```bash
# secrets.env
HF_TOKEN=hf_xxxx
WANDB_API_KEY=xxxx
```

---

### `task deploy`

The main deployment task. Creates a pod from a YAML config, waits for it to be reachable, uploads secrets and SSH keys, and runs the boot script — all in one command.

```bash
task deploy CONFIG=config/pods/dev.yaml
task deploy CONFIG=config/pods/prune-7b.yaml
```

#### What it does, step by step

**1. Create the pod**

Calls `rp pod create` with the specified YAML config. The pod is created on RunPod and begins booting.

```bash
rp pod create config/pods/prune-7b.yaml
```

**2. Resolve the pod ID**

Looks up the pod by name (from the YAML `name` field) to get its ID.

```bash
rp pod id bdd-prune-7b
# → abc123def456
```

**3. Wait for SSH**

Polls the pod's SSH port up to 60 times (5 seconds apart, ~5 minutes total) until the connection is accepted. This handles the delay between pod creation and the container actually being ready.

```bash
# internally runs something like:
ssh -p <port> root@<host> -i $SSH_KEY -o ConnectTimeout=5 exit
```

**4. Upload the GitHub SSH key**

Transfers your GitHub deploy key (`GIT_SSH_KEY`) to the pod via SCP and configures it:

- Copies the key to `~/.ssh/id_ed25519` on the pod
- Sets permissions to `600`
- Adds `github.com` to `~/.ssh/known_hosts`

This allows the pod to clone private repositories during the boot script.

**5. Upload and apply secrets**

Transfers `secrets.env` (or `$SECRETS_FILE`) to the pod via SCP, then runs `apply-secrets.sh` on the pod, which:

- Writes `HF_TOKEN` to `~/.cache/huggingface/token`
- Runs `wandb login` with `WANDB_API_KEY`
- Deletes the secrets file from the pod after applying

Secrets are never left on disk in plaintext.

**6. Run the boot script**

Uploads and executes `scripts/pod-start.sh`, which:

- Sources environment variables written by the RunPod container runtime (`/etc/rp-environment`)
- Clones the repo specified in `GIT_REPO` to `/workspace/` (skips if already present)
- Checks out `GIT_BRANCH`
- Runs `setup.sh` to initialize the Python environment via `uv`
- Installs extras if `UV_EXTRAS` is set (e.g. `--all-extras` or `"train,eval"`)
- Prints GPU info via `nvidia-smi`

**7. Done**

Prints a completion message with the pod ID so you can SSH in:

```
Pod abc123def456 is ready.
```

#### Full example

```bash
# Create a 4x RTX 5090 pod for a pruning experiment
task deploy CONFIG=config/pods/prune-7b.yaml

# Once deployed, SSH in
rp pod ssh $(rp pod id bdd-prune-7b)
```

---

### `task pod:send-git-key`

Upload a GitHub SSH key to an already-running pod. Useful if you need to re-push credentials or set up a second pod manually.

```bash
task pod:send-git-key POD_ID=abc123def456
```

Reads `SSH_KEY` and `GIT_SSH_KEY` from `.env`.

---

### `task pod:send-secrets`

Upload and apply `secrets.env` to a running pod.

```bash
task pod:send-secrets POD_ID=abc123def456
task pod:send-secrets POD_ID=abc123def456 SECRETS_FILE=my-secrets.env
```

---

### `task pod:setup`

Run the boot script on an already-running pod. Use this to re-run setup after a pod restart, or to set up a pod that was created manually.

```bash
task pod:setup POD_ID=abc123def456 SETUP_SCRIPT_PATH=scripts/my-setup.sh
```

---

### Typical workflows

**Fresh deployment:**

```bash
task deploy CONFIG=config/pods/dev.yaml
```

**Re-run setup after pod restart:**

```bash
POD_ID=$(rp pod id bdd-dev)
task pod:setup POD_ID=$POD_ID SETUP_SCRIPT_PATH=scripts/pod-start.sh
```

**Refresh secrets on a running pod:**

```bash
task pod:send-secrets POD_ID=$(rp pod id bdd-dev)
```

**Tear down when done:**

```bash
rp pod delete $(rp pod id bdd-dev) --yes
```
