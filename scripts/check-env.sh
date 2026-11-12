#!/usr/bin/env bash
# Confere o .env da raiz sem imprimir segredos.  Uso (da raiz do repo):  bash scripts/check-env.sh
# Requer: cast (Foundry) e curl.
set -u
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "❌ .env não encontrado na raiz (cp .env.example .env)"; exit 1; }
set -a; source <(tr -d '\r' < .env); set +a
command -v cast >/dev/null || export PATH="$HOME/.foundry/bin:$PATH"

ok=0; bad=0; warn=0
pass() { echo "✅ $1"; ok=$((ok+1)); }
fail() { echo "❌ $1"; bad=$((bad+1)); }
note() { echo "⚠️  $1"; warn=$((warn+1)); }
chain_of() { cast chain-id --rpc-url "$1" 2>/dev/null; }

echo "== Blockchain (Davi) =="
if [ -z "${SEPOLIA_RPC_URL:-}" ]; then fail "SEPOLIA_RPC_URL vazio"
else
  id=$(chain_of "$SEPOLIA_RPC_URL")
  [ "$id" = "11155111" ] && pass "SEPOLIA_RPC_URL responde (Sepolia)" || fail "SEPOLIA_RPC_URL não é Sepolia ou não responde (chain: ${id:-sem resposta})"
fi

if [ -z "${MAINNET_RPC_URL:-}" ]; then note "MAINNET_RPC_URL vazio (simulação usa fixtures)"
else
  id=$(chain_of "$MAINNET_RPC_URL")
  [ "$id" = "1" ] && pass "MAINNET_RPC_URL responde (mainnet)" || fail "MAINNET_RPC_URL não é mainnet ou não responde (chain: ${id:-sem resposta})"
fi

ATT=""
if [ -z "${ATTESTER_PRIVATE_KEY:-}" ]; then note "ATTESTER_PRIVATE_KEY vazio (/attest fica em modo mock)"
elif [[ ! "$ATTESTER_PRIVATE_KEY" =~ ^0x[0-9a-fA-F]{64}$ ]]; then fail "ATTESTER_PRIVATE_KEY mal formatada (precisa de 0x + 64 hex)"
else
  ATT=$(cast wallet address --private-key "$ATTESTER_PRIVATE_KEY")
  pass "ATTESTER_PRIVATE_KEY válida → carteira $ATT"
  if [ -n "${SEPOLIA_RPC_URL:-}" ]; then
    bal=$(cast balance "$ATT" --rpc-url "$SEPOLIA_RPC_URL" --ether 2>/dev/null)
    [ -n "$bal" ] && [ "$bal" != "0.000000000000000000" ] && pass "saldo na Sepolia: $bal ETH" || fail "carteira sem saldo na Sepolia (${bal:-erro})"
  fi
fi

if [ -n "${ATTESTER_ADDRESS:-}" ] && [ -n "$ATT" ] && [ "${ATTESTER_ADDRESS,,}" != "${ATT,,}" ]; then
  note "ATTESTER_ADDRESS ($ATTESTER_ADDRESS) difere da carteira da chave — só é usado no deploy"
fi

if [ -z "${REGISTRY_ADDRESS:-}" ]; then note "REGISTRY_ADDRESS vazio (/attest fica em modo mock)"
elif [ -n "${SEPOLIA_RPC_URL:-}" ]; then
  code=$(cast code "$REGISTRY_ADDRESS" --rpc-url "$SEPOLIA_RPC_URL" 2>/dev/null)
  if [ -z "$code" ] || [ "$code" = "0x" ]; then fail "REGISTRY_ADDRESS sem contrato na Sepolia"
  else
    pass "REGISTRY_ADDRESS tem contrato"
    if [ -n "$ATT" ]; then
      is=$(cast call "$REGISTRY_ADDRESS" 'isAttester(address)(bool)' "$ATT" --rpc-url "$SEPOLIA_RPC_URL" 2>/dev/null)
      [ "$is" = "true" ] && pass "carteira é attester no contrato" || fail "carteira NÃO é attester no contrato (/attest vai reverter)"
    fi
  fi
fi

if [ -z "${ETHERSCAN_API_KEY:-}" ]; then note "ETHERSCAN_API_KEY vazio (idade/verificação do contrato vêm das fixtures)"
else
  r=$(curl -s --ssl-no-revoke "https://api.etherscan.io/v2/api?chainid=1&module=proxy&action=eth_blockNumber&apikey=$ETHERSCAN_API_KEY")
  [[ "$r" == *'"result":"0x'* ]] && pass "ETHERSCAN_API_KEY aceita" || fail "ETHERSCAN_API_KEY recusada"
fi

echo; echo "== LLM (Rafael) =="
if [ -z "${OPENROUTER_API_KEY:-}" ]; then note "OPENROUTER_API_KEY vazio (explicações sem LLM, só regras)"
else
  code=$(curl -s --ssl-no-revoke -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $OPENROUTER_API_KEY" "${LLM_BASE_URL:-https://openrouter.ai/api/v1}/key")
  [ "$code" = "200" ] && pass "OPENROUTER_API_KEY aceita" || fail "OPENROUTER_API_KEY recusada (HTTP $code)"
fi

echo; echo "== Modo =="
case "${OFFLINE:-0}" in
  0) pass "OFFLINE=0 (usa RPC/LLM/Etherscan reais)";;
  1) note "OFFLINE=1 (tudo por fixtures — bom para ensaio sem internet)";;
  *) fail "OFFLINE deve ser 0 ou 1";;
esac

echo; echo "Resumo: $ok ok, $warn avisos, $bad erros"
[ "$bad" -eq 0 ]
