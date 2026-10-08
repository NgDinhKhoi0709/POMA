#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the POMA research pipeline.
# Safe to run repeatedly: it only installs missing pieces.
set -euo pipefail

cd "$(dirname "$0")/.."

PWSH_VERSION="7.4.6"

echo "==> Installing POMA Python dependencies"
python3 -m pip install --upgrade pip

# Core pipeline + evaluation + test dependencies.
python3 -m pip install \
  openai \
  requests \
  beautifulsoup4 \
  python-dotenv \
  tqdm \
  jsonschema \
  pyvi \
  nltk \
  pytest

# Vendored baseline systems (chain_of_query, coagt, ...).
python3 -m pip install -r baselines/requirements.txt

# PowerShell Core provides the `powershell` binary used by the Q2 experiment
# runbook (scripts/run_q2_experiments.ps1) and its pytest coverage.
if ! command -v pwsh >/dev/null 2>&1; then
  echo "==> Installing PowerShell ${PWSH_VERSION}"
  tmp_tar="$(mktemp)"
  curl -fsSL -o "${tmp_tar}" \
    "https://github.com/PowerShell/PowerShell/releases/download/v${PWSH_VERSION}/powershell-${PWSH_VERSION}-linux-x64.tar.gz"
  sudo mkdir -p /opt/microsoft/powershell/7
  sudo tar zxf "${tmp_tar}" -C /opt/microsoft/powershell/7
  sudo chmod +x /opt/microsoft/powershell/7/pwsh
  sudo ln -sf /opt/microsoft/powershell/7/pwsh /usr/local/bin/pwsh
  sudo ln -sf /opt/microsoft/powershell/7/pwsh /usr/local/bin/powershell
  rm -f "${tmp_tar}"
else
  echo "==> PowerShell already present: $(pwsh --version)"
fi

echo "==> POMA environment ready"
