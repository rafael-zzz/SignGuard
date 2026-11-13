#!/usr/bin/env bash
# RPC de origem separado do MAINNET_RPC_URL usado pela API (fork local).
set -euo pipefail
if ! command -v anvil >/dev/null 2>&1; then
  echo 'Anvil não encontrado. Instale Foundry: https://getfoundry.sh/introduction/installation' >&2
  exit 1
fi
: "${FORK_RPC_URL:?Defina FORK_RPC_URL com o RPC mainnet de origem}"
args=(--silent --fork-url "$FORK_RPC_URL" --host 127.0.0.1 --port "${ANVIL_PORT:-8545}" --chain-id 1)
if [[ -n "${FORK_BLOCK_NUMBER:-}" ]]; then
  args+=(--fork-block-number "$FORK_BLOCK_NUMBER")
fi
exec anvil "${args[@]}"
